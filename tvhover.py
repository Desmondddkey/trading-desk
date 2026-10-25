#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tvhover.py — Item 8：hover 代號彈 TradingView 圖（網絡版 widget）

Desmond 2026-10-11 Item 8：「hover 彈 TradingView 圖（網絡版 widget，file:// 唔得）」

★ 之前嘅顧慮同答案：
  當時寫「file:// 唔得」—— 呢個顧慮係**啱一半**：
  TradingView 嘅 `tv.js` widget 需要 (a) 網絡、(b) 一個真正嘅 origin。
  網站係 GitHub Pages（https://desmondddkey.github.io/trading-desk/），
  兩樣都有 → **widget 喺 live 一定得**；只有本地 `file://` 開 docs/*.html 唔得。
  所以呢個功能**唔可以本地驗證**，只可以驗證「JS 有冇正確注入 + 邏輯冇語法錯」。

★ 設計（三個約束）：
  ① 唔拖慢首次載入：`tv.js` **lazy load**，第一次 hover 才下載。
  ② 唔開 100 個 iframe：全頁**共用一個 popup**，換股就清空重建。
  ③ 手機冇 hover：mobile 照舊 tap 就開 TV 新分頁（唔彈窗），唔會爛。

★ 觸發：hover 400ms 後才彈（避免掃過成個表就彈幾十次）。
  移去 popup 唔會即刻收（要俾你睇圖）；scroll 就收。
"""

# ── CSS（注入 <style>）──
TVHOVER_CSS = """
#tvpop{display:none;position:fixed;z-index:9999;width:440px;
  background:#0b1120;border:1px solid #2a3a5c;border-radius:10px;
  overflow:hidden}
#tvpopbar{display:flex;align-items:center;gap:8px;padding:6px 9px;
  background:#111a2e;border-bottom:1px solid #1e2a44;font-size:11.5px}
#tvpopsym{font-weight:700;color:#9fd4ff;flex:1 1 auto}
#tvpopbar a{color:#7fd4a8;text-decoration:none;font-size:11.5px}
#tvpopbar a:hover{text-decoration:underline}
#tvpopclose{background:none;border:none;color:#7f90ad;cursor:pointer;
  font-size:14px;padding:0 3px;font-family:inherit}
#tvpopclose:hover{color:#fff}
#tvpopchart{height:340px;background:#0b1120}
#tvpopnote{font-size:10.5px;color:#8fa3c8;padding:0 9px 6px;min-height:0}
@media(max-width:700px){#tvpop{display:none!important}}
"""

# ── JS（注入 <script>，喺 PAGE 之後）──
TVHOVER_JS = r"""
(function(){
  var box=null, timer=null, cur=null, tvLoaded=false, tvFailed=false, syncing=false;

  function ensureBox(){
    if(box) return box;
    box=document.createElement('div');
    box.id='tvpop';
    box.innerHTML='<div id="tvpopbar"><span id="tvpopsym"></span>'
      +'<a id="tvpopopen" target="_blank" rel="noopener">開 TV ↗</a>'
      +'<button id="tvpopclose" type="button" title="關閉">&#10005;</button></div>'
      +'<div id="tvpopchart"></div><div id="tvpopnote"></div>';
    document.body.appendChild(box);
    box.querySelector('#tvpopclose').addEventListener('click',hide);
    return box;
  }
  function hide(){ clearTimeout(timer); if(box) box.style.display='none'; }

  function loadTV(cb){
    if(tvLoaded) return cb();
    if(tvFailed){
      say('\u26a0 TradingView widget \u8f09\u5514\u5230\uff08\u7db2\u7d61\uff0f\u88ab\u906e\uff09\u2014\u2014 \u9ede\u300c\u958b TV \u2197\u300d\u76f4\u63a5\u53bb\u7db2\u7ad9');
      return;
    }
    var s=document.createElement('script');
    s.src='https://s3.tradingview.com/tv.js';
    s.async=true;
    s.onload=function(){ tvLoaded=true; cb(); };
    s.onerror=function(){ tvFailed=true;
      say('\u26a0 TradingView widget \u8f09\u5514\u5230\uff08\u7db2\u7d61\uff0f\u88ab\u906e\uff09\u2014\u2014 \u9ede\u300c\u958b TV \u2197\u300d\u76f4\u63a5\u53bb\u7db2\u7ad9'); };
    document.head.appendChild(s);
  }
  function say(t){ var n=document.getElementById('tvpopnote'); if(n) n.textContent=t||''; }

  function show(el){
    var sym=el.getAttribute('data-sym');
    if(!sym) return;
    var b=ensureBox();
    b.querySelector('#tvpopsym').textContent=sym;
    b.querySelector('#tvpopopen').href=el.href||('#');
    if(cur!==sym){
      cur=sym;
      b.querySelector('#tvpopchart').innerHTML='';
      say('\u8f09\u5165\u4e2d\u2026');
      loadTV(function(){
        var host=b.querySelector('#tvpopchart');
        host.innerHTML='<div id="tvwbox" style="height:340px"></div>';
        try{
          /* global TradingView */
          new TradingView.widget({
            container_id:'tvwbox', symbol:sym, interval:'D',
            theme:'dark', style:'1', locale:'zh_TW',
            hide_side_toolbar:true, hide_top_toolbar:false,
            allow_symbol_change:false, save_image:false,
            withdateranges:false, details:false,
            studies:['Volume@tv-basicstudies'],
            width:'100%', height:340, autosize:false
          });
          setTimeout(function(){ say(''); }, 1100);
        }catch(e){ say('\u26a0 widget \u8d77\u5514\u5230\uff1a'+e.message); }
      });
    }
    b.style.display='block';
    place(el);
  }

  function place(el){
    if(!box) return;
    var r=el.getBoundingClientRect(), w=box.offsetWidth||440, h=box.offsetHeight||400;
    var left=r.right+14, top=r.top-6;
    if(left+w>window.innerWidth-10) left=Math.max(8, r.left-w-14);
    if(top+h>window.innerHeight-10) top=Math.max(8, window.innerHeight-h-10);
    if(top<8) top=8;
    box.style.left=left+'px'; box.style.top=top+'px';
  }
  function near(el){
    return el.closest && el.closest('a.tv');
  }

  document.addEventListener('mouseover',function(e){
    var a=near(e.target);
    if(!a) return;
    var sym=a.getAttribute('data-sym');
    if(sym && sym===cur && box && box.style.display==='block'){ clearTimeout(timer); return; }
    clearTimeout(timer);
    timer=setTimeout(function(){ show(a); }, 400);      /* 400ms：掃過唔會連彈 */
  }, true);

  document.addEventListener('mouseout',function(e){
    var a=near(e.target);
    if(!a) return;
    clearTimeout(timer);
    setTimeout(function(){
      if(syncing) return;
      if(box && box.style.display==='block' && box.matches(':hover')) return;
      hide();
    }, 260);
  }, true);

  document.addEventListener('mouseenter',function(){ syncing=true; }, true);
  document.addEventListener('mouseleave',function(){ syncing=false; }, true);
  window.addEventListener('scroll',function(){
    if(box && box.style.display==='block') hide();
  }, {passive:true});
  window.addEventListener('keydown',function(e){ if(e.key==='Escape') hide(); });
})();
"""
