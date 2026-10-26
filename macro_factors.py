# -*- coding: utf-8 -*-
"""macro_factors.py — 「世界主線」因子 IC 回測

問題：邊個宏觀因子真正影響 SPY／QQQ／IWM 未來回報？
做法：
  ① 取公開數據（FRED csv 免 key；yfinance 取 ETF/商品）
  ② 每個因子計 Rank IC（Spearman）對 5/10/20 日前瞻回報
  ③ 時間序列分五組（Q1 最低 → Q5 最高），睇 Q5−Q1 差距
  ④ 只報告，不改任何實盤規則

判讀門檻（事先寫死，唔准事後搬）
  |IC| ≥ 0.10 且 |t| ≥ 2.0  → 「有預測力」
  |IC| ≥ 0.05               → 「弱」
  其餘                       → 「冇」

輸出：output/macro_factors.json + console
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
START = "2015-01-01"
HORIZONS = (5, 10, 20)
FRED = {"DGS10": "10Y 國債", "DFII10": "實質利率 10Y", "BAMLH0A0HYM2": "高收益債利差",
        "T10Y3M": "10Y-3M 曲線", "NFCI": "金融條件 NFCI",
        "DCOILBRENTEU": "布蘭特原油"}
YF = {"SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM", "HG=F": "銅",
      "XLU": "公用股 XLU", "SMH": "半導體 SMH", "GLD": "黃金",
      "DX-Y.NYB": "美元指數", "TLT": "長債 TLT", "HYG": "高收益債 HYG"}


def log(m):
    print(m, file=sys.stderr)


def fred(sid):
    r = subprocess.run(
        ["curl", "-sS", "-m", "40",
         f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={START}"],
        capture_output=True, text=True, errors="replace")
    rows = [l.split(",") for l in r.stdout.strip().splitlines()[1:] if l]
    if not rows:
        return None
    idx, vals = [], []
    for d, v in ((r[0], r[1]) for r in rows):
        try:
            vals.append(float(v))
            idx.append(pd.Timestamp(d))
        except ValueError:
            continue
    return pd.Series(vals, index=pd.DatetimeIndex(idx)).sort_index()


def yf_close(tickers):
    import yfinance as yf
    df = yf.download(tickers, start=START, interval="1d",
                     auto_adjust=True, progress=False, threads=True)
    return df["Close"] if "Close" in df.columns.get_level_values(0) else df


def main():
    px = yf_close(list(YF))
    if "SPY" not in px.columns:
        log("✗ 冇 SPY")
        return 1
    idx = px["SPY"].dropna().index

    cols = {}
    for sid, name in FRED.items():
        s = fred(sid)
        if s is not None and len(s):
            cols[name] = s.reindex(idx, method="ffill")
            log(f"  FRED {sid}: {len(s)} 行")
    for t, name in YF.items():
        if t in px.columns:
            cols[name] = px[t]
    df = pd.DataFrame(cols).reindex(idx).ffill()

    # 衍生因子
    df["10Y 20日變化"] = df["10Y 國債"].diff(20)
    df["HY利差 20日變化"] = df["高收益債利差"].diff(20)
    df["銅 20日回報"] = df["銅"].pct_change(20) * 100
    df["公用股/SPY 20日"] = ((df["公用股 XLU"] / df["SPY"]).pct_change(20) * 100)
    df["半導體/SPY 20日"] = ((df["半導體 SMH"] / df["SPY"]).pct_change(20) * 100)
    df["美元 20日回報"] = df["美元指數"].pct_change(20) * 100
    df["長債 20日回報"] = df["長債 TLT"].pct_change(20) * 100

    factors = [c for c in df.columns
               if c not in ("SPY", "QQQ", "IWM", "銅", "公用股 XLU",
                            "半導體 SMH", "黃金", "美元指數", "長債 TLT",
                            "高收益債 HYG")]

    for h in HORIZONS:
        df[f"SPY+{h}"] = df["SPY"].shift(-h) / df["SPY"] - 1
        df[f"QQQ+{h}"] = df["QQQ"].shift(-h) / df["QQQ"] - 1
        df[f"IWM+{h}"] = df["IWM"].shift(-h) / df["IWM"] - 1

    rows = []
    for f in factors:
        for h in HORIZONS:
            sub = df[[f, f"SPY+{h}", f"QQQ+{h}", f"IWM+{h}"]].dropna()
            if len(sub) < 250:
                continue
            # Spearman = 排名後 Pearson（唔靠 scipy）
            ic = (sub[f].rank().corr(sub[f"SPY+{h}"].rank()))
            n = len(sub)
            t = ic * np.sqrt((n - 2) / max(1e-9, (1 - ic ** 2)))
            # 五組
            try:
                q = pd.qcut(sub[f], 5, labels=False, duplicates="drop")
                g = sub.groupby(q)[f"SPY+{h}"].mean() * 100
                spread = float(g.iloc[-1] - g.iloc[0]) if len(g) >= 5 else np.nan
            except Exception:                                 # noqa: BLE001
                spread = np.nan
            rows.append({"factor": f, "h": h, "n": int(n),
                         "ic": round(float(ic), 3), "t": round(float(t), 2),
                         "q5_minus_q1_pct": round(spread, 3) if spread == spread else None})

    res = pd.DataFrame(rows)
    res["abs_ic"] = res["ic"].abs()
    res = res.sort_values(["abs_ic"], ascending=False)

    def verdict(r):
        if abs(r["ic"]) >= 0.10 and abs(r["t"]) >= 2.0:
            return "有預測力"
        if abs(r["ic"]) >= 0.05:
            return "弱"
        return "冇"

    print("=== 因子 Rank IC（對 SPY 前瞻回報，2015 起）===")
    print(f"{'因子':22s} {'日':>4} {'n':>5} {'IC':>7} {'t':>6} {'Q5-Q1%':>8}  判斷")
    for _, r in res.iterrows():
        if r["h"] != 20:
            continue
        print(f"{r['factor']:22s} {r['h']:>4} {r['n']:>5} {r['ic']:>7.3f} "
              f"{r['t']:>6.2f} {(r['q5_minus_q1_pct'] if r['q5_minus_q1_pct'] is not None else float('nan')):>8.2f}  {verdict(r)}")

    print("\n=== 各因子 × 三個週期 IC ===")
    piv = res.pivot_table(index="factor", columns="h", values="ic")
    print(piv.round(3).to_string())

    best = res[res["h"] == 20].head(8).to_dict("records")
    os.makedirs(OUT, exist_ok=True)
    json.dump({"start": START, "n_days": int(len(df)),
               "rows": res.drop(columns=["abs_ic"]).to_dict("records"),
               "top20d": best}, io.open(os.path.join(OUT, "macro_factors.json"),
                                        "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    log("✓ output/macro_factors.json")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
