# -*- coding: utf-8 -*-
"""tight_scan.py — 全市場 Tight Range 掃描（S&P 500 ∪ Nasdaq 100 ∪ L2）

為咩要（Desmond 2026-10-27）：
  原本 scan 只覆蓋 L2 focus/stalk（~74 隻），所以 PLTR／CRM／NVDA 呢類
  「唔在 L2 但圖好靚」嘅股永遠唔會出現。

宇宙：S&P 500 + Nasdaq 100 + L2（去重，約 600 隻），每週更新名單。
指標：TIGHT（10 日箱體 ÷ ATR50）、連續 inside day、距 40MA、距 52 週高、ATR%、EXT。
篩選：價 ≥ $5、成交額 ≥ $8M、TIGHT ≥ 60（唔夠緊唔出）。
輸出：output/tight_scan.json + data/universe_wide.json（名單快取）

用法：python tight_scan.py [--refresh-universe]
"""
from __future__ import annotations

import glob
import io
import json
import os
import pickle
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
UNIV = os.path.join(HERE, "data", "universe_wide.json")
CACHE = os.path.join(HERE, "data", "tight_prices.pkl")
MIN_PRICE = 5.0
MIN_DOLLAR = 8e6
MIN_TIGHT = 60.0


def log(m):
    print(m, file=sys.stderr)


def wide_universe(refresh=False):
    """S&P 500 ∪ Nasdaq 100 ∪ L2；一週快取。"""
    fresh = (not refresh and os.path.exists(UNIV)
             and (datetime.now() - datetime.fromtimestamp(os.path.getmtime(UNIV)))
             < timedelta(days=7))
    if fresh:
        try:
            return json.load(io.open(UNIV, encoding="utf-8"))
        except (OSError, ValueError):
            pass
    tks = set()
    # S&P 500（公開 CSV，Wikipedia 會 403）
    try:
        import csv
        import urllib.request
        u = ("https://raw.githubusercontent.com/datasets/"
             "s-and-p-500-companies/main/data/constituents.csv")
        raw = urllib.request.urlopen(
            urllib.request.Request(u, headers={"User-Agent": "hermes"}),
            timeout=40).read().decode("utf-8", "replace")
        for row in csv.DictReader(io.StringIO(raw)):
            sym = (row.get("Symbol") or "").strip().upper().replace(".", "-")
            if sym:
                tks.add(sym)
        log(f"  S&P 500: {len(tks)} 隻")
    except Exception as e:                                    # noqa: BLE001
        log(f"  ⚠ S&P 500 名單讀唔到：{type(e).__name__}")
    # L2
    for pat in (r"C:/Users/rain0/trading-os/output/layer2_*.json",):
        fs = sorted(glob.glob(pat))
        if fs:
            try:
                d = json.load(io.open(fs[-1], encoding="utf-8"))
                for r in (d.get("focus_list") or []) + (d.get("stalk_list") or []):
                    t = (r.get("ticker") or "").upper()
                    if t:
                        tks.add(t)
            except Exception:                                 # noqa: BLE001
                pass
    tks = sorted(t for t in tks if t and len(t) <= 6)
    if tks:
        json.dump(tks, io.open(UNIV, "w", encoding="utf-8"))
    return tks


def prices(tks, refresh=False):
    fresh = (not refresh and os.path.exists(CACHE)
             and (datetime.now() - datetime.fromtimestamp(os.path.getmtime(CACHE)))
             < timedelta(hours=12))
    if fresh:
        try:
            return pickle.load(io.open(CACHE, "rb"))
        except Exception:                                     # noqa: BLE001
            pass
    import yfinance as yf
    log(f"  yfinance 下載 {len(tks)} 隻…")
    df = yf.download(tks, period="1y", interval="1d", auto_adjust=True,
                     progress=False, threads=True, group_by="ticker")
    data = {}
    for t in tks:
        try:
            sub = df[t].dropna(subset=["Close"])
            if len(sub) < 60:
                continue
            data[t] = [[str(i.date()), float(r["Open"]), float(r["High"]),
                        float(r["Low"]), float(r["Close"]), float(r["Volume"] or 0)]
                       for i, r in sub.iterrows()]
        except Exception:                                     # noqa: BLE001
            continue
    pickle.dump(data, io.open(CACHE, "wb"))
    log(f"  完成 {len(data)} 隻")
    return data


def metrics(bars):
    n = len(bars)
    if n < 60:
        return None
    hi = [b[2] for b in bars]
    lo = [b[3] for b in bars]
    cl = [b[4] for b in bars]
    vol = [b[5] for b in bars]
    trs = [max(hi[i] - lo[i], abs(hi[i] - cl[i - 1]), abs(lo[i] - cl[i - 1]))
           for i in range(1, n)]
    atr50 = sum(trs[-50:]) / 50
    if not atr50:
        return None
    box = max(hi[-10:]) - min(lo[-10:])
    box_atr = box / atr50
    tight = max(0.0, min(100.0, 100.0 * (1 - box_atr / 6.0)))
    ins = 0
    for i in range(n - 1, 0, -1):
        if hi[i] <= hi[i - 1] and lo[i] >= lo[i - 1]:
            ins += 1
        else:
            break
    ma40 = sum(cl[-40:]) / 40
    ma50 = sum(cl[-50:]) / 50
    hi52 = max(cl[-252:]) if n >= 252 else max(cl)
    dollars = cl[-1] * sum(vol[-10:]) / 10
    return dict(close=round(cl[-1], 2), tight=round(tight, 1),
                box_atr=round(box_atr, 2), inside=ins,
                d40=round((cl[-1] / ma40 - 1) * 100, 2),
                ext=round((cl[-1] - ma50) / atr50, 2),
                off52=round((cl[-1] / hi52 - 1) * 100, 2),
                atrp=round(atr50 / cl[-1] * 100, 2),
                dollar_m=round(dollars / 1e6, 1))


def main(argv=None):
    refresh = "--refresh-universe" in (argv or sys.argv[1:])
    tks = wide_universe(refresh)
    if not tks:
        log("✗ 冇宇宙")
        return 1
    px = prices(tks, refresh)
    rows = []
    for t, bars in px.items():
        m = metrics(bars)
        if not m:
            continue
        if m["close"] < MIN_PRICE or m["dollar_m"] * 1e6 < MIN_DOLLAR:
            continue
        if m["tight"] < MIN_TIGHT:
            continue
        rows.append(dict(ticker=t, **m))
    rows.sort(key=lambda r: -r["tight"])
    os.makedirs(OUT, exist_ok=True)
    payload = {"date": date.today().isoformat(),
               "universe": len(px), "hits": len(rows),
               "min_tight": MIN_TIGHT, "rows": rows[:120]}
    json.dump(payload, io.open(os.path.join(OUT, "tight_scan.json"), "w",
                               encoding="utf-8"), ensure_ascii=False, indent=0)
    log(f"✓ tight_scan.json｜宇宙 {len(px)}｜命中 {len(rows)}")
    for r in rows[:8]:
        log(f"  {r['ticker']:6s} TIGHT {r['tight']:5.1f}｜箱 {r['box_atr']} ATR"
            f"｜ID {r['inside']}｜距40MA {r['d40']:+.1f}%｜距52高 {r['off52']:+.1f}%")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
