# -*- coding: utf-8 -*-
"""rsnewhigh_page.py — RS 新高領先股（10 個交易日內創相對強度新高）。

數據：data/rs_new_high.json（rsnewhigh_fetch.py；來源 Chinar Amrutkar market-leaders）
呢頁只顯示，唔自己再計 RS —— 數值同來源保持一致，避免「同名兩義」。
"""
from __future__ import annotations

import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "rs_new_high.json")

CSS = """
.rn-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:0 0 4px}
.rn-head h2{margin:0;font-size:19px;font-weight:800}
.rn-meta{font-size:11px;opacity:.6}
.rn-chips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.rn-chip{font-size:11.5px;padding:3px 9px;border-radius:99px;cursor:pointer;
  border:1px solid rgba(148,163,184,.35);background:transparent;color:inherit}
.rn-chip.on{background:rgba(59,130,246,.16);border-color:#3b82f6;font-weight:700}
.rn-tbl{width:100%;border-collapse:separate;border-spacing:0;font-size:12.5px}
.rn-tbl th{position:sticky;top:0;z-index:2;background:#0b1220;text-align:left;
  font-size:10.5px;font-weight:800;letter-spacing:.04em;opacity:.75;padding:6px 7px;
  border-bottom:1px solid rgba(148,163,184,.3);white-space:nowrap;cursor:pointer}
.rn-tbl td{padding:3px 7px;border-bottom:1px solid rgba(148,163,184,.10);
  white-space:nowrap;font-variant-numeric:tabular-nums}
html[data-theme="light"] .rn-tbl th{background:#f6f8fb}
.rn-tk{font-weight:800;text-decoration:none;color:inherit}
.rn-tk:hover{color:#f97316}
.rn-nm{max-width:230px;overflow:hidden;text-overflow:ellipsis;opacity:.75}
.rn-y{color:#22c55e;font-weight:700}
.rn-n{opacity:.25}
.rn-note{font-size:10.5px;line-height:1.7;opacity:.62;margin-top:10px;max-width:900px}
.rn-wrap{max-height:calc(100vh - 240px);overflow:auto}
"""

JS = r"""
(function(){
  var root=document.getElementById('rnRoot'); if(!root) return;
  var rows=[].slice.call(root.querySelectorAll('tbody tr'));
  var chips=[].slice.call(root.querySelectorAll('.rn-chip'));
  var state={minAdr:0, minDvol:0, onlyWeek:false, maxAgo:10};
  function apply(){
    var n=0;
    rows.forEach(function(r){
      var d=r.dataset, ok=true;
      if(parseFloat(d.ago)>state.maxAgo) ok=false;
      if(state.minAdr && parseFloat(d.adr||0)<state.minAdr) ok=false;
      if(state.minDvol && parseFloat(d.dvol||0)<state.minDvol) ok=false;
      if(state.onlyWeek && d.wk!=='1') ok=false;
      r.style.display=ok?'':'none';
      if(ok) n++;
    });
    var c=document.getElementById('rnCount'); if(c) c.textContent='顯示 '+n+' / '+rows.length+' 隻';
  }
  chips.forEach(function(b){
    b.addEventListener('click',function(){
      var k=b.dataset.k, v=b.dataset.v;
      if(k==='adr'){ state.minAdr = (state.minAdr===parseFloat(v))?0:parseFloat(v); }
      if(k==='dvol'){ state.minDvol = (state.minDvol===parseFloat(v))?0:parseFloat(v); }
      if(k==='wk'){ state.onlyWeek=!state.onlyWeek; }
      chips.forEach(function(x){
        if(x.dataset.k===k){
          var on=false;
          if(k==='adr') on = state.minAdr===parseFloat(x.dataset.v);
          if(k==='dvol') on = state.minDvol===parseFloat(x.dataset.v);
          if(k==='wk') on = state.onlyWeek===true;
          x.classList.toggle('on',on);
        }
      });
      apply();
    });
  });
  apply();
})();
"""


def _load(p, d):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return d


def _n(v, d=1, plus=False):
    if v is None or v == "":
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    return f"{f:+.{d}f}" if plus else f"{f:.{d}f}"


def build():
    d = _load(SRC, {})
    rows = d.get("rows") or []
    if not rows:
        return ("RS 新高領先股",
                "<p>DATA_UNAVAILABLE — 未跑 rsnewhigh_fetch.py（data/rs_new_high.json）</p>")

    body = [f"<style>{CSS}</style>", '<div class="card" id="rnRoot">']
    body.append('<div class="rn-head"><h2>RS 新高領先股</h2>'
                f'<span class="rn-meta">{len(rows)} 隻｜{_esc(d.get("as_of"))}'
                f'｜10 個交易日內創 RS 新高</span></div>')
    body.append('<div class="rn-chips">'
                '<span class="rn-chip" data-k="adr" data-v="4">ADR ≥4%</span>'
                '<span class="rn-chip" data-k="adr" data-v="8">ADR ≥8%</span>'
                '<span class="rn-chip" data-k="dvol" data-v="20">成交額 ≥$20M</span>'
                '<span class="rn-chip" data-k="dvol" data-v="100">成交額 ≥$100M</span>'
                '<span class="rn-chip" data-k="wk" data-v="1">有週線 RS 訊號</span>'
                '<span class="rn-meta" id="rnCount" style="margin-left:auto"></span>'
                '</div>')

    heads = ["代號", "名稱", "板塊", "突破日", "距今", "價", "ADR%",
             "成交額$M", "突破%", "3M", "6M", "12M", "週線", "距週高%"]
    body.append('<div class="rn-wrap"><table class="rn-tbl"><thead><tr>'
                + "".join(f"<th>{h}</th>" for h in heads) + "</tr></thead><tbody>")
    for r in rows:
        y = lambda v: '<span class="rn-y">✓</span>' if v else '<span class="rn-n">·</span>'
        body.append(
            f'<tr data-ago="{r.get("ago") or 0}" data-adr="{r.get("adr") or 0}"'
            f' data-dvol="{r.get("dvol_m") or 0}" data-wk="{1 if r.get("wk") else 0}">'
            f'<td><a class="rn-tk" href="https://www.tradingview.com/chart/?symbol={r["t"]}"'
            f' target="_blank" rel="noopener" data-sym="{r["t"]}">{r["t"]}</a></td>'
            f'<td class="rn-nm">{_esc(r.get("name"))}</td>'
            f'<td class="rn-nm">{_esc(r.get("sector"))}</td>'
            f'<td>{_esc(r.get("date"))}</td><td>{r.get("dago") if r.get("dago") is not None else "—"}</td>'
            f'<td>{_n(r.get("close"), 2)}</td><td>{_n(r.get("adr"), 1)}</td>'
            f'<td>{_n(r.get("dvol_m"), 0)}</td><td>{_n(r.get("bp"), 2)}</td>'
            f'<td>{y(r.get("s3"))}</td><td>{y(r.get("s6"))}</td><td>{y(r.get("s12"))}</td>'
            f'<td>{y(r.get("wk"))}</td><td>{_n(r.get("wk_px"), 1)}</td></tr>')
    body.append('</tbody></table></div>')
    body.append(
        '<p class="rn-note">① 定義由來源決定：過去 10 個交易日內，RS ratio（股價相對基準）'
        '創 250 日新高；3M／6M／12M 係同一件事拉長窗口；週線訊號係週線級別。'
        '② 「距今」＝突破日距最新一日嘅工作日數（來源嘅 sessions_ago 同日期有矛盾，我以日期為準）。'
        '③ 數字唔會二次加工；缺失顯示 —。'
        '④ 排序：預設「距今」升序（最新突破先），任何欄可以撳。</p>')
    body.append('</div>')
    body.append(f"<script>{JS}</script>")
    return ("RS 新高領先股", "".join(body))


def _esc(x):
    import html
    return html.escape(str(x if x is not None else ""))
