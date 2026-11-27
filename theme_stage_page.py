# -*- coding: utf-8 -*-
"""theme_stage_page.py — 「主題」tab（四階段 S1–S4）呈現層。

Data 由 stage_theme.py 產生（唯一實作），呢個模組只讀 data/stage_theme.json。
缺失一律顯示 —（Missing ≠ Zero）。
"""
from __future__ import annotations

import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "stage_theme.json")

C_S1 = "#6b7280"
C_S2 = "#3b82f6"
C_S3 = "#c8a63a"
C_S4 = "#ec4899"
HCOL = {"Strong": "#3ddc97", "Healthy": "#7DBE8A", "Neutral": "#f5c542", "Weak": "#ff8b8b"}
HZH = {"Strong": "強", "Healthy": "健", "Neutral": "中", "Weak": "弱"}

CSS = """
.ths-bar{display:flex;height:12px;border-radius:6px;overflow:hidden;margin:2px 0 10px}
.ths-bar span{display:block;height:100%}
.ths-chips{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin:0 0 12px}
.ths-chip{border:1px solid rgba(148,163,184,.25);border-radius:10px;padding:7px 6px 6px;
  background:rgba(148,163,184,.06)}
.ths-chip .k{font-size:10.5px;letter-spacing:.06em;opacity:.6;font-weight:800}
.ths-chip .v{font-size:19px;font-weight:800;line-height:1.15;font-variant-numeric:tabular-nums}
.ths-chip .n{font-size:10.5px;opacity:.55;font-variant-numeric:tabular-nums}
.ths-svg{display:block;width:100%;height:auto;margin:2px 0 4px}
.ths-lg{display:flex;gap:14px;font-size:11.5px;opacity:.72;margin:0 0 2px}
.ths-lg i{display:inline-block;width:16px;height:2.5px;border-radius:2px;vertical-align:3px;
  margin-right:5px}
.ths-rd{font-size:13.5px;line-height:1.55;margin:10px 0 0}
.ths-tbl{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums;
  table-layout:fixed}
.ths-tbl th{text-align:left;font-size:10px;letter-spacing:.03em;opacity:.6;font-weight:700;
  padding:5px 3px;border-bottom:1px solid rgba(148,163,184,.3);white-space:nowrap}
.ths-tbl td{padding:4px 3px;border-bottom:1px solid rgba(148,163,184,.1);white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.ths-tbl col.c-g{width:auto}
.ths-hb{font-size:11px;font-weight:800;letter-spacing:.02em}
.ths-dn{opacity:.45}
"""


def _j(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _svg(hist):
    """兩條線：S2%（藍）同 S4%（粉），60 個交易日，固定 0–100 軸。"""
    if len(hist) < 5:
        return ""
    W, H, PL, PR, PT, PB = 320, 108, 4, 4, 6, 14
    n = len(hist)
    def x(i):
        return PL + (W - PL - PR) * i / max(1, n - 1)
    def y(v):
        return PT + (H - PT - PB) * (1 - v / 100.0)
    def line(key, col):
        pts = " ".join(f"{x(i):.1f},{y(h[key]):.1f}" for i, h in enumerate(hist))
        return (f'<polyline fill="none" stroke="{col}" stroke-width="1.6" '
                f'stroke-linejoin="round" points="{pts}"/>')
    grid = "".join(
        f'<line x1="{PL}" x2="{W-PR}" y1="{y(v):.1f}" y2="{y(v):.1f}" '
        f'stroke="currentColor" stroke-opacity=".12" stroke-width="1"/>'
        for v in (0, 50, 100))
    lbl = (f'<text x="{PL}" y="{H-3}" font-size="8" fill="currentColor" opacity=".45">'
           f'{hist[0]["d"][5:]}</text>'
           f'<text x="{W-PR}" y="{H-3}" font-size="8" fill="currentColor" opacity=".45" '
           f'text-anchor="end">{hist[-1]["d"][5:]}</text>')
    return (f'<svg class="ths-svg" viewBox="0 0 {W} {H}" preserveAspectRatio="none" '
            f'role="img" aria-label="S2 同 S4 百分比走勢">'
            f'{grid}{line("s4", C_S4)}{line("s2", C_S2)}{lbl}</svg>')


def panel_html() -> str:
    d = _j(SRC)
    head = ('<div class="nxt-block"><h3>主題 · 四階段 S1–S4</h3>')
    if d.get("status") != "OK" or not d.get("rows"):
        return ('<section class="nxt-panel" id="panel-theme">'
                '<div class="nxt-block"><h3>主題 · 四階段 S1–S4</h3>'
                '<p class="nxt-note" style="margin:0">— 未取得數據（唔會當 0）。</p></div></section>')

    p, c = d.get("pct") or {}, d.get("counts") or {}
    order = [("S1", C_S1), ("S2", C_S2), ("S3", C_S3), ("S4", C_S4)]
    bar = "".join(f'<span style="width:{p.get(k, 0)}%;background:{col}"></span>'
                  for k, col in order)
    chips = "".join(
        f'<div class="ths-chip"><div class="k" style="color:{col}">{k}</div>'
        f'<div class="v" style="color:{col}">{p.get(k, "—")}%</div>'
        f'<div class="n">{c.get(k, "—")} 隻</div></div>' for k, col in order)

    hist = d.get("history") or []
    s2_now = p.get("S2") or 0
    s4_now = p.get("S4") or 0
    if s4_now >= 55:
        rd = (f'S4 <b>{s4_now}%</b> 過半 → 大市仍然向下，'
              f'S2 只有 {s2_now}%。呢個環境嘅默認動作係<b>唔加倉</b>，'
              f'唔係揀邊隻股。')
    elif s2_now >= 40:
        rd = f'S2 <b>{s2_now}%</b> 主導 → 推進階段，可以正常做突破。'
    else:
        rd = (f'S2 {s2_now}%／S4 {s4_now}% → 分裂市：'
              f'只做自己行業 S2 最高嗰兩三個，其餘唔做。')
    if len(hist) >= 11:
        dd = hist[-1]["s2"] - hist[-11]["s2"]
        rd += (f'<br>S2 線 10 日 <b>{dd:+.1f}pp</b>'
               f'（{"改善" if dd > 0.5 else "轉差" if dd < -0.5 else "橫行"}）。')
    elif len(hist) >= 2:
        dd = hist[-1]["s2"] - hist[0]["s2"]
        rd += f'<br>S2 線期內 <b>{dd:+.1f}pp</b>。'

    rows = []
    for r in d["rows"]:
        col = HCOL.get(r.get("health"), "currentColor")
        lb = HZH.get(r.get("health"), "—")
        d2 = r.get("d_s2")
        d2s = "—" if d2 is None else f'{d2:+.0f}'
        d2cls = "" if d2 is None or abs(d2) >= 1 else " ths-dn"
        g = r["group"]
        rows.append(
            f'<tr><td title="{g}">{g}</td>'
            f'<td class="ths-dn">{r.get("n", "—")}</td>'
            f'<td class="ths-dn">{r.get("s1", "—")}%</td>'
            f'<td style="font-weight:800;color:{C_S2}">{r.get("s2", "—")}%</td>'
            f'<td class="ths-dn">{r.get("s3", "—")}%</td>'
            f'<td style="color:{C_S4}">{r.get("s4", "—")}%</td>'
            f'<td class="{d2cls.strip()}">{d2s}</td>'
            f'<td class="ths-hb" style="color:{col}" title="{r.get("health", "")}">{lb}</td></tr>')

    h = ['<section class="nxt-panel" id="panel-theme">', head,
         f'<p class="nxt-note" style="margin:0 0 8px">{d.get("as_of", "—")}｜'
         f'覆蓋 {d.get("covered", "—")}/{d.get("universe", "—")} 隻'
         f'（歷史不足 {d.get("universe", 0) - d.get("covered", 0)} 隻剔除）</p>',
         f'<div class="ths-bar">{bar}</div>',
         f'<div class="ths-chips">{chips}</div>',
         f'<div class="ths-lg"><span><i style="background:{C_S2}"></i>S2 推進</span>'
         f'<span><i style="background:{C_S4}"></i>S4 下跌</span></div>',
         _svg(hist),
         f'<p class="ths-rd">{rd}</p>',
         '</div>',
         '<div class="nxt-block"><h3>行業分佈（按 S2 排）</h3>',
         '<div class="nxt-hscroll"><table class="ths-tbl">'
         '<colgroup><col class="c-g"><col style="width:22px"><col style="width:34px">'
         '<col style="width:38px"><col style="width:34px"><col style="width:38px">'
         '<col style="width:34px"><col style="width:24px"></colgroup>'
         '<thead><tr>'
         '<th>行業</th><th>n</th><th>S1</th><th>S2</th><th>S3</th><th>S4</th>'
         '<th>ΔS2</th><th>健</th></tr></thead><tbody>',
         "".join(rows),
         '</tbody></table></div>',
         f'<p class="nxt-note">健 = 強/健/中/弱（= S2%−S4%：≥+5／≥−15／≥−35／其餘）。'
         f'只列 ≥{d.get("def", {}).get("min_n", 5)} 隻嘅行業'
         f'（{d.get("groups_shown", "—")}/{d.get("groups_total", "—")} 個）；'
         f'n&lt;10 嘅百分比波動大。ΔS2 = 相對 20 個交易日前（pp）。</p></div>',
         '<div class="nxt-block"><h3>定義（可以自己覆核）</h3>'
         '<p class="nxt-note" style="margin:0">'
         'MA150（≈30 週線）＋斜率（20 日／60 日，ATR 單位）。'
         '價&gt;MA 且升 = S2；價&gt;MA 但唔升 = S3；'
         '價≤MA 且跌（或低於 MA 超過 2 ATR）= S4；其餘貼近 MA = S1。<br>'
         '健康 = S2% − S4%：≥+5 Strong、≥−15 Healthy、≥−35 Neutral、其餘 Weak。'
         '<br>呢個係按定義自建，唔係 Deepvue 原指標；我哋池係流動股 '
         f'{d.get("universe", "—")} 隻，唔可以同全美股家數直接比。</p></div>',
         '</section>']
    return "".join(h)


if __name__ == "__main__":
    print(panel_html()[:400])
