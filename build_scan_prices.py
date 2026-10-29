# -*- coding: utf-8 -*-
"""build_scan_prices.py — 抓齊所有 Daily Scan 出現過嘅股票價格（回測用）

問題：data/tight_prices.pkl 只有 568 隻，但 96 個快照出現過 278 隻，
      只有 80 隻重疊 → gto_daily 只能用到 16 日資料（嚴重偏誤）。
做法：抓 3 年日線，輸出 data/scan_prices.pkl（同一個格式：
      {ticker: [[date, o, h, l, c, v], ...]}），gto_daily 會自動合併兩個 cache。
"""
from __future__ import annotations

import glob
import io
import json
import os
import pickle
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = r"C:/Users/rain0/trading-os/output/layer2_*.json"
OUT = os.path.join(HERE, "data", "scan_prices.pkl")


def tickers():
    s = set()
    for f in sorted(glob.glob(SNAP)):
        try:
            with io.open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:                                    # noqa: BLE001
            continue
        for k in ("focus_list", "stalk_list"):
            for r in (d.get(k) or []):
                t = r.get("ticker")
                if t:
                    s.add(t)
    return sorted(s)


def main() -> int:
    ts = tickers()
    print(f"需要 {len(ts)} 隻", file=sys.stderr)
    old = {}
    if os.path.exists(OUT):
        with io.open(OUT, "rb") as f:
            old = pickle.load(f)

    import yfinance as yf
    d = yf.download(ts, period="3y", interval="1d", progress=False,
                    auto_adjust=False, group_by="ticker", threads=True)
    out = dict(old)
    n = 0
    for t in ts:
        try:
            f = d[t] if isinstance(d.columns, pd.MultiIndex) else d
            f = f.dropna(subset=["Close"])
            if len(f) < 80:
                continue
            rows = []
            for idx, r in f.iterrows():
                rows.append([idx.strftime("%Y-%m-%d"), float(r["Open"]),
                             float(r["High"]), float(r["Low"]),
                             float(r["Close"]), float(r["Volume"])])
            out[t] = rows
            n += 1
        except Exception:                                    # noqa: BLE001
            continue
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "wb") as f:
        pickle.dump(out, f)
    print(f"寫入 {len(out)} 隻（今次更新 {n}）→ {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
