# -*- coding: utf-8 -*-
"""fear_backtest.py — 「投降／過熱」儀表 2 年回測（SPY / QQQ / IWM）

第一性原理：
  一個指標要有用，必須證明「訊號出現之後，未來回報分佈同隨機日子唔同」。
  唔係講故事，係比較同一段時間內：有訊號 vs 全部日子 嘅前瞻回報。

可回測組件（歷史數據攞得到）
  A  VIX 水平 ≥ 30
  B  VIX / VIX3M > 1（期限結構倒掛）
  C  廣度：宇宙內 close > 200MA 嘅比例 < 25%
  D  CNN Fear & Greed < 25（有歷史才可以）

過熱（逃頂）組件
  E  F&G > 75
  F  VIX < 14
  G  廣度 > 85%

輸出：console 表 + output/fear_backtest.json
"""
from __future__ import annotations

import io
import json
import os
import pickle
import sys
from datetime import timedelta

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
W = HERE          # trading-os-web 本身
CACHE = os.path.join(W, "data", "fear_prices.pkl")
OUT = os.path.join(W, "output")
HORIZONS = (5, 10, 20, 60)


def log(m):
    print(m, file=sys.stderr)


def prices(tickers, period="3y", refresh=False):
    import yfinance as yf
    cache = {}
    if os.path.exists(CACHE) and not refresh:
        try:
            cache = pickle.load(io.open(CACHE, "rb"))
        except Exception:                                     # noqa: BLE001
            cache = {}
    need = [t for t in tickers if t not in cache]
    if need:
        log(f"  yfinance 下載 {len(need)} 隻…")
        df = yf.download(need, period=period, interval="1d",
                         auto_adjust=True, progress=False, threads=True)
        close = df["Close"] if "Close" in df.columns.get_level_values(0) else df
        for t in need:
            if t in close.columns:
                cache[t] = close[t].dropna()
        pickle.dump(cache, io.open(CACHE, "wb"))
        log(f"  完成，快取 {len(cache)} 隻")
    return cache


def cnn_series(key):
    """CNN graphdata → pd.Series（250 日歷史）；key = fear_and_greed_historical /
    put_call_options / stock_price_breadth"""
    import urllib.request
    u = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    h = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"),
         "Referer": "https://www.cnn.com/", "Accept": "*/*"}
    try:
        d = json.loads(urllib.request.urlopen(
            urllib.request.Request(u, headers=h), timeout=40).read())
        data = (d.get(key) or {}).get("data") or []
        if not data:
            return None
        idx = pd.to_datetime([r["x"] for r in data], unit="ms", utc=True).tz_convert(None)
        vals = [r["y"] for r in data]
        return pd.Series(vals, index=idx).sort_index()
    except Exception as e:                                    # noqa: BLE001
        log(f"  ⚠ CNN {key} 抓唔到：{type(e).__name__}")
        return None


def main():
    uni = []
    try:
        ms = json.load(io.open(os.path.join(W, "data", "market_scan.json"), encoding="utf-8"))
        uni = sorted({(r.get("symbol") or "").upper()
                      for r in (ms.get("universe") or []) if r.get("symbol")})
    except Exception:                                         # noqa: BLE001
        pass
    log(f"宇宙 {len(uni)} 隻")

    px = prices(list(dict.fromkeys(uni + ["SPY", "QQQ", "IWM",
                                          "^VIX", "^VIX3M", "^VXN"])), refresh=True)
    spy, qqq, iwm = px.get("SPY"), px.get("QQQ"), px.get("IWM")
    vix, vix3m, vxn = px.get("^VIX"), px.get("^VIX3M"), px.get("^VXN")
    if any(x is None for x in (spy, qqq, iwm, vix)):
        log("✗ 核心數據不足")
        return 1

    # 廣度：宇宙內 close > 200MA 比例
    cols = {}
    for t in uni:
        s = px.get(t)
        if s is not None and len(s) > 220:
            cols[t] = s
    cdf = pd.DataFrame(cols).sort_index()
    above = (cdf > cdf.rolling(200).mean()).sum(axis=1) / cdf.notna().sum(axis=1).replace(0, np.nan)
    breadth = (above * 100).reindex(spy.index).ffill()

    df = pd.DataFrame({"SPY": spy, "QQQ": qqq, "IWM": iwm,
                       "VIX": vix, "VIX3M": vix3m, "VXN": vxn,
                       "breadth": breadth}).dropna(subset=["SPY", "VIX"])
    df["vix_ratio"] = df["VIX"] / df["VIX3M"]

    fg = cnn_series("fear_and_greed_historical")
    pc = cnn_series("put_call_options")
    df["fg"] = fg.reindex(df.index, method="ffill") if fg is not None else np.nan
    df["pc"] = pc.reindex(df.index, method="ffill") if pc is not None else np.nan
    log(f"  F&G {df['fg'].notna().sum()} 日｜P/C {df['pc'].notna().sum()} 日")

    df = df.dropna(subset=["breadth"])
    log(f"樣本 {len(df)} 日｜{df.index[0].date()} → {df.index[-1].date()}")

    # 分數（投降）
    df["A"] = (df["VIX"] >= 30).astype(int)
    df["B"] = (df["vix_ratio"] > 1.0).astype(int)
    df["C"] = (df["breadth"] < 25).astype(int)
    df["D"] = (df["fg"] < 25).fillna(False).astype(int)
    df["P"] = (df["pc"] >= 0.80).fillna(False).astype(int)
    df["bottom_score"] = df[["A", "B", "C", "D", "P"]].sum(axis=1)

    df["E"] = (df["fg"] > 75).fillna(False).astype(int)
    df["F"] = (df["VIX"] < 14).astype(int)
    df["G"] = (df["breadth"] > 85).astype(int)
    df["top_score"] = df[["E", "F", "G"]].sum(axis=1)

    for h in HORIZONS:
        for t in ("SPY", "QQQ", "IWM"):
            df[f"{t}_{h}"] = df[t].shift(-h) / df[t] - 1

    res = {"window": [str(df.index[0].date()), str(df.index[-1].date())],
           "n_days": int(len(df)), "buckets": {}, "signals": {}}

    print("\n=== 投降分（0–4）→ 未來回報中位數 %／勝率 ===")
    print(f"{'分':>3} {'n':>5} " + " ".join(f"{t}-{h}d" for t in ("SPY", "QQQ", "IWM") for h in (20,)))
    for s in range(0, 6):
        sub = df[df["bottom_score"] == s]
        if len(sub) < 5:
            continue
        row = {"n": int(len(sub))}
        cells = []
        for t in ("SPY", "QQQ", "IWM"):
            m = sub[f"{t}_20"].median() * 100
            w = (sub[f"{t}_20"] > 0).mean() * 100
            row[f"{t}_20_med"] = round(float(m), 2)
            row[f"{t}_20_win"] = round(float(w), 1)
            cells.append(f"{t} {m:+.2f}% / {w:.0f}%")
        res["buckets"][s] = row
        print(f"{s:>3} {len(sub):>5} " + "  ".join(cells))

    print("\n=== 逐個訊號單獨睇（20 日） ===")
    base = {t: df[f"{t}_20"].median() * 100 for t in ("SPY", "QQQ", "IWM")}
    print("基準（全部日子）：" + "  ".join(f"{t} {base[t]:+.2f}%" for t in base))
    for k, name in (("A", "VIX≥30"), ("B", "VIX/VIX3M>1"), ("C", "廣度<25%"),
                    ("D", "F&G<25"), ("P", "P/C≥0.80")):
        sub = df[df[k] == 1]
        if len(sub) < 5:
            print(f"{name:14s} n={len(sub)} 樣本不足")
            continue
        line = {"n": int(len(sub))}
        cells = []
        for t in ("SPY", "QQQ", "IWM"):
            m = sub[f"{t}_20"].median() * 100
            w = (sub[f"{t}_20"] > 0).mean() * 100
            line[f"{t}_20_med"] = round(float(m), 2)
            line[f"{t}_20_win"] = round(float(w), 1)
            cells.append(f"{t} {m:+.2f}%/勝{w:.0f}%")
        res["signals"][k] = line
        print(f"{name:14s} n={len(sub):>4} " + "  ".join(cells))

    print("\n=== 過熱分（0–3）→ 未來 20 日 ===")
    for s in range(0, 4):
        sub = df[df["top_score"] == s]
        if len(sub) < 5:
            continue
        cells = []
        for t in ("SPY", "QQQ", "IWM"):
            m = sub[f"{t}_20"].median() * 100
            w = (sub[f"{t}_20"] > 0).mean() * 100
            cells.append(f"{t} {m:+.2f}%/勝{w:.0f}%")
        res["buckets"][f"top{s}"] = {"n": int(len(sub))}
        print(f"{s:>3} {len(sub):>5} " + "  ".join(cells))

    # 最近 15 個交易日狀態
    print("\n=== 最近 15 日 ===")
    tail = df.tail(15)[["VIX", "vix_ratio", "VXN", "breadth", "fg",
                        "bottom_score", "top_score"]]
    print(tail.round(2).to_string())

    os.makedirs(OUT, exist_ok=True)
    json.dump(res, io.open(os.path.join(OUT, "fear_backtest.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
    log("✓ 寫入 output/fear_backtest.json")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
