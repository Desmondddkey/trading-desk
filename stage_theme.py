# -*- coding: utf-8 -*-
"""stage_theme.py — 行業「四階段」（Weinstein S1–S4）分佈掃描。

Desmond 2026-11-27：RAE Deepvue Stage Analysis 圖 → 網站「今日 > 大市 > 主題」。

★ 呢個係我哋自己按定義重建，唔係供應商原指標。
   供應商嘅 Health 分數無法由圖上欄位推回，所以我哋自己定義（見 HEALTH 註解），
   而且只用頁面上見得到嘅欄位計，讀者可以自己覆核。

階段定義（全部可量化，冇主觀；單位統一用 ATR，唔用固定 %）
  MA150 ≈ 30 週線（Weinstein 標準）
  slope_k = (MA150[t] − MA150[t−k]) / ATR14[t]        ← 單位：ATR
  trend   = 0.6 × slope_20 + 0.4 × slope_60
  升 = trend > +0.4 ｜ 跌 = trend < −0.4 ｜ 其餘 = 平

  dist = (價 − MA150) / ATR14                     ← 單位：ATR
  S2 價 > MA150 且 升            （推進）
  S3 價 > MA150 且 唔升          （做頭）
  S4 價 ≤ MA150 且（跌 或 dist < −2 ATR）  （下跌）
  S1 價 ≤ MA150、唔跌、且 dist ≥ −2 ATR    （打底）

  ★ 為咩要 −2 ATR：跌市中 MA150 會先跌後平。價格遠低於一條已經平咗嘅
    MA（dist < −2 ATR）代表「跌完但未回到均值」，唔係打底。冇呢條，
    S1 會吞掉 37% 樣本（實測），四階段就失去分辨力。
    加上之後分佈 S1 13% / S2 21% / S3 7% / S4 59%（2026-11-25，596 隻）。

健康度（只用 S2% 同 S4% 兩欄，讀者可自己覆核）
  score = S2% − S4%
  ≥ +5 Strong ｜ −15…+5 Healthy ｜ −35…−15 Neutral ｜ < −35 Weak

輸出：data/stage_theme.json
用法：python stage_theme.py
"""
from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PKL = os.path.join(HERE, "data", "screener_ohlc.pkl")
IND = os.path.join(HERE, "data", "ticker_industry.json")
OUT = os.path.join(HERE, "data", "stage_theme.json")
OUT_PAGE = os.path.join(HERE, "data", "stage_for_page.json")

MA_LEN = 150
SLOPE_SHORT = 20
SLOPE_LONG = 60
TREND_TH = 0.4          # ATR 單位
NEAR_ATR = 2.0          # 低於 MA 超過 2 ATR = 仍未回到均值，算 S4 唔算 S1
HIST_DAYS = 60          # 兩條線顯示幾多個交易日
MIN_N = 5               # 行業至少要幾多隻才顯示
MIN_BARS = MA_LEN + SLOPE_LONG + 5

STAGES = ("S1", "S2", "S3", "S4")


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["High"].astype(float), df["Low"].astype(float), df["Close"].astype(float)
    pc = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def stage_series(df: pd.DataFrame):
    """回傳 (stage Series, close Series) — 逐日標籤，UI 同歷史共用一個實作。"""
    df = df.dropna(subset=["Close"])
    if len(df) < MIN_BARS:
        return None
    c = df["Close"].astype(float)
    ma = c.rolling(MA_LEN).mean()
    atr = _atr(df)
    s20 = (ma - ma.shift(SLOPE_SHORT)) / atr
    s60 = (ma - ma.shift(SLOPE_LONG)) / atr
    trend = 0.6 * s20 + 0.4 * s60
    dist = (c - ma) / atr
    up = c > ma
    rise = trend > TREND_TH
    fall = trend < -TREND_TH
    far = dist < -NEAR_ATR
    st = pd.Series("S1", index=c.index, dtype=object)
    st[up & rise] = "S2"
    st[up & ~rise] = "S3"
    st[(~up) & (fall | far)] = "S4"
    st[(~up) & (~fall) & (~far)] = "S1"
    st[trend.isna() | ma.isna() | dist.isna()] = None
    return st, c


def _et_now():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("America/New_York"))


def _drop_partial(df: pd.DataFrame) -> pd.DataFrame:
    """未收市嘅當日 bar 要剔走。中途價會靜靜改寫整個階段判讀，
    而且冇任何地方會報錯 —— 所以喺入口就切走（Missing ≠ Zero）。"""
    if df is None or len(df) == 0:
        return df
    try:
        now = _et_now()
    except Exception:                                            # noqa: BLE001
        return df
    last = pd.Timestamp(df.index[-1]).date()
    mins = now.hour * 60 + now.minute
    if last == now.date() and 9 * 60 + 30 <= mins < 16 * 60 + 30:
        return df.iloc[:-1]
    return df


def _pcts(counts: dict, k: int) -> dict:
    """整數百分比，用最大餘數法 → 四欄一定加起來 100。
    逐欄 round() 會出現 101%（實測 Packaged Software），讀者一加就見到。"""
    raw = {s: 100.0 * counts[s] / k for s in STAGES}
    base = {s: int(raw[s]) for s in STAGES}
    left = 100 - sum(base.values())
    order = sorted(STAGES, key=lambda s: -(raw[s] - base[s]))
    for s in order[:max(0, left)]:
        base[s] += 1
    return base


def load():
    try:
        raw = pd.read_pickle(PKL)
    except (OSError, ValueError) as e:
        print(f"DATA_UNAVAILABLE: {PKL} ({e})", file=sys.stderr)
        return {}, {}
    ind = {}
    try:
        ind = json.load(io.open(IND, encoding="utf-8"))
    except (OSError, ValueError):
        print(f"⚠ 行業對照讀唔到：{IND}", file=sys.stderr)
    return raw, ind


def compute():
    raw, ind = load()
    if not raw:
        return {"status": "DATA_UNAVAILABLE"}

    per_day = {}          # date -> list[stage]
    today_stage = {}      # ticker -> stage
    for t, df in raw.items():
        try:
            df = _drop_partial(df)
            got = stage_series(df)
        except (KeyError, ValueError) as e:      # 個別壞檔唔可以拖死全頁
            print(f"⚠ {t} 跳過：{e}", file=sys.stderr)
            continue
        if got is None:
            continue
        st, _c = got
        last = st.dropna()
        if last.empty:
            continue
        today_stage[t] = str(last.iloc[-1])
        tail = st.iloc[-HIST_DAYS:]
        for d, v in tail.items():
            if v is None:
                continue
            per_day.setdefault(d, []).append(v)

    if not today_stage:
        return {"status": "DATA_UNAVAILABLE"}

    counts = {s: sum(1 for v in today_stage.values() if v == s) for s in STAGES}
    n = sum(counts.values())
    pct = {s: (100.0 * counts[s] / n) for s in STAGES}

    hist = []
    for d in sorted(per_day)[-HIST_DAYS:]:
        vals = per_day[d]
        k = len(vals)
        if k < 50:
            continue
        hist.append({
            "d": pd.Timestamp(d).strftime("%Y-%m-%d"),
            "n": k,
            "s1": round(100.0 * vals.count("S1") / k, 1),
            "s2": round(100.0 * vals.count("S2") / k, 1),
            "s3": round(100.0 * vals.count("S3") / k, 1),
            "s4": round(100.0 * vals.count("S4") / k, 1),
        })

    # 行業層：今日分佈 + ΔS2（對 20 個交易日前）
    prev_day = hist[-21]["d"] if len(hist) >= 21 else None
    prev_stage = {}
    if prev_day:
        for t, df in raw.items():
            try:
                got = stage_series(df)
            except (KeyError, ValueError):
                continue
            if got is None:
                continue
            st = got[0].dropna()
            ts = pd.Timestamp(prev_day)
            st = st[st.index <= ts]
            if not st.empty:
                prev_stage[t] = str(st.iloc[-1])

    groups = {}
    for t, s in today_stage.items():
        g = (ind.get(t) or {}).get("industry") or (ind.get(t) or {}).get("sector") or "未分類"
        g = str(g).strip() or "未分類"
        groups.setdefault(g, []).append(t)

    rows = []
    for g, members in groups.items():
        if len(members) < MIN_N:
            continue
        k = len(members)
        c = {s: sum(1 for t in members if today_stage.get(t) == s) for s in STAGES}
        pr = _pcts(c, k)
        row = {
            "group": g,
            "n": k,
            "s1": pr["S1"], "s2": pr["S2"], "s3": pr["S3"], "s4": pr["S4"],
        }
        if prev_stage:
            pm = [t for t in members if t in prev_stage]
            if len(pm) >= MIN_N:
                p2 = 100.0 * sum(1 for t in pm if prev_stage[t] == "S2") / len(pm)
                row["d_s2"] = round(row["s2"] - p2, 1)
        score = row["s2"] - row["s4"]
        row["score"] = score
        row["health"] = ("Strong" if score >= 5 else "Healthy" if score >= -15
                         else "Neutral" if score >= -35 else "Weak")
        rows.append(row)
    rows.sort(key=lambda r: (-r["s2"], -r["n"]))

    as_of = hist[-1]["d"] if hist else datetime.now().strftime("%Y-%m-%d")
    out = {
        "status": "OK",
        "as_of": as_of,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "universe": len(raw),
        "covered": n,
        "counts": counts,
        "pct": {s: round(pct[s], 1) for s in STAGES},
        "history": hist,
        "rows": rows,
        "groups_shown": len(rows),
        "groups_total": len(groups),
        "def": {
            "ma": MA_LEN, "slope": [SLOPE_SHORT, SLOPE_LONG], "trend_th": TREND_TH,
            "hist_days": HIST_DAYS, "min_n": MIN_N, "min_bars": MIN_BARS,
            "health": "score = S2% − S4%；≥+5 Strong｜≥−15 Healthy｜≥−35 Neutral｜<−35 Weak",
            "note": "自建重建（Weinstein 四階段），唔係供應商原指標。",
        },
    }
    return out


def main() -> int:
    out = compute()
    if out.get("status") != "OK":
        print("⚠ stage_theme：DATA_UNAVAILABLE（唔會寫檔，唔會當 0）", file=sys.stderr)
        return 1
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # ── 同一份計算，輸出 stage_page.py 用嘅舊 schema（一套定義、兩個畫面）──
    _HEALTH_ZH = {"Strong": "強", "Healthy": "健康", "Neutral": "中性", "Weak": "弱"}
    page = {
        "asof": out["as_of"],
        "n": out["covered"],
        "agg": out["counts"],
        "agg_pct": out["pct"],
        "groups": [{
            "group": r["group"], "n": r["n"],
            "S1": round(r["s1"] * r["n"] / 100), "S2": round(r["s2"] * r["n"] / 100),
            "S3": round(r["s3"] * r["n"] / 100), "S4": round(r["s4"] * r["n"] / 100),
            "pct": {"S1": r["s1"], "S2": r["s2"], "S3": r["s3"], "S4": r["s4"]},
            "health": _HEALTH_ZH.get(r["health"], "中性"),
        } for r in out["rows"]],
        "history": [{"date": h["d"], "n": h["n"], "S1": h["s1"], "S2": h["s2"],
                     "S3": h["s3"], "S4": h["s4"]} for h in out["history"]],
        "params": {"ma_days": MA_LEN, "slope_days": [SLOPE_SHORT, SLOPE_LONG],
                   "trend_th_atr": TREND_TH, "near_atr": NEAR_ATR},
        "source": "trading-os-web/stage_theme.py（screener_ohlc.pkl）",
    }
    with io.open(OUT_PAGE, "w", encoding="utf-8") as f:
        json.dump(page, f, ensure_ascii=False, indent=1)
    c = out["counts"]
    p = out["pct"]
    print(f"✓ 主題 Stage 分佈 {out['as_of']}｜覆蓋 {out['covered']}/{out['universe']} 隻"
          f"｜S1 {p['S1']}% S2 {p['S2']}% S3 {p['S3']}% S4 {p['S4']}%"
          f"｜行業 {out['groups_shown']}/{out['groups_total']}")
    top = out["rows"][:3]
    for r in top:
        print(f"   {r['group']:<28} S2 {r['s2']:>3}% S4 {r['s4']:>3}% {r['health']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
