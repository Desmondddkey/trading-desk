# -*- coding: utf-8 -*-
"""stage_page.py — Stage Analysis（Weinstein 四階段），市場 › Stage Analysis

只讀 output/stage_analysis.json；collector（stage_analysis.py）每日跑。
"""
from __future__ import annotations

import html as _h
import io
import json
import os
from datetime import date

_T = "C:/Users/rain0/trading-os/output/stage_analysis.json"
COL = {"S1": "#3b7dd8", "S2": "#d8a12a", "S3": "#d63384", "S4": "#e8657a"}
NAME = {"S1": "S1 底部", "S2": "S2 上升", "S3": "S3 頭部", "S4": "S4 下跌"}
HC = {"強": "#1f7f52", "健康": "#2f8f5b", "中性": "#6b7280", "弱": "#b4751a", "看淡": "#a04a44"}

CSS = """
<style>
.st-kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:0 0 10px}
.st-kpi>div{border:1px solid var(--hair);border-radius:8px;padding:8px 10px}
.st-kpi .k{font-size:11px;opacity:.65}
.st-kpi .v{font-size:20px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.2}
.st-bar{display:flex;height:14px;border-radius:4px;overflow:hidden;margin:2px 0 8px}
.st-bar i{display:block;height:100%}
.st-leg{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;opacity:.9}
.st-leg span{display:inline-flex;align-items:center;gap:5px}
.st-leg b{display:inline-block;width:9px;height:9px;border-radius:2px}
.st-hist{margin:10px 0 0}
.st-tbl table{width:100%;border-collapse:collapse;font-size:12px}
.st-tbl th{text-align:left;font-weight:600;padding:5px 6px;border-bottom:1px solid var(--hair);
  font-size:11px;opacity:.75;white-space:nowrap}
.st-tbl td{padding:5px 6px;border-bottom:1px solid rgba(148,163,184,.12);vertical-align:middle}
.st-tbl td.n{text-align:right;font-variant-numeric:tabular-nums}
.st-mini{display:flex;height:8px;border-radius:3px;overflow:hidden;min-width:90px;width:150px}
.st-mini i{display:block;height:100%}
.st-chip{font-size:10.5px;padding:1px 7px;border-radius:999px;color:#fff;white-space:nowrap}
.st-note{font-size:10.5px;opacity:.55;margin-top:8px}
@media(max-width:760px){.st-kpi{grid-template-columns:repeat(2,1fr)}
  .st-mini{width:70px;min-width:70px}}
</style>
"""


def _svg(hist):
    if len(hist) < 2:
        return ""
    W, H, PAD = 1000, 190, 26
    keys = ["S1", "S2", "S3", "S4"]
    mx = max(max(h[k] for k in keys) for h in hist)
    mx = max(10, min(100, mx * 1.12))
    n = len(hist)
    def X(i): return PAD + i * (W - 2 * PAD) / (n - 1)
    def Y(v): return H - PAD - v / mx * (H - 2 * PAD)
    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" '
         f'style="max-width:100%;height:auto" role="img" aria-label="四階段佔比走勢">']
    for g in range(0, int(mx) + 1, max(5, int(mx // 4))):
        P.append(f'<line x1="{PAD}" y1="{Y(g):.1f}" x2="{W-PAD}" y2="{Y(g):.1f}" '
                 f'stroke="currentColor" stroke-opacity=".12" stroke-width="1"/>')
        P.append(f'<text x="4" y="{Y(g)+3:.1f}" font-size="9" fill="currentColor" '
                 f'opacity=".5">{g}%</text>')
    for k in keys:
        pts = " ".join(f"{X(i):.1f},{Y(h[k]):.1f}" for i, h in enumerate(hist))
        P.append(f'<polyline points="{pts}" fill="none" stroke="{COL[k]}" stroke-width="1.8" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')
        P.append(f'<circle cx="{X(n-1):.1f}" cy="{Y(hist[-1][k]):.1f}" r="3" fill="{COL[k]}"/>')
    for i in (0, n - 1):
        P.append(f'<text x="{X(i):.1f}" y="{H-6}" font-size="9" fill="currentColor" '
                 f'opacity=".5" text-anchor="{"start" if i == 0 else "end"}">{hist[i]["date"]}</text>')
    P.append("</svg>")
    return "".join(P)


def build():
    try:
        with io.open(_T, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:                                    # noqa: BLE001
        return ("Stage Analysis",
                f'<div class="card"><div class="body dim">DATA_UNAVAILABLE：'
                f'{_h.escape(type(e).__name__)}（{_h.escape(_T)}）</div></div>')

    asof = d.get("asof") or "?"
    age = None
    try:
        age = (date.today() - date.fromisoformat(asof)).days
    except Exception:                                         # noqa: BLE001
        pass
    warn = ""
    if age is not None and age > 4:
        warn = (f'<p class="st-note" style="color:#b4751a">⚠ 數據停咗 {age} 日'
                f'（最後 {asof}）——collector 未跑</p>')

    agg, pct = d.get("agg", {}), d.get("agg_pct", {})
    P = [CSS]
    P.append('<div class="card"><h2>Stage Analysis '
             f'<small>{_h.escape(asof)} · {d.get("n", 0)} 隻</small></h2><div class="body">')
    P.append('<div class="st-kpi">')
    for k in ("S1", "S2", "S3", "S4"):
        P.append(f'<div><div class="k">{NAME[k]}</div>'
                 f'<div class="v" style="color:{COL[k]}">{pct.get(k, 0):.1f}%</div>'
                 f'<div class="k">{agg.get(k, 0)} 隻</div></div>')
    P.append("</div>")

    P.append('<div class="st-bar">')
    for k in ("S1", "S2", "S3", "S4"):
        P.append(f'<i style="width:{pct.get(k, 0)}%;background:{COL[k]}"></i>')
    P.append("</div>")
    P.append('<div class="st-leg">')
    for k in ("S1", "S2", "S3", "S4"):
        P.append(f'<span><b style="background:{COL[k]}"></b>{NAME[k]} '
                 f'{pct.get(k, 0):.1f}%（{agg.get(k, 0)}）</span>')
    P.append("</div>")
    warn and P.append(warn)
    P.append("</div></div>")

    hist = d.get("history") or []
    if hist:
        P.append('<div class="card"><h2>S2 佔比走勢 '
                 f'<small>近 {len(hist)} 週</small></h2><div class="body st-hist">')
        P.append(_svg(hist))
        P.append('<div class="st-leg" style="margin-top:6px">')
        for k in ("S1", "S2", "S3", "S4"):
            P.append(f'<span><b style="background:{COL[k]}"></b>{NAME[k]}</span>')
        P.append("</div>")
        P.append('<div class="st-note">每週用同一條規則重算（30 週 SMA、4 週斜率 ±1%）；'
                 '樣本 = 當時有足夠週線嘅股票，所以 n 會同今日總數唔同。</div>')
        P.append("</div></div>")

    rows = d.get("groups") or []
    P.append('<div class="card"><h2>行業分組 '
             f'<small>{len(rows)} 組（每組 ≥3 隻）</small></h2><div class="body">')
    P.append('<div class="st-tbl"><table><thead><tr>'
             '<th>行業</th><th class="n">隻數</th><th>分佈</th>'
             '<th class="n">S1</th><th class="n">S2</th><th class="n">S3</th>'
             '<th class="n">S4</th><th>健康</th></tr></thead><tbody>')
    for r in rows:
        p = r["pct"]
        P.append("<tr>"
                 f'<td>{_h.escape(r["group"])}</td>'
                 f'<td class="n" data-v="{r["n"]}">{r["n"]}</td>'
                 '<td><div class="st-mini">'
                 + "".join(f'<i style="width:{p[k]}%;background:{COL[k]}"></i>'
                           for k in ("S1", "S2", "S3", "S4"))
                 + "</div></td>"
                 + "".join(f'<td class="n" data-v="{p[k]}">{p[k]:.1f}%</td>'
                           for k in ("S1", "S2", "S3", "S4"))
                 + f'<td><span class="st-chip" style="background:{HC.get(r["health"], "#6b7280")}">'
                   f'{r["health"]}</span></td></tr>')
    P.append("</tbody></table></div>")
    P.append('<div class="st-note">S2 ≥70% 強｜60–70 健康｜45–60 中性｜30–45 弱｜&lt;30 看淡。'
             '分類：收市 vs 30 週 SMA、SMA 4 週斜率 ±1%。</div>')
    P.append("</div></div>")
    return ("Stage Analysis", "".join(P))
