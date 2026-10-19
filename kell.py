#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kell.py — Oliver Kell「Cycle of Price Action」六階段分類器（web 版）

Desmond 2026-10-11 網站 item 7：「Oliver Kell market cycle 每隻股標位」

★ 定義來源（KB 冇，所以攞原文）：kelltrading.com（Oliver Kell 本人網站）
＋ 2020 USIC 研討會（+941% 冠軍）。基準 = 日線 10 EMA + 20 EMA。

  ① Reversal Extension   恐慌拋售、遠離 EMA（底部）      → 唔好追
  ② Wedge Pop            突破楔形／基底第一支推力         → ★佢話「最高機率多頭入場」
  ③ EMA Crossback        升勢中回踩 10/20 EMA 受支撐     → ★佢話「第二次入場」
  ④ Base 'n Break        沿上升 EMA 整固後破新高         → continuation
  ⑤ Exhaustion Extension 拋物線遠離 10 EMA              → 減倉止賺
  ⑥ Wedge Drop           跌穿 10 EMA，升勢破壞           → 離場

★ 已驗證（`trading-os-lab/kell_cycle.py`，1,279 單實盤）：
    ③ EMA Crossback 係 Desmond 最好嘅位置（持 ≥1 日：52.5% 勝率、+7.014%）
    ⑤ Exhaustion Extension 最差（20% 勝率、−1.675%）

呢個模組係同一個分類器嘅 web 版 —— 圖表要用。
**唔可以有第二套實作**（EDGE-036 教訓）：門檻全部同 lab 版本一致。
"""
import math
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "kell_ohlc.pkl")

# 六階段（同 lab 版本一致）
STAGES = ["① Reversal Extension", "② Wedge Pop", "③ EMA Crossback",
          "④ Base 'n Break", "⑤ Exhaustion Extension", "⑥ Wedge Drop",
          "— 無法分類"]

# ★ 2026-10-20 Desmond：「kell 階段全部轉返做英文」
# 保留 dict 介面（下游有 .get()），但值 = 英文原名，唔再譯中文
STAGE_SHORT = {s: s for s in STAGES}

# 階段顏色（同網站主題一致）
STAGE_COLOR = {
    "① Reversal Extension": "#f59e0b",
    "② Wedge Pop": "#22c55e",
    "③ EMA Crossback": "#38bdf8",
    "④ Base 'n Break": "#4ade80",
    "⑤ Exhaustion Extension": "#ef4444",
    "⑥ Wedge Drop": "#94a3b8",
    "— 無法分類": "#64748b",
}

# ★ 已量度嘅勝率（lab：1,279 單實盤，持倉 ≥1 日）—— 放喺圖上做參考
STAGE_WR = {
    "① Reversal Extension": None,
    "② Wedge Pop": 47.8,
    "③ EMA Crossback": 52.5,
    "④ Base 'n Break": None,      # 樣本不足
    "⑤ Exhaustion Extension": 20.0,
    "⑥ Wedge Drop": 59.1,
    "— 無法分類": None,
}

# 佢叫我哋做咩（原文語意）
STAGE_ACTION = {
    "① Reversal Extension": "唔好追（未確認）",
    "② Wedge Pop": "★ 佢話最高機率入場（我實盤：47.8%）",
    "③ EMA Crossback": "★ 佢話第二次入場（我實盤最好：52.5%）",
    "④ Base 'n Break": "continuation 加倉",
    "⑤ Exhaustion Extension": "減倉止賺（我實盤最差：20%）",
    "⑥ Wedge Drop": "離場",
    "— 無法分類": "─",
}


def log(*a):
    print(*a, file=sys.stderr)


def fetch(tickers, maxage_days=1):
    """抓 1 年日線（足夠 50SMA + 10/20 EMA）。"""
    import yfinance as yf
    if os.path.exists(CACHE):
        try:
            d = pd.read_pickle(CACHE)
            have = set(d.columns.get_level_values(0))
            if not (set(tickers) - have):
                m = max(pd.Timestamp(c) for c in d.index[-1:])
                if (pd.Timestamp.now() - m).days <= maxage_days:
                    return d
        except Exception:
            pass
    old = None
    if os.path.exists(CACHE):
        try:
            old = pd.read_pickle(CACHE)
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
        log(f"⚠ kell fetch 失敗：{type(e).__name__}")
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


def classify_row(r):
    """單一 bar → 階段。★ 優先次序同 lab 版一模一樣。"""
    try:
        px = float(r["Close"]); e10 = float(r["e10"]); e20 = float(r["e20"])
        a = float(r["atr"]); a10 = float(r["atrx10"])
        s10 = float(r["slope10"])
        up = bool(r["up"]); nh = bool(r["newhigh20"]); rng = float(r["rng10"])
        lo = float(r["Low"]); cu = bool(r["cross_up10"]); cd = bool(r["cross_dn10"])
    except Exception:
        return "— 無法分類"
    if not all(math.isfinite(v) for v in (px, e10, e20, a, a10, s10, rng)):
        return "— 無法分類"
    if up and a10 >= 2.5:
        return "⑤ Exhaustion Extension"
    if cd or (not up and s10 < 0 and a10 < -0.5):
        return "⑥ Wedge Drop"
    if up and nh and rng <= 12.0:
        return "④ Base 'n Break"
    if up and lo <= e10 and px >= e10 and s10 > 0:
        return "③ EMA Crossback"
    if cu:
        return "② Wedge Pop"
    if (not up) and a10 <= -1.0 and s10 <= 0:
        return "① Reversal Extension"
    if up:
        return "③ EMA Crossback" if a10 <= 2.5 else "⑤ Exhaustion Extension"
    return "⑥ Wedge Drop"


def stages(tickers, ohlc=None, maxage_days=1):
    """回傳 {ticker: {stage, short, color, action, wr, atrx10, dist10, close}}。"""
    if not tickers:
        return {}
    d = ohlc if ohlc is not None else fetch(list(tickers), maxage_days)
    if d is None or not len(d.columns):
        return {}
    out = {}
    # 基準（SPY）用嚟計相對強度 —— 唔一定齊，冇就唔用
    for tk in tickers:
        try:
            f = d[tk].dropna(subset=["Close"]).copy()
        except Exception:
            continue
        if len(f) < 30:
            continue
        c, h, l = f["Close"], f["High"], f["Low"]
        pc = c.shift(1)
        tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
        f["atr"] = tr.rolling(14).mean()
        f["e10"] = c.ewm(span=10, adjust=False).mean()
        f["e20"] = c.ewm(span=20, adjust=False).mean()
        f["sma50"] = c.rolling(50).mean()
        f["hh20"] = h.rolling(20).max()
        f["rng10"] = (h.rolling(10).max() - l.rolling(10).min()) / c * 100
        f["atrx10"] = (c - f["e10"]) / f["atr"]
        f["slope10"] = (f["e10"] / f["e10"].shift(5) - 1) * 100
        f["above10"] = c > f["e10"]
        f["cross_up10"] = f["above10"] & (~f["above10"].shift(1).fillna(False))
        f["cross_dn10"] = (~f["above10"]) & (f["above10"].shift(1).fillna(False))
        f["up"] = f["e10"] > f["e20"]
        f["newhigh20"] = h >= f["hh20"].shift(1)
        r = f.iloc[-1]
        st = classify_row(r)
        a10 = float(r["atrx10"]) if math.isfinite(r["atrx10"]) else None
        out[tk] = {
            "ticker": tk, "stage": st, "short": STAGE_SHORT.get(st, st),
            "color": STAGE_COLOR.get(st, "#64748b"),
            "action": STAGE_ACTION.get(st, "─"),
            "wr": STAGE_WR.get(st),
            "atrx10": round(a10, 2) if a10 is not None else None,
            "close": round(float(r["Close"]), 2),
            "up": bool(r["up"]),
        }
    return out


def chip(tk, info):
    """一個 HTML chip（表格用）。"""
    if not info:
        return '<span class="kchip dim">—</span>'
    col = info["color"]
    wr = f"｜實盤 {info['wr']:.0f}%" if info.get("wr") else ""
    return (f'<span class="kchip" style="border-color:{col};color:{col}" '
            f'title="{info["action"]}{wr}">{info["short"]}</span>')


def legend_html():
    """階段圖例（放喺表下面）。"""
    rows = []
    for st in STAGES:
        if st == "— 無法分類":
            continue
        col = STAGE_COLOR[st]
        wr = STAGE_WR.get(st)
        wr_txt = f"實盤勝率 {wr:.0f}%" if wr else "樣本不足"
        rows.append(
            f'<div class="kleg"><span class="kdot" style="background:{col}"></span>'
            f'<b>{STAGE_SHORT[st]}</b>'
            f'<span class="dim">{STAGE_ACTION[st]}｜{wr_txt}</span></div>')
    return ('<div class="klegend">' + "".join(rows) + '</div>'
            '<div class="note">Oliver Kell「Cycle of Price Action」六階段，'
            '基準＝日線 10 EMA + 20 EMA。'
            '定義來源：kelltrading.com（佢本人網站）+ 2020 USIC 研討會。'
            '勝率數字來自我哋 1,279 單實盤（持倉 ≥1 日）—— '
            '<b>③ EMA Crossback 係最好，⑤ Exhaustion Extension 最差</b>。</div>')


KELL_CSS = """
.kchip{display:inline-block;padding:1px 7px;border:1px solid;border-radius:9px;
  font-size:11px;white-space:nowrap;font-weight:600}
.kchip.dim{border-color:#475569;color:#64748b}
.klegend{display:flex;flex-wrap:wrap;gap:6px 16px;margin:8px 0 4px}
.kleg{display:flex;align-items:center;gap:6px;font-size:12px}
.kdot{width:9px;height:9px;border-radius:50%;flex:0 0 auto}
.haskell{font-weight:800}
"""


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:] or ["NVDA", "AMD", "MU", "CRWD"]
    res = stages(args)
    for t in args:
        i = res.get(t)
        if i:
            print(f"  {t:<7}{i['short']:<14}ATRX10 {i['atrx10']:>+6.2f}"
                  f"  {i['action']}")
        else:
            print(f"  {t:<7}（冇數據）")
