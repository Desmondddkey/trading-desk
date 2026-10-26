# -*- coding: utf-8 -*-
"""fear_gauge_page.py — 投降／過熱儀表

數據：output/fear_gauge.json（fear_gauge.py 每日收市後寫）
回測：output/fear_backtest.json（3 年 753 日，2023-10-24 → 2026-10-23）
"""
from __future__ import annotations

import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "output", "fear_gauge.json")

CSS = """
.fg-hero{display:flex;gap:18px;align-items:center;flex-wrap:wrap}
.fg-score{font-size:44px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}
.fg-verdict{font-size:15px;font-weight:800;margin-top:4px}
.fg-meta{font-size:11px;opacity:.6;margin-top:6px}
.fg-tbl{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:10px}
.fg-tbl th{text-align:left;font-size:10.5px;letter-spacing:.04em;opacity:.55;
  font-weight:800;padding:6px 8px;border-bottom:1px solid rgba(148,163,184,.25)}
.fg-tbl td{padding:6px 8px;border-bottom:1px solid rgba(148,163,184,.1);
  font-variant-numeric:tabular-nums}
.fg-tbl td.n,.fg-tbl th.n{text-align:right}
.fg-hit{color:#22c55e;font-weight:800}
.fg-miss{opacity:.4}
.fg-bar{height:4px;background:rgba(148,163,184,.18);border-radius:2px;overflow:hidden}
.fg-bar i{display:block;height:100%;background:linear-gradient(90deg,#22c55e,#f97316)}
.fg-note{font-size:10.5px;line-height:1.7;opacity:.6;margin-top:12px;max-width:820px}
.fg-warn{border-left:2px solid #f97316;padding:6px 10px;font-size:11px;opacity:.8;margin:10px 0}
"""


def _load(p, d):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return d


def build():
    d = _load(SRC, {})
    if not d:
        return ("投降儀表", '<p>DATA_UNAVAILABLE — 未跑 fear_gauge.py</p>')

    s = d.get("score", 0)
    col = "#22c55e" if s >= 3 else "#f97316" if s == 2 else "#94a3b8"
    pct = 100.0 * s / 5

    L = [f"<style>{CSS}</style>", '<div class="card">',
         '<h2 style="margin:0 0 10px">投降／過熱儀表</h2>',
         '<div class="fg-hero">',
         f'<div><div class="fg-score" style="color:{col}">{s}<span '
         f'style="font-size:16px;opacity:.45">/5</span></div>',
         f'<div class="fg-verdict" style="color:{col}">{d.get("verdict","")}</div></div>',
         f'<div style="flex:1 1 260px;min-width:220px">'
         f'<div class="fg-bar"><i style="width:{pct:.0f}%"></i></div>'
         f'<div class="fg-meta">數據日 {d.get("date","?")}｜'
         f'歷史同分 20 日：{d.get("expectancy","—")}</div></div>',
         '</div>']

    L.append('<table class="fg-tbl"><thead><tr>'
             '<th>訊號</th><th class="n">現值</th><th>狀態</th>'
             '<th class="n">歷史 20 日（SPY）</th></tr></thead><tbody>')
    for c in d.get("checks", []):
        hit = c.get("hit")
        L.append(f'<tr class="{"fg-hit" if hit else "fg-miss"}">'
                 f'<td>{c.get("name")}</td>'
                 f'<td class="n">{c.get("value")}</td>'
                 f'<td>{"✅ 觸發" if hit else "—"}</td>'
                 f'<td class="n">{c.get("edge")}</td></tr>')
    L.append('</tbody></table>')

    L.append('<div class="fg-warn">'
             '<b>過熱方向（逃頂）回測冇 edge</b> —— '
             'VIX&lt;14 與廣度&gt;85% 樣本不足；唯一觸發過嘅組別（1 分）'
             '20 日中位數 +2.89%，反而高過基準 +2.09%。'
             '所以呢頁只會喺<b>投降方向</b>發警報，唔會扮識估頂。</div>')

    bt = d.get("backtest") or {}
    if bt.get("buckets"):
        L.append('<table class="fg-tbl"><thead><tr>'
                 '<th>投降分</th><th class="n">日數</th>'
                 '<th class="n">20 日中位數</th><th class="n">勝率</th>'
                 '</tr></thead><tbody>')
        for score, n, med, win in bt["buckets"]:
            star = " ★" if score >= 3 else ""
            L.append(f'<tr><td>{score} 分{star}</td><td class="n">{n}</td>'
                     f'<td class="n">{med:+.2f}%</td>'
                     f'<td class="n">{win:.0f}%</td></tr>')
        L.append('</tbody></table>')
        L.append(f'<div class="fg-meta">回測 {bt.get("window")}｜'
                 f'{bt.get("days")} 個交易日｜標的 SPY（QQQ／IWM 同向）</div>')

    L.append('<div class="fg-note">'
             '<b>未接嘅來源（誠實標示）</b>：AAII 每週情緒、Gamma（GEX／DIX）、'
             '空頭持倉（FINRA 雙週）三家都封鎖無頭抓取 → 唔會用假數填。'
             '<b>P/C 口徑</b>：用 CNN 發佈嘅 5 日平均 put/call（同 Cboe Equity 唔同），'
             '所以觸發門檻訂 0.80 而非 0.67。'
             '<b>唔可以當見底訊號</b>：分數 2 只係「超跌累積」，'
             '歷史上 20 日勝率 78.6%＝有 21.4% 機會繼續跌。'
             '倉位照由每天嘅 plan card 決定，唔好用呢頁加大注碼。'
             '</div></div>')
    return ("投降儀表", "".join(L))
