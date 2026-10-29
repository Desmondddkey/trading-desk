# -*- coding: utf-8 -*-
"""grade_colors.py — 評分顏色唯一來源（RS 位置圖 scatter = FOCUS/STALK 表）

Desmond 2026-10-29：「下面兩個列表要跟返 RS 位置圖 A+ / A / B / C 既顏色」
數值直接照 rs_scan 散點圖原本嘅色，兩處以後只可以經呢個檔取色。
"""
GRADE_COLORS = {
    "A+": "#22c55e",   # 綠
    "A":  "#f97316",   # 橙
    "B":  "#3b82f6",   # 藍
    "C":  "#ef4444",   # 紅
    "D":  "#7f1d1d",   # 深紅
}


def col(g, default="rgba(148,163,184,.75)"):
    return GRADE_COLORS.get(g, default)
