# -*- coding: utf-8 -*-
"""martinluk_page.py — 外部數據 → Martin Luk 分頁

Desmond 2026-10-29：要求喺「外部數據」之下加一個新分頁（唔係塞入 external.html）。
內容：FAQ／Q&A／screeners 嵌入 + 官方連結 + 我哋自己嘅使用限制。
"""
from __future__ import annotations

CSS = """
.ml-wrap{max-width:1100px}
.ml-hd{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:2px 0 8px}
.ml-hd .t{font-size:15px;font-weight:800}
.ml-hd .u{font-size:11px;opacity:.55}
.ml-badge{font-size:10.5px;padding:1px 7px;border-radius:5px;font-weight:700;
  background:rgba(34,197,94,.14);color:#22c55e;border:1px solid rgba(34,197,94,.3)}
.ml-frame{width:100%;height:70vh;min-height:520px;border:1px solid rgba(128,128,128,.25);
  border-radius:6px;background:#fff}
.ml-links{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
.ml-btn{font-size:11.5px;padding:5px 10px;border:1px solid rgba(249,115,22,.45);
  border-radius:5px;color:#f97316;text-decoration:none;font-weight:700}
.ml-note{font-size:11.5px;line-height:1.85;opacity:.82;margin-top:8px}
.ml-kpi{display:flex;gap:14px;flex-wrap:wrap;margin:8px 0 12px}
.ml-kpi div{font-size:11.5px;opacity:.8}
.ml-kpi b{font-size:14px;display:block;margin-top:1px}
"""


def build():
    P = [f"<style>{CSS}</style>"]
    P.append('<h2>🏆 Martin Luk <small>FAQ / Q&amp;A / Screeners</small></h2>')
    P.append('<div class="ml-wrap">')
    P.append('<div class="ml-kpi">'
             '<div>2025 USIC 股票組（$20,000+）<b style="color:#22c55e">冠軍 +969.8%</b></div>'
             '<div>2024 同組<b>第 6 名 +283.1%</b></div>'
             '<div>2026 至 9 月底<b>+785.8%</b></div>'
             '</div>')
    P.append('<div class="ml-hd"><span class="t">martinluk.com</span>'
             '<span class="u">fan page（非官方）</span>'
             '<span class="ml-badge">✓ 可嵌入</span></div>')
    P.append('<div class="ml-links">'
             '<a class="ml-btn" href="https://martinluk.com/faq/index.html" '
             'target="_blank" rel="noopener">↗ FAQ</a>'
             '<a class="ml-btn" href="https://martinluk.com/qa/index.html" '
             'target="_blank" rel="noopener">↗ Q&amp;A 搜尋</a>'
             '<a class="ml-btn" href="https://www.youtube.com/@martinlukkt" '
             'target="_blank" rel="noopener">↗ YouTube</a>'
             '<a class="ml-btn" href="https://x.com/martinlukkt" '
             'target="_blank" rel="noopener">↗ X</a>'
             '<a class="ml-btn" href="https://www.twitch.tv/martinlukkt" '
             'target="_blank" rel="noopener">↗ Twitch</a>'
             '</div>')
    P.append('<iframe class="ml-frame" loading="lazy" src="https://martinluk.com/" '
             'title="Martin Luk FAQ" referrerpolicy="no-referrer-when-downgrade"></iframe>')
    P.append('<div class="ml-note">'
             '★ 內容：FAQ（螢幕／TradingView 設定、screener 用途、學習期用幾多風險）、'
             'Q&amp;A 搜尋、screeners。<br>'
             '★ 佢嘅 risk-per-trade 係「每單固定風險」框架；我哋係「油門 0.2% 探路 → '
             '0.5% 確認 → 33% 倉上限」——<b>兩套唔可以互相換算</b>，只可以當參考。<br>'
             '★ 如果 iframe 空白，係對方臨時改 header；按上面 ↗ 開新視窗。'
             '</div>')
    P.append('</div>')
    return ("Martin Luk", "".join(P))


def main():
    t, b = build()
    print(f"{t} — {len(b):,} chars")


if __name__ == "__main__":
    main()
