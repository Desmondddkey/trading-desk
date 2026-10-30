# -*- coding: utf-8 -*-
"""growth_cycle.py — 成長週期（第一性原理版）

需求（Desmond 2026-10-30，TradersLab Lab Report 蒸餾）：
  回答一條問題：而家應該幾積極？

兩項輸入
  ① 風險閘門：成長 vs 價值（IWF / IWD）嘅【10 週結構】
     收市升穿結構上軌 = risk-on
     收市跌穿結構下軌 = risk-off
     軌內 = 維持上一次確認狀態（避免噪音翻轉）
  ② 動能：比率 10 日變化（正 = 加速，負 = 衰減）

六個區（順序）
  RISK-OFF → PROBE → RAMP UP → TRIM / HOLD → RELOAD → 回 RISK-OFF

延伸度（extension）
  ext = (比率 − EMA10) ÷ ((上軌 − 下軌)/2)
  ext ≥ 1.5 = 伸展（容易減持）；ext < 1.5 = 未伸展（可以加）

輸出 output/cycle.json：
  current（區、閘門、動能、延伸、區內日數）
  zones（六區 → 之後 10 日 SPY 回報／勝率／n）
  history（近 260 個交易日逐日 zone）
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r"C:/Users/rain0/trading-os/output/cycle.json"

ZONES = ["RISK-OFF", "PROBE", "RAMP UP", "TRIM", "HOLD", "RELOAD"]


def _data():
    import yfinance as yf
    end = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    d = yf.download(["IWF", "IWD", "SPY"], start="2012-01-01", end=end,
                    interval="1d", auto_adjust=True, progress=False,
                    group_by="ticker", threads=True)
    out = {}
    for s in ("IWF", "IWD", "SPY"):
        try:
            f = d[s].dropna(subset=["Close"])["Close"]
            out[s] = f
        except Exception:                                    # noqa: BLE001
            return None
    return out


def build_series(c: pd.Series, hi: pd.Series, lo: pd.Series):
    """回傳 DataFrame：ratio / upper / lower / gate / mom / ext / zone"""
    ratio = c
    up = hi.ewm(span=10, adjust=False).mean()
    dn = lo.ewm(span=10, adjust=False).mean()
    gate, state = [], "OFF"
    for i in range(len(ratio)):
        r = ratio.iloc[i]
        if r > up.iloc[i]:
            state = "ON"
        elif r < dn.iloc[i]:
            state = "OFF"
        gate.append(state)
    g = pd.Series(gate, index=ratio.index)
    mom = ratio.pct_change(10) * 100
    half = ((up - dn) / 2).replace(0, np.nan)
    ext = (ratio - up) / half
    return pd.DataFrame({"ratio": ratio, "upper": up, "lower": dn,
                         "gate": g, "mom": mom, "ext": ext})


def zone_of(gate, mom, ext, prev=None):
    on = gate == "ON"
    if not on:
        return "RISK-OFF" if (mom is None or mom < 0) else "PROBE"
    e = ext if (ext == ext) else 0.0
    if mom is None:
        mom = 0.0
    if mom > 0:
        return "RAMP UP" if e >= 1.5 else "RELOAD"
    return "TRIM" if e >= 1.5 else "HOLD"


def main() -> int:
    d = _data()
    if not d:
        print("DATA_UNAVAILABLE", file=sys.stderr)
        return 0
    iwf, iwd, spy = d["IWF"], d["IWD"], d["SPY"]
    idx = iwf.index.intersection(iwd.index)
    ratio = (iwf.loc[idx] / iwd.loc[idx]).dropna()
    # 週線結構，再映射返日線
    wk = ratio.resample("W-FRI")
    wc, wh, wl = wk.last(), wk.max(), wk.min()
    st = build_series(wc, wh, wl)
    # 日線用最近一個已收週嘅狀態
    daily = st.reindex(ratio.index, method="ffill")

    rows = []
    prev = None
    for day, r in daily.iterrows():
        z = zone_of(r["gate"], r["mom"], r["ext"], prev)
        prev = z
        rows.append({"date": day.strftime("%Y-%m-%d"), "zone": z,
                     "gate": r["gate"],
                     "mom": None if pd.isna(r["mom"]) else round(float(r["mom"]), 3),
                     "ext": None if pd.isna(r["ext"]) else round(float(r["ext"]), 2),
                     "ratio": round(float(r["ratio"]), 4)})
    h = pd.DataFrame(rows).set_index("date")

    # 區內日數
    last_zone = h["zone"].iloc[-1]
    n = 0
    for z in reversed(list(h["zone"])):
        if z != last_zone:
            break
        n += 1

    # 之後 10 日 SPY 回報，按區分組
    fwd = spy.pct_change(10).shift(-10) * 100
    stats = {}
    for z in ZONES:
        days = h[h["zone"] == z].index
        vals = [float(fwd.loc[d]) for d in days
                if d in fwd.index and pd.notna(fwd.loc[d])]
        if vals:
            stats[z] = {"n": len(vals),
                        "mean": round(float(np.mean(vals)), 2),
                        "wr": round(float(np.mean([v > 0 for v in vals]) * 100), 1),
                        "p25": round(float(np.percentile(vals, 25)), 2),
                        "p75": round(float(np.percentile(vals, 75)), 2)}
        else:
            stats[z] = {"n": 0}

    cur = h.iloc[-1]
    payload = {
        "as_of": h.index[-1],
        "current": {"zone": last_zone, "gate": cur["gate"],
                    "mom": cur["mom"], "ext": cur["ext"],
                    "days_in_zone": n, "ratio": cur["ratio"]},
        "zones": stats,
        "history": [{"date": d0, "zone": r["zone"]}
                    for d0, r in h.tail(260).iterrows()],
        "rule": "gate=10週EMA上/下軌；mom=10日變化；ext=(ratio-EMA)/半軌寬；"
                "ext≥1.5 視為伸展",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"{payload['as_of']} {last_zone}｜gate {cur['gate']}｜"
          f"mom {cur['mom']}｜ext {cur['ext']}｜{n} 日", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
