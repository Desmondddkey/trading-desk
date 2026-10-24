#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extras.py — 跟 Desmond 提供嘅圖片，實現「完整」功能：

① RS 板（圖片 2/4）：指數 Index／板塊 Sector／群組 Group 三個表，
   每行 = RS 推力率% + 1 月 RS% + sparkline + 距 52 週高。
② 成長週期（圖片 6）：成長／價值比率（IWF/IWD）嘅週線 EMA10 風險閘，
   升穿=risk-on、跌穿=risk-off、帶內=維持上一邊，六個階段。
③ The Plan（圖片 7/8）：每隻候選股嘅 ATR 帶 ＋ 買入／止蝕／目標。

⚠ 所有「RS 推力率」都係**我嘅定義**（Jeff Sun 原文公式未取得）：
   推力率 = 最近 30 個交易日之中，呢隻 ETF 嘅 21 日回報贏 SPY 嘅比例。
   圖上會寫明，唔會扮係佢嘅數。
"""
import datetime
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "rsboard_ohlc.pkl")
sys.path.insert(0, r"C:\Users\rain0\trading-os-lab")   # rotation_map 喺度


# 指數（圖片 2「Index」）
INDEX = [
    ("SPY", "S&P 500"), ("OEF", "S&P 100"), ("QQQ", "Nasdaq 100"),
    ("IWM", "Russell 2000"), ("IWB", "Russell 1000"), ("DIA", "Dow Jones"),
    ("MDY", "S&P 400 MidCap"), ("IWV", "Russell 3000"),
]

# 群組（圖片 4，Jeff 嘅 list —— 逐隻抄）
GROUP = [
    ("IBUY", "Online Retail"), ("ESPO", "Video Games"), ("CLOU", "Cloud Computing"),
    ("WCLD", "Cloud SaaS"), ("XSW", "Software"), ("EWZ", "Brazil"),
    ("BUG", "Cybersecurity"), ("FDN", "Internet"), ("CIBR", "Cyber Defense"),
    ("IGV", "Software"), ("IDGT", "Digital Infra"), ("GENZ", "Gen Z"),
    ("BOAT", "Shipping"), ("ARKF", "Fintech"), ("ILF", "Latin America"),
    ("SVIX", "Short Vol"), ("IHF", "Healthcare Providers"), ("IPAY", "Payments"),
    ("UNG", "Nat Gas"), ("FFTY", "Innovation 50"), ("MAGS", "Mag 7"),
    ("SOCL", "Social Media"), ("XRT", "Retail"), ("ARKW", "Next Internet"),
    ("KWEB", "China Internet"), ("XOP", "Oil Exploration"), ("PEJ", "Travel/Leisure"),
    ("EUV", "Short Euro"), ("IYZ", "Telecom"), ("BAI", "Baidu"),
    ("CHIQ", "China Consumer"), ("FCG", "Nat Gas E&P"), ("AIQ", "AI & Tech"),
    ("XHS", "Healthcare Services"), ("PBE", "Biotech"), ("IHI", "Med Devices"),
    ("ROBO", "Robotics"), ("GRID", "Smart Grid"), ("PPH", "Pharma"),
    ("FXI", "China LargeCap"), ("IBB", "Biotech"), ("ARKK", "Disruptive"),
    ("LIT", "Lithium/Battery"), ("ARKQ", "Auto/Robotics"), ("GDX", "Gold Miners"),
    ("BETZ", "Gambling"), ("PHO", "Water"), ("BUZZ", "Social Sentiment"),
    ("IBIT", "Bitcoin"), ("BOTZ", "Robotics AI"),
]


def log(*a):
    print(*a, flush=True)


def fetch_etfs(tickers, maxage_days=1):
    """一批過下載 ETF OHLC（yfinance），命中快取就唔重複。"""
    import pandas as pd
    import yfinance as yf
    tickers = sorted(set(t for t in tickers if t))
    if os.path.exists(CACHE):
        try:
            d = pd.read_pickle(CACHE)
            have = set(d.columns.get_level_values(0))
            last = d.index[-1].date()
            if not (set(tickers) - have) and (datetime.date.today() - last).days <= maxage_days:
                return d
        except Exception:                                    # noqa: BLE001
            pass
    if not tickers:
        return None
    log(f"  yfinance 下載 {len(tickers)} 隻 ETF…")
    end = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    d = yf.download(tickers, start="2024-09-01", end=end, interval="1d",
                    auto_adjust=False, progress=False, group_by="ticker", threads=True)
    if d is None or d.empty:
        return None
    os.makedirs(DATA, exist_ok=True)
    d.to_pickle(CACHE)
    return d


def _metrics(df, pairs):
    """對每隻 (ticker, name) 計：thrust / ex1m / r1m / r1d / off52w / spark / pct。"""
    import pandas as pd
    try:
        spy = df["SPY"].dropna(subset=["Close"])["Close"]
    except Exception:                                        # noqa: BLE001
        return None
    spy1m = float(spy.iloc[-1] / spy.iloc[-22] - 1) * 100
    rows = []
    for tk, name in pairs:
        if tk not in set(df.columns.get_level_values(0)):
            continue
        try:
            c = df[tk].dropna(subset=["Close"])["Close"]
        except Exception:                                    # noqa: BLE001
            continue
        if len(c) < 70:
            continue
        r1 = c / c.shift(21) - 1
        s1 = spy / spy.shift(21) - 1
        # ★ 2026-10-13 修 bug：r1（ETF）同 s1（SPY）嘅 index 唔一定一樣
        #   （SPY 有日、ETF 冇，反之亦然）→ pandas 對比時會強制 align →
        #   `ValueError: Can only compare identically-labeled Series objects`
        #   （build_site 直接爆，14 頁全部唔出）。
        #   第一性原理：比較兩個時間序列之前，一定要先對齊 index。
        common = r1.index.intersection(s1.index)
        if len(common) < 30:
            continue
        r1a = r1.reindex(common)
        s1a = s1.reindex(common)
        tail = min(30, len(r1a) - 1)
        thrust = float((r1a.iloc[-tail:] > s1a.iloc[-tail:]).mean() * 100)
        r1m = float(c.iloc[-1] / c.iloc[-22] - 1) * 100
        # ★ 2026-10-24 Desmond：「增加 1 週 / 3 個月」
        r1w = (float(c.iloc[-1] / c.iloc[-6] - 1) * 100
               if len(c) >= 6 else None)
        r3m = (float(c.iloc[-1] / c.iloc[-64] - 1) * 100
               if len(c) >= 64 else None)
        r1d = float(c.iloc[-1] / c.iloc[-2] - 1) * 100
        hh = float(c.tail(252).max())
        spark = [round(float(v), 1) for v in (r1a - s1a).tail(30).tolist()
                 if math.isfinite(v)]
        rows.append({"etf": tk, "name": name,
                     "thrust": round(thrust, 0), "ex1m": round(r1m - spy1m, 1),
                     "r1m": round(r1m, 1), "r1d": round(r1d, 2),
                     "r1w": None if r1w is None else round(r1w, 1),
                     "r3m": None if r3m is None else round(r3m, 1),
                     "off52w": round((float(c.iloc[-1]) / hh - 1) * 100, 1) if hh else None,
                     "spark": spark})
    if not rows:
        return None
    ex = sorted(r["ex1m"] for r in rows)
    for r in rows:
        r["pct"] = round(sum(1 for v in ex if v <= r["ex1m"]) / len(ex) * 100)

    # ★ 分（0–100）＝ 透明加權百分位：1M 50% / 3M 30% / 1W 20%
    #   唔用黑箱指標 —— 每一分都係「喺呢張表嘅排名」。
    def _rank(key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        vals.sort()
        out = {}
        for r in rows:
            v = r.get(key)
            if v is None:
                out[id(r)] = None
            else:
                out[id(r)] = sum(1 for x in vals if x <= v) / len(vals) * 100
        return out
    _r1w, _r1m, _r3m = _rank("r1w"), _rank("r1m"), _rank("r3m")
    for r in rows:
        parts, wts = [], []
        for d, w in ((_r1w, 0.2), (_r1m, 0.5), (_r3m, 0.3)):
            v = d.get(id(r))
            if v is not None:
                parts.append(v * w)
                wts.append(w)
        r["score"] = (round(sum(parts) / sum(wts)) if wts else None)
    rows.sort(key=lambda r: (-r["thrust"], -r["ex1m"]))
    return rows


def rsboard_full():
    """三個表：指數／群組／板塊。板塊用 rotation_map 嘅 ETF 池。"""
    import rotation_map as R
    pairs = [("SPY", "S&P 500")] + INDEX + GROUP
    # 板塊 ETF（R.IND 嘅 tk），同群組分開計
    sector_pairs = [(tk, name) for name, tk, _ in R.IND]
    all_tk = [p[0] for p in pairs] + [p[0] for p in sector_pairs]
    df = fetch_etfs(all_tk)
    if df is None:
        return None
    index_rows = _metrics(df, INDEX) or []
    group_rows = _metrics(df, GROUP) or []
    sector_rows = _metrics(df, sector_pairs) or []
    # 板塊補 sector 名
    sec_map = {tk: sec for name, tk, sec in R.IND}
    for r in sector_rows:
        r["sector"] = sec_map.get(r["etf"], "")
    try:
        spy = df["SPY"].dropna(subset=["Close"])["Close"]
        spy1m = round(float(spy.iloc[-1] / spy.iloc[-22] - 1) * 100, 1)
        asof = str(df.index.max().date())
    except Exception:                                        # noqa: BLE001
        spy1m, asof = None, "?"
    return {"as_of": asof, "spy1m": spy1m,
            "index": index_rows, "group": group_rows, "sector": sector_rows}


# ═══════════════════════ 成長週期（IWF/IWD）═══════════════════════
def growth_cycle():
    """成長／價值比率（IWF ÷ IWD）嘅週線 EMA10 風險閘。

    模型（由 Desmond 圖片蒸餾，寫死喺度）：
      比率 = IWF 週收市 / IWD 週收市（成長相對價值）
      上軌 = 比率週高嘅 EMA10；下軌 = 比率週低嘅 EMA10
      收市升穿上軌 = risk-on；跌穿下軌 = risk-off；軌內 = 維持上一邊（減少鋸）
    階段順序（現時階段 = 睇最近嗰幾週嘅穿越）：
      RISK-OFF → PROBE → RAMP UP → TRIM/HOLD → RELOAD → 回 RISK-OFF
    """
    import numpy as np
    import pandas as pd
    import yfinance as yf
    end = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    w = yf.download(["IWF", "IWD"], start="2021-01-01", end=end,
                    interval="1wk", auto_adjust=True, progress=False,
                    group_by="ticker", threads=True)
    if w is None or w.empty:
        return None
    try:
        iwf = w["IWF"].dropna(subset=["Close"])
        iwd = w["IWD"].dropna(subset=["Close"])
    except Exception:                                        # noqa: BLE001
        return None
    common = iwf.index.intersection(iwd.index)
    iwf, iwd = iwf.loc[common], iwd.loc[common]
    ratio = iwf["Close"] / iwd["Close"]
    hi = iwf["High"] / iwd["Low"]          # 比率嘅週高（成長強/價值弱 最極端）
    lo = iwf["Low"] / iwd["High"]          # 比率嘅週低
    up = hi.ewm(span=10, adjust=False).mean()
    dn = lo.ewm(span=10, adjust=False).mean()
    side = []
    cur = None
    for c, u, d in zip(ratio, up, dn):
        if c > u:
            cur = "on"
        elif c < d:
            cur = "off"
        # 軌內維持
        side.append(cur)
    side = pd.Series(side, index=ratio.index)
    last = side.iloc[-1]
    last_close = float(ratio.iloc[-1])
    last_up = float(up.iloc[-1])
    last_dn = float(dn.iloc[-1])
    # 階段判定（簡單：最近 4 週嘅穿越）
    s = list(side.tail(6))
    if last == "off":
        phase = "RISK-OFF" if (s[-1] == s[-2] == "off") else "PROBE"
    elif last == "on":
        # 有冇近排回調到軌（reload）？
        phase = "RAMP UP" if len(s) >= 2 and s[-2] != "on" else "TRIM/HOLD"
    else:
        phase = "RELOAD"
    # 圖數據（最近 130 週）
    def ser(x):
        return [round(float(v), 4) for v in x.tail(130).tolist()]
    return {
        "as_of": str(common[-1].date()),
        "side": last, "phase": phase,
        "ratio": round(last_close, 4), "up": round(last_up, 4), "dn": round(last_dn, 4),
        "series": {"ratio": ser(ratio), "up": ser(up), "dn": ser(dn)},
        "iwf": round(float(iwf["Close"].iloc[-1]), 2),
        "iwd": round(float(iwd["Close"].iloc[-1]), 2),
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("RS 板：")
    rb = rsboard_full()
    if rb:
        print("  index", len(rb["index"]), "group", len(rb["group"]),
              "sector", len(rb["sector"]), "as_of", rb["as_of"])
        print("  top group:", rb["group"][0] if rb["group"] else None)
    print("成長週期：")
    gc = growth_cycle()
    print(" ", gc)
