# -*- coding: utf-8 -*-
"""livefeeds.py — 外部即時數據源（iframe 原貌）Desmond 2026-10-19

★ 需求：「LoneStockTrader / TradersLab · Market Overview
        開一個新頁面 用返 直接 iframe（NEL）」

★ 實測（curl，2026-10-19）：
   app.lonestocktrader.com/dashboard/basket-charts
     → 307 → /login（登入頁 200，**冇 X-Frame-Options**）
   www.traderslab.io/market-overview
     → 307 → /sign-in?redirect_url=…（登入頁 200，**冇 X-Frame-Options**）

★★ 所以：iframe 載得入，但會顯示【登入頁】，唔會直接顯示圖表。
   原因唔係 X-Frame-Options，而係第三方 Cookie 被瀏覽器封鎖 →
   iframe 內登入通常唔會成功（OAuth redirect 亦會斷）。

★ 因此本頁設計（誠實原則，唔扮成功）：
   ① 每個源一張卡，卡頂有【↗ 開原站】按鈕（喺原站登入一次，之後瀏覽器有 cookie）
   ② iframe 用 lazy load（唔會一次過拉兩個重頁）
   ③ 每張卡有「載入中」提示 + 「載入失敗？」說明
   ④ 頂部有整體警告：呢兩個源需要登入，iframe 未必顯示到內容
"""
import html as _h
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

FEEDS = [
    dict(
        key="lst",
        name="LoneStockTrader",
        sub="Basket Charts · 籃子圖表",
        url="https://app.lonestocktrader.com/dashboard/basket-charts",
        home="https://app.lonestocktrader.com/",
        note="籃子圖表：主題／行業籃子相對強弱。需要登入帳戶。",
        login=True,
    ),
    dict(
        key="rstock",
        name="RocketStock",
        sub="RS Ranking · SEPA 排名",
        url="https://rocketstock.app/rs-ranking?tab=sepa",
        home="https://rocketstock.app/",
        note="SEPA（Mark Minervini 方法）相對強弱排名。"
             "★ 實測（2026-10-19）原站回 X-Frame-Options: SAMEORIGIN "
             "＋ CSP frame-ancestors 'self'，明確禁止嵌入 → 只能開原站。",
        login=True,
        embed=False,
    ),
    dict(
        key="tlab",
        name="TradersLab",
        sub="Market Overview · 市場總覽",
        url="https://www.traderslab.io/market-overview",
        home="https://www.traderslab.io/",
        note="Market Overview：PrimeTrading 嘅成長週期 → 領先者 → 設置流程。需要登入帳戶。",
        login=True,
    ),
]

CSS = """
.lf-warn{border:1px solid rgba(245,158,11,.5);background:rgba(245,158,11,.08);
  border-radius:12px;padding:12px 15px;margin:0 0 16px;font-size:13px;
  line-height:1.75}
.lf-warn b{color:#b45309}
[data-theme="dark"] .lf-warn b{color:#fbc06a}
.lf-card{border:1px solid rgba(128,128,128,.28);border-radius:14px;
  overflow:hidden;margin:0 0 16px;background:rgba(128,128,128,.03)}
.lf-hd{display:flex;align-items:center;gap:10px;padding:11px 15px;
  background:rgba(128,128,128,.08);flex-wrap:wrap}
.lf-hd .nm{font-weight:800;font-size:14px}
.lf-hd .sb{font-size:11.5px;opacity:.62}
.lf-btns{margin-left:auto;display:flex;gap:7px}
.lf-btns a{font-size:11.5px;padding:5px 11px;border-radius:8px;
  border:1px solid rgba(128,128,128,.4);text-decoration:none;color:inherit;
  font-weight:700;white-space:nowrap}
.lf-btns a:hover{background:rgba(128,128,128,.18)}
.lf-btns a.pri{background:#2563eb;border-color:#2563eb;color:#fff}
.lf-btns a.pri:hover{background:#1d4ed8}
.lf-body{position:relative;background:rgba(128,128,128,.05)}
.lf-frame{width:100%;height:78vh;min-height:520px;border:0;display:block;
  background:#fff}
[data-theme="dark"] .lf-frame{background:#0f1420}
.lf-nobody{padding:18px 16px;background:rgba(128,128,128,.05)}
.lf-load{position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:12px;
  font-size:13px;opacity:.75;pointer-events:none;text-align:center;padding:20px}
.lf-spin{width:26px;height:26px;border:3px solid rgba(128,128,128,.3);
  border-top-color:#2563eb;border-radius:50%;animation:lfsp .9s linear infinite}
@keyframes lfsp{to{transform:rotate(360deg)}}
.lf-note{font-size:12px;line-height:1.8;opacity:.75;padding:10px 15px;
  border-top:1px solid rgba(128,128,128,.16)}
"""

JS = """
function lfLoad(id){
  var f=document.getElementById('fr-'+id), l=document.getElementById('ld-'+id);
  if(!f) return;
  f.src = f.dataset.src;
  f.onload = function(){ if(l) l.style.display='none'; };
  setTimeout(function(){ if(l) l.style.display='none'; }, 20000);
}
"""


def _esc(v):
    return _h.escape(str(v)) if v is not None else ""


def build():
    parts = [f"<style>{CSS}</style><script>{JS}</script>"]
    parts.append('<h2>外部即時數據 <small>iframe 原貌</small></h2>')
    parts.append(
        '<p class="crumb">直接嵌入原站畫面（同 NEL 一樣做法）｜'
        '資料由對方網站即時提供，唔經我哋轉存</p>')

    parts.append(
        '<div class="lf-warn">'
        '<b>⚠ 呢兩個源需要登入帳戶</b><br>'
        '實測（2026-10-19）：兩個網址都會 307 轉去登入頁，'
        '而登入頁本身冇設 <code>X-Frame-Options</code>，所以 iframe <b>載得入</b>。'
        '但瀏覽器會封鎖 iframe 內嘅第三方 Cookie → '
        '<b>喺呢個框入面登入通常唔會成功</b>，你會見到登入畫面或者空白。<br>'
        '★ 正確用法：① 先按右上「↗ 開原站」喺真瀏覽器登入一次 '
        '② 返嚟呢頁再按「載入」—— 部分瀏覽器仍然會擋，'
        '所以最穩陣係直接喺原站睇。'
        '</div>')

    for f in FEEDS:
        parts.append('<div class="lf-card">')
        parts.append(
            f'<div class="lf-hd">'
            f'<span class="nm">{_esc(f["name"])}</span>'
            f'<span class="sb">{_esc(f["sub"])}</span>'
            '<span class="lf-btns">'
            + ("" if f.get("embed") is False else
               f'<a href="#" onclick="lfLoad(\'{f["key"]}\');'
               'return false;">載入</a>')
            + f'<a class="pri" href="{_esc(f["url"])}" target="_blank" '
            'rel="noopener noreferrer">↗ 開原站</a>'
            '</span></div>')
        if f.get("embed") is False:
            parts.append(
                '<div class="lf-nobody">'
                '<div style="font-size:13px;line-height:1.8;opacity:.8">'
                '原站禁止 iframe 嵌入（<code>X-Frame-Options: SAMEORIGIN</code>'
                ' ＋ <code>CSP frame-ancestors &quot;self&quot;</code>），'
                '所以只能用上方「↗ 開原站」喺新視窗睇。</div></div>')
            parts.append(f'<div class="lf-note">{_esc(f["note"])}'
                         f'<br>網址：<code>{_esc(f["url"])}</code></div>')
            parts.append('</div>')
            continue
        parts.append('<div class="lf-body">')
        parts.append(
            f'<div class="lf-load" id="ld-{f["key"]}">'
            '<div class="lf-spin"></div>'
            '<div><b>未載入</b><br>按右上「載入」開始'
            '（iframe 首次載入可能要 10–20 秒）</div></div>')
        parts.append(
            f'<iframe class="lf-frame" id="fr-{f["key"]}" '
            f'data-src="{_esc(f["url"])}" '
            'loading="lazy" referrerpolicy="no-referrer-when-downgrade" '
            'sandbox="allow-same-origin allow-scripts allow-forms '
            'allow-popups allow-popups-to-escape-sandbox"></iframe>')
        parts.append('</div>')
        parts.append(f'<div class="lf-note">{_esc(f["note"])}'
                     f'<br>網址：<code>{_esc(f["url"])}</code></div>')
        parts.append('</div>')

    parts.append(
        '<div class="note" style="font-size:12px;line-height:1.8">'
        '<b>為什麼唔自己 render？</b> 因為呢兩個源嘅內容係登入後動態產生，'
        '我哋冇帳戶亦冇 API，抄出嚟只會係猜測。'
        'iframe 至少保證你睇到嘅係真嘅原站畫面（或者真嘅登入頁），'
        '唔會出現我哋自己編嘅數字。</div>')
    return ("外部即時數據", "".join(parts))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    _t, b = build()
    out = os.path.join(HERE, "livefeeds_body.html")
    io.open(out, "w", encoding="utf-8").write(b)
    print(f"✓ livefeeds body {len(b):,} 字 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
