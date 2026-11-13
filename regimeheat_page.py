# -*- coding: utf-8 -*-
"""regimeheat_page.py — 環境熱力圖：今日 2D 環境 + Setup×環境 矩陣。

數據：trading-os/output/regime_heat.json（regime_heat.py，每日一次）
規則：每格樣本 < 10 一律標 insufficient（灰色），唔准用顏色扮有 edge。
"""
from __future__ import annotations

import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(r"C:\Users\rain0\trading-os", "output", "regime_heat.json")

CSS = """
.rh-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:0 0 6px}
.rh-head h2{margin:0;font-size:19px;font-weight:800}
.rh-meta{font-size:11px;opacity:.6}
.rh-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0 16px}
@media (max-width:760px){.rh-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
.rh-q{border:1px solid rgba(148,163,184,.28);border-radius:6px;padding:8px 10px}
.rh-q.on{border-color:#3b82f6;background:rgba(59,130,246,.10)}
.rh-q b{font-size:13px}
.rh-q div{font-size:11px;opacity:.65;margin-top:2px}
.rh-tbl{width:100%;border-collapse:collapse;font-size:12px}
.rh-tbl th{text-align:left;font-size:10.5px;letter-spacing:.04em;opacity:.6;font-weight:800;
  padding:6px 8px;border-bottom:1px solid rgba(148,163,184,.3);white-space:nowrap}
.rh-tbl td{padding:4px 8px;border-bottom:1px solid rgba(148,163,184,.12);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.rh-c{border-radius:4px;padding:2px 6px;display:inline-block;min-width:64px;text-align:center}
.rh-na{opacity:.35;border:1px dashed rgba(148,163,184,.4)}
.rh-note{font-size:10.5px;line-height:1.7;opacity:.62;margin-top:10px;max-width:900px}
"""

QNAME = {"Q1": "低波動 × 趨勢", "Q2": "高波動 × 趨勢",
         "Q3": "低波動 × 區間", "Q4": "高波動 × 區間"}


def _load(p, d=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return d


def _cell(c):
    if not c or not c.get("n"):
        return '<span class="rh-c rh-na">—</span>'
    if not c.get("enough"):
        return f'<span class="rh-c rh-na" title="樣本 {c["n"]} < 10">{c["n"]}｜未夠樣本</span>'
    ev = c.get("ev_r") or 0
    col = "#15803d" if ev > 0 else "#b91c1c"
    bg = "rgba(34,197,94,.14)" if ev > 0 else "rgba(239,68,68,.14)"
    return (f'<span class="rh-c" style="color:{col};background:{bg}">'
            f'{c["n"]}｜{ev:+.2f}R</span>')


def build():
    d = _load(SRC)
    if not d:
        return ("環境熱力圖",
                "<p>DATA_UNAVAILABLE — 未跑 regime_heat.py（output/regime_heat.json）</p>")
    t = d.get("today") or {}
    q = t.get("q")
    qs = ["Q1", "Q2", "Q3", "Q4"]

    p = [f"<style>{CSS}</style>", '<div class="card">']
    p.append('<div class="rh-head"><h2>環境熱力圖</h2>'
             f'<span class="rh-meta">數據日 {d.get("as_of")}｜'
             f'持續性 平均 {d.get("avg_run_days")} 日（≥3 日者 {d.get("avg_run_3plus")} 日）｜'
             f'指標視窗 {d.get("indicator_window")} 日</span></div>')

    p.append('<div class="rh-grid">')
    for x in qs:
        on = " on" if x == q else ""
        extra = (f'ATR% p{t.get("atrp_pct"):.0f}｜ER p{t.get("er_pct"):.0f}' if on else "　")
        p.append(f'<div class="rh-q{on}"><b>{x} {QNAME[x]}</b><div>{extra}</div></div>')
    p.append('</div>')

    # 轉移矩陣
    tr = d.get("transition_pct") or {}
    p.append('<h3 style="font-size:13px;margin:14px 0 6px">環境轉移機率（%）</h3>')
    p.append('<table class="rh-tbl"><thead><tr><th>由＼去</th>'
             + "".join(f'<th>{x}</th>' for x in qs) + '</tr></thead><tbody>')
    for a in qs:
        cells = "".join(f'<td>{tr.get(a, {}).get(b) if tr.get(a, {}).get(b) is not None else "—"}</td>'
                        for b in qs)
        p.append(f'<tr><td><b>{a}</b></td>{cells}</tr>')
    p.append('</tbody></table>')

    # Setup × 環境
    setups = d.get("setups") or {}
    p.append('<h3 style="font-size:13px;margin:16px 0 6px">Setup × 環境（n｜當日收市 EV）</h3>')
    p.append('<table class="rh-tbl"><thead><tr><th>Setup</th>'
             + "".join(f'<th>{x}</th>' for x in qs) + '</tr></thead><tbody>')
    for s in sorted(setups):
        row = setups[s]
        p.append(f'<tr><td><b>{s}</b></td>'
                 + "".join(f'<td>{_cell(row.get(x))}</td>' for x in qs) + '</tr>')
    p.append('</tbody></table>')

    lag = "⚠ 指標滯後：平均環境長度短過指標視窗，偵測到時可能已轉" \
        if (d.get("avg_run_3plus") or 0) < (d.get("indicator_window") or 0) else "✅ 滯後可接受"
    p.append(
        f'<p class="rh-note">① {lag}。'
        f'② 四象限用滾動 252 日百分位（50% 分界），唔用絕對門檻 —— 絕對門檻唔會適應市場。'
        f'③ 每格要 n ≥ {d.get("min_cell")} 才算數；未夠樣本嘅格一律灰色，唔准當 edge。'
        f'④ 已評分警報 {d.get("n_graded")} 單；要填滿 {len(setups)} 個 setup × 4 格，'
        f'大約要 {d.get("min_cell") * 4 * max(1, len(setups))} 單以上。'
        f'⑤ 呢頁係「今日邊類策略有資格」嘅閘，唔係入場訊號。</p>')
    p.append('</div>')
    return ("環境熱力圖", "".join(p))
