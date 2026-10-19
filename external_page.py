# -*- coding: utf-8 -*-
"""external_page.py — 外部數據源頁（Desmond 2026-10-19）

★ 需求：Desmond 提供 3 個外部站，想「係我既網頁到讀取接入佢既信息」。

★ 實測結果（curl X-Frame-Options + Location）：
    i-manage-risk.github.io/NEL   → HTTP 200、純靜態 SPA  ✓ 可 iframe
    app.lonestocktrader.com/...   → HTTP 307 → /login      ✗ 要登入
    www.traderslab.io/...         → HTTP 307 → /sign-in    ✗ 要登入

★ 第一性原理：
    可以嵌嘅就嵌（NEL）；要登入嘅嵌入只會見到登入頁，
    強行嵌 = 扮有數據 = 比冇更差。所以誠實列為「外部連結」。

★ 頁面結構：
    ① 可嵌入區（NEL）
    ② 需登入區（2 個卡片，明寫原因）
    ③ 資料來源說明
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _esc(v):
    import html as _h
    return _h.escape(str(v)) if v is not None else ""


CSS = """
.ext-card{border:1px solid rgba(128,128,128,.28);border-radius:13px;
  overflow:hidden;margin:0 0 14px;background:rgba(128,128,128,.035)}
.ext-hd{display:flex;align-items:center;gap:10px;padding:12px 15px;
  background:rgba(128,128,128,.08);flex-wrap:wrap}
.ext-hd .t{font-weight:700;font-size:14px}
.ext-hd .u{font-size:11px;opacity:.6;font-family:ui-monospace,monospace}
.ext-badge{font-size:10.5px;padding:2px 8px;border-radius:999px;
  border:1px solid rgba(128,128,128,.4)}
.b-ok{background:rgba(47,191,113,.15);border-color:rgba(47,191,113,.5);
  color:#1a7f4b}
.b-lock{background:rgba(224,168,0,.14);border-color:rgba(224,168,0,.55);
  color:#8a6100}
[data-theme="dark"] .b-ok{color:#7ce0a8}
[data-theme="dark"] .b-lock{color:#fbc06a}
.ext-body{padding:0}
.ext-frame{width:100%;height:80vh;min-height:560px;border:0;display:block;
  background:#fff}
.ext-note{padding:14px 16px;font-size:13px;line-height:1.8}
.ext-btn{display:inline-flex;align-items:center;gap:6px;margin-top:10px;
  padding:9px 15px;border-radius:9px;border:1px solid rgba(128,128,128,.4);
  background:rgba(128,128,128,.1);color:inherit;text-decoration:none;
  font-size:13px;font-weight:600}
.ext-btn:hover{background:rgba(128,128,128,.2)}
.ext-why{font-size:12px;opacity:.72;line-height:1.75;margin-top:8px}
@media(max-width:900px){.ext-frame{height:68vh;min-height:420px}}
"""


def build():
    parts = [f'<style>{CSS}</style>']
    parts.append('<h2>🌐 外部數據源 <small>第三方站接入</small></h2>')
    parts.append('<p class="crumb">唯讀研究用途｜'
                 '<b>非買入指令</b>｜嵌入與否按對方伺服器實際回應決定</p>')

    # ── ① 可嵌入 ──
    parts.append('<div class="ext-card">'
                 '<div class="ext-hd">'
                 '<span class="t">🖥 NEL · Market Console</span>'
                 '<span class="ext-badge b-ok">✓ 可嵌入</span>'
                 '<span class="u">i-manage-risk.github.io/NEL</span>'
                 '</div><div class="ext-body">'
                 '<iframe class="ext-frame" loading="lazy" '
                 'src="https://i-manage-risk.github.io/NEL/index.html" '
                 'title="NEL Market Console"></iframe>'
                 '<div class="ext-note">'
                 '★ 純靜態 SPA（GitHub Pages），冇 login 牆 → 可以原樣嵌入。<br>'
                 '★ 內容：Now / Pulse / Flow / Crowding / <b>Stocks（screener）</b> / Replay。<br>'
                 '★ 呢個站嘅方法論係我哋 desk.html 嘅來源之一。'
                 '<div class="ext-why">⚠️ 佢嘅資料由自己嘅 workspace.js 載入，'
                 '同我哋嘅 breadth / layer2 唔一定同步 —— <b>兩套數字唔可以互相引用</b>。</div>'
                 '<a class="ext-btn" href="https://i-manage-risk.github.io/NEL/index.html#screener" '
                 'target="_blank" rel="noopener">↗ 開 screener（新視窗）</a>'
                 '</div></div></div>')

    # ── ② 需登入 ──
    for icon, name, url, why in [
        ("📊", "LoneStockTrader · Basket Charts",
         "https://app.lonestocktrader.com/dashboard/basket-charts",
         "伺服器回 HTTP 307 → <code>/login</code>。"
         "iframe 只會顯示登入頁；亦唔可以代你登入（憑證唔准經我）。"),
        ("📈", "TradersLab · Market Overview",
         "https://www.traderslab.io/market-overview",
         "伺服器回 HTTP 307 → <code>/sign-in?redirect_url=…</code>。"
         "同樣需要登入 session。"),
    ]:
        parts.append(
            f'<div class="ext-card"><div class="ext-hd">'
            f'<span class="t">{icon} {_esc(name)}</span>'
            f'<span class="ext-badge b-lock">🔒 需登入</span>'
            f'</div><div class="ext-note">'
            f'<div class="ext-why">{why}</div>'
            f'<div class="ext-why">★ 想我讀到佢嘅數據，唯一合法做法係你喺自己瀏覽器'
            f'登入後<b>截圖</b>或<b>匯出 CSV</b> 俾我 —— 我唔會、亦唔應該代你登入。</div>'
            f'<a class="ext-btn" href="{_esc(url)}" target="_blank" rel="noopener">'
            f'↗ 開 {_esc(name.split(" · ")[0])}（新視窗）</a>'
            f'</div></div>')

    # ── ③ 說明 ──
    parts.append('<div class="card"><h2>★ 接入原則</h2><div class="body">'
                 '<div style="font-size:13px;line-height:1.9">'
                 '① <b>冇 login 牆</b> → 直接 iframe（NEL）<br>'
                 '② <b>有 login 牆</b> → 只提供連結，唔扮嵌入（呢個頁嘅兩個站）<br>'
                 '③ <b>有公開 API / CSV</b> → 我自己 parse（例如 Stockbee MM、Nasdaq 財報）<br><br>'
                 '★ 為什麼唔強行嵌 login 站：iframe 會顯示登入頁，'
                 '你會以為「冇數據」—— <b>比明寫「需登入」更差</b>。'
                 '</div></div></div>')
    return ("外部數據源", "".join(parts))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    t, b = build()
    out = os.path.join(HERE, "external_body.html")
    io.open(out, "w", encoding="utf-8").write(b)
    print(f"✓ external body {len(b):,} 字 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
