# -*- coding: utf-8 -*-
"""tv_meta.py — 用 TradingView screener 抓指定股票嘅 sector / industry / 回報

為咩要（Desmond 2026-10-25）：
  yfinance 嘅 sector（Healthcare / Technology…）同 TradingView 嘅
  19 個 sector（Health Technology / Health Services…）名唔一致
  → GROUP RS 對唔上，73 隻只有 21 隻有數字。
  唯一可靠做法：用同一把尺（TradingView）抓同一批股嘅分類。

輸出：data/tv_meta.json
  {"PACS": {"sector": "Health Services", "industry": "Medical/Nursing Services",
            "perf": {"1w": .., "1m": .., "3m": ..}, "close": ..}}

用法：python tv_meta.py
"""
from __future__ import annotations

import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "tv_meta.json")


def log(m):
    print(m, file=sys.stderr)


def universe():
    tk = set()
    for pat in (r"C:/Users/rain0/trading-os/output/layer2_*.json",
                r"C:/Users/rain0/trading-os/output/rs_select_*.json"):
        fs = sorted(glob.glob(pat))
        if not fs:
            continue
        try:
            d = json.load(io.open(fs[-1], encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rows = d.get("rows") or (d.get("focus_list") or []) + (d.get("stalk_list") or [])
        for r in rows:
            t = (r.get("ticker") or "").upper()
            if t:
                tk.add(t)
    return sorted(tk)


def main():
    try:
        from tradingview_screener import Query, col
    except ImportError:
        log("✗ 冇 tradingview_screener")
        return 1

    tk = universe()
    if not tk:
        log("✗ 冇宇宙")
        return 1

    out = {}
    try:
        old = json.load(io.open(OUT, encoding="utf-8"))
        out.update(old)
    except (OSError, ValueError):
        pass

    q = (Query()
         .select("name", "sector", "industry", "close",
                 "Perf.W", "Perf.1M", "Perf.3M")
         .where(col("name").isin(tk))
         .limit(len(tk) + 50))
    _, df = q.get_scanner_data()
    got = 0
    for _, r in df.iterrows():
        t = str(r.get("name") or "").upper()
        if not t:
            continue
        out[t] = {
            "sector": r.get("sector") or "",
            "industry": r.get("industry") or "",
            "close": float(r["close"]) if r.get("close") == r.get("close") else None,
            "perf": {"1w": r.get("Perf.W"), "1m": r.get("Perf.1M"),
                     "3m": r.get("Perf.3M")},
        }
        got += 1

    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    cov = sum(1 for t in tk if out.get(t, {}).get("industry"))
    log(f"✓ {OUT}｜今次抓到 {got}｜覆蓋 {cov}/{len(tk)}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
