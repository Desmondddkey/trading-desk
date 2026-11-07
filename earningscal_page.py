# -*- coding: utf-8 -*-
"""earningscal_page.py — 財報日曆（直接喺頁面顯示 Finviz，唔跳轉）

Desmond 2026-11-07：「改成打開頁面可以直接顯示 finviz 呢個網站 唔洗轉跳」

做法：<iframe> 嵌 Finviz earnings calendar；上面一條日期 bar（-1 / 今日 / +1…+3），
按一下只換 iframe src，唔會離開本站。如果 Finviz 擋 iframe，下面有原站連結。
"""
from __future__ import annotations

import datetime as _dt
import html as _h

BASE = "https://finviz.com/calendar/earnings"


def _et_today():
    """用 HKT 日期近似 ET（美股收市後用同一日）。"""
    return _dt.date.today()


def build():
    d0 = _et_today()
    days = []
    for off in (-1, 0, 1, 2, 3):
        d = d0 + _dt.timedelta(days=off)
        label = "今日" if off == 0 else f"{off:+d} 日"
        days.append((d.isoformat(), label, d.strftime("%m-%d %a")))

    src = f"{BASE}?day={days[1][0]}"
    uniq = days[1][0]

    P = ["""<style>
.ec-bar{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:0 0 8px}
.ec-bar button{font-size:12px;padding:4px 10px;border-radius:6px;cursor:pointer;
  border:1px solid rgba(148,163,184,.35);background:transparent;color:inherit}
.ec-bar button.on{background:#c2410c;border-color:#c2410c;color:#fff}
.ec-nav{margin-left:auto;font-size:11px;opacity:.6}
.ec-wrap{border:1px solid rgba(148,163,184,.25);border-radius:8px;overflow:hidden;
  background:#fff}
.ec-wrap iframe{width:100%;height:calc(100vh - 190px);min-height:680px;border:0;display:block}
.ec-note{font-size:10.5px;opacity:.55;margin-top:8px;line-height:1.6}
</style>"""]

    P.append('<div class="card"><h2>財報日曆 <small>Finviz · 直接喺頁面顯示</small></h2>'
             '<div class="body">')
    P.append('<div class="ec-bar">')
    for iso, label, sub in days:
        cls = ' class="on"' if iso == uniq else ""
        P.append(f'<button{cls} data-src="{BASE}?day={iso}" '
                 f'onclick="ecGo(this)">{_h.escape(label)}'
                 f'<span style="opacity:.6;font-size:10px"> { _h.escape(sub)}</span></button>')
    P.append(f'<span class="ec-nav">資料日 {uniq}（HKT）</span>')
    P.append('</div>')
    P.append(f'<div class="ec-wrap"><iframe id="ecframe" src="{src}" '
             'loading="lazy" referrerpolicy="no-referrer"></iframe></div>')
    P.append('<div class="ec-note">如果空白 = Finviz 擋咗嵌入，按下面原站連結。'
             f'<br><a href="{src}" target="_blank" rel="noopener">在 finviz.com 開啟</a></div>')
    P.append('</div></div>')
    P.append("""<script>
function ecGo(btn){
  var f=document.getElementById('ecframe');
  f.src=btn.dataset.src;
  document.querySelectorAll('.ec-bar button').forEach(function(b){b.classList.remove('on');});
  btn.classList.add('on');
}
</script>""")
    return ("財報日曆", "".join(P))


if __name__ == "__main__":
    print(build()[0])
