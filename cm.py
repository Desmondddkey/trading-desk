#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cm.py — 1chartmaster「RS Leader Pullback Buy」分類器

Desmond 2026-10-11 網站指令：
  「增加 1chartmaster 針對既 RA leader pull back buy 開多個新分類
   你可以查詢我既訂閱 read only 蒸餾出實際做法」

★ 蒸餾來源（證據庫，全部原文，唔准演繹）：
  `trading-os-lab/xtraders/1chartmaster/corpus.json`
  · Tweet 2100021732518051902（2026-09-16）「Why Relative Strength 🔵 on
    Weakness is the Ultimate Edge」— 三階段執行框架
  · Tweet 2086787063815229930（2026-08-10）「buying tight risk spots and
    then trimming into vertical strength」— 8 EMA / 21 EMA 入場位

原文關鍵句（逐字）：
  「you track Relative Strength (RS) leaders and buy them when they
    pull back into structural support」
  「When the market drops 2%, an RS leader might only drop 0.5% or hold
    a tight inside day at a key moving average. That is your tell.」
  「If volume dries up on the pullback and buyers step in to defend the
    level, that's your trigger.」
  「like the 8-week EMA, an inside day, or a volume pivot」
  「narrow range right near moving average support (like the 8 EMA or 21 EMA)」

→ 量化為 5 個條件（L1–L5），全部可從日線 OHLCV 算出。
"""
import math
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "cm_ohlc.pkl")

# ── 量化門檻（寫死，唔准見到數才改）─────────────────────────────
RS_EXCESS_1M = 0.0        # L1: 1 個月超額回報 > 0（跑贏大市）
RS_EXCESS_3M = 0.0        # L1: 3 個月超額回報 > 0（持續）
SUP_TOL_PCT = 3.0         # L2: 距均線支撐 ≤ 3%（8EMA / 21EMA / 8週EMA）
DRYUP_VOL = 0.85          # L3: 回調日成交量 < 0.85 × 20 日均量
DEFEND_CLOSE = 0.0        # L4: 收市 ≥ 昨收（買家出嚟守）
TIGHT_RNG = 6.0           # L5: 5 日高低範圍 ≤ 6%（tight risk）

# RAF（Relative-strength And Footprint）分級 —— 5 個條件嘅組合
GRADES = [
    (5, "A+ 完美", "#22c55e", "五個條件全中：領導股 + 回調到支撐 + 量縮 + 買家守 + 風險窄"),
    (4, "A 強", "#4ade80", "四個條件中：標準 1CM 設置"),
    (3, "B 觀察", "#38bdf8", "三個條件中：值得放監察名單"),
    (2, "C 邊緣", "#94a3b8", "兩個條件中：唔夠"),
    (0, "D 唔算", "#475569", "少於兩個條件"),
]


def log(*a):
    print(*a, file=sys.stderr)


def fetch(tickers, maxage_days=1):
    """抓 1 年日線（夠 8週EMA = 40日、21EMA、量能）。"""
    import yfinance as yf
    old = None
    if os.path.exists(CACHE):
        try:
            old = pd.read_pickle(CACHE)
            have = set(old.columns.get_level_values(0))
            if not (set(tickers) - have):
                m = pd.Timestamp(old.index[-1])
                if (pd.Timestamp.now() - m).days <= maxage_days:
                    return old
        except Exception:
            old = None
    need = list(tickers)
    if old is not None:
        have = set(old.columns.get_level_values(0))
        need = [t for t in tickers if t not in have]
        if not need:
            return old
    try:
        new = yf.download(need, period="1y", interval="1d", auto_adjust=False,
                          progress=False, group_by="ticker", threads=True)
    except Exception as e:                                   # noqa: BLE001
        log(f"⚠ cm fetch 失敗：{type(e).__name__}")
        return old
    if old is not None and len(new.columns):
        parts = [old]
        for t in sorted(set(new.columns.get_level_values(0))):
            x = new[t].copy()
            if isinstance(x, pd.Series):
                continue
            x.columns = pd.MultiIndex.from_product([[t], list(x.columns)])
            parts.append(x)
        new = pd.concat(parts, axis=1)
    os.makedirs(DATA, exist_ok=True)
    try:
        new.to_pickle(CACHE)
    except Exception:
        pass
    return new


def grade(n):
    for lo, name, col, desc in GRADES:
        if n >= lo:
            return name, col, desc
    return GRADES[-1][1], GRADES[-1][2], GRADES[-1][3]


def classify(tickers, ohlc=None, bench="SPY", maxage_days=1):
    """回傳 {ticker: {...5 個條件 + 分級 + 數字}}。

    5 個條件（對應原文）：
      L1 RS 領導    1M 及 3M 超額回報 > 0（原文 Step 1）
      L2 回調到支撐  距 8EMA / 21EMA / 40SMA(8週) 任一個 ≤ 3%（原文入場位）
      L3 量縮       今日量 < 0.85 × 20日均量（原文「volume dries up」）
      L4 買家守     收市 ≥ 昨收（原文「buyers step in to defend」）
      L5 風險窄     5 日高低範圍 ≤ 6%（原文「tight risk」）
    """
    syms = list(tickers)
    d = ohlc if ohlc is not None else fetch(syms + [bench], maxage_days)
    if d is None or not len(d.columns):
        return {}
    have = set(d.columns.get_level_values(0))
    if bench not in have:
        bench = None
    ref1 = ref3 = None
    if bench:
        b = d[bench].dropna(subset=["Close"])["Close"]
        if len(b) > 64:
            ref1 = float(b.iloc[-1] / b.iloc[-22] - 1) * 100
            ref3 = float(b.iloc[-1] / b.iloc[-64] - 1) * 100
    out = {}
    for tk in syms:
        try:
            f = d[tk].dropna(subset=["Close"]).copy()
        except Exception:
            continue
        if len(f) < 60:
            continue
        c, h, l, v = f["Close"], f["High"], f["Low"], f["Volume"]
        e8 = c.ewm(span=8, adjust=False).mean()
        e21 = c.ewm(span=21, adjust=False).mean()
        s40 = c.rolling(40).mean()          # 8 週 EMA 嘅日線代理
        v20 = v.rolling(20).mean()
        px = float(c.iloc[-1])
        r1 = float(c.iloc[-1] / c.iloc[-22] - 1) * 100 if len(c) > 22 else None
        r3 = float(c.iloc[-1] / c.iloc[-64] - 1) * 100 if len(c) > 64 else None
        ex1 = (r1 - ref1) if (r1 is not None and ref1 is not None) else r1
        ex3 = (r3 - ref3) if (r3 is not None and ref3 is not None) else r3
        sup = {"8EMA": float(e8.iloc[-1]), "21EMA": float(e21.iloc[-1]),
               "8週(40SMA)": float(s40.iloc[-1])}
        best = None
        for nm, lvl in sup.items():
            if lvl > 0:
                dist = (px / lvl - 1) * 100
                if best is None or abs(dist) < abs(best[1]):
                    best = (nm, dist)
        vol_now = float(v.iloc[-1]) if math.isfinite(v.iloc[-1]) else None
        vol_avg = float(v20.iloc[-1]) if math.isfinite(v20.iloc[-1]) else None
        rvol = (vol_now / vol_avg) if (vol_now and vol_avg) else None
        prev_c = float(c.iloc[-2])
        rng5 = ((h.rolling(5).max() - l.rolling(5).min()) / c * 100).iloc[-1]
        rng5 = float(rng5) if math.isfinite(rng5) else None

        c1 = (ex1 is not None and ex3 is not None
              and ex1 > RS_EXCESS_1M and ex3 > RS_EXCESS_3M)
        c2 = bool(best and abs(best[1]) <= SUP_TOL_PCT)
        c3 = bool(rvol is not None and rvol < DRYUP_VOL)
        c4 = bool(px >= prev_c)
        c5 = bool(rng5 is not None and rng5 <= TIGHT_RNG)
        conds = [c1, c2, c3, c4, c5]
        n = sum(conds)
        gname, gcol, gdesc = grade(n)
        out[tk] = {
            "ticker": tk, "n": n, "grade": gname, "color": gcol, "desc": gdesc,
            "c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5,
            "ex1": round(ex1, 2) if ex1 is not None else None,
            "ex3": round(ex3, 2) if ex3 is not None else None,
            "sup": best[0] if best else None,
            "sup_dist": round(best[1], 2) if best else None,
            "rvol": round(rvol, 2) if rvol is not None else None,
            "rng5": round(rng5, 2) if rng5 is not None else None,
            "close": round(px, 2),
        }
    return out


def chip(tk, info):
    if not info:
        return '<span class="cmchip dim">—</span>'
    return (f'<span class="cmchip" style="border-color:{info["color"]};'
            f'color:{info["color"]}" title="{info["desc"]}">'
            f'{info["grade"]} {info["n"]}/5</span>')


def detail_cells(info):
    """表格用：5 個條件逐個打勾。"""
    if not info:
        return "<td>—</td>" * 5
    def m(b):
        return ('<span style="color:#22c55e">✓</span>' if b
                else '<span style="color:#475569">·</span>')
    sup = (f'{info["sup"]} {info["sup_dist"]:+.1f}%'
           if info.get("sup") else "—")
    return (f'<td>{m(info["c1"])} {info["ex1"]:+.0f}/{info["ex3"]:+.0f}%</td>'
            f'<td>{m(info["c2"])} {sup}</td>'
            f'<td>{m(info["c3"])} {info["rvol"] if info["rvol"] is not None else "—"}×</td>'
            f'<td>{m(info["c4"])}</td>'
            f'<td>{m(info["c5"])} {info["rng5"] if info["rng5"] is not None else "—"}%</td>')


def legend_html():
    rows = []
    for lo, name, col, desc in GRADES:
        rows.append(f'<div class="cmleg"><span class="cmdot" style="background:{col}">'
                    f'</span><b>{name}</b><span class="dim">{desc}</span></div>')
    return (
        '<div class="cmlegend">' + "".join(rows) + '</div>'
        '<div class="note">'
        '<b>1chartmaster「RS Leader Pullback Buy」</b>——'
        '原文：「you track Relative Strength (RS) leaders and buy them when they '
        '<b>pull back into structural support</b>」'
        '（Tweet 2100021732518051902，2026-09-16）。<br>'
        '五個條件對應佢原文嘅三階段框架：'
        '<b>L1</b> RS 領導（Step 1 識別）｜'
        '<b>L2</b> 回調到 8EMA／21EMA／8週 EMA 支撐（Step 2 等佢嚟）｜'
        '<b>L3</b> 回調時量縮（Step 3「volume dries up」）｜'
        '<b>L4</b> 買家守支撐（Step 3「buyers step in to defend」）｜'
        '<b>L5</b> 風險窄（「tight risk」）。<br>'
        '證據庫：<code>trading-os-lab/xtraders/1chartmaster/</code>'
        '（31 條蒸餾 + 54 條 exact timestamp）。'
        '</div>')


CM_CSS = """
.cmchip{display:inline-block;padding:1px 7px;border:1px solid;border-radius:8px;
  font-size:10.5px;white-space:nowrap;font-weight:700}
.cmchip.dim{border-color:#475569;color:#64748b}
.cmlegend{display:flex;flex-wrap:wrap;gap:6px 16px;margin:8px 0 4px}
.cmleg{display:flex;align-items:center;gap:6px;font-size:11.5px}
.cmdot{width:9px;height:9px;border-radius:50%;flex:0 0 auto}
"""


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:] or ["NVDA", "CRWD", "PLTR", "AMD"]
    res = classify(args)
    for t in args:
        i = res.get(t)
        if i:
            print(f"  {t:<7}{i['grade']:<10}{i['n']}/5"
                  f"  ex1 {i['ex1']:+.1f}% / ex3 {i['ex3']:+.1f}%"
                  f"  {i['sup']} {i['sup_dist']:+.1f}%  rvol {i['rvol']}")
        else:
            print(f"  {t:<7}（冇數據）")
