# -*- coding: utf-8 -*-
"""weekly_gate.py — 週線 10SMA 進場閘（Qullamaggie 式「optimal weekly entry」）

來源（Desmond 2026-10-28 貼文）：
  「if things are not at the optimal entry point on the weekly, maybe I
   shouldn't swing it on the daily.」
  「buying weakness into the weekly 10 SMA within the context of
   leadership and a base, is a stress free way of trading.」

定義（寫死）
  週線 = 日線 resample W-FRI
  W10  = 10 週簡單平均
  d%   = (現價 − W10) / W10 × 100
  rising = W10 連續 2 週上升

判定
  |d%| ≤ 3 且 rising      → "貼W10"（最佳週線進場點）
  −6 ≤ d% < −3 且 rising  → "接近"（等回多一點）
  d% > 3                  → "偏離"（離週線太遠，日線 swing 勝算低）
  其他                     → "未到位"

用法
  from weekly_gate import w10_info
  info = w10_info(df)      # df: 日線 OHLC，index=日期，需 Close（最好有 High/Low）
"""
from __future__ import annotations

import pandas as pd


def _weekly(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if not isinstance(d.index, pd.DatetimeIndex):
        d.index = pd.to_datetime(d.index)
    agg = {}
    if "Open" in d.columns:
        agg["Open"] = "first"
    if "High" in d.columns:
        agg["High"] = "max"
    if "Low" in d.columns:
        agg["Low"] = "min"
    if "Close" in d.columns:
        agg["Close"] = "last"
    if "Volume" in d.columns:
        agg["Volume"] = "sum"
    if "Close" not in agg:            # 只有一個 Series 嘅情況
        agg = {"Close": "last"}
    return d.resample("W-FRI").agg(agg).dropna(subset=["Close"])


def w10_info(df, tol=3.0):
    """回傳 dict(d_pct, rising, label, w10) 或 None"""
    try:
        if df is None or len(df) < 70:
            return None
        if isinstance(df, pd.Series):
            df = df.to_frame("Close")
        w = _weekly(df)
        if len(w) < 12:
            return None
        w10 = w["Close"].rolling(10).mean()
        if w10.dropna().empty:
            return None
        _cl = df["Close"].dropna() if isinstance(df, pd.DataFrame) else df.dropna()
        if len(_cl) == 0:
            return None
        cur = float(_cl.iloc[-1])
        base = float(w10.iloc[-1])
        prev = float(w10.iloc[-2])
        if not base or cur != cur or base != base:   # nan 保護
            return None
        d_pct = (cur / base - 1) * 100
        rising = bool(base > prev)
        if abs(d_pct) <= tol and rising:
            label = "貼W10"
        elif -6 <= d_pct < -tol and rising:
            label = "接近"
        elif d_pct > tol:
            label = "偏離"
        else:
            label = "未到位"
        return {"d_pct": round(d_pct, 2), "rising": rising,
                "label": label, "w10": round(base, 2)}
    except Exception:                                        # noqa: BLE001
        return None


def badge(info, cls="wg"):
    """小徽章 HTML：貼W10 綠色、接近 橙、偏離 灰"""
    if not info:
        return ""
    lab = info["label"]
    col = {"貼W10": "#22c55e", "接近": "#f97316"}.get(lab, "#94a3b8")
    show = {"貼W10": "W10", "接近": "W10~"}.get(lab, "")
    if not show:
        return ""
    tip = (f"距週線 10SMA {info['d_pct']:+.1f}%"
           f"｜{'上升' if info['rising'] else '下降'}｜{lab}")
    return (f'<span class="{cls}" title="{tip}" style="color:{col};'
            f'font-weight:800;font-size:10.5px;margin-left:4px">{show}</span>')
