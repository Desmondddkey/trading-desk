# -*- coding: utf-8 -*-
"""htf_page.py — HTF High Tight Flag + 50/80 法則（選股 › HTF Flag）

來源：Elite Swing Traders @1ChartMaster（2026-11-09）
只讀 output/htf_flag.json。"""
from __future__ import annotations

import html as _h
import io
import json
import os
from datetime import date

_T = "C:/Users/rain0/trading-os/output/htf_flag.json"
TAG_C = {"高位附近": "#1f7f52", "回調": "#6b7280", "深度回調": "#b4751a",
         "腰斬": "#a04a44", "蒸發八成": "#7f1d1d"}

CSS = """
<style>
.hf-kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:0 0 10px}
.hf-kpi>div{border:1px solid var(--hair);border-radius:8px;padding:8px 10px}
.hf-kpi .k{font-size:11px;opacity:.65}
.hf-kpi .v{font-size:20px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.2}
.hf-tbl{overflow-x:auto;-webkit-overflow-scrolling:touch}
.hf-tbl table{min-width:640px;width:100%;border-collapse:collapse;font-size:12px}
.hf-tbl th{text-align:left;font-weight:600;padding:5px 6px;border-bottom:1px solid var(--hair);
  font-size:11px;opacity:.75;white-space:nowrap}
.hf-tbl td{padding:5px 6px;border-bottom:1px solid rgba(148,163,184,.12);white-space:nowrap}
.hf-tbl td.n{text-align:right;font-variant-numeric:tabular-nums}
.hf-chip{font-size:10.5px;padding:1px 7px;border-radius:999px;color:#fff}
.hf-note{font-size:10.5px;opacity:.55;margin-top:8px}
@media(max-width:760px){.hf-kpi{grid-template-columns:repeat(2,1fr)}}
</style>
"""


def build():
    try:
        with io.open(_T, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:                                    # noqa: BLE001
        return ("HTF Flag", f'<div class="card"><div class="body dim">DATA_UNAVAILABLE：{_h.escape(type(e).__name__)}</div></div>')

    asof = d.get("asof") or "?"
    age = None
    try:
        age = (date.today() - date.fromisoformat(asof)).days
    except Exception:                                         # noqa: BLE001
        pass
    rows = d.get("rows") or []
    near = sum(1 for r in rows if r["tag"] == "高位附近")
    rule50 = sum(1 for r in rows if r["rule"] == "50")
    rule80 = sum(1 for r in rows if r["rule"] == "80")

    P = [CSS]
    P.append('<div class="card"><h2>HTF High Tight Flag '
             f'<small>{_h.escape(asof)} · 8 週內 +100% 清單</small></h2><div class="body">')
    P.append('<div class="hf-kpi">')
    P.append(f'<div><div class="k">HTF 名單</div><div class="v">{d.get("n_flag", 0)}</div>'
             f'<div class="k">掃描 {d.get("n_universe", 0)} 隻</div></div>')
    P.append(f'<div><div class="k">50/80 受害者</div>'
             f'<div class="v" style="color:#a04a44">{d.get("n_50_80", 0)}</div>'
             f'<div class="k">腰斬 {rule50}｜蒸發八成 {rule80}</div></div>')
    P.append(f'<div><div class="k">仍喺高位 ±10%</div><div class="v" style="color:#1f7f52">{near}</div>'
             '<div class="k">未被法則擊中</div></div>')
    P.append(f'<div><div class="k">命中率</div>'
             f'<div class="v">{(d.get("n_50_80", 0) / max(1, d.get("n_flag", 1)) * 100):.0f}%</div>'
             '<div class="k">HTF → 腰斬或更差</div></div>')
    P.append("</div>")
    if age is not None and age > 4:
        P.append(f'<p class="hf-note" style="color:#b4751a">⚠ 數據停咗 {age} 日</p>')
    P.append('<p class="hf-note">規則：40 個交易日內由區間低點升 ≥100% → HTF；'
             '之後由最高收市跌 ≥50% = 腰斬，≥80% = 蒸發八成。'
             '名單按跌幅排序 —— 上面係「升得最靚、跌得最傷」嗰批。</p>')
    P.append("</div></div>")

    if rows:
        P.append('<div class="card"><h2>名單 '
                 f'<small>{len(rows)} 隻</small></h2><div class="body">')
        P.append('<div class="hf-tbl"><table><thead><tr>'
                 '<th>代號</th><th class="n">升幅</th><th class="n">幾日</th>'
                 '<th class="n">高位</th><th class="n">現價</th><th class="n">距高位</th>'
                 '<th>狀態</th><th>成立日</th></tr></thead><tbody>')
        for r in rows:
            c = TAG_C.get(r["tag"], "#6b7280")
            P.append("<tr>"
                     f'<td><b>{_h.escape(r["ticker"])}</b></td>'
                     f'<td class="n" data-v="{r["gain"]}">+{r["gain"]:.0f}%</td>'
                     f'<td class="n" data-v="{r["run_days"]}">{r["run_days"]}</td>'
                     f'<td class="n">{r["peak"]:.2f}</td>'
                     f'<td class="n">{r["last"]:.2f}</td>'
                     f'<td class="n" data-v="{r["drawdown"]}">{r["drawdown"]:.0f}%</td>'
                     f'<td><span class="hf-chip" style="background:{c}">{r["tag"]}</span></td>'
                     f'<td>{r["flag_date"]}</td></tr>')
        P.append("</tbody></table></div></div></div>")
    return ("HTF Flag", "".join(P))
