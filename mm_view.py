# -*- coding: utf-8 -*-
"""mm_view.py — MM Model 頁面嘅三個圖（對正 Mark Minervini 原圖格式）

圖 1  價格（log）+ 模型權益曲線，左上角統計（Max DD / Total Return / Gain Per Annum）
圖 2  Composite Indicator — 樓梯線，0-100，40 / 60 虛線，左下角「date = value」
圖 3  S&P 500 Allocation % — 樓梯線，0-100，左下角「date = value」
＋ 年回報表（Model vs S&P）、期間回報表（YTD / 1 / 2 / 5 / 10 / 15 / 20 / Max）

純 SVG，無 CDN。
"""
from __future__ import annotations

import math as _m

GREEN = "#2f8f5b"
DARK = "#3f3f46"
GREY = "#9ca3af"
ORANGE = "#d2694a"
BLUE = "#5b6ca8"


def _s(v):
    return f"{v:.1f}"


def price_chart(cs, stats_m, stats_b, W=1160):
    """圖 1：S&P（藍）× 模型（橙），log 尺，左邊統計，下面年份。"""
    px, eq = cs.get("px") or [], cs.get("eq") or []
    if len(px) < 50:
        return '<div class="dim">DATA_UNAVAILABLE</div>'
    n = len(px)
    pad_l, pad_r = 58, 54
    x0, x1 = pad_l, W - pad_r
    h = 260
    H = h + 26

    vals = [v for v in px if v] + [v for v in eq if v]
    lo, hi = _m.log10(min(vals)), _m.log10(max(vals))
    pad = (hi - lo) * 0.06
    lo, hi = lo - pad, hi + pad

    def X(i):
        return x0 + i / max(1, n - 1) * (x1 - x0)

    def Y(v):
        return 6 + (hi - _m.log10(v)) / (hi - lo) * (h - 12)

    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-width:660px;max-width:{W}px" '
         f'role="img" aria-label="MM Model vs S&P 500 (log)">']
    # 對數格線（同原圖一樣：32 / 100 / 316 / 1,000 / …）
    for exp in range(1, 6):
        for mult in (1, 3.162):
            v = (10 ** exp) * mult
            if lo <= _m.log10(v) <= hi:
                P.append(f'<line x1="{x0}" y1="{Y(v):.1f}" x2="{x1}" y2="{Y(v):.1f}" '
                         f'stroke="#e5e7eb" stroke-width="0.7"/>')
                lab = f"{v:,.0f}"
                P.append(f'<text x="{x0-5}" y="{Y(v)+3:.1f}" font-size="9" fill="#6b7280" '
                         f'text-anchor="end">{lab}</text>')
                P.append(f'<text x="{x1+5}" y="{Y(v)+3:.1f}" font-size="9" fill="#6b7280">{lab}</text>')
    P.append(f'<polyline points="' + " ".join(
        f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(px) if v)
        + f'" fill="none" stroke="{BLUE}" stroke-width="1.1"/>')
    P.append(f'<polyline points="' + " ".join(
        f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(eq) if v)
        + f'" fill="none" stroke="{ORANGE}" stroke-width="1.2"/>')
    # 左上統計（同原圖位置）
    P.append(f'<text x="{x0+6}" y="16" font-size="10" fill="#111827" font-weight="700">'
             f'Max Drawdown: 模型 {stats_m["maxdd"]}%　S&amp;P {stats_b["maxdd"]}%</text>')
    P.append(f'<text x="{x0+6}" y="30" font-size="10" fill="#111827" font-weight="700">'
             f'Total Return: 模型 {stats_m["total"]:,.0f}%　S&amp;P {stats_b["total"]:,.0f}%'
             f'　Gain Per Annum: {stats_m["cagr"]}%</text>')
    # 年份
    last, lastx = "", -1e9
    for i, ds in enumerate(cs["date"]):
        yr = ds[:4]
        if yr != last:
            last = yr
            if X(i) - lastx > (x1 - x0) * 0.045:
                lastx = X(i)
                P.append(f'<text x="{X(i):.1f}" y="{H-6}" font-size="9" fill="#6b7280" '
                         f'text-anchor="middle">{yr}</text>')
    P.append('</svg>')
    return "".join(P)


def step_chart(dates, values, W=1160, h=110, colour=GREEN, label="", value_txt="",
               dash=(40, 60), lo=0, hi=100):
    """圖 2／3：樓梯線（同原圖一樣一格一格跳）。"""
    if not dates or len(dates) < 5:
        return '<div class="dim">DATA_UNAVAILABLE</div>'
    n = len(values)
    pad_l, pad_r = 30, 40
    x0, x1 = pad_l, W - pad_r
    H = h + 22

    def X(i):
        return x0 + (i / max(1, n - 1)) * (x1 - x0)

    def Y(v):
        return 4 + (hi - max(lo, min(hi, v))) / (hi - lo) * (h - 8)

    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-width:660px;max-width:{W}px" '
         f'role="img" aria-label="{label}">']
    for v in range(10, hi, 10):
        P.append(f'<line x1="{x0}" y1="{Y(v):.1f}" x2="{x1}" y2="{Y(v):.1f}" '
                 f'stroke="#eef0f2" stroke-width="0.6"/>')
        if v % 20 == 0:
            P.append(f'<text x="{x0-4}" y="{Y(v)+3:.1f}" font-size="8.5" fill="#6b7280" '
                     f'text-anchor="end">{v}</text>')
            P.append(f'<text x="{x1+4}" y="{Y(v)+3:.1f}" font-size="8.5" fill="#6b7280">{v}</text>')
    for d in dash or ():
        P.append(f'<line x1="{x0}" y1="{Y(d):.1f}" x2="{x1}" y2="{Y(d):.1f}" '
                 f'stroke="#9ca3af" stroke-width="0.9" stroke-dasharray="5 4"/>')
    pts = []
    for i, v in enumerate(values):
        if v is None:
            continue
        pts.append(f"{X(i):.1f},{Y(v):.1f}")
        if i < n - 1:
            pts.append(f"{X(i+1):.1f},{Y(v):.1f}")     # 樓梯：橫向保留到下一格
    P.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{colour}" '
             f'stroke-width="1"/>')
    P.append(f'<text x="{x0+4}" y="{h-14}" font-size="9.5" fill="#111827">{value_txt}</text>')
    P.append(f'<text x="{x0+4}" y="{h-3}" font-size="9" fill="#6b7280">{label}</text>')
    last, lastx = "", -1e9
    for i, ds in enumerate(dates):
        yr = ds[:4]
        if yr != last:
            last = yr
            if X(i) - lastx > (x1 - x0) * 0.045:
                lastx = X(i)
                P.append(f'<text x="{X(i):.1f}" y="{H-4}" font-size="9" fill="#6b7280" '
                         f'text-anchor="middle">{yr}</text>')
    P.append('</svg>')
    return "".join(P)


def annual_table(rows):
    out = ['<div class="tscroll"><table class="mm-tbl"><thead><tr>'
           '<th data-v="0">年</th><th class="n">Model</th><th class="n">S&amp;P 500</th>'
           '<th class="n">差</th></tr></thead><tbody>']
    for r in rows:
        d = r["m"] - r["b"]
        cls = "mm-on" if d > 0 else "mm-off"
        out.append(f'<tr><td data-v="{r["year"]}">{r["year"]}</td>'
                   f'<td class="n">{r["m"]:+.1f}%</td>'
                   f'<td class="n">{r["b"]:+.1f}%</td>'
                   f'<td class="n {cls}">{d:+.1f}%</td></tr>')
    out.append('</tbody></table></div>')
    return "".join(out)


def period_table(periods):
    out = ['<table class="mm-tbl"><thead><tr><th>期間</th>'
           '<th class="n">Model</th><th class="n">S&amp;P 500</th></tr></thead><tbody>']
    for k, v in periods:
        out.append(f'<tr><td>{k}</td><td class="n">{v[0]:+.1f}%</td>'
                   f'<td class="n">{v[1]:+.1f}%</td></tr>')
    out.append('</tbody></table>')
    return "".join(out)
