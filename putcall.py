# -*- coding: utf-8 -*-
"""putcall.py — 建立 Put/Call Ratio 資料（CBOE Equity P/C + SPX）

輸入  output/putcall_raw.csv（putcall_fetch.py 產生）
      SPX 日線（yfinance，快取 12 小時）
輸出  output/putcall.json
      series: [{d, pc, ma250, spx}] 由 2006 至今
      climax: [{d, pc, spx}] 賣壓高峰（SPX 回撤底部 ± 視窗內最大 P/C）
      latest: 當日數值、250 日平均、百分位
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "output", "putcall_raw.csv")
OUT = os.path.join(HERE, "output", "putcall.json")
SPX_CACHE = os.path.join(HERE, "cache", "spx_daily.pkl")
DD_MIN = 8.0          # 只標示 SPX 回撤 ≥8% 的底部
EVENT_GAP = 120       # 兩個標記至少相隔 120 個交易日


def _pc():
    if not os.path.exists(RAW):
        return None
    rows = []
    for line in io.open(RAW, encoding="utf-8"):
        p = line.strip().split(",")
        if len(p) == 2:
            try:
                rows.append((p[0], float(p[1])))
            except ValueError:
                pass
    if not rows:
        return None
    s = pd.Series({pd.Timestamp(d): v for d, v in rows}).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    # 清洗：CBOE Equity P/C 歷史上界 ~1.5；0 或 >1.8 屬解析錯誤
    s = s[(s > 0.05) & (s < 1.8)]
    return s


def _spx():
    os.makedirs(os.path.dirname(SPX_CACHE), exist_ok=True)
    if os.path.exists(SPX_CACHE):
        age = dt.datetime.now() - dt.datetime.fromtimestamp(os.path.getmtime(SPX_CACHE))
        if age < dt.timedelta(hours=12):
            with open(SPX_CACHE, "rb") as f:
                return pickle.load(f)
    import yfinance as yf
    d = yf.download("^GSPC", start="2006-01-01", progress=False, auto_adjust=True)
    if hasattr(d.columns, "levels"):
        d.columns = [c[0] for c in d.columns]
    s = d["Close"].dropna()
    with open(SPX_CACHE, "wb") as f:
        pickle.dump(s, f)
    return s


def _climaxes(pc: pd.Series, spx: pd.Series):
    """SPX 每個 ≥8% 回撤的底部附近，P/C 的最大值 → 賣壓高峰標記。"""
    idx = spx.index
    peak = spx.iloc[0]
    peak_i = 0
    trough, trough_i = peak, 0
    events = []
    for i in range(1, len(spx)):
        v = spx.iloc[i]
        if v >= peak:
            if peak_i and (trough / peak - 1) * 100 <= -DD_MIN:
                events.append((peak_i, trough_i))
            peak, peak_i, trough, trough_i = v, i, v, i
        else:
            if v < trough:
                trough, trough_i = v, i
    if peak_i and (trough / peak - 1) * 100 <= -DD_MIN:
        events.append((peak_i, trough_i))

    out, last_i = [], -10 ** 9
    for _, ti in events:
        lo = max(0, ti - 12)
        hi = min(len(pc) - 1, ti + 6)
        win = pc.iloc[lo:hi + 1]
        if win.empty:
            continue
        d = win.idxmax()
        j = pc.index.get_loc(d)
        if j - last_i < EVENT_GAP:
            continue
        last_i = j
        out.append({"d": d.strftime("%Y-%m-%d"), "pc": round(float(win.max()), 3)})
    return out


def main() -> int:
    pc = _pc()
    if pc is None:
        print("DATA_UNAVAILABLE: putcall_raw.csv", file=sys.stderr)
        return 0
    spx = _spx()
    ma = pc.rolling(250, min_periods=120).mean()

    df = pd.DataFrame({"pc": pc, "ma250": ma}).join(spx.rename("spx"), how="left")
    df["spx"] = df["spx"].ffill()
    df = df[df["pc"].notna()].loc["2006-01-01":]

    events = _climaxes(pc.loc["2006-01-01":], spx.loc["2006-01-01":])
    cur = df.iloc[-1]
    pct = float((pc.tail(756) < cur["pc"]).mean() * 100)      # 3 年百分位

    payload = {
        "as_of": df.index[-1].strftime("%Y-%m-%d"),
        "latest": {
            "pc": round(float(cur["pc"]), 3),
            "ma250": None if pd.isna(cur["ma250"]) else round(float(cur["ma250"]), 3),
            "spx": None if pd.isna(cur["spx"]) else round(float(cur["spx"]), 1),
            "pct3y": round(pct, 1),
            "n": int(len(df)),
        },
        "series": [{"d": d.strftime("%Y-%m-%d"),
                    "pc": round(float(r["pc"]), 3),
                    "ma": None if pd.isna(r["ma250"]) else round(float(r["ma250"]), 3),
                    "spx": None if pd.isna(r["spx"]) else round(float(r["spx"]), 1)}
                   for d, r in df.iterrows()],
        "climax": events,
        "source": "CBOE Equity Put/Call Ratio（官方存檔 2006-11→2019-10 + "
                  "每日統計頁逐日抓取）；SPX = yfinance",
        "rule": f"豎線 = SPX 回撤 ≥{DD_MIN:.0f}% 底部附近 P/C 最高的一日；"
                f"相鄰標記至少相隔 {EVENT_GAP} 個交易日",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"{payload['as_of']} P/C {cur['pc']:.3f}｜MA250 "
          f"{cur['ma250']:.3f}｜3y 百分位 {pct:.0f}%｜"
          f"{len(payload['series'])} 日｜{len(events)} 個高峰", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
