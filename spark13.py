# -*- coding: utf-8 -*-
"""spark13.py — Jeff Sun 風格「推移」條：13 週走勢 mini bars。

每隻股：13 個週線回報（相對 SPY），最後一根用藍色。
輸出 data/spark13.json：{t: {"v": [13 個值], "pos4": "3/4"}}

規則：
  · 週線 = W-FRI resample 收市
  · 值 = 該週股票回報 − SPY 回報（相對強弱）
  · pos4 = 最近 4 週之中有幾週正數（顯示 3/4）
"""
from __future__ import annotations

import io
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "screener_ohlc.pkl")
OUT = os.path.join(HERE, "data", "spark13.json")
WEEKS = 13


def weekly(df):
    s = df["Close"].dropna()
    if len(s) < 70:
        return None
    w = s.resample("W-FRI").last().dropna()
    if len(w) < WEEKS + 1:
        return None
    return w.pct_change().dropna().tail(WEEKS) * 100


def main():
    d = pd.read_pickle(SRC)
    spy = d.get("_SPY")
    if spy is None:
        spy = d.get("SPY")
    if spy is None:
        print("DATA_UNAVAILABLE — 冇 SPY")
        return 1
    sw = weekly(spy)
    if sw is None:
        print("DATA_UNAVAILABLE — SPY 週線不足")
        return 1
    out, n = {}, 0
    for t, df in d.items():
        if t.startswith("_"):
            continue
        try:
            wk = weekly(df)
        except Exception:                                        # noqa: BLE001
            continue
        if wk is None:
            continue
        idx = wk.index.intersection(sw.index)
        if len(idx) < WEEKS:
            continue
        rel = (wk.loc[idx] - sw.loc[idx]).round(2)
        vals = [float(x) for x in rel.tolist()]
        out[t] = {"v": vals, "pos4": f"{sum(1 for x in vals[-4:] if x > 0)}/4"}
        n += 1
    if not out:
        print("DATA_UNAVAILABLE — 冇 ticker")
        return 1
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps({"as_of": str(sw.index[-1])[:10], "weeks": WEEKS, "rows": out},
                   ensure_ascii=False, separators=(",", ":")))
    print(f"✓ {n} 隻｜{WEEKS} 週｜as_of {str(sw.index[-1])[:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
