# -*- coding: utf-8 -*-
"""beachball_page.py — 沙灘球反應（Water Balloon）

數據來源：C:/Users/rain0/trading-os/output/beachball.json
定義（同 beachball.py 一致，唔准另作解釋）
  · 逆市上升 = SPY 跌嘅日子，隻股照升（最近 20 個交易日計次數）
  · NHBP = RS 線創 20 日新高，但股價未創 20 日新高（領導先於價格）
  · 沙灘球分 = NHBP × 2 + 逆市上升
"""
from __future__ import annotations

import glob
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"C:/Users/rain0/trading-os/output/beachball.json"
IND = os.path.join(HERE, "data", "ticker_industry.json")


def _esc(x):
    return (str(x).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _load(p, default):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return default


CSS = """
.bb-note{font-size:11px;line-height:1.7;opacity:.72;margin:0 0 12px;max-width:820px}
.bb-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
.bb-tbl th{text-align:left;font-weight:800;font-size:11px;letter-spacing:.04em;
  opacity:.6;padding:6px 8px;border-bottom:1px solid rgba(148,163,184,.25);
  white-space:nowrap}
.bb-tbl td{padding:5px 8px;border-bottom:1px solid rgba(148,163,184,.10);
  font-variant-numeric:tabular-nums}
.bb-tbl td.n,.bb-tbl th.n{text-align:right}
.bb-tk{font-weight:800;text-decoration:none;color:inherit}
.bb-tk:hover{color:#f97316}
.bb-ind{font-size:10.5px;opacity:.55;margin-top:1px}
.bb-sc{font-weight:800;color:#22c55e;font-size:14px}
.bb-bar{height:3px;background:rgba(148,163,184,.2);border-radius:2px;margin-top:3px}
.bb-bar i{display:block;height:100%;background:#22c55e;border-radius:2px}
"""


def _irs():
    fs = sorted(glob.glob(r"C:/Users/rain0/trading-os-web/output/industry_rs_20*.json"))
    if not fs:
        return {}
    try:
        d = json.load(io.open(fs[-1], encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(r.get("industry") or "").lower(): r for r in (d.get("rows") or [])}


def build():
    d = _load(SRC, {})
    rows = d.get("rows") or []
    ind = {str(k).upper(): (v.get("industry") or v.get("sector") or "")
           for k, v in _load(IND, {}).items()}

    if not rows:
        return ("沙灘球反應", "<p>DATA_UNAVAILABLE — 未跑 beachball.py</p>")

    grs = _irs()
    top = max(r["ball"] for r in rows) or 1
    out = [f'<style>{CSS}</style>',
           '<div class="card"><h2 style="margin:0 0 6px">沙灘球反應</h2>',
           f'<div style="font-size:11px;opacity:.55;margin:0 0 8px">'
           f'數據日 {_esc(d.get("as_of"))}｜視窗 {d.get("window")} 個交易日｜'
           f'{d.get("n")} 隻</div>',
           '<div class="bb-note">'
           '<b>逆市上升</b>＝SPY 跌嗰日隻股照升，計次數。'
           '<b>NHBP</b>＝RS 線（股／SPY）創 20 日新高，但股價未创 20 日新高'
           '（領導先於價格）。<b>沙灘球分</b>＝NHBP × 2 ＋ 逆市上升。'
           '沙灘球＝被按落水即彈返上嚟，大市越差越明顯。'
           '</div>',
           '<table class="bb-tbl"><thead><tr>',
           '<th>#</th><th>代號</th><th class="n">沙灘球分</th>'
           '<th class="n">逆市上升</th><th class="n">NHBP</th>',
           '<th class="n">GROUP RS</th>',
           '<th class="n">20 日相對 SPY</th><th class="n">收市</th>',
           '</tr></thead><tbody>']

    for i, r in enumerate(rows, 1):
        t = r.get("ticker") or ""
        rel = r.get("rel20")
        rc = "#22c55e" if (rel or 0) > 0 else "#ef4444"
        w = 100.0 * r["ball"] / top

        _g = grs.get((ind.get(t.upper(), "") or "").lower())
        if _g and isinstance(_g.get("rs"), (int, float)):
            _d = _g.get("delta")
            _dtxt = (f' <span style="font-size:10.5px;opacity:.8">{_d:+.0f}</span>'
                     if isinstance(_d, (int, float)) else "")
            gcell = (f'<td class="n" style="color:#22c55e"><b>{_g["rs"]:.0f}</b>'
                     f'{_dtxt}</td>')
        else:
            gcell = '<td class="n" style="opacity:.35">—</td>'

        out.append(
            f'<tr><td style="opacity:.45">{i}</td>'
            f'<td><a class="bb-tk" href="https://www.tradingview.com/chart/?symbol={_esc(t)}"'
            f' target="_blank" rel="noopener">{_esc(t)}</a>'
            f'<div class="bb-ind">{_esc(ind.get(t.upper(), "—"))}</div></td>'
            f'<td class="n"><span class="bb-sc">{r["ball"]}</span>'
            f'<div class="bb-bar"><i style="width:{w:.0f}%"></i></div></td>'
            f'<td class="n">{r["down_up"]}</td>'
            f'<td class="n">{r["nhbp"]}</td>'
            + gcell
            + f'<td class="n" style="color:{rc}">{rel if rel is not None else "—"}%</td>'
            f'<td class="n">{r.get("last")}</td></tr>')

    out.append('</tbody></table></div>')
    return ("沙灘球反應", "".join(out))
