# -*- coding: utf-8 -*-
"""industry_rs.py — 全部行業嘅 RS 分數 + 5 日變化（解決「group move」盲區）

Desmond 2026-10-25：「把群組 RS 由頭 13 擴到全部行業；另外要知有冇 move」

做法（第一性原理：唔用黑箱）
  1. 分母 = market_scan.json 嘅 universe（430 隻，有 industry + perf 1w/1m/3m）
  2. 每個行業（≥3 隻成員）取成員 1M / 3M 回報嘅 **中位數**（唔用平均，防單隻爆升扭曲）
  3. RS = 該行業 1M 中位數在所有行業之中嘅 **百分位 0–100**
  4. 5 日變化 = 今日 RS − 5 個交易日前（用 data/market_scan_YYYY-MM-DD.json 舊檔重算）
  5. 同時計 1W 中位數（短線動能）同成員數

輸出：output/industry_rs_YYYY-MM-DD.json
  {"date": "...", "rows": [{industry, n, rs, rs_5d_ago, delta, med1m, med1w, med3m}]}

用法：python industry_rs.py
"""
from __future__ import annotations

import glob
import io
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCANS = os.path.join(HERE, "data", "market_scan_*.json")
OUT = os.path.join(HERE, "output")
MIN_N = 3


def log(m):
    print(m, file=sys.stderr)


def _med(xs):
    xs = sorted(x for x in xs if isinstance(x, (int, float)))
    if not xs:
        return None
    k = len(xs) // 2
    return xs[k] if len(xs) % 2 else (xs[k - 1] + xs[k]) / 2.0


def _aggs(path):
    """回傳 {industry: {n, med1m, med1w, med3m}}"""
    try:
        d = json.load(io.open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    rows = d.get("universe") or []
    buckets = {}
    for r in rows:
        ind = (r.get("industry") or "").strip()
        if not ind:
            continue
        p = r.get("perf") or {}
        buckets.setdefault(ind, []).append(p)
    out = {}
    for ind, ps in buckets.items():
        if len(ps) < MIN_N:
            continue
        out[ind] = {
            "n": len(ps),
            "med1m": _med([p.get("1m") for p in ps]),
            "med1w": _med([p.get("1w") for p in ps]),
            "med3m": _med([p.get("3m") for p in ps]),
        }
    return out


def _percentile(aggs):
    """1M 中位數 → 百分位 0–100"""
    items = [(k, v["med1m"]) for k, v in aggs.items()
             if isinstance(v.get("med1m"), (int, float))]
    items.sort(key=lambda x: x[1])
    n = len(items)
    out = {}
    for i, (k, _) in enumerate(items):
        out[k] = round(100.0 * i / max(n - 1, 1), 1)
    return out


def main():
    files = sorted(glob.glob(SCANS))
    if not files:
        log("✗ 冇 market_scan_*.json")
        return 1
    latest = os.path.join(HERE, "data", "market_scan.json")
    if not os.path.exists(latest) or os.path.getmtime(latest) < os.path.getmtime(files[-1]):
        latest = files[-1]

    today = _aggs(latest)
    if not today:
        log("✗ 今日冇行業資料")
        return 1
    pct_now = _percentile(today)

    # 5 個交易日前
    hist = [f for f in files if os.path.abspath(f) != os.path.abspath(latest)]
    old = hist[-5] if len(hist) >= 5 else (hist[0] if hist else None)
    pct_old = _percentile(_aggs(old)) if old else {}

    rows = []
    for ind, v in today.items():
        rs = pct_now.get(ind)
        r5 = pct_old.get(ind)
        rows.append({
            "industry": ind, "n": v["n"], "rs": rs,
            "rs_5d_ago": r5,
            "delta": round(rs - r5, 1) if (rs is not None and r5 is not None) else None,
            "med1m": v["med1m"], "med1w": v["med1w"], "med3m": v["med3m"],
        })
    rows.sort(key=lambda r: -(r["rs"] or 0))

    os.makedirs(OUT, exist_ok=True)
    payload = {
        "date": date.today().isoformat(),
        "as_of": os.path.basename(latest),
        "base": os.path.basename(old) if old else None,
        "n_industries": len(rows),
        "rows": rows,
    }
    dst = os.path.join(OUT, f"industry_rs_{payload['date']}.json")
    json.dump(payload, io.open(dst, "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    log(f"✓ {dst}｜{len(rows)} 個行業｜基準 {payload['base']}")
    top = rows[:5]
    log("  最強：" + "、".join(f"{r['industry']}({r['rs']:.0f}"
                              f"{'+' if (r['delta'] or 0) > 0 else ''}"
                              f"{r['delta'] if r['delta'] is not None else '—'})"
                              for r in top))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
