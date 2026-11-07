# -*- coding: utf-8 -*-
"""earnings_cal_page.py — 財報日曆（本站原生渲染）

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



import glob
import html as _h
import io
import json
import os

OUT = r"C:/Users/rain0/trading-os/output"
FINVIZ = "https://finviz.com/calendar/earnings?day="

CSS = """
.ec-bar{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:0 0 10px}
.ec-bar button{font-size:12px;padding:4px 10px;border-radius:6px;cursor:pointer;
  border:1px solid rgba(148,163,184,.35);background:transparent;color:inherit}
.ec-bar button.on{background:#c2410c;border-color:#c2410c;color:#fff}
.ec-day{margin:14px 0 4px;font-size:12px;font-weight:800;letter-spacing:.03em;opacity:.75}
.ec-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
.ec-tbl th{text-align:left;font-size:10px;letter-spacing:.05em;opacity:.5;font-weight:800;
  padding:4px 7px;border-bottom:1px solid rgba(148,163,184,.25);white-space:nowrap}
.ec-tbl td{padding:3px 7px;border-bottom:1px solid rgba(148,163,184,.1);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.ec-tbl td.n,.ec-tbl th.n{text-align:right}
.ec-tbl td.nm{max-width:260px;overflow:hidden;text-overflow:ellipsis}
.ec-tk{font-weight:800}
.ec-bad{color:#a04a44;font-weight:700}
.ec-soon{color:#b9a05f;font-weight:700}
.ec-note{font-size:10.5px;opacity:.55;line-height:1.6;margin-top:10px}
.ec-mini{opacity:.55;font-size:10.5px}
"""


def _load():
    files = sorted(glob.glob(os.path.join(OUT, "earnings_*.json")))
    if not files:
        return None, None
    p = files[-1]
    try:
        with io.open(p, encoding="utf-8") as f:
            rows = json.load(f)
    except Exception:
        return None, None
    return rows, os.path.basename(p).replace("earnings_", "").replace(".json", "")


def build():
    rows, dref = _load()
    if not rows:
        return ("財報日曆", '<div class="card"><div class="body">'
                            'DATA_UNAVAILABLE — 未跑 earnings collector'
                            '（trading-os/output/earnings_*.json）。</div></div>')

    rows = [r for r in rows if r.get("date")]
    rows.sort(key=lambda r: (r["date"], -(r.get("mcap") or 0)))
    dates = sorted({r["date"] for r in rows})[:12]

    L = [f"<style>{CSS}</style>"]
    L.append('<div class="card"><h2>財報日曆 <small>本站原生 · Finviz 資料 · '
             f'截至 {_h.escape(dref)}</small></h2><div class="body">')
    L.append('<div class="ec-bar">')
    L.append('<button class="on" data-k="all" onclick="ecF(this)">全部</button>')
    L.append('<button data-k="bad" onclick="ecF(this)">⛔ 禁新倉</button>')
    L.append('<button data-k="big" onclick="ecF(this)">市值 &gt; $50B</button>')
    L.append('</div>')

    for dt in dates:
        day = [r for r in rows if r["date"] == dt]
        n_bad = sum(1 for r in day if r.get("status") == "EARNINGS_BLACKOUT")
        L.append(f'<div class="ec-day">{_h.escape(dt)}　'
                 f'<span class="ec-mini">{len(day)} 隻 · {n_bad} 隻禁新倉 · </span>'
                 f'<a class="ec-mini" href="{FINVIZ}{dt}" target="_blank" rel="noopener">Finviz</a></div>')
        L.append('<div class="tscroll"><table class="ec-tbl"><thead><tr>'
                 '<th>代號</th><th>公司</th><th class="n">市值 $B</th><th>時段</th>'
                 '<th class="n">EPS 預測</th><th class="n">上年</th><th>狀態</th>'
                 '</tr></thead><tbody>')
        for r in day:
            st = r.get("status") or ""
            badge = ('<span class="ec-bad">⛔ 禁新倉</span>' if st == "EARNINGS_BLACKOUT"
                     else '<span class="ec-soon">⏳ 即將</span>')
            if r.get("held"):
                badge += ' <span class="ec-mini">持倉</span>'
            elif r.get("watch"):
                badge += ' <span class="ec-mini">觀察</span>'
            mcap = r.get("mcap") or 0
            L.append(
                f'<tr data-k="{"bad" if st == "EARNINGS_BLACKOUT" else "soon"}" '
                f'data-m="{mcap/1e9:.1f}">'
                f'<td><span class="ec-tk">{_h.escape(str(r.get("sym") or ""))}</span></td>'
                f'<td class="nm">{_h.escape(str(r.get("name") or ""))}</td>'
                f'<td class="n">{mcap/1e9:,.0f}</td>'
                f'<td>{_h.escape(str(r.get("when") or ""))}</td>'
                f'<td class="n">{_h.escape(str(r.get("eps_fc") or "—"))}</td>'
                f'<td class="n">{_h.escape(str(r.get("eps_ly") or "—"))}</td>'
                f'<td>{badge}</td></tr>')
        L.append('</tbody></table></div>')

    L.append('<div class="ec-note">資料：自家 earnings collector（cron earnings-daily 每日更新），'
             '市值、盤前／盤後、EPS 預測同 blackout 判斷都出自同一份檔。</div>')
    L.append('</div></div>')
    L.append("""<script>
function ecF(btn){var k=btn.dataset.k;
  document.querySelectorAll('.ec-bar button').forEach(function(b){b.classList.remove('on');});
  btn.classList.add('on');
  document.querySelectorAll('.ec-tbl tbody tr').forEach(function(tr){
    var ok = k==='all' ? true : k==='bad' ? tr.dataset.k==='bad'
             : parseFloat(tr.dataset.m) > 50;
    tr.style.display = ok ? '' : 'none';
  });
  document.querySelectorAll('.ec-day').forEach(function(d){
    var t=d.nextElementSibling; if(!t) return;
    var vis=[].some.call(t.querySelectorAll('tbody tr'), function(tr){return tr.style.display!=='none';});
    d.style.display = vis ? '' : 'none';
    t.style.display = vis ? '' : 'none';
  });
}
</script>""")
    return ("財報日曆", "".join(L))


if __name__ == "__main__":
    print(build()[0])
