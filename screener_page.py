# -*- coding: utf-8 -*-
"""screener_page.py — 一個頁面做晒選股（Finviz 式篩選）。

數據：data/screener.json（screener_cache.py）
唯一尺：所有數字由 screener_cache.py 計，呢頁只負責篩選／顯示，唔准自己再計一次。

欄位定義（同 cache 一致，唔准改寫法）
  RS       本池百分位 0–99（3/6/9/12 個月相對 SPY 加權超額）
  ATR%     ATR14 ÷ 價
  ATRX     (價 − 50MA) ÷ ATR14
  TIGHT    100 × (1 − 10日高低箱 ÷ ATR50 ÷ 6)
  距21EMA  (價 − EMA21) ÷ ATR14
  距20日高 (價 ÷ 20日最高 − 1) × 100
  距52高   (價 ÷ 52週最高 − 1) × 100
"""
from __future__ import annotations

import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "screener.json")

CSS = """
.scr-head{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin:0 0 2px}
.scr-head h2{margin:0;font-size:19px;font-weight:800;letter-spacing:.01em}
.scr-meta{font-size:11px;opacity:.6}
.scr-tools{display:flex;flex-wrap:wrap;gap:6px;align-items:flex-end;margin:12px 0 8px}
.scr-f{display:flex;flex-direction:column;gap:2px}
.scr-f label{font-size:10px;opacity:.55;letter-spacing:.03em;white-space:nowrap}
.scr-f input,.scr-f select{background:rgba(148,163,184,.10);color:inherit;
  border:1px solid rgba(148,163,184,.30);border-radius:4px;padding:4px 6px;
  font-size:12px;font-variant-numeric:tabular-nums;min-width:64px}
.scr-f input:focus,.scr-f select:focus{outline:none;border-color:#3b82f6}
.scr-f.wide input{min-width:130px}
.scr-btn{background:rgba(148,163,184,.10);color:inherit;border:1px solid rgba(148,163,184,.30);
  border-radius:4px;padding:5px 9px;font-size:11.5px;cursor:pointer;white-space:nowrap}
.scr-btn:hover{border-color:#3b82f6}
.scr-btn.on{background:rgba(59,130,246,.16);border-color:#3b82f6;font-weight:700}
.scr-count{font-size:11.5px;opacity:.7;margin-left:auto;font-variant-numeric:tabular-nums}
.scr-wrap{max-height:78vh;overflow:auto;border-top:1px solid rgba(148,163,184,.22)}
.scr-tbl{width:100%;border-collapse:collapse;font-size:12.5px;table-layout:auto}
.scr-tbl th{position:sticky;top:0;z-index:2;background:#0b1220;
  text-align:left;font-size:10.5px;font-weight:800;letter-spacing:.04em;opacity:.72;
  padding:7px 7px;border-bottom:1px solid rgba(148,163,184,.30);white-space:nowrap;
  cursor:pointer;user-select:none}
.scr-tbl td{padding:3px 7px;border-bottom:1px solid rgba(148,163,184,.10);
  white-space:nowrap;font-variant-numeric:tabular-nums;text-align:left}
.scr-tbl tr:hover td{background:rgba(148,163,184,.08)}
.scr-tk{font-weight:800;text-decoration:none;color:inherit}
.scr-tk:hover{color:#f97316}
.scr-ind{max-width:230px;overflow:hidden;text-overflow:ellipsis;opacity:.75;font-size:11.5px}
.scr-tag{display:inline-block;font-size:10px;padding:0 4px;margin-right:3px;border-radius:3px;
  border:1px solid rgba(148,163,184,.35);opacity:.95}
.scr-tag.g{color:#22c55e;border-color:rgba(34,197,94,.55)}
.scr-tag.b{color:#3b82f6;border-color:rgba(59,130,246,.55)}
.scr-tag.o{color:#f97316;border-color:rgba(249,115,22,.55)}
.scr-up{color:#22c55e}.scr-dn{color:#ef4444}
.scr-note{font-size:10.5px;line-height:1.7;opacity:.6;margin:10px 0 0;max-width:900px}
html[data-theme="light"] .scr-tbl th{background:#f6f8fb}
/* 手機：只留決策欄（代號 RS ATR% ATRX TIGHT 距21EMA 距20日高 距52高 訊號） */
@media (max-width:900px){
  .scr-tbl th:nth-child(2),.scr-tbl td:nth-child(2),
  .scr-tbl th:nth-child(3),.scr-tbl td:nth-child(3),
  .scr-tbl th:nth-child(4),.scr-tbl td:nth-child(4),
  .scr-tbl th:nth-child(5),.scr-tbl td:nth-child(5),
  .scr-tbl th:nth-child(6),.scr-tbl td:nth-child(6),
  .scr-tbl th:nth-child(7),.scr-tbl td:nth-child(7),
  .scr-tbl th:nth-child(15),.scr-tbl td:nth-child(15),
  .scr-tbl th:nth-child(16),.scr-tbl td:nth-child(16){display:none}
  .scr-tbl{font-size:12px}
  .scr-tbl th,.scr-tbl td{padding:3px 5px}
  .scr-f input,.scr-f select{min-width:58px}
  .scr-f.wide input{min-width:120px}
}
"""

JS = r"""
(function(){
  var root=document.getElementById('scrRoot');
  if(!root) return;
  var rows=[].slice.call(root.querySelectorAll('tbody tr'));
  var $=function(id){return document.getElementById(id)};
  var msg=$('scrCount');
  function num(id,dflt){var v=parseFloat(($(id).value||'').trim());return isNaN(v)?dflt:v}
  function txt(id){return ($(id).value||'').trim().toLowerCase()}
  function apply(){
    var q=txt('fQ'), sec=$('fSector').value, tag=$('fTag').value;
    var rs=num('fRs',null), ax=num('fAtrx',null), tg=num('fTight',null),
        ap=num('fAtrp',null), rv=num('fRvol',null), d52=num('fD52',null),
        dv=num('fDvol',null);
    var shown=0;
    for(var i=0;i<rows.length;i++){
      var r=rows[i], d=r.dataset, ok=true;
      if(q && d.t.toLowerCase().indexOf(q)<0 && d.ind.toLowerCase().indexOf(q)<0) ok=false;
      if(ok && sec && d.sector!==sec) ok=false;
      if(ok && tag && d.tags.indexOf(tag)<0) ok=false;
      if(ok && rs!==null && (d.rs==='' || parseFloat(d.rs)<rs)) ok=false;
      if(ok && ax!==null && (d.atrx==='' || parseFloat(d.atrx)>ax)) ok=false;
      if(ok && tg!==null && (d.tight==='' || parseFloat(d.tight)<tg)) ok=false;
      if(ok && ap!==null && (d.atrp==='' || parseFloat(d.atrp)<ap)) ok=false;
      if(ok && rv!==null && (d.rvol==='' || parseFloat(d.rvol)<rv)) ok=false;
      if(ok && d52!==null && (d.d52==='' || parseFloat(d.d52)<d52)) ok=false;
      if(ok && dv!==null && (d.dvol==='' || parseFloat(d.dvol)<dv)) ok=false;
      r.style.display=ok?'':'none';
      if(ok) shown++;
    }
    msg.textContent='顯示 '+shown+' / '+rows.length+' 隻';
  }
  var ids=['fQ','fSector','fRs','fAtrx','fTight','fAtrp','fRvol','fD52','fDvol','fTag'];
  ids.forEach(function(id){
    var el=$(id); if(!el) return;
    el.addEventListener('input',apply); el.addEventListener('change',apply);
  });
  var PRESETS={
    '全部':      {fRs:'',fAtrx:'',fTight:'',fD52:'',fDvol:'',fTag:''},
    'A+ 候選':   {fRs:'80',fAtrx:'4',fTight:'40',fD52:'-15',fDvol:'30',fTag:''},
    '領導':      {fRs:'90',fAtrx:'',fTight:'',fD52:'-10',fDvol:'',fTag:'領導'},
    '近突破':    {fRs:'',fAtrx:'4',fTight:'',fD52:'-2',fDvol:'30',fTag:''},
    '回調':      {fRs:'75',fAtrx:'',fTight:'',fD52:'',fDvol:'',fTag:'回調'},
    '收縮':      {fRs:'70',fAtrx:'',fTight:'45',fD52:'-15',fDvol:'',fTag:''},
    '新高':      {fRs:'',fAtrx:'',fTight:'',fD52:'-1',fDvol:'',fTag:'新高'},
    'RS新高':    {fRs:'',fAtrx:'',fTight:'',fD52:'',fDvol:'',fTag:'RS新高'}
  };
  var btns=[].slice.call(root.querySelectorAll('.scr-presets .scr-btn'));
  if(!btns.length) btns=[].slice.call(root.querySelectorAll('[data-p]'));
  btns.forEach(function(b){
    b.addEventListener('click',function(){
      var p=PRESETS[b.dataset.p]||{};
      Object.keys(p).forEach(function(k){ var e=$(k); if(e) e.value=p[k]; });
      btns.forEach(function(x){x.classList.remove('on')});
      b.classList.add('on');
      apply();
    });
  });
  $('scrReset').addEventListener('click',function(){
    ['fQ','fRs','fAtrx','fTight','fAtrp','fRvol','fD52','fDvol'].forEach(function(k){$(k).value=''});
    $('fSector').value=''; $('fTag').value=''; apply();
  });
  $('scrCsv').addEventListener('click',function(){
    var hdrs=[].slice.call(root.querySelectorAll('thead th')).map(function(th){
      return th.textContent.replace(/[▼▲]/g,'').trim()});
    var out=[hdrs.join(',')];
    rows.forEach(function(r){
      if(r.style.display==='none') return;
      var cs=[].slice.call(r.cells).map(function(td){
        var s=(td.dataset.txt||td.textContent).replace(/\s+/g,' ').trim();
        return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;
      });
      out.push(cs.join(','));
    });
    var blob=new Blob(['\ufeff'+out.join('\n')],{type:'text/csv;charset=utf-8'});
    var a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download='screener_'+new Date().toISOString().slice(0,10)+'.csv';
    document.body.appendChild(a); a.click(); a.remove();
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
    return (f"{f:+.{d}f}" if plus else f"{f:.{d}f}")


def _cls(v):
    if v is None:
        return ""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    return "scr-up" if f > 0 else ("scr-dn" if f < 0 else "")


def _tight_cell(t):
    if t is None:
        return "—"
    try:
        f = float(t)
    except (TypeError, ValueError):
        return "—"
    c = "#22c55e" if f >= 70 else ("#f97316" if f >= 55 else "")
    style = f' style="color:{c};font-weight:700"' if c else ""
    return f'<span{style}>{f:.0f}</span>'


TAGCLS = {"領導": "g", "新高": "g", "RS新高": "b", "突破": "b", "回調": "o", "收縮": "o"}


def build():
    d = _load(SRC, {})
    rows = d.get("rows") or []
    if not rows:
        return ("Stock Screener",
                "<p>DATA_UNAVAILABLE — 未跑 screener_cache.py（data/screener.json）</p>")

    sectors = sorted({(r.get("sector") or "") for r in rows if r.get("sector")})
    sec_opts = "".join(f'<option value="{s}">{s}</option>' for s in sectors)

    body = []
    body.append(f"<style>{CSS}</style>")
    body.append('<div class="card" id="scrRoot">')
    body.append(
        '<div class="scr-head"><h2>STOCK SCREENER</h2>'
        f'<span class="scr-meta">{len(rows)} 隻｜價格截至 {d.get("as_of") or "—"}'
        f'｜掃描 {str(d.get("scan_generated") or "")[:10] or "—"}'
        f'｜RS = 本池百分位（基準 SPY）</span></div>')

    presets = ["全部", "A+ 候選", "領導", "近突破", "回調", "收縮", "新高", "RS新高"]
    pbtn = "".join(
        f'<button class="scr-btn{" on" if p == "全部" else ""}" data-p="{p}">{p}</button>'
        for p in presets)
    body.append(f'<div class="scr-tools">{pbtn}<span class="scr-count" id="scrCount"></span></div>')

    def fld(fid, label, ph="", wide=False, typ="number", step="any"):
        cls = "scr-f wide" if wide else "scr-f"
        return (f'<div class="{cls}"><label for="{fid}">{label}</label>'
                f'<input id="{fid}" type="{typ}" step="{step}" placeholder="{ph}"></div>')

    body.append('<div class="scr-tools">')
    body.append(fld("fQ", "搜尋 代號／行業", "NVDA / Semi", wide=True, typ="text"))
    body.append('<div class="scr-f"><label for="fSector">板塊</label>'
                f'<select id="fSector"><option value="">全部</option>{sec_opts}</select></div>')
    body.append(fld("fRs", "RS ≥", "0"))
    body.append(fld("fAtrx", "ATRX ≤", "99"))
    body.append(fld("fTight", "TIGHT ≥", "0"))
    body.append(fld("fAtrp", "ATR% ≥", "0"))
    body.append(fld("fRvol", "RVOL ≥", "0"))
    body.append(fld("fD52", "距52高 ≥ %", "-100"))
    body.append(fld("fDvol", "成交額 ≥ $M", "0"))
    body.append('<div class="scr-f"><label for="fTag">訊號</label>'
                '<select id="fTag"><option value="">全部</option>'
                '<option>領導</option><option>突破</option><option>回調</option>'
                '<option>收縮</option><option>新高</option><option>RS新高</option></select></div>')
    body.append('<button class="scr-btn" id="scrReset">重設</button>')
    body.append('<button class="scr-btn" id="scrCsv">下載 CSV</button>')
    body.append('</div>')

    heads = [
        ("代號", "股票代號"), ("行業", "TradingView 行業"),
        ("價", "最後收市價"), ("1D", "一日變動 %"),
        ("1W", "一週 %"), ("1M", "一個月 %"), ("3M", "三個月 %"),
        ("RS", "本池 RS 百分位 0–99（3/6/9/12 個月相對 SPY 加權）"),
        ("ATR%", "ATR14 ÷ 價"), ("ATRX", "（價 − 50MA）÷ ATR14；≤4 可入場"),
        ("TIGHT", "100 ×（1 − 10日箱 ÷ ATR50 ÷ 6）；本池中位約 25、≥45 已算收縮（同 tight_scan 同一條公式）"),
        ("距21EMA", "（價 − EMA21）÷ ATR14；0 = 貼住 21EMA"),
        ("距20日高", "（價 ÷ 20日最高 − 1）× 100；0 = 喺突破位"),
        ("距52高", "（價 ÷ 52週最高 − 1）× 100"),
        ("RVOL", "成交額相對 50 日平均（TradingView）"),
        ("成交額$M", "10 日平均成交額（百萬美元）"),
        ("訊號", "領導 RS≥90 且距52高≥−10｜新高 距52高≥−0.5｜突破 距20日高≥−0.3 且 RVOL≥1.5｜回調 距21EMA ±0.5 且 RS≥75 且喺50MA上｜收縮 TIGHT≥70 且距52高≥−12｜RS新高 RS line 距自己52週高≤0.5%"),
    ]
    th = "".join(f'<th title="{t}">{h}</th>' for h, t in heads)

    body.append('<div class="scr-wrap"><table class="scr-tbl"><thead><tr>' + th + '</tr></thead><tbody>')
    for r in rows:
        perf = r.get("perf") or {}
        tags = r.get("tags") or []
        tg = "".join(f'<span class="scr-tag {TAGCLS.get(x, "")}">{x}</span>' for x in tags)
        ind = r.get("industry") or r.get("sector") or ""
        ind_s = (ind[:30] + "…") if len(ind) > 30 else ind
        rs = r.get("rs")
        d52 = r.get("d52w")
        tags_txt = " ".join(tags)
        _blank = lambda v: "" if v is None else v          # noqa: E731
        body.append(
            f'<tr data-t="{r["t"]}" data-ind="{ind}" data-sector="{r.get("sector") or ""}"'
            f' data-rs="{_blank(rs)}" data-atrx="{_blank(r.get("atrx"))}"'
            f' data-tight="{_blank(r.get("tight"))}" data-atrp="{_blank(r.get("atr_pct"))}"'
            f' data-rvol="{_blank(r.get("rvol"))}" data-d52="{_blank(d52)}"'
            f' data-dvol="{_blank(r.get("dvol_m"))}" data-tags="{tags_txt}">'
            f'<td><a class="scr-tk" href="https://www.tradingview.com/chart/?symbol={r["t"]}"'
            f' target="_blank" rel="noopener" data-sym="{r["t"]}">{r["t"]}</a></td>'
            f'<td class="scr-ind" data-txt="{ind}">{ind_s}</td>'
            f'<td>{_n(r.get("close"), 2)}</td>'
            f'<td class="{_cls(r.get("chg1d"))}">{_n(r.get("chg1d"), 1, True)}</td>'
            f'<td class="{_cls(perf.get("1w"))}">{_n(perf.get("1w"), 1, True)}</td>'
            f'<td class="{_cls(perf.get("1m"))}">{_n(perf.get("1m"), 1, True)}</td>'
            f'<td class="{_cls(perf.get("3m"))}">{_n(perf.get("3m"), 1, True)}</td>'
            f'<td>{_n(rs, 0)}</td>'
            f'<td>{_n(r.get("atr_pct"), 1)}</td>'
            f'<td>{_n(r.get("atrx"), 2)}</td>'
            f'<td>{_tight_cell(r.get("tight"))}</td>'
            f'<td>{_n(r.get("d21"), 2)}</td>'
            f'<td>{_n(r.get("dist_pivot"), 1)}</td>'
            f'<td>{_n(d52, 1)}</td>'
            f'<td>{_n(r.get("rvol"), 1)}×</td>'
            f'<td>{_n(r.get("dvol_m"), 0)}</td>'
            f'<td>{tg}</td></tr>')
    body.append('</tbody></table></div>')

    body.append(
        '<p class="scr-note">'
        '① 全部數字同其他頁共用同一條尺：ATR14 / EMA21 / 50MA 由 rs_scan 定義，TIGHT 由 tight_scan 定義，'
        'RS 百分位用真百分位（唔用飽和公式）。'
        '② 缺失顯示 —（例：上市未夠一年冇 12 個月回報 → 冇 RS），唔會當 0。'
        '③ 預設只係幫你填格，唔會自動交易；呢頁永遠唔會出買入訊號，最多標「訊號」。'
        '④ 744 隻嚟自 TV 掃描（成交額 ≥$30M、ADR ≥4%、無 Biotech），唔係全美股。'
        '</p>')
    body.append('</div>')
    body.append(f"<script>{JS}</script>")
    return ("Stock Screener", "".join(body))


if __name__ == "__main__":
    t, b = build()
    print(t, len(b))
