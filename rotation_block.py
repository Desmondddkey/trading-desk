# -*- coding: utf-8 -*-
"""rotation_block.py — 行業輪動區塊（放喺 Sectors 頁最頂）

Desmond 2026-10-24：
  「將 rotation-map 個 job 變成 daily；新增到我既 Sector，重點放最高，
   之後下面轉強 Focus、觀察 Stalk、同轉弱，最後成個列表」

分工（同一把尺，唔准另創）：
  重點   = 輪動分 top 3
  轉強   = stage ∈ {加速, 成熟}
  觀察   = stage ∈ {再現, 新興}
  轉弱   = stage == 轉弱
  全部   = 34 個行業完整列表
★ 同 rotation_map.py 畫 PNG 嘅分組完全一致（見該檔 strengths/watch/weak）。

數據：trading-os-lab/output/rotation_latest.json（由 rotation_map.py 寫）
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = r"C:/Users/rain0/trading-os-lab/output/rotation_latest.json"

FOCUS = ("加速", "成熟")
STALK = ("再現", "新興")


def _esc(v):
    import html as h
    return h.escape(str(v)) if v is not None else ""


def _p(v, d=1):
    try:
        return f"{float(v):+.{d}f}%"
    except (TypeError, ValueError):
        return "—"


def _cls(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "rot-flat"
    return "rot-pos" if x > 0 else ("rot-neg" if x < 0 else "rot-flat")


CSS = """
.rot-h{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:0 0 2px}
.rot-h h2{margin:0;font-size:20px}
.rot-sub{font-size:11.5px;opacity:.62}
.rot-top{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));
  gap:10px;margin:10px 0 14px}
.rot-card{border:1px solid rgba(128,128,128,.28);border-radius:10px;
  padding:10px 12px;background:rgba(128,128,128,.04)}
.rot-card .rk{font-size:10.5px;font-weight:800;opacity:.55;letter-spacing:.06em}
.rot-card .nm{font-size:14px;font-weight:800;margin:2px 0 1px}
.rot-card .et{font-size:10.5px;opacity:.6}
.rot-card .sc{font-size:26px;font-weight:800;line-height:1.1;margin-top:4px}
.rot-card .row{font-size:11.5px;opacity:.8;margin-top:3px}
.rot-3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:6px 0 14px}
.rot-pan{border:1px solid rgba(128,128,128,.24);border-radius:10px;
  padding:8px 10px;background:rgba(128,128,128,.03)}
.rot-pan h4{margin:0 0 6px;font-size:12.5px;font-weight:800;
  display:flex;gap:6px;align-items:baseline}
.rot-pan h4 small{font-weight:400;opacity:.55;font-size:10.5px}
.rot-pan .it{font-size:11.5px;padding:2px 0;border-bottom:1px solid rgba(128,128,128,.1)}
.rot-pan .it:last-child{border:0}
.rot-pan .it b{font-weight:800}
.rot-tbl{width:100%;border-collapse:collapse;font-size:11.5px;
  font-variant-numeric:tabular-nums;table-layout:fixed}
.rot-tbl th{text-align:left;font-size:10px;font-weight:700;opacity:.6;
  padding:4px 5px;border-bottom:1px solid rgba(128,128,128,.3);white-space:nowrap}
.rot-tbl td{padding:3px 5px;border-bottom:1px solid rgba(128,128,128,.1);
  text-align:left;overflow:hidden}
.rot-tbl tr:hover td{background:rgba(249,115,22,.05)}
.rot-pos{color:#15803d}.rot-neg{color:#dc2626}.rot-flat{opacity:.5}
html[data-theme="dark"] .rot-pos{color:#7ce0a8}
html[data-theme="dark"] .rot-neg{color:#ff8f8f}
.rot-stage{font-size:10px;font-weight:800;padding:1px 5px;border-radius:999px;
  border:1px solid currentColor;display:inline-block;white-space:nowrap}
.rot-x{display:inline-block;min-width:46px;font-variant-numeric:tabular-nums}
.rot-note{font-size:10.5px;opacity:.6;line-height:1.65;margin-top:6px}
@media(max-width:820px){
  .rot-3{grid-template-columns:1fr}
  .rot-tbl{font-size:11.5px}
  .rot-tbl th:nth-child(3),.rot-tbl td:nth-child(3),
  .rot-tbl th:nth-child(9),.rot-tbl td:nth-child(9){display:none}
}
"""

STAGE_COL = {"加速": "#22c55e", "成熟": "#4ade80", "再現": "#38bdf8",
             "新興": "#f59e0b", "轉弱": "#f97316", "落後": "#94a3b8"}


def _stage(st):
    col = STAGE_COL.get(st, "#94a3b8")
    return f'<span class="rot-stage" style="color:{col}">{_esc(st)}</span>'


def _it(r):
    return (f'<div class="it"><b>{_esc(r.get("name"))}</b> '
            f'<span style="opacity:.55;font-size:10.5px">{_esc(r.get("etf"))}</span>'
            f'　<span class="{_cls(r.get("x1m"))}">{_p(r.get("x1m"))}</span>'
            f'<span style="opacity:.5;font-size:10.5px"> 1M</span></div>')


def _xb(x, scale=12.0):
    """超額回報 mini bar：中線 0，右綠左紅，scale = ±12%"""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return ""
    w = min(1.0, abs(v) / scale) * 26.0
    c = "#22c55e" if v >= 0 else "#ef4444"
    if v >= 0:
        rect = f'<rect x="28" y="3" width="{w:.1f}" height="5" fill="{c}" rx="2"/>'
    else:
        rect = f'<rect x="{28 - w:.1f}" y="3" width="{w:.1f}" height="5" fill="{c}" rx="2"/>'
    return (f'<svg width="56" height="11" viewBox="0 0 56 11" '
            f'style="vertical-align:-1px">'
            f'<rect x="0" y="3" width="56" height="5" fill="rgba(128,128,128,.14)" rx="2"/>'
            f'{rect}<line x1="28" y1="1.5" x2="28" y2="9.5" stroke="currentColor" '
            f'stroke-width="1" opacity=".3"/></svg>')


def build():
    if not os.path.exists(DATA):
        return ('<div class="card"><div class="rot-h"><h2>行業 RS</h2>'
                '<span class="rot-sub">DATA_UNAVAILABLE</span></div>'
                '<div class="dim">未跑 rotation_map.py</div></div>')
    try:
        d = json.load(io.open(DATA, encoding="utf-8"))
    except Exception as e:                                     # noqa: BLE001
        return (f'<div class="card"><div class="dim">'
                f'rotation_latest.json 讀唔到：{_esc(type(e).__name__)}</div></div>')

    rows = d.get("rows") or []
    if not rows:
        return '<div class="card"><div class="dim">輪動數據為空</div></div>'

    P = [f"<style>{CSS}</style>"]
    P.append('<div class="card" style="padding:0 0 8px">')
    P.append('<div class="rot-h"><h2>行業 RS</h2>'
             f'<span class="rot-sub">數據 {_esc(d.get("date"))}'
             f'｜{len(rows)} 個行業</span></div>')
    P.append('<table class="rot-tbl"><colgroup>'
             '<col style="width:30px"><col style="width:52px">'
             '<col><col style="width:86px"><col style="width:40px">'
             '<col style="width:120px"><col style="width:120px">'
             '<col style="width:120px"><col style="width:40px">'
             '</colgroup><thead><tr>'
             '<th>#</th><th>ETF</th><th>名稱</th><th>PHASE</th><th>RS</th>'
             '<th>1W</th><th>1M</th><th>3M</th><th>寬</th>'
             '</tr></thead><tbody>')
    for r in rows:
        br = ("寬" if r.get("above20") in (1, True, "1")
              else ("窄" if r.get("above20") in (0, False, "0") else "?"))
        tk = r.get("etf") or ""
        P.append(
            '<tr>'
            f'<td>{_esc(r.get("rank"))}</td>'
            f'<td><a class="tv" data-sym="{_esc(tk)}" '
            f'href="https://www.tradingview.com/chart/?symbol={_esc(tk)}" '
            f'target="_blank" rel="noopener">{_esc(tk)}</a></td>'
            f'<td style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
            f'{_esc(r.get("name"))}</td>'
            f'<td>{_stage(r.get("stage"))}</td>'
            f'<td>{int(float(r.get("score") or 0))}</td>'
            f'<td><span class="rot-x">{_p(r.get("x1w"))}</span>{_xb(r.get("x1w"))}</td>'
            f'<td><span class="rot-x">{_p(r.get("x1m"))}</span>{_xb(r.get("x1m"))}</td>'
            f'<td><span class="rot-x">{_p(r.get("x3m"))}</span>{_xb(r.get("x3m"))}</td>'
            f'<td class="{"rot-pos" if br == "寬" else "rot-flat"}">{br}</td>'
            '</tr>')
    P.append('</tbody></table>')
    P.append('<div class="rot-note">'
             '數值＝行業回報 − SPY 回報；bar 中線 0，右綠左紅（±12% 滿格）。'
             'PHASE 沿用原本階段分組。'
             '</div>')
    P.append('</div>')
    return "".join(P)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    h = build()
    print(f"rotation block: {len(h):,} chars")
    for k in ("重點", "轉強 Focus", "觀察 Stalk", "轉弱", "全部行業"):
        print(("OK  " if k in h else "MISS") + f" {k}")
