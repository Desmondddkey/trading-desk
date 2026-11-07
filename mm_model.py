# -*- coding: utf-8 -*-
"""mm_model.py — MM Model（Mark Minervini 式市場時機模型）25 子模型複合分

原圖（Desmond 2026-11-07）："The Trading Model that could save your portfolio"
  · 25 個子模型 → 合成指標 0-100
  · 門檻 70（圖中另有一條「Gold 門檻 75」）
  · 高分 = 全倉；低分 = 現金；中間 = 減半
  · 上圖 = 標普（log）+ 綠／紅底代表 risk-on / risk-off
  · 中圖 = 合成指標 0-100（70 / 30 線）
  · 下圖 = 25 個模型逐個狀態

★★ 誠實聲明（SOUL §8.28）
  Minervini 原版 25 個子模型冇公開。呢 25 條係【我方可核 proxy】：
  每條只用公開指數價／VIX／利率／美元計，逐條列喺頁面，任何人都重算得到。
  唔可以當成官方數字，亦唔可以當投資建議。

定義（寫死）
  分數 = 25 條 true 嘅比例 × 100（每條等權 4 分）
  倉位 = <55 全現金｜55-70 線性｜≥70 全倉
  回測 = 今日收市計分，下一個交易日開倉（無前視），成本 0.02% 每邊
更新：cron 平日 17:15 HKT（18:00 前 build 好）
"""
from __future__ import annotations

import html as _h
import io
import json
import os
import pickle
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "mm_model.pkl")
OUT = os.path.join(HERE, "output")
CACHE_H = 6.0
FULL_AT, HALF_AT, CASH_AT = 70, 55, 55
GOLD_AT = 75
COST = 0.0002

TICKERS = ["^GSPC", "^IXIC", "^DJI", "^RUT", "^VIX", "^TNX", "DX-Y.NYB"]


def _esc(x):
    return _h.escape(str(x if x is not None else ""))


def log(*a):
    print(*a, flush=True)


def fetch(refresh=False):
    if not refresh and os.path.exists(CACHE):
        if (time.time() - os.path.getmtime(CACHE)) / 3600.0 < CACHE_H:
            try:
                with io.open(CACHE, "rb") as f:
                    d = pickle.load(f)
                if d and "^GSPC" in d:
                    return d
            except Exception:                                # noqa: BLE001
                pass
    import yfinance as yf
    d = {}
    try:
        for t in TICKERS:
            s = yf.download(t, period="max", interval="1d", auto_adjust=True,
                            progress=False, threads=False)
            if s is None or len(s) == 0:
                continue
            if hasattr(s.columns, "nlevels") and s.columns.nlevels > 1:
                s.columns = [c[0] for c in s.columns]
            s = s.rename(columns=str.lower)["close"].dropna()
            if len(s) > 200:
                d[t] = s
        if "^GSPC" in d:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            with io.open(CACHE, "wb") as f:
                pickle.dump(d, f)
        return d
    except Exception as e:                                   # noqa: BLE001
        log(f"⚠ mm fetch：{type(e).__name__}: {e}")
        try:
            with io.open(CACHE, "rb") as f:
                return pickle.load(f)
        except Exception:                                    # noqa: BLE001
            return {}


def compute(d):
    import numpy as np
    import pandas as pd

    px = d["^GSPC"]
    df = pd.DataFrame({"c": px})
    df["sma200"] = df["c"].rolling(200).mean()
    df["sma50"] = df["c"].rolling(50).mean()
    df["sma20"] = df["c"].rolling(20).mean()
    df["ema21"] = df["c"].ewm(span=21, adjust=False).mean()
    df["hi252"] = df["c"].rolling(252).max()
    df["hi63"] = df["c"].rolling(63).max()
    tr = df["c"].pct_change().abs()
    df["vol20"] = df["c"].pct_change().rolling(20).std() * np.sqrt(252) * 100
    df["atr_pct"] = tr.rolling(20).mean() * 100

    def al(tk):
        s = d.get(tk)
        return s.reindex(df.index).ffill() if s is not None else None

    vix, tnx, dxy = al("^VIX"), al("^TNX"), al("DX-Y.NYB")
    ixic, iuji, iwm = al("^IXIC"), al("^DJI"), al("^RUT")

    def ma(s, n):
        return s.rolling(n).mean() if s is not None else None

    R = {}
    R["標普 > 200MA"] = df["c"] > df["sma200"]
    R["標普 > 50MA"] = df["c"] > df["sma50"]
    R["50MA > 200MA"] = df["sma50"] > df["sma200"]
    R["200MA 上升（20日）"] = df["sma200"] > df["sma200"].shift(20)
    R["50MA 上升（10日）"] = df["sma50"] > df["sma50"].shift(10)
    R["標普 > 21EMA"] = df["c"] > df["ema21"]
    R["21EMA > 50MA"] = df["ema21"] > df["sma50"]
    R["標普 > 20MA"] = df["c"] > df["sma20"]
    R["20 日回報 > 0"] = df["c"].pct_change(20) > 0
    R["60 日回報 > 0"] = df["c"].pct_change(60) > 0
    R["距 52 週高 ≤ 5%"] = df["c"] >= df["hi252"] * 0.95
    R["52 週高喺 63 日內"] = df["hi252"] == df["hi63"]
    R["連續 50 日喺 200MA 上"] = (df["c"] > df["sma200"]).rolling(50).sum() >= 50
    R["距 200MA < 15%"] = df["c"] < df["sma200"] * 1.15
    R["VIX < 20"] = vix < 20
    R["VIX < 25 且唔急升"] = (vix < 25) & (vix < vix.shift(5) * 1.2)
    R["ATR20% < 2.5"] = df["atr_pct"] < 2.5
    R["20 日波動 < 25%"] = df["vol20"] < 25
    R["距 1 年高 > −10%"] = df["c"] > df["hi252"] * 0.90
    R["納指 > 200MA"] = ixic > ma(ixic, 200)
    R["道指 > 200MA"] = iuji > ma(iuji, 200)
    R["羅素 > 200MA"] = iwm > ma(iwm, 200)
    R["羅素 > 50MA"] = iwm > ma(iwm, 50)
    R["10 年息 20 日唔急升"] = tnx < tnx.shift(20) + 0.2
    R["美元 20 日唔急升"] = dxy < dxy.shift(20) * 1.02

    names = list(R)
    M = pd.DataFrame({n: R[n].astype(float) for n in names})

    # ★ 樣本起點 = 全部輸入都有數據嘅第一日（VIX 1990 起）——
    #   否則 NaN 比較會變 False，早期分數係假嘅（Missing ≠ Zero）
    firsts = [df["sma200"].first_valid_index()]
    for x in (vix, tnx, dxy, ixic, iuji, iwm):
        if x is not None:
            firsts.append(x.first_valid_index())
    start0 = max([x for x in firsts if x is not None])
    M = M.loc[start0:]
    df = df.loc[start0:]
    score = M.mean(axis=1) * 100

    # 倉位（今日收市決定，下一日生效）：圖中 70 / 30 兩條線
    # 倉位映射：<55 = 全現金（唔交易）｜55-70 = 線性 0→100｜≥70 = 全倉
    # ★ 原版 75 分 → 71% 倉，所以高分區唔一定 100%，用線性最接近
    expo = pd.Series(
        np.where(score >= FULL_AT, 1.0,
                 np.where(score >= CASH_AT,
                          (score - CASH_AT) / (FULL_AT - CASH_AT), 0.0)),
        index=df.index).clip(0, 1)
    expo = expo.shift(1).fillna(0.0)
    ret = df["c"].pct_change().fillna(0.0)
    trade = expo.diff().abs().fillna(0.0)
    strat = expo * ret - trade * COST
    eq = (1 + strat).cumprod()
    bh = (1 + ret).cumprod()

    def stats(e):
        yrs = len(e) / 252.0
        cagr = (e.iloc[-1] ** (1 / yrs) - 1) * 100 if yrs > 1 else 0
        dd = float((e / e.cummax() - 1).min() * 100)
        return {"cagr": round(cagr, 2), "maxdd": round(dd, 2),
                "total": round((e.iloc[-1] - 1) * 100, 1)}

    # 有效樣本：由 25 條全部有值開始
    start = M.dropna().index[0] if len(M.dropna()) else df.index[250]
    mask = df.index >= start
    return {
        "date": df.index[-1].strftime("%Y-%m-%d"),
        "score": None if pd.isna(score.iloc[-1]) else round(float(score.iloc[-1]), 0),
        "expo_today": (100 if (score.iloc[-1] >= FULL_AT) else
                       (round(float((score.iloc[-1] - CASH_AT) / (FULL_AT - CASH_AT) * 100))
                        if (score.iloc[-1] >= CASH_AT) else 0)),
        "models": [{"name": n, "on": bool(M[n].iloc[-1] == 1) if not pd.isna(M[n].iloc[-1]) else None,
                    "days": int((M[n].tail(250) == 1).sum())} for n in names],
        "stats_model": stats(eq[mask]), "stats_bh": stats(bh[mask]),
        "span": [start.strftime("%Y-%m-%d"), df.index[-1].strftime("%Y-%m-%d")],
        "chart": _series(df, score, eq, bh, expo, mask),
        "monthly": _monthly(score, expo),
        "annual": _annual(strat, ret, mask),
        "periods": _periods(eq[mask], bh[mask]),
    }


def _monthly(score, expo):
    import pandas as pd
    d = pd.DataFrame({"s": score, "a": expo * 100.0}).resample("ME").last().dropna()
    return {"date": [x.strftime("%Y-%m-%d") for x in d.index],
            "score": [round(float(v), 1) for v in d["s"]],
            "alloc": [round(float(v), 0) for v in d["a"]]}


def _annual(strat, ret, mask):
    import pandas as pd
    df = pd.DataFrame({"m": strat[mask], "b": ret[mask]})
    out = []
    for y, g in df.groupby(df.index.year):
        if len(g) < 20:
            continue
        out.append({"year": int(y),
                    "m": round(float((1 + g["m"]).prod() - 1) * 100, 1),
                    "b": round(float((1 + g["b"]).prod() - 1) * 100, 1)})
    return list(reversed(out))[:20]   # 最新年喺最上


def _periods(eq, bh):
    def seg(series, n):
        if n == "max":
            a, b = series.iloc[0], series.iloc[-1]
        elif n == "ytd":
            y0 = series[series.index.year == series.index[-1].year]
            a, b = y0.iloc[0], y0.iloc[-1]
        else:
            k = 252 * n
            if len(series) <= k:
                return None
            a, b = series.iloc[-1 - k], series.iloc[-1]
        return round((b / a - 1) * 100, 1)
    out = []
    for lab, n in (("YTD", "ytd"), ("1 年", 1), ("2 年", 2), ("5 年", 5),
                   ("10 年", 10), ("15 年", 15), ("20 年", 20), ("Max", "max")):
        a, b = seg(eq, n), seg(bh, n)
        if a is None or b is None:
            continue
        out.append((lab, (a, b)))
    return out


def _series(df, score, eq, bh, expo, mask, n=1400):
    t = df[mask]
    sc = score[mask]
    e = eq[mask]
    b = bh[mask]
    x = expo[mask]
    step = max(1, len(t) // n)

    def pick(s):
        return [None if v != v else round(float(v), 4) for v in s.iloc[::step]]

    # ★ 兩條線都由 100 起（原圖係同一 log 尺比較，唔可以一條由 1 起）
    def norm(series):
        base = series.dropna().iloc[0]
        return [None if v != v else round(float(v) / base * 100, 2) for v in series.iloc[::step]]
    return {
        "date": [d.strftime("%Y-%m-%d") for d in t.index[::step]],
        "px": norm(t["c"]),
        "score": [None if v != v else round(float(v), 1) for v in sc.iloc[::step]],
        "eq": norm(e), "bh": norm(b),
        "expo": [round(float(v), 2) for v in x.iloc[::step]],
    }


# ────────────────────────────── 圖 ──────────────────────────────
def _chart(cs, W=1160):
    if not cs or len(cs.get("px", [])) < 50:
        return '<div class="dim">DATA_UNAVAILABLE</div>'
    px, sc, eq = cs["px"], cs["score"], cs["eq"]
    n = len(px)
    pad_r = 58
    x0, x1 = 6, W - pad_r - 6
    h1, h2, h3 = 250, 90, 90
    gap = 26
    H = h1 + h2 + h3 + gap * 2 + 16

    def X(i):
        return x0 + i / max(1, n - 1) * (x1 - x0)

    valid = [v for v in px if v]
    import math as _m
    lo, hi = min(valid), max(valid)
    lo, hi = _m.log10(lo), _m.log10(hi)
    pad = (hi - lo) * 0.04
    lo, hi = lo - pad, hi + pad

    def Y(v):
        return 4 + (hi - _m.log10(v)) / (hi - lo) * (h1 - 8)

    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-width:640px;max-width:{W}px" '
         f'role="img" aria-label="MM Model 歷史">']
    # risk-on/off 底色
    for i in range(1, n):
        col = "#cfe8d8" if cs["expo"][i] >= 0.7 else ("#f2e4c2" if cs["expo"][i] >= 0.4 else "#f0d6d3")
        P.append(f'<rect x="{X(i-1):.1f}" y="0" width="{max((x1-x0)/n*1.2,0.6):.1f}" '
                 f'height="{h1}" fill="{col}" fill-opacity="0.55"/>')
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(px) if v)
    P.append(f'<polyline points="{pts}" fill="none" stroke="#334155" stroke-width="1.2"/>')
    # 分數
    y2 = h1 + gap
    P.append(f'<text x="{x0}" y="{y2-4}" font-size="9.5" fill="#6b7280">合成指標 0-100</text>')
    for lv in (FULL_AT, HALF_AT):
        yy = y2 + (100 - lv) / 100 * h2
        P.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" '
                 f'stroke="#94a3b8" stroke-dasharray="3 3" stroke-width="0.8"/>')
        P.append(f'<text x="{W-pad_r+4}" y="{yy+3:.1f}" font-size="9" fill="#6b7280">{lv}</text>')
    P.append('<polyline points="' + " ".join(
        f"{X(i):.1f},{y2 + (100-v)/100*h2:.1f}" for i, v in enumerate(sc) if v is not None)
        + '" fill="none" stroke="#1f7f52" stroke-width="1"/>')
    # 權益曲線
    y3 = y2 + h2 + gap
    P.append(f'<text x="{x0}" y="{y3-4}" font-size="9.5" fill="#6b7280">'
             f'模型（綠）vs 買入持有（灰）— log</text>')
    allv = [v for k in ("eq", "bh") for v in cs[k] if v]   # ★ 同一把尺，先可比
    la = _m.log10(min(allv)) if allv else 0
    lb = _m.log10(max(allv)) if allv else 1
    for key, col, wd in (("bh", "#94a3b8", 0.9), ("eq", "#1f7f52", 1.3)):
        vals = [v for v in cs[key] if v]
        if not vals:
            continue
        a, b = la, lb
        P.append('<polyline points="' + " ".join(
            f"{X(i):.1f},{y3 + (b - _m.log10(v)) / max(b - a, 1e-6) * h3:.1f}"
            for i, v in enumerate(cs[key]) if v) + f'" fill="none" stroke="{col}" '
            f'stroke-width="{wd}"/>')
    # 年份
    last = ""
    lastx = -1e9
    for i, ds in enumerate(cs["date"]):
        yr = ds[:4]
        if yr != last:
            last = yr
            if X(i) - lastx > (x1 - x0) * 0.07:
                lastx = X(i)
                P.append(f'<text x="{X(i):.1f}" y="{H-2}" font-size="9" fill="#6b7280" '
                         f'text-anchor="middle">{yr}</text>')
    P.append('</svg>')
    return "".join(P)


CSS = """
.mm-hero{display:flex;gap:26px;flex-wrap:wrap;align-items:flex-start}
.mm-score{font-size:46px;font-weight:800;line-height:1}
.mm-verdict{font-size:13px;font-weight:800;margin-top:6px}
.mm-meta{font-size:11px;opacity:.6;margin-top:6px}
.mm-bar{height:8px;background:rgba(148,163,184,.25);border-radius:4px;overflow:hidden;margin-top:8px;max-width:420px}
.mm-bar i{display:block;height:100%}
.mm-tbl{width:100%;border-collapse:collapse;font-size:12px}
.mm-tbl th{text-align:left;font-size:10px;letter-spacing:.05em;opacity:.55;font-weight:800;
  padding:5px 7px;border-bottom:1px solid rgba(148,163,184,.25)}
.mm-tbl td{padding:4px 7px;border-bottom:1px solid rgba(148,163,184,.1);font-variant-numeric:tabular-nums}
.mm-on{color:#1f7f52;font-weight:800}.mm-off{color:#a04a44;opacity:.8}
.mm-note{font-size:10.5px;opacity:.55;line-height:1.7;margin-top:8px}
.mm-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}
.mm-scroll svg{display:block}
"""


def build():
    import mm_view as V
    try:
        with io.open(os.path.join(OUT, "mm_model.json"), encoding="utf-8") as f:
            snap = json.load(f)
    except Exception:                                        # noqa: BLE001
        snap = None
    if not snap:
        return ("MM Model", '<div class="card"><div class="body">'
                            'DATA_UNAVAILABLE — 未跑 mm_model.py（output/mm_model.json）。'
                            '</div></div>')
    s = snap["score"] or 0
    if s >= FULL_AT:
        verdict, col = "全倉（invested）", "#2f8f5b"
    elif s >= CASH_AT:
        verdict, col = f"減倉（{snap['expo_today']}% 倉）", "#b9a05f"
    else:
        verdict, col = "全現金（no trade）", "#a04a44"

    st, bh = snap["stats_model"], snap["stats_bh"]
    cs = snap["chart"]
    mo = snap.get("monthly") or {}

    L = [f"<style>{CSS}</style>"]

    # ── 頭：分數 + 倉位
    L.append('<div class="card"><h2>MM Model <small>' + _esc(snap["date"]) +
             '｜25 個子模型 → 合成 0-100</small></h2><div class="body">')
    L.append(f'<div class="mm-hero"><div><div class="mm-score" style="color:{col}">{int(s)}'
             f'<span style="font-size:15px;opacity:.45">/100</span></div>'
             f'<div class="mm-verdict" style="color:{col}">{verdict}</div>'
             f'<div class="mm-bar"><i style="width:{min(100,s):.0f}%;background:{col}"></i></div>'
             f'<div class="mm-meta"><55 = 全現金（no trade）｜55-70 線性加倉｜≥70 全倉</div></div>'
             f'<div class="mm-meta">建議倉位 {snap["expo_today"]}%<br>'
             f'樣本 {_esc(snap["span"][0])} → {_esc(snap["span"][1])}</div>'
             f'<div class="mm-meta">Model CAGR <b>{st["cagr"]}%</b>｜最大回撤 '
             f'<b>{st["maxdd"]}%</b><br>S&amp;P CAGR {bh["cagr"]}%｜最大回撤 {bh["maxdd"]}%</div>'
             '</div></div></div>')

    # ── 圖 1：價格 + 模型（log）
    L.append('<div class="card"><h2>1 · S&amp;P 500 vs Composite Model '
             '<small>log 尺｜藍 = S&amp;P｜橙 = 模型</small></h2>'
             '<div class="body"><div class="mm-scroll">')
    L.append(V.price_chart(cs, st, bh))
    L.append('</div></div>')

    # ── 圖 2：Composite Indicator
    L.append('<div class="card"><h2>2 · Composite Indicator '
             '<small>0-100｜虛線 40 / 60</small></h2><div class="body"><div class="mm-scroll">')
    L.append(V.step_chart(mo.get("date"), mo.get("score"),
                          colour="#2f8f5b", label="Composite Indicator",
                          value_txt=f'{snap["date"]} = {s:.1f}',
                          dash=(40, 60), lo=0, hi=100))
    L.append('</div></div></div>')

    # ── 圖 3：Allocation %
    L.append('<div class="card"><h2>3 · S&amp;P 500 Allocation % '
             '<small>0-100｜0 = 全現金｜100 = 全倉</small></h2><div class="body"><div class="mm-scroll">')
    L.append(V.step_chart(mo.get("date"), mo.get("alloc"),
                          colour="#52525b", label="S&amp;P 500 Allocation %",
                          value_txt=f'{snap["date"]} = {snap["expo_today"]:.1f}%',
                          dash=(50,), lo=0, hi=100))
    L.append('</div></div></div>')

    # ── 表：年回報 + 期間回報
    L.append('<div class="grid2">')
    L.append('<div class="card"><h2>年回報 <small>近 20 年</small></h2><div class="body">')
    L.append(V.annual_table(snap.get("annual") or []))
    L.append('</div></div>')
    L.append('<div class="card"><h2>期間回報</h2><div class="body">')
    L.append(V.period_table(snap.get("periods") or []))
    L.append('</div></div></div>')

    # ── 25 個子模型
    on = sum(1 for m in snap["models"] if m["on"])
    L.append(f'<div class="card"><h2>25 個子模型 <small>{on}/25 成立</small></h2>'
             '<div class="body">')
    L.append('<div class="tscroll"><table class="mm-tbl"><thead><tr>'
             '<th>#</th><th>模型</th><th>狀態</th><th class="n">近 250 日成立</th>'
             '</tr></thead><tbody>')
    for i, m in enumerate(snap["models"], 1):
        stt = ("<span class='mm-on'>成立</span>" if m["on"]
               else "<span class='mm-off'>唔成立</span>" if m["on"] is not None else "—")
        L.append(f'<tr><td>{i}</td><td>{_esc(m["name"])}</td><td>{stt}</td>'
                 f'<td class="n">{m["days"]}</td></tr>')
    L.append('</tbody></table></div>')
    L.append('<div class="mm-note">★ Minervini 原版 25 個子模型冇公開。以上 25 條係我方可核 proxy，'
             '只用公開指數價、VIX、10 年息、美元計，公式寫死喺 mm_model.py。'
             '唔可以當成官方數字或者投資建議。</div></div></div>')
    # 預設最右（最新）；向左滑睇歷史
    L.append('<script>(function(){function R(){document.querySelectorAll'
             '(".mm-scroll").forEach(function(e){e.scrollLeft=e.scrollWidth;});}'
             'if(document.readyState!=="loading")R();'
             'else document.addEventListener("DOMContentLoaded",R);'
             'window.addEventListener("resize",R);})();</script>')
    return ("MM Model", "".join(L))


def main(argv=None):
    import sys
    argv = sys.argv[1:] if argv is None else argv
    d = fetch(refresh="--refresh" in argv)
    if not d:
        log("DATA_UNAVAILABLE")
        return 1
    snap = compute(d)
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "mm_model.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False)
    log(f"{snap['date']}  score {snap['score']}  expo {snap['expo_today']}%  "
        f"model CAGR {snap['stats_model']['cagr']}% vs BH {snap['stats_bh']['cagr']}%  → {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
