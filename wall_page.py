# -*- coding: utf-8 -*-
"""wall_page.py — Stock Wall：把 Stock Screener 篩出嚟嘅股票排成圖表牆。

用法：screenwall.html?t=CAKE,CVLT,AMD …（最多 60 隻，由 screener 一撳帶過來）
數據：docs/wall_series.json（screener_extra.py 產生；45 根日線 delta 編碼）
呢頁唔會自己計任何選股條件，只畫圖；數值全部由 screener 帶入。
"""
from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))

CSS = """
.wl-top{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:0 0 10px}
.wl-top h2{margin:0;font-size:19px;font-weight:800}
.wl-meta{font-size:11px;opacity:.6}
.wl-back{font-size:11.5px;text-decoration:none;color:inherit;opacity:.7}
.wl-back:hover{opacity:1;color:#f97316}
.wl-grid{display:grid;gap:10px;grid-template-columns:repeat(4,minmax(0,1fr))}
@media (max-width:1250px){.wl-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:680px){.wl-grid{grid-template-columns:1fr}}
.wl-card{border:1px solid rgba(148,163,184,.24);border-radius:6px;padding:8px 9px 6px;
  background:rgba(148,163,184,.04);min-width:0}
.wl-h{display:flex;align-items:baseline;gap:6px;min-width:0}
.wl-tk{font-size:13.5px;font-weight:800;text-decoration:none;color:inherit;letter-spacing:.02em}
.wl-tk:hover{color:#f97316}
.wl-nm{font-size:11px;opacity:.68;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.wl-sub{font-size:10.5px;opacity:.55;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}
.wl-num{font-size:11px;margin-top:2px;font-variant-numeric:tabular-nums;opacity:.9}
.wl-up{color:#22c55e}.wl-dn{color:#ef4444}
.wl-chart{margin-top:4px}
.wl-f{display:flex;gap:8px;flex-wrap:wrap;font-size:10px;opacity:.62;margin-top:2px;
  font-variant-numeric:tabular-nums}
.wl-empty{font-size:12px;opacity:.7;padding:20px 0}
"""

JS = r"""
(function(){
  var q=new URLSearchParams(location.search);
  var list=(q.get('t')||'').split(',').map(function(s){return s.trim().toUpperCase()}).filter(Boolean);
  var root=document.getElementById('wlRoot');
  var head=document.getElementById('wlMeta');
  var grid=document.getElementById('wlGrid');
  if(!list.length){
    grid.innerHTML='<div class="wl-empty">未收到股票。返去 <a href="screener.html">Stock Screener</a> 揀完再撳「📊 Stock Wall」。</div>';
    return;
  }
  if(list.length>60) list=list.slice(0,60);
  var ver=q.get('v')||'';
  fetch('wall_series.json'+(ver?('?v='+ver):''),{cache:'no-store'})
   .then(function(r){return r.json()})
   .then(function(d){
     var T=d.tickers||{}, bars=d.bars||45, out=[];
     var EMA=[10,21,50];
     list.forEach(function(tk){
       var o=T[tk];
       if(!o){ out.push('<div class="wl-card"><div class="wl-h"><a class="wl-tk" href="https://www.tradingview.com/chart/?symbol='+tk+'" target="_blank" rel="noopener">'+tk+'</a></div><div class="wl-sub">冇圖表數據</div></div>'); return; }
       out.push(card(tk,o,bars,EMA));
     });
     grid.innerHTML=out.join('');
     head.textContent=list.length+' 隻｜圖表截至 '+(d.as_of||'—');
   })
   .catch(function(e){
     grid.innerHTML='<div class="wl-empty">圖表包讀唔到（wall_series.json）：'+e+'</div>';
   });

  function dec(s){
    var arr=[], prev=null;
    s.split(';').forEach(function(b){
      var p=b.split(',').map(Number);
      if(p.length<4||p.some(isNaN)) return;
      var base = prev===null ? 0 : prev;
      var o=p[0]+base,h=p[1]+base,l=p[2]+base,c=p[3]+base;
      arr.push([o/100,h/100,l/100,c/100]); prev=c;
    });
    return arr;
  }
  function ema(vals,span){
    if(!vals.length) return [];
    var k=2/(span+1), out=[], seed=0, n=Math.min(span,vals.length);
    for(var i=0;i<n;i++) seed+=vals[i];
    seed/=n; out[n-1]=seed;
    for(var i=n;i<vals.length;i++) out[i]=vals[i]*k+out[i-1]*(1-k);
    for(var i=0;i<n-1;i++) out[i]=null;
    return out;
  }
  function card(tk,o,bars,spans){
    var B=dec(o.k||'');
    if(B.length<5){return '<div class="wl-card"><div class="wl-h"><a class="wl-tk" href="https://www.tradingview.com/chart/?symbol='+tk+'" target="_blank" rel="noopener">'+tk+'</a></div><div class="wl-sub">K 線唔夠</div></div>';}
    var W=340,H=118,PL=3,PR=30,PT=4,PB=4;
    var lo=Infinity,hi=-Infinity;
    B.forEach(function(b){lo=Math.min(lo,b[2]);hi=Math.max(hi,b[1]);});
    var closes=B.map(function(b){return b[3];});
    var es=spans.map(function(n){return ema(closes,n)});
    es.forEach(function(e){e.forEach(function(v){if(v!==null){lo=Math.min(lo,v);hi=Math.max(hi,v);}})});
    var pad=(hi-lo)*0.06; lo-=pad; hi+=pad;
    var pw=W-PL-PR, ph=H-PT-PB;
    function X(i){return PL+(i+0.5)*pw/B.length;}
    function Y(v){return PT+(hi-v)/(hi-lo)*ph;}
    var bw=Math.max(1.6,pw/B.length*0.62);
    var svg=['<svg class="wl-chart" viewBox="0 0 '+W+' '+H+'" width="100%" height="'+H+'" preserveAspectRatio="none">'];
    for(var i=0;i<B.length;i++){
      var b=B[i], up=b[3]>=b[0], col=up?'#16a34a':'#dc2626';
      var x=X(i);
      svg.push('<line x1="'+x.toFixed(1)+'" y1="'+Y(b[1]).toFixed(1)+'" x2="'+x.toFixed(1)+'" y2="'+Y(b[2]).toFixed(1)+'" stroke="'+col+'" stroke-width="0.8" opacity="0.75"/>');
      var y1=Y(Math.max(b[0],b[3])), y2=Y(Math.min(b[0],b[3]));
      svg.push('<rect x="'+(x-bw/2).toFixed(1)+'" y="'+y1.toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+Math.max(0.8,(y2-y1)).toFixed(1)+'" fill="'+col+'" opacity="0.85"/>');
    }
    var COLS=['#94a3b8','#f97316','#3b82f6'];
    es.forEach(function(e,k){
      var d='', started=false;
      e.forEach(function(v,i){
        if(v===null) return;
        d+=(started?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)+' ';
        started=true;
      });
      if(d) svg.push('<path d="'+d+'" fill="none" stroke="'+COLS[k]+'" stroke-width="1.05" opacity="'+(k===1?0.95:0.75)+'"/>');
    });
    // 右邊價位（高／中／低）
    [[hi,''], [ (hi+lo)/2,''], [lo,'']].forEach(function(p){
      svg.push('<text x="'+(W-PR+3)+'" y="'+(Y(p[0])+3).toFixed(1)+'" font-size="8" fill="currentColor" opacity="0.45">'+(p[0]<10?p[0].toFixed(2):p[0].toFixed(1))+'</text>');
    });
    svg.push('</svg>');
    var chg=o.chg===null||o.chg===undefined?'—':((o.chg>0?'+':'')+o.chg.toFixed(1)+'%');
    var cls=(o.chg>0)?'wl-up':(o.chg<0?'wl-dn':'');
    var n=function(v,d){return (v===null||v===undefined)?'—':Number(v).toFixed(d)};
    return '<div class="wl-card">'
      +'<div class="wl-h"><a class="wl-tk" href="https://www.tradingview.com/chart/?symbol='+tk+'" target="_blank" rel="noopener">'+tk+'</a>'
      +'<span class="wl-nm">'+(o.n||'')+'</span></div>'
      +'<div class="wl-sub">'+(o.s||'')+(o.i?(' · '+o.i):'')+'</div>'
      +'<div class="wl-num">收 '+n(o.c,2)+' <span class="'+cls+'">('+chg+')</span> · ATR% '+n(o.atr,1)+' · ADR '+n(o.adr,1)+'</div>'
      +svg.join('')
      +'<div class="wl-f"><span>RS '+n(o.rs,0)+'</span><span>ATRX '+n(o.ax,2)+'</span>'
      +'<span>TIGHT '+n(o.tg,0)+'</span><span>距52高 '+n(o.d52,1)+'%</span></div>'
      +'</div>';
  }
})();
"""


def build():
    body = [
        f"<style>{CSS}</style>",
        '<div class="card" id="wlRoot">',
        '<div class="wl-top"><h2>STOCK WALL</h2>'
        '<span class="wl-meta" id="wlMeta">載入中…</span>'
        '<a class="wl-back" href="screener.html">← 返 Stock Screener</a></div>',
        '<div class="wl-grid" id="wlGrid"></div>',
        '</div>',
        f"<script>{JS}</script>",
    ]
    return ("Stock Wall", "".join(body))
