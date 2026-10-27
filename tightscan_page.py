# -*- coding: utf-8 -*-
"""tightscan_page.py — 全市場 Tight Range 掃描頁

數據：output/tight_scan.json（tight_scan.py；S&P500 ∪ L2，568 隻）
篩選：價≥$5、成交額≥$8M、TIGHT ≥ 60
"""
from __future__ import annotations

import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "output", "tight_scan.json")
IND = os.path.join(HERE, "data", "tv_meta.json")

CSS = """
.ts-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
.ts-tbl th{text-align:left;font-size:10.5px;letter-spacing:.04em;opacity:.55;
  font-weight:800;padding:6px 8px;border-bottom:1px solid rgba(148,163,184,.25);
  white-space:nowrap;cursor:pointer;user-select:none}
.ts-tbl th:hover{opacity:.9}
.ts-tbl td{padding:5px 8px;border-bottom:1px solid rgba(148,163,184,.1);
  font-variant-numeric:tabular-nums}
.ts-tbl td.n,.ts-tbl th.n{text-align:right}
.ts-tk{font-weight:800;text-decoration:none;color:inherit}
.ts-tk:hover{color:#f97316}
.ts-note{font-size:10.5px;line-height:1.65;opacity:.6;margin:10px 0 0;max-width:820px}
.ts-id{color:#22c55e;font-weight:800}
.ts-w{color:#f97316;font-weight:800}
"""

JS = """
function tsSort(th, i){
  var tb = th.closest('table').tBodies[0];
  var rows = Array.prototype.slice.call(tb.rows);
  var dir = th.dataset.dir === 'asc' ? -1 : 1;
  th.dataset.dir = dir === 1 ? 'desc' : 'asc';
  rows.sort(function(a,b){
    var x = parseFloat(a.cells[i].dataset.v), y = parseFloat(b.cells[i].dataset.v);
    if (isNaN(x)) x = -1e9; if (isNaN(y)) y = -1e9;
    return (y - x) * dir;
  });
  rows.forEach(function(r){ tb.appendChild(r); });
}
"""


def _load(p, d):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return d


def _bar(t):
    w = max(2.0, 54.0 * min(100.0, max(0.0, t)) / 100.0)
    c = "#22c55e" if t >= 70 else ("#f97316" if t >= 55 else "#94a3b8")
    tick = 2.0 + 54.0 * 0.70
    return (f'<svg width="58" height="10" viewBox="0 0 58 10">'
            f'<rect x="0" y="3" width="58" height="4" fill="rgba(128,128,128,.2)" rx="2"/>'
            f'<rect x="2" y="3" width="{w:.1f}" height="4" fill="{c}" rx="2"/>'
            f'<line x1="{tick:.1f}" y1="1.5" x2="{tick:.1f}" y2="9" '
            f'stroke="currentColor" stroke-width="1" opacity=".35"/></svg>')


def build():
    d = _load(SRC, {})
    rows = d.get("rows") or []
    if not rows:
        return ("Tight Range", "<p>DATA_UNAVAILABLE — 未跑 tight_scan.py</p>")

    ind = {str(k).upper(): (v.get("industry") or "")
           for k, v in _load(IND, {}).items()}

    P = [f"<style>{CSS}</style><script>{JS}</script>",
         '<div class="card">',
         '<h2 style="margin:0 0 4px">Tight Range 掃描</h2>',
         f'<div style="font-size:11px;opacity:.55;margin:0 0 10px">'
         f'數據日 {d.get("date")}｜宇宙 {d.get("universe")} 隻（S&P 500 ∪ L2）'
         f'｜命中 {d.get("hits")} 隻（TIGHT ≥ {d.get("min_tight"):.0f}）</div>',
         '<table class="ts-tbl"><thead><tr>',
         '<th class="n" onclick="tsSort(this,0)" data-dir="desc">TIGHT</th>',
         '<th onclick="tsSort(this,1)">代號</th>',
         '<th>行業</th>',
         '<th class="n" onclick="tsSort(this,3)">箱ATR</th>',
         '<th class="n" onclick="tsSort(this,4)">ID</th>',
         '<th class="n" onclick="tsSort(this,5)">距40MA</th>',
         '<th class="n" onclick="tsSort(this,6)">距52高</th>',
         '<th class="n" onclick="tsSort(this,7)">EXT</th>',
         '<th class="n" onclick="tsSort(this,8)">ATR%</th>',
         '<th class="n" onclick="tsSort(this,9)">成交額$M</th>',
         '</tr></thead><tbody>']

    for r in rows:
        t = r.get("ticker") or ""
        d40 = r.get("d40")
        d40c = "#f97316" if isinstance(d40, (int, float)) and abs(d40) <= 3 else "inherit"
        idc = ' class="ts-id"' if (r.get("inside") or 0) >= 2 else ""
        P.append(
            f'<tr><td class="n" data-v="{r["tight"]}">'
            f'<b>{r["tight"]:.0f}</b> {_bar(r["tight"])}</td>'
            f'<td><a class="ts-tk" href="https://www.tradingview.com/chart/?symbol={t}"'
            f' target="_blank" rel="noopener">{t}</a></td>'
            f'<td style="font-size:10.5px;opacity:.55">{ind.get(t, "")}</td>'
            f'<td class="n" data-v="{r["box_atr"]}">{r["box_atr"]}</td>'
            f'<td class="n" data-v="{r["inside"]}"><span{idc}>{r["inside"] or "—"}</span></td>'
            f'<td class="n" data-v="{d40}" style="color:{d40c}">{d40:+.1f}%</td>'
            f'<td class="n" data-v="{r["off52"]}">{r["off52"]:+.1f}%</td>'
            f'<td class="n" data-v="{r["ext"]}">{r["ext"]:.2f}</td>'
            f'<td class="n" data-v="{r["atrp"]}">{r["atrp"]:.1f}%</td>'
            f'<td class="n" data-v="{r["dollar_m"]}">{r["dollar_m"]:.0f}</td></tr>')

    P.append('</tbody></table>')
    P.append('<div class="ts-note">'
             '<b>TIGHT</b>＝100 ×（1 − 箱體ATR/6），箱體＝最近 10 日（最高−最低）÷ ATR50。'
             '≥70 綠（可做突破）｜55–69 橙（只做回調）｜＞70 分位置有刻度線。'
             '<b>ID</b>＝連續 inside day 日數（≥2 綠字，1ChartMaster「double inside days」）。'
             '<b>距40MA</b> ±3% 標橙＝貼 8 週線。'
             '<b>篩選</b>：價 ≥$5、成交額 ≥$8M、TIGHT ≥60；唔夠緊唔會出現。'
             '<b>注意</b>：TIGHT 只否決「鬆」，唔保證贏；入場仍要 RS + RVOL + LoD。'
             '</div></div>')
    return ("Tight Range", "".join(P))
