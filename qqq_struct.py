# -*- coding: utf-8 -*-
"""qqq_struct.py — QQQ 雙結構（21EMA 日線 × 10 週 SMA 週線）

蒸餾自 Desmond 2026-11-07 提供嘅圖：
　只有 QQQ 自己嘅價。兩條結構線：21EMA（日）、10 週 SMA（週）。
　價格喺每條線上下 → 四種狀態（RISK ON / PULLBACK / PROBE / RISK OFF）。
　延伸 = 價格離線幾遠，用 ATR 計，再用自己歷史做 z 分數；|z| ≥ 1.5 = 延伸。

定義（寫死，唔准事後改）
　TR      = max(H−L, |H−C₋₁|, |L−C₋₁|)｜ATR14 = Wilder 平滑（alpha = 1/14）
　ext_d   = (C − EMA21) / ATR14_d
　ext_w   = (C_w − SMA10_w) / ATR14_w          （週線 resample W-FRI，值喺週五收市已知）
　z       = ext / σ，σ = 近 2,520 個交易日 ext 嘅標準差（最少 250 個）
　狀態    = 收市 vs EMA21（日）× 週收市 vs SMA10（週）
　run     = 由對上一個 RISK ON 期間嘅最高收市，跌到本段最低收市嘅百分比

唯讀：只寫自己 cache／output，唔碰任何實盤常數。
網絡失敗 → 用舊 cache → 兩者皆無 = DATA_UNAVAILABLE（唔會拖死 build）。
"""
from __future__ import annotations

import html as _h
import io
import json
import os
import pickle
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "qqq_struct.pkl")
OUT = os.path.join(HERE, "output")
CACHE_H = 6.0            # 6 小時：同 fear_gauge / group_rs 同一個新鮮度紀律
WIN = 2520               # 10 年交易日

# ★ 2026-11-07 Desmond：「顏色改返同張圖一樣」→ 全部由原圖 pixel 取樣
COL = {
    "RISK ON": "#1f7f52",     # 深綠
    "PULLBACK": "#b9a05f",    # 金字（取樣 b4a564）
    "PROBE": "#906060",       # 褐紅（取樣 906060）
    "RISK OFF": "#a04a44",    # 磚紅（條帶取樣 b05040）
}
EXT_UP = "#544878"            # price upside extended（取樣）
EXT_DN = "#904848"            # price downside extended（取樣）
SMA_COL = "#b4ccd8"           # 10 週結構（取樣，寬帶）
EMA_COL = "#c0d8e4"           # 21EMA 結構（取樣，緊帶）
PULLBACK_C = COL["PULLBACK"]
DESC = {
    "RISK ON": "兩線之上 — 趨勢環境",
    "PULLBACK": "週線之上、日線之下 — 上升趨勢回調",
    "PROBE": "日線之上、週線之下 — 嘗試轉向，結構未過",
    "RISK OFF": "兩線之下 — 大部分大跌日喺呢度發生",
}


def _esc(x):
    return _h.escape(str(x if x is not None else ""))


def log(*a):
    print(*a, flush=True)


# ────────────────────────────── 數據 ──────────────────────────────
def load(refresh=False):
    """QQQ 日線 OHLC（max 歷史）。回 DataFrame 或 None。"""
    import pandas as pd

    if not refresh and os.path.exists(CACHE):
        age_h = (time.time() - os.path.getmtime(CACHE)) / 3600.0
        if age_h < CACHE_H:
            try:
                with io.open(CACHE, "rb") as f:
                    df = pickle.load(f)
                if df is not None and len(df) > 300:
                    return df
            except Exception:                                # noqa: BLE001
                pass
    try:
        import yfinance as yf
        raw = yf.download("QQQ", period="max", interval="1d",
                          auto_adjust=True, progress=False, threads=False)
        if raw is None or len(raw) == 0:
            raise RuntimeError("empty download")
        if hasattr(raw.columns, "nlevels") and raw.columns.nlevels > 1:
            raw.columns = [c[0] for c in raw.columns]
        df = raw.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
        df = df.dropna()
        os.makedirs(DATA, exist_ok=True)
        with io.open(CACHE, "wb") as f:
            pickle.dump(df, f)
        return df
    except Exception as e:                                   # noqa: BLE001
        log(f"⚠ QQQ 下載失敗：{type(e).__name__}: {e}")
        try:
            with io.open(CACHE, "rb") as f:
                return pickle.load(f)
        except Exception:                                    # noqa: BLE001
            return None


# ────────────────────────────── 計算 ──────────────────────────────
def compute(df):
    import numpy as np
    import pandas as pd

    d = df.copy()
    c, h, l = d["close"], d["high"], d["low"]

    d["ema21"] = c.ewm(span=21, adjust=False).mean()
    prev = c.shift(1)
    tr = pd.concat([h - l, (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1 / 14.0, adjust=False).mean()
    d["ext_d"] = (c - d["ema21"]) / d["atr"]

    # 週線結構（W-FRI）：值喺週五收市已知，之後 ffill 去每日，冇前視
    w = d["close"].resample("W-FRI").last().dropna().to_frame("wc")
    wh = d["high"].resample("W-FRI").max().reindex(w.index)
    wl = d["low"].resample("W-FRI").min().reindex(w.index)
    w["sma10"] = w["wc"].rolling(10).mean()
    wp = w["wc"].shift(1)
    wtr = pd.concat([wh - wl, (wh - wp).abs(), (wl - wp).abs()], axis=1).max(axis=1)
    w["watr"] = wtr.ewm(alpha=1 / 14.0, adjust=False).mean()
    w["ext_w"] = (w["wc"] - w["sma10"]) / w["watr"]

    for col in ("sma10", "ext_w", "wc"):
        d["w_" + col] = w[col].reindex(d.index, method="ffill")

    d["z_d"] = d["ext_d"] / d["ext_d"].rolling(WIN, min_periods=250).std()
    d["z_w"] = d["w_ext_w"] / d["w_ext_w"].rolling(WIN, min_periods=250).std()

    above_d = c > d["ema21"]
    above_w = d["w_wc"] > d["w_sma10"]
    d["state"] = np.select(
        [above_d & above_w, (~above_d) & above_w, above_d & (~above_w)],
        ["RISK ON", "PULLBACK", "PROBE"], default="RISK OFF")
    d.loc[d["w_sma10"].isna(), "state"] = "NA"

    # 連續段
    st = d["state"]
    grp = (st != st.shift()).cumsum()
    d["ep"] = grp
    runs = []
    for _, idx in d.groupby("ep").groups.items():
        runs.append({"state": st.loc[idx[0]], "start": idx[0], "end": idx[-1],
                     "days": len(idx)})
    return d, runs


def _stats(d, runs):
    import numpy as np

    st = d["state"]
    cur = st.iloc[-1]
    cur_run = runs[-1]
    past = [r for r in runs[:-1] if r["state"] == cur]
    days_list = [r["days"] for r in past]

    def _md(v, f=0):
        return float(np.median(v)) if v else None

    # 本段 run：對上一個 RISK ON 段嘅最高收市 → 本段最低收市
    def _leg(i_last):
        j = i_last
        while j > 0 and runs[j]["state"] != "RISK ON":
            j -= 1
        if runs[j]["state"] != "RISK ON" or j == i_last:
            return None
        peak = float(d.loc[runs[j]["start"]:runs[j]["end"], "close"].max())
        trough = float(d.loc[runs[i_last]["start"]:runs[i_last]["end"], "close"].min())
        return (trough / peak - 1.0) * 100

    cur_leg = _leg(len(runs) - 1)
    legs = []
    for i in range(1, len(runs) - 1):
        v = _leg(i)
        if v is not None:
            legs.append(v)

    # 現時低於各線嘅日數 + 歷史中位
    def below_days(col_bool):
        b = ~col_bool
        cnt, i = 0, len(b) - 1
        end = b.index[-1]
        while i >= 0 and bool(b.iloc[i]):
            cnt += 1
            i -= 1
        start = b.index[i + 1] if i + 1 < len(b) else end
        # 歷史同類（連續低於）段長度中位
        g = (b != b.shift()).cumsum()
        lens = [len(x) for k, x in b.groupby(g) if bool(x.iloc[0])]
        return cnt, start, (float(np.median(lens[:-1])) if len(lens) > 1 else None)

    dd, dstart, dmed = below_days(d["close"] > d["ema21"])
    wd, wstart, wmed = below_days(d["w_wc"] > d["w_sma10"])

    return {
        "state": cur, "cur_days": cur_run["days"], "cur_start": cur_run["start"],
        "med_days": _md(days_list), "max_days": (max(days_list) if days_list else None),
        "n_past": len(past),
        "leg": cur_leg, "leg_med": _md(legs), "leg_worst": (min(legs) if legs else None),
        "below_d": dd, "below_d_start": dstart, "below_d_med": dmed,
        "below_w": wd, "below_w_start": wstart, "below_w_med": wmed,
    }


def snapshot(d, runs, df_raw_unused=None):
    """回一個純 dict（給頁面＋output JSON）。"""
    import numpy as np

    last = d.iloc[-1]
    prev = d.iloc[-2]
    s = _stats(d, runs)
    close = float(last["close"])

    z_d = float(last["z_d"]) if np.isfinite(last["z_d"]) else None
    z_w = float(last["z_w"]) if np.isfinite(last["z_w"]) else None

    # 10 年分佈（用同一把尺）
    tail = d.tail(WIN)

    def _rank(series, v):
        vv = series.dropna().values
        if v is None or len(vv) == 0:
            return None
        if v < 0:
            return int((vv <= v).sum()), len(vv), float((vv <= v).mean() * 100)
        return int((vv >= v).sum()), len(vv), float((vv >= v).mean() * 100)

    def _hist(series, lo=-4.0, hi=4.0, bins=80):
        v = series.dropna().values
        v = v[(v >= lo) & (v <= hi)]
        cnt, edges = np.histogram(v, bins=bins, range=(lo, hi))
        return {"edges": [round(float(x), 3) for x in edges],
                "counts": [int(x) for x in cnt]}

    lvl_d = float(last["ema21"])
    lvl_w = float(last["w_sma10"])
    snap = {
        "date": d.index[-1].strftime("%Y-%m-%d"),
        "close": round(close, 2),
        "chg_pct": round((close / float(prev["close"]) - 1) * 100, 2),
        "state": s["state"],
        "state_desc": DESC.get(s["state"], ""),
        "ema21": round(lvl_d, 2), "sma10w": round(lvl_w, 2),
        "dist_d_pct": round((close / lvl_d - 1) * 100, 2),
        "dist_w_pct": round((close / lvl_w - 1) * 100, 2),
        "ext_d": round(float(last["ext_d"]), 2),
        "ext_w": round(float(last["w_ext_w"]), 2),
        "z_d": round(z_d, 2) if z_d is not None else None,
        "z_w": round(z_w, 2) if z_w is not None else None,
        "sigma_d": round(float(tail["z_d"].std() or 1), 4),
        "hist_d": _hist(tail["z_d"]), "hist_w": _hist(tail["z_w"]),
        "tail_d": _rank(tail["z_d"], z_d), "tail_w": _rank(tail["z_w"], z_w),
        "days_in_state": s["cur_days"],
        "state_start": s["cur_start"].strftime("%Y-%m-%d"),
        "state_med": s["med_days"], "state_max": s["max_days"], "state_n": s["n_past"],
        "below_d": s["below_d"], "below_d_start": s["below_d_start"].strftime("%Y-%m-%d"),
        "below_d_med": s["below_d_med"],
        "below_w": s["below_w"], "below_w_start": s["below_w_start"].strftime("%Y-%m-%d"),
        "below_w_med": s["below_w_med"],
        "leg": round(s["leg"], 2) if s["leg"] is not None else None,
        "leg_med": round(s["leg_med"], 2) if s["leg_med"] is not None else None,
        "leg_worst": round(s["leg_worst"], 2) if s["leg_worst"] is not None else None,
        "sessions": int(len(d)),
        "span": f"{d.index[0].strftime('%Y-%m-%d')} → {d.index[-1].strftime('%Y-%m-%d')}",
        "chart": _chart_series(d),
    }
    return snap


def _chart_series(d, n=504):
    t = d.tail(n)
    return {
        "dates": [x.strftime("%Y-%m-%d") for x in t.index],
        "close": [round(float(x), 2) for x in t["close"]],
        "ema21": [round(float(x), 2) for x in t["ema21"]],
        "sma10w": [round(float(x), 2) if x == x else None for x in t["w_sma10"]],
        "state": [str(x) for x in t["state"]],
        "ext_d": [round(float(x), 2) for x in t["ext_d"]],
        "ext_w": [round(float(x), 2) if x == x else None for x in t["w_ext_w"]],
    }


def build_snapshot(refresh=False):
    df = load(refresh=refresh)
    if df is None or len(df) < 300:
        return None
    d, runs = compute(df)
    return snapshot(d, runs)


# ────────────────────────────── 圖 ──────────────────────────────
def _gauge(z, label):
    """−4σ … +4σ 橫尺，±1.5σ 標記，今晚位置。"""
    if z is None:
        return '<div class="dim">—</div>'
    W, H = 520, 54
    pad = 14
    lo, hi = -4.0, 4.0

    def X(v):
        return pad + (v - lo) / (hi - lo) * (W - 2 * pad)

    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px" '
         f'role="img" aria-label="{_esc(label)} 延伸尺">']
    P.append(f'<rect x="{X(-1.5):.1f}" y="18" width="{X(-1.5)-pad:.1f}" height="10" '
             f'fill="#ef4444" fill-opacity="0.18"/>')
    P.append(f'<rect x="{X(1.5):.1f}" y="18" width="{pad + (W - pad - X(1.5)):.1f}" '
             f'height="10" fill="{EXT_UP}" fill-opacity="0.18"/>')
    P.append(f'<rect x="{pad}" y="18" width="{W-2*pad:.1f}" height="10" fill="#64748b" '
             f'fill-opacity="0.25" rx="3"/>')
    for v, lab in ((-1.5, "−1.5σ"), (0, "0"), (1.5, "+1.5σ")):
        P.append(f'<line x1="{X(v):.1f}" y1="14" x2="{X(v):.1f}" y2="32" '
                 f'stroke="#94a3b8" stroke-width="1" stroke-dasharray="2 3" '
                 f'fill-opacity="0.8"/>')
        P.append(f'<text x="{X(v):.1f}" y="44" fill="#94a3b8" font-size="9.5" '
                 f'text-anchor="middle">{lab}</text>')
    col = EXT_DN if z <= -1.5 else EXT_UP if z >= 1.5 else "#e2e8f0"
    P.append(f'<circle cx="{X(max(lo, min(hi, z))):.1f}" cy="23" r="5.5" fill="{col}" '
             f'stroke="#0b1120" stroke-width="1.5"/>')
    P.append(f'<text x="{X(max(lo, min(hi, z))):.1f}" y="10" fill="{col}" '
             f'font-size="11" font-weight="700" text-anchor="middle">{z:+.2f}σ</text>')
    P.append('</svg>')
    return "".join(P)


def _histo(hist, z):
    if not hist or not hist.get("counts"):
        return ""
    counts = hist["counts"]
    edges = hist["edges"]
    W, H = 520, 96
    pad = 14
    top = 8
    mx = max(counts) or 1
    n = len(counts)
    bw = (W - 2 * pad) / n

    def X(v):
        return pad + (v + 4.0) / 8.0 * (W - 2 * pad)

    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px" '
         f'role="img" aria-label="十年分佈">']
    for i, cnt in enumerate(counts):
        e0 = edges[i]
        hgt = (cnt / mx) * (H - top - 16)
        col = EXT_DN if e0 < -1.5 else EXT_UP if e0 >= 1.5 else "#64748b"
        P.append(f'<rect x="{pad + i*bw:.2f}" y="{H-16-hgt:.1f}" width="{max(bw-0.4,0.6):.2f}" '
                 f'height="{hgt:.1f}" fill="{col}" fill-opacity="0.85"><title>'
                 f'{e0:+.2f} ~ {edges[i+1]:+.2f}σ：{cnt} 日</title></rect>')
    P.append(f'<line x1="{pad}" y1="{H-16}" x2="{W-pad}" y2="{H-16}" '
             f'stroke="#475569" stroke-width="1"/>')
    if z is not None:
        xz = X(max(-4.0, min(4.0, z)))
        P.append(f'<line x1="{xz:.1f}" y1="{top-4}" x2="{xz:.1f}" y2="{H-16}" '
                 f'stroke="#e2e8f0" stroke-width="1.2" stroke-dasharray="3 3"/>')
    for v in (-1.5, 0, 1.5):
        P.append(f'<text x="{X(v):.1f}" y="{H-4}" fill="#94a3b8" font-size="9.5" '
                 f'text-anchor="middle">{v:+.1f}σ</text>')
    P.append('</svg>')
    return "".join(P)


def _chart(cs):
    if not cs or len(cs.get("close", [])) < 30:
        return '<div class="dim">DATA_UNAVAILABLE</div>'
    closes = cs["close"]
    ema = cs["ema21"]
    sma = [v for v in cs["sma10w"] if v is not None]
    n = len(closes)
    W = 1160
    pad_r = 62
    x0, x1 = 4, W - pad_r - 4
    ph, sh, eh = 340, 16, 120          # 價格 / 狀態帶 / 延伸
    gap = 26
    H = ph + sh + eh + gap * 2 + 18

    lo = min(min(closes), min(ema), min(sma) if sma else min(closes))
    hi = max(max(closes), max(ema), max(sma) if sma else max(closes))
    pad = (hi - lo) * 0.06 or 1
    lo, hi = lo - pad, hi + pad

    def X(i):
        return x0 + i / max(1, n - 1) * (x1 - x0)

    def Y(v):
        return 2 + (hi - v) / (hi - lo) * (ph - 4)

    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-width:640px;max-width:{W}px" '
         f'role="img" aria-label="QQQ 雙結構兩年圖">']
    # 價格格線
    import math as _m
    step = max(10, round((hi - lo) / 6 / 10) * 10)
    g = _m.floor(lo / step) * step
    while g <= hi:
        if 14 < Y(g) < ph - 4:
            P.append(f'<line x1="{x0}" y1="{Y(g):.1f}" x2="{x1}" y2="{Y(g):.1f}" '
                     f'stroke="#334155" stroke-width="0.7" stroke-opacity="0.6"/>')
            P.append(f'<text x="{W-pad_r+6}" y="{Y(g)+3.5:.1f}" fill="#94a3b8" '
                     f'font-size="9.5">{g:.0f}</text>')
        g += step
    P.append(f'<text x="{x0+2}" y="13" fill="#94a3b8" font-size="9.5" '
             f'letter-spacing=".06em">QQQ 收市</text>')
    # 結構線
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(ema))
    P.append(f'<polyline points="{pts}" fill="none" stroke="{EMA_COL}" '
             f'stroke-width="1.1" stroke-opacity="0.75"/>')
    seg = [(i, v) for i, v in enumerate(cs["sma10w"]) if v is not None]
    if seg:
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in seg)
        P.append(f'<polyline points="{pts}" fill="none" stroke="{SMA_COL}" '
                 f'stroke-width="1.3" stroke-dasharray="5 3" stroke-opacity="0.85"/>')
    # 價格（逐段上色）
    for i in range(1, n):
        st = cs["state"][i]
        P.append(f'<line x1="{X(i-1):.1f}" y1="{Y(closes[i-1]):.1f}" '
                 f'x2="{X(i):.1f}" y2="{Y(closes[i]):.1f}" '
                 f'stroke="{COL.get(st, "#94a3b8")}" stroke-width="1.6"/>')
    # 狀態帶
    sy = ph + gap
    bw = (x1 - x0) / max(1, n)
    for i, st in enumerate(cs["state"]):
        P.append(f'<rect x="{X(i):.2f}" y="{sy}" width="{max(bw, 0.7):.2f}" height="{sh}" '
                 f'fill="{COL.get(st, "#475569")}"><title>{cs["dates"][i]} '
                 f'{st}</title></rect>')
    # 延伸面板
    ey0 = sy + sh + gap
    eh_in = eh - 22
    elo, ehi = -4.0, 4.0
    P.append(f'<text x="{x0+2}" y="{ey0-4}" fill="#94a3b8" font-size="9.5" '
             f'letter-spacing=".06em">延伸（ATR）</text>')

    def EY(v):
        return ey0 + (ehi - max(elo, min(ehi, v))) / (ehi - elo) * eh_in

    P.append(f'<rect x="{x0}" y="{EY(1.5):.1f}" width="{x1-x0}" height="{EY(-1.5)-EY(1.5):.1f}" '
             f'fill="#64748b" fill-opacity="0.07"/>')
    for v, lab in ((-1.5, "−1.5"), (0, "0"), (1.5, "+1.5")):
        P.append(f'<line x1="{x0}" y1="{EY(v):.1f}" x2="{x1}" y2="{EY(v):.1f}" '
                 f'stroke="#94a3b8" stroke-width="0.8" '
                 f'stroke-dasharray="{"" if v == 0 else "3 3"}" stroke-opacity="0.7"/>')
        P.append(f'<text x="{W-pad_r+6}" y="{EY(v)+3.5:.1f}" fill="#94a3b8" '
                 f'font-size="9.5">{lab}</text>')
    for i, v in enumerate(cs["ext_d"]):
        y = EY(v)
        ytop = min(y, EY(0))
        hh = abs(EY(0) - y)
        col = EXT_DN if v < 0 else EXT_UP
        P.append(f'<rect x="{X(i):.2f}" y="{ytop:.1f}" width="{max(bw*0.8,0.7):.2f}" '
                 f'height="{max(hh,0.6):.1f}" fill="{col}" fill-opacity="0.75">'
                 f'<title>{cs["dates"][i]} 日線 {v:+.2f} ATR</title></rect>')
    # 週線延伸（幼線）：每週只放一個點，避免同一週 5 個重複值造成階梯
    wpts = []
    prev_w = None
    for i, v in enumerate(cs["ext_w"]):
        if v is None:
            continue
        if v != prev_w:
            wpts.append((i, v))
            prev_w = v
    if wpts:
        P.append('<polyline points="' + " ".join(f"{X(i):.1f},{EY(v):.1f}" for i, v in wpts)
                 + f'" fill="none" stroke="{PULLBACK_C}" stroke-width="1.2" stroke-opacity="0.85"/>')
    # 月份標籤：每月第一個交易日，最少相隔 4% 圖寬
    lastm = ""
    lastx = -1e9
    for i, ds in enumerate(cs["dates"]):
        m = ds[:7]
        if m != lastm:
            lastm = m
            if X(i) - lastx > (x1 - x0) * 0.06:
                lastx = X(i)
                P.append(f'<text x="{X(i):.1f}" y="{H-2}" fill="#94a3b8" font-size="9.5" '
                         f'text-anchor="middle">{ds[2:7]}</text>')
    P.append('</svg>')
    return "".join(P)


def _card_open(title, extra=""):
    return f'<div class="card"><h2>{title}{extra}</h2><div class="body">'


JSON_PATH = os.path.join(OUT, "qqq_struct.json")


def _load_json():
    try:
        with io.open(JSON_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return None


def _age_days(ds):
    """日曆日差（由 ISO 字串）；讀唔到 = None（唔准當 0）。"""
    import datetime as _dt
    try:
        d = _dt.date.fromisoformat(str(ds)[:10])
    except Exception:                                        # noqa: BLE001
        return None
    return (_dt.date.today() - d).days


# ────────────────────────────── 頁面 ──────────────────────────────
CSS = """
.qs-name{font-size:30px;font-weight:800;line-height:1;letter-spacing:-.02em}
.qs-sub{font-size:11px;opacity:.62;margin-top:6px;line-height:1.7}
.qs-row{display:flex;gap:26px;flex-wrap:wrap;align-items:flex-start}
.qs-cell{min-width:150px}
.qs-k{font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;opacity:.55;font-weight:800}
.qs-v{font-size:19px;font-weight:700;font-variant-numeric:tabular-nums;margin-top:3px}
.qs-v small{font-size:11px;font-weight:600;opacity:.6;margin-left:5px}
.qs-leg{display:flex;gap:14px;flex-wrap:wrap;font-size:11px;margin-top:10px;opacity:.8}
.qs-leg i{width:9px;height:9px;border-radius:2px;display:inline-block;margin-right:5px}
.qs-statlist{margin-top:2px}
.qs-stat{display:grid;grid-template-columns:minmax(110px,1fr) auto;gap:1px 14px;
  padding:6px 0;border-bottom:1px solid rgba(148,163,184,.12);font-size:12.5px}
.qs-stat .l{opacity:.72}
.qs-stat .v{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
.qs-stat .n{grid-column:1/-1;font-size:10.5px;opacity:.55;font-variant-numeric:tabular-nums}
.qs-tbl{width:100%;border-collapse:collapse;font-size:12px}
.qs-tbl th{text-align:left;font-size:10px;letter-spacing:.05em;opacity:.55;font-weight:800;
  padding:5px 8px;border-bottom:1px solid rgba(148,163,184,.25)}
.qs-tbl td{padding:5px 8px;border-bottom:1px solid rgba(148,163,184,.1);
  font-variant-numeric:tabular-nums}
.qs-tbl td.n,.qs-tbl th.n{text-align:right}
.qs-note{font-size:10.5px;opacity:.55;line-height:1.7;margin-top:10px}
"""


def build(snap=None):
    # ★ 頁面只讀 JSON（唔上網）：collector = `python qqq_struct.py`
    #   build 期間上網會令成個 generator 慢同可能卡死（trading-desk-site 嘅 page 合約）
    if snap is None:
        snap = _load_json()
    if not snap:
        return ("QQQ 雙結構", '<div class="card"><div class="body">'
                             'DATA_UNAVAILABLE — 未跑 qqq_struct.py（output/qqq_struct.json）。</div></div>')

    st = snap["state"]
    col = COL.get(st, "#94a3b8")
    z_d, z_w = snap["z_d"], snap["z_w"]

    L = [f"<style>{CSS}</style>"]

    # ── 0 新鮮度（Missing ≠ Zero：檔一舊就講，唔准扮今日）
    age = _age_days(snap.get("date"))
    if age is not None and age > 5:
        L.append(f'<div class="card"><div class="body" style="color:#f59e0b;font-size:12px">'
                 f'⚠ 數據停咗 {age} 日（最後 {snap.get("date")}）— collector 未跑，'
                 f'以下係舊快照。</div></div>')

    # ── ① 狀態卡
    L.append(_card_open("QQQ 雙結構",
                        f'<small>{snap["date"]}｜只有 QQQ 自己嘅價：21EMA（日）× 10 週 SMA（週）</small>'))
    L.append('<div class="qs-row">')
    L.append(f'<div><div class="qs-name" style="color:{col}">{st}</div>'
             f'<div class="qs-sub">{_esc(snap["state_desc"])}</div></div>')
    L.append(f'<div class="qs-cell"><div class="qs-k">收市</div>'
             f'<div class="qs-v">{snap["close"]:.2f}<small>{snap["chg_pct"]:+.2f}%</small></div></div>')
    L.append(f'<div class="qs-cell"><div class="qs-k">距 21EMA</div>'
             f'<div class="qs-v" style="color:{COL["RISK ON"] if snap["dist_d_pct"]>=0 else COL["RISK OFF"]}">'
             f'{snap["dist_d_pct"]:+.2f}%<small>{snap["ema21"]:.2f}</small></div></div>')
    L.append(f'<div class="qs-cell"><div class="qs-k">距 10 週 SMA</div>'
             f'<div class="qs-v" style="color:{COL["RISK ON"] if snap["dist_w_pct"]>=0 else COL["RISK OFF"]}">'
             f'{snap["dist_w_pct"]:+.2f}%<small>{snap["sma10w"]:.2f}</small></div></div>')
    L.append(f'<div class="qs-cell"><div class="qs-k">日線延伸</div>'
             f'<div class="qs-v">{snap["ext_d"]:+.2f}<small>ATR　{(z_d or 0):+.2f}σ</small></div></div>')
    L.append(f'<div class="qs-cell"><div class="qs-k">週線延伸</div>'
             f'<div class="qs-v">{snap["ext_w"]:+.2f}<small>ATR　{(z_w or 0):+.2f}σ</small></div></div>')
    L.append('</div>')
    L.append('<div class="qs-leg">' + "".join(
        f'<span><i style="background:{c}"></i>{k}</span>' for k, c in COL.items()) + '</div>')
    L.append('</div></div>')

    # ── ② 統計表
    L.append(_card_open("狀態統計", '<small>同一把尺量歷史，唔係感覺</small>'))
    rows = [
        ("今次狀態已持續", f'第 {snap["days_in_state"]} 個交易日',
         f'中位 {snap["state_med"]:.0f}｜最長 {snap["state_max"]}｜歷史 {snap["state_n"]} 段'),
        ("低於 21EMA", f'{snap["below_d"]} 日（由 {snap["below_d_start"]}）',
         f'歷史中位 {(snap["below_d_med"] or 0):.0f} 日'),
        ("低於 10 週 SMA", f'{snap["below_w"]} 日（由 {snap["below_w_start"]}）',
         f'歷史中位 {(snap["below_w_med"] or 0):.0f} 日'),
        ("重上 21EMA 要", f'{snap["ema21"]:.2f}（距 {(snap["ema21"]/snap["close"]-1)*100:+.1f}%）', "收市價計"),
        ("重上 10 週 SMA 要", f'{snap["sma10w"]:.2f}（距 {(snap["sma10w"]/snap["close"]-1)*100:+.1f}%）', "週五收市計"),
        ("本段跌幅", (f'{snap["leg"]:+.2f}%' if snap["leg"] is not None else "—"),
         (f'歷史中位 {snap["leg_med"]:+.2f}%｜最差 {snap["leg_worst"]:+.2f}%'
          if snap["leg_med"] is not None else "（本段前面冇 RISK ON 段可比）")),
    ]
    L.append('<div class="qs-statlist">')
    for a, b_, c_ in rows:
        L.append(f'<div class="qs-stat"><span class="l">{_esc(a)}</span>'
                 f'<span class="v">{_esc(b_)}</span>'
                 f'<span class="n">{_esc(c_)}</span></div>')
    L.append('</div>')
    L.append('<div class="qs-note">本段跌幅 = 對上一個 RISK ON 段最高收市 → 本段最低收市。'
             '「重上」價位係今日嘅線值，線自己會跟價走。</div>')
    L.append('</div></div>')

    # ── ③ 兩把尺
    L.append('<div class="grid2">')
    for key, tit, z, hist, tail, line in (
            ("d", "日線：21EMA 延伸（ATR）", z_d, snap["hist_d"], snap["tail_d"], "21EMA"),
            ("w", "週線：10 週 SMA 延伸（ATR）", z_w, snap["hist_w"], snap["tail_w"], "10 週 SMA")):
        L.append('<div class="card"><h2>' + tit +
                 '</h2><div class="body">')
        L.append(_gauge(z, tit))
        L.append(_histo(hist, z))
        if tail:
            cnt, tot, pct = tail
            side = "向下" if (z or 0) < 0 else "向上"
            L.append(f'<div class="qs-note">{side}延伸：近十年 {tot:,} 日中只有 <b>{cnt}</b> 日'
                     f'有今日咁遠或更遠（第 {pct:.2f} 個百分位）。'
                     f'「遠」本身唔係買賣理由，係風險定價。</div>')
        L.append('</div></div>')
    L.append('</div>')

    # ── ④ 兩年圖
    L.append(_card_open("QQQ × 兩條結構 — 近兩年",
                        '<small>價格逐段按狀態上色；下面 = 四種狀態色帶同延伸（ATR）</small>'))
    L.append(_chart(snap["chart"]))
    L.append('<div class="qs-leg" style="margin-top:8px">'
             f'<span><i style="background:{EMA_COL}"></i>21EMA</span>'
             f'<span><i style="background:{SMA_COL}"></i>10 週 SMA</span>'
             f'<span><i style="background:{EXT_DN}"></i>負延伸</span>'
             f'<span><i style="background:{EXT_UP}"></i>正延伸</span>'
             f'<span><i style="background:{PULLBACK_C}"></i>週線延伸線</span></div>')
    L.append(f'<div class="qs-note">延伸 =（收市 − 線）÷ ATR14；|z| ≥ 1.5 = 延伸（z = 延伸 ÷ 近 {WIN:,} 日標準差）。'
             f'狀態 = 收市 vs 21EMA × 週收市 vs 10 週 SMA。'
             f'樣本 {snap["sessions"]:,} 日（{snap["span"]}）。</div>')
    L.append('</div></div>')
    return ("QQQ 雙結構", "".join(L))


# ────────────────────────────── CLI ──────────────────────────────
def main(argv=None):
    import sys
    argv = sys.argv[1:] if argv is None else argv
    snap = build_snapshot(refresh="--refresh" in argv)
    if not snap:
        log("DATA_UNAVAILABLE")
        return 1
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "qqq_struct.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    log(f"{snap['date']}  {snap['state']}  close {snap['close']}  "
        f"z_d {snap['z_d']}  z_w {snap['z_w']}  "
        f"days_in_state {snap['days_in_state']}")
    log(f"→ {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
