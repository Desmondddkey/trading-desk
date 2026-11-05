# -*- coding: utf-8 -*-
"""ntmflow.py — QQQ 近月期權 NTM 名義金額（Call vs Put）每日收集

RAE（反向工程）自 @TailThatWagsDog 的 ThinkScript 概念：
  · 取最近到期（DTE 1–10）的 QQQ 期權鏈
  · 只計近價（NTM）：行使價在現價 ±2% 內
  · 名義金額 = Σ 未平倉合約 × 100 × 行使價
  · 比率 = Call$ ÷ Put$
  · 比率 90 百分位 = 多頭極端（藍）；10 百分位 = 空頭極端（紅）
  · 訊號持續到相反極端出現為止

限制（誠實標明）：Yahoo/ yfinance 只提供當日快照，冇歷史期權鏈 →
所以本工具由今日起每日累積；未夠 20 個觀察之前，唔會出「極端」判定。

輸出 data/ntm_flow.csv（append-only）＋ output/ntmflow.json
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "data", "ntm_flow.csv")
OUT = os.path.join(HERE, "output", "ntmflow.json")
SYM = "QQQ"
BAND = 0.02          # ±2% = near-the-money
MIN_DTE, MAX_DTE = 1, 10
MIN_N = 20           # 少於此數唔判極端
HI_PCT, LO_PCT = 90, 10


def _chain():
    import yfinance as yf
    t = yf.Ticker(SYM)
    today = dt.date.today()
    best = None
    for e in t.options:
        d = dt.date.fromisoformat(e)
        dte = (d - today).days
        if MIN_DTE <= dte <= MAX_DTE:
            best = (e, dte)
            break
    if not best:
        return None
    exp, dte = best
    ch = t.option_chain(exp)
    spot = float(t.fast_info.get("last_price") or 0)
    if not spot:
        h = t.history(period="1d")
        spot = float(h["Close"].iloc[-1])
    rows = []
    for side, df in (("call", ch.calls), ("put", ch.puts)):
        df = df[(df["strike"] >= spot * (1 - BAND)) & (df["strike"] <= spot * (1 + BAND))]
        oi = pd.to_numeric(df.get("openInterest"), errors="coerce").fillna(0)
        notional = float((oi * 100 * df["strike"]).sum())
        rows.append((side, notional, float(oi.sum()), int(len(df))))
    d = {r[0]: {"usd": r[1], "oi": r[2], "n": r[3]} for r in rows}
    return {"date": today.isoformat(), "expiry": exp, "dte": dte, "spot": spot,
            "call_usd": d["call"]["usd"], "put_usd": d["put"]["usd"],
            "call_oi": d["call"]["oi"], "put_oi": d["put"]["oi"],
            "call_n": d["call"]["n"], "put_n": d["put"]["n"]}


def _append(rec):
    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    new = not os.path.exists(CSV)
    with io.open(CSV, "a", encoding="utf-8", newline="\n") as f:
        if new:
            f.write("date,expiry,dte,spot,call_usd,put_usd,ratio,call_oi,put_oi\n")
        f.write(f"{rec['date']},{rec['expiry']},{rec['dte']},{rec['spot']:.2f},"
                f"{rec['call_usd']:.0f},{rec['put_usd']:.0f},"
                f"{(rec['call_usd'] / rec['put_usd'] if rec['put_usd'] else 0):.4f},"
                f"{rec['call_oi']:.0f},{rec['put_oi']:.0f}\n")


def _load():
    if not os.path.exists(CSV):
        return pd.DataFrame()
    df = pd.read_csv(CSV)
    return df.drop_duplicates(subset=["date"], keep="last").sort_values("date")


def main() -> int:
    try:
        rec = _chain()
    except Exception as e:                                    # noqa: BLE001
        print(f"DATA_UNAVAILABLE: {e}", file=sys.stderr)
        return 0
    if not rec or not rec["put_usd"]:
        print("DATA_UNAVAILABLE: 期權鏈空", file=sys.stderr)
        return 0
    df = _load()
    seen = set(df["date"].astype(str)) if len(df) else set()
    if rec["date"] not in seen:
        _append(rec)
        df = _load()

    ratio = rec["call_usd"] / rec["put_usd"]
    n = int(len(df))
    hi = lo = None
    if n >= MIN_N:
        hi = float(df["ratio"].quantile(HI_PCT / 100))
        lo = float(df["ratio"].quantile(LO_PCT / 100))

    # 狀態機：極端出現才轉向，否則沿用上一狀態
    state = "NEUTRAL"
    if n >= MIN_N:
        prev = "NEUTRAL"
        for r in df["ratio"]:
            if r >= hi:
                prev = "LONG"
            elif r <= lo:
                prev = "SHORT"
        state = prev

    qqq = None
    try:
        import yfinance as yf
        h = yf.Ticker(SYM).history(period="1y")
        qqq = [{"d": d.strftime("%Y-%m-%d"), "c": round(float(v), 2)}
               for d, v in h["Close"].items()]
    except Exception:                                         # noqa: BLE001
        pass

    payload = {
        "as_of": rec["date"],
        "latest": {**{k: rec[k] for k in ("expiry", "dte", "spot")},
                   "call_usd": round(rec["call_usd"] / 1e6, 2),
                   "put_usd": round(rec["put_usd"] / 1e6, 2),
                   "ratio": round(ratio, 3)},
        "signal": state, "n": n, "min_n": MIN_N,
        "hi": None if hi is None else round(hi, 3),
        "lo": None if lo is None else round(lo, 3),
        "history": df.tail(120).to_dict("records"),
        "qqq": qqq,
        "source": "yfinance QQQ 期權鏈（每日快照）；名義 = OI×100×行使價，"
                  "只計現價 ±2% 的近價合約",
        "rule": f"比率 {HI_PCT} 百分位=多頭極端（藍），{LO_PCT} 百分位=空頭極端（紅），"
                f"持續到相反極端；少於 {MIN_N} 個觀察不判。",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, default=float)
    print(f"{rec['date']} exp {rec['expiry']}({rec['dte']}d) "
          f"call ${rec['call_usd']/1e6:.1f}M put ${rec['put_usd']/1e6:.1f}M "
          f"ratio {ratio:.2f} n={n} state={state}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
