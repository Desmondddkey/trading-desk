# -*- coding: utf-8 -*-
"""avwap52.py — 52 週高點 AVWAP（The Setup Factory 2026-11-17）。

做乜：由「52 週最高價嗰日」做 anchor，計成交量加權平均價（AVWAP）。
     價重返 AVWAP 上方 = 高位買入者嘅平均成本被消化 → 強勢趨勢嘅入場區。

輸出 data/avwap52.json：
  {as_of, anchor_rule, rows: {TICKER: {avwap, d_pct, d_atr, state, anchor, days}}}

state：
  在上   close > avwap + 0.5 ATR   （已重奪）
  重疊   |close − avwap| ≤ 0.5 ATR （貼線＝可執行入場區）
  在下   close < avwap − 0.5 ATR   （未收復）
"""
from __future__ import annotations

import io
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "screener_ohlc.pkl")
OUT = os.path.join(HERE, "data", "avwap52.json")
LOOKBACK = 252
BAND_ATR = 0.5


def _atr14(df):
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return float(tr.rolling(14).mean().iloc[-1])


def one(df):
    df = df.dropna(subset=["High", "Low", "Close", "Volume"])
    if len(df) < 60:
        return None
    win = df.tail(LOOKBACK)
    if win["Volume"].sum() <= 0:
        return None
    anchor = win["High"].idxmax()
    sub = df.loc[anchor:]
    if len(sub) < 2 or sub["Volume"].sum() <= 0:
        return None
    tp = (sub["High"] + sub["Low"] + sub["Close"]) / 3.0
    avwap = float((tp * sub["Volume"]).sum() / sub["Volume"].sum())
    close = float(df["Close"].iloc[-1])
    atr = _atr14(df)
    if not atr or atr <= 0:
        return None
    d_atr = (close - avwap) / atr
    if d_atr > BAND_ATR:
        state = "在上"
    elif d_atr < -BAND_ATR:
        state = "在下"
    else:
        state = "重疊"
    return {
        "avwap": round(avwap, 2),
        "close": round(close, 2),
        "d_pct": round(100 * (close / avwap - 1), 2),
        "d_atr": round(d_atr, 2),
        "state": state,
        "anchor": str(anchor)[:10],
        "days": int(len(sub)),
    }


def main():
    data = pd.read_pickle(SRC)
    rows, last = {}, None
    for t, df in data.items():
        try:
            r = one(df)
        except Exception:                                        # noqa: BLE001
            continue
        if r:
            rows[t] = r
            last = str(df.index[-1])[:10] if last is None else last
    if not rows:
        print("DATA_UNAVAILABLE — 冇 ticker 計得出 AVWAP")
        return 1
    payload = {"as_of": last, "lookback": LOOKBACK, "band_atr": BAND_ATR, "rows": rows}
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    cnt = {}
    for r in rows.values():
        cnt[r["state"]] = cnt.get(r["state"], 0) + 1
    print(f"✓ {len(rows)} 隻｜as_of {last}｜" +
          "／".join(f"{k} {v}" for k, v in sorted(cnt.items())))
    for t in ("NVDA", "QQQ", "SPY"):
        if t in rows:
            r = rows[t]
            print(f"   {t}: AVWAP {r['avwap']}｜收 {r['close']}｜{r['d_atr']:+.2f} ATR｜"
                  f"{r['state']}｜anchor {r['anchor']}（{r['days']} 日）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
