# -*- coding: utf-8 -*-
"""thrust20.py — Stockbee 20% 廣度研究（Pradeep Bonde 2026-11）。

量度：5 日內升 ≥20% 嘅股票數（UP20）／跌 ≥20%（DOWN20）／淨值，加 50 日均線。
判讀（原作者圖上文字）：
  極端偏多讀數 → 之後多數回調
  極端偏空讀數 → 之後多數反彈

⚠️ 池嘅限制：本地池係 743 隻流動股票（成交額 ≥$30M、ADR ≥4%），
   唔係全美股 ~6000 隻，所以絕對數字唔可以同 Stockbee 圖直接比較，
   只可以用嚟睇「相對自己歷史」嘅極端程度（百分位）。

輸出 data/thrust20.json（每日刷新）。
"""
from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "screener_ohlc.pkl")
OUT = os.path.join(HERE, "data", "thrust20.json")
LOOKBACK = 250


def main():
    data = pd.read_pickle(SRC)
    cols = {}
    for t, df in data.items():
        if t.startswith("_") or df is None or len(df) < 30:
            continue
        c = df["Close"].dropna()
        if len(c) < 30:
            continue
        cols[t] = c
    if not cols:
        print("DATA_UNAVAILABLE — 冇價格")
        return 1

    px = pd.DataFrame(cols).sort_index().tail(LOOKBACK + 10)
    pct5 = px.pct_change(5)
    up = (pct5 >= 0.20).sum(axis=1)
    dn = (pct5 <= -0.20).sum(axis=1)
    net = up - dn
    df = pd.DataFrame({"up": up, "dn": dn, "net": net}).dropna()
    df["up_ma"] = df["up"].rolling(50, min_periods=10).mean()
    df["net_ma"] = df["net"].rolling(50, min_periods=10).mean()

    if len(df) < 60:
        print("DATA_UNAVAILABLE — 歷史不足")
        return 1

    last = df.iloc[-1]
    rank = lambda s, v: round(100.0 * (s <= v).mean(), 1)   # noqa: E731
    up_pct = rank(df["up"], last["up"])
    dn_pct = rank(df["dn"], last["dn"])

    if up_pct >= 90:
        sig, note = "極端偏多", "5 日升 20% 家數處歷史高位 → 之後多數回調（唔追高）"
    elif dn_pct >= 90:
        sig, note = "極端偏空", "5 日跌 20% 家數處歷史高位 → 之後多數反彈（留意轉勢）"
    else:
        sig, note = "中性", "兩邊都唔極端；跟隨趨勢與個股設置"

    tail = df.tail(60)
    payload = {
        "asOf": str(df.index[-1])[:10],
        "pool": len(cols),
        "lookback": len(df),
        "latest": {
            "up20": int(last["up"]), "dn20": int(last["dn"]), "net": int(last["net"]),
            "up_ma50": round(float(last["up_ma"]), 1),
            "net_ma50": round(float(last["net_ma"]), 1),
            "up_pctile": up_pct, "dn_pctile": dn_pct,
        },
        "signal": sig, "note": note,
        "series": {
            "dates": [str(x)[:10] for x in tail.index],
            "up": [int(x) for x in tail["up"]],
            "dn": [int(x) for x in tail["dn"]],
            "net": [int(x) for x in tail["net"]],
        },
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False,
                                                          separators=(",", ":")))
    print(f"✓ UP20 {payload['latest']['up20']}（p{up_pct}）｜"
          f"DOWN20 {payload['latest']['dn20']}（p{dn_pct}）｜"
          f"NET {payload['latest']['net']}｜{sig}｜{payload['asOf']}｜池 {len(cols)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
