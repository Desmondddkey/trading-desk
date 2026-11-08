# -*- coding: utf-8 -*-
"""room_page.py — 系統房間（一張圖睇晒成個系統；深／淺兩版）

圖片：docs/room_dark.png / room_light.png（room_render.py 出 SVG，瀏覽器截 PNG）
"""
from __future__ import annotations

CSS = """
.rm-fig{margin:0;width:100%;max-width:100%;height:auto}
.rm-legend{display:grid;grid-template-columns:repeat(2,1fr);gap:10px 22px;font-size:12.5px}
@media(max-width:760px){.rm-legend{grid-template-columns:1fr}}
.rm-item{border-left:2px solid rgba(148,163,184,.35);padding:2px 0 2px 10px}
.rm-k{font-weight:800}
.rm-a{opacity:.75}
.rm-note{font-size:10.5px;opacity:.6;margin-top:10px;line-height:1.6}
"""

ROWS = [
    ("左牆 · 帳單", "1,279 單、−19,317、1.68:1", "review2.html", "覆盤（R／期望值）"),
    ("右牆 · 四把聲", "Jeff Sun／Martin Luk／J Law／Minervini", "lukplaybook.html", "Luk 手冊"),
    ("後牆 · 三塊屏", "QQQ 雙結構｜MM Model｜行業輪動", "qqqstruct.html", "QQQ 雙結構"),
    ("地板 · 出場階梯", "2R 減 33% → ATRX 8 → 拖 10EMA", "process.html", "每日流程"),
    ("書桌 · 今日 3 條", "1 Watchlist／2 MM 校準／3 一頁睇晒", "finish.html", "收工標準"),
    ("垃圾桶 · 紀律", "追高／報復交易／加單救返", "calculator.html", "倉位計算機"),
]


def build():
    L = [f"<style>{CSS}</style>"]
    L.append('<div class="card"><h2>系統房間 <small>一張圖睇晒：錢、人、屏幕、規矩</small></h2>'
             '<div class="body">')
    L.append('<img class="fig-light rm-fig" src="room_light.png" alt="系統房間（淺色）" '
             'style="width:100%;height:auto;border-radius:10px">')
    L.append('<img class="fig-dark rm-fig" src="room_dark.png" alt="系統房間（深色）" '
             'style="width:100%;height:auto;border-radius:10px">')
    L.append('<div class="rm-note">深／淺兩版同一構圖；跟隨你嘅主題自動切換。</div>')
    L.append('</div></div>')

    L.append('<div class="card"><h2>每件物件去邊</h2><div class="body"><div class="rm-legend">')
    for k, a, href, name in ROWS:
        L.append(f'<div class="rm-item"><div class="rm-k">{k}</div>'
                 f'<div class="rm-a">{a}</div>'
                 f'<div><a href="{href}">{name} →</a></div></div>')
    L.append('</div></div></div>')
    return ("系統房間", "".join(L))


if __name__ == "__main__":
    print(build()[0])
