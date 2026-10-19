# -*- coding: utf-8 -*-
"""datahealth.py — 數據健康後台（Data Health）

Desmond 2026-10-20：「如果有任務無做日更既野做返一個後台出黎
要確保到數據更新，我唔想佢有任何假野 / 假更新」

呢頁解決三件事：
  ① 一眼睇到邊個數據源過期 / 缺失
  ② 每個源寫明「邊個 job 負責」「用喺邊度」
  ③ 過期嘅源**唔會**被當成即時數據使用（配合 freshness.py）
"""
import sys

import freshness as F

CSS = """
.dh-top{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 16px}
.dh-kpi{flex:1 1 120px;padding:12px 14px;border-radius:12px;
  border:1px solid rgba(128,128,128,.28);background:rgba(128,128,128,.05)}
.dh-kpi .n{font-size:26px;font-weight:800;line-height:1.1}
.dh-kpi .l{font-size:11px;opacity:.6;margin-top:3px}
.dh-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
.dh-tbl th{text-align:left;font-size:10.5px;letter-spacing:.05em;
  text-transform:uppercase;opacity:.55;padding:7px 9px;font-weight:700;
  border-bottom:1px solid rgba(128,128,128,.28)}
.dh-tbl td{padding:8px 9px;border-bottom:1px solid rgba(128,128,128,.1);
  text-align:left!important;white-space:normal;word-break:break-word}
.dh-tbl tr:hover{background:rgba(128,128,128,.06)}
.fr-b{font-size:11px;font-weight:800;padding:2px 8px;border-radius:999px;
  white-space:nowrap;border:1px solid currentColor}
.fr-fresh{color:#16a34a}
.fr-stale{color:#ea580c}
.fr-miss{color:#dc2626}
.dh-warn{border:1px solid rgba(220,38,38,.45);background:rgba(220,38,38,.08);
  border-radius:12px;padding:13px 15px;margin:0 0 16px;font-size:12.5px;
  line-height:1.8}
.dh-warn b{color:#dc2626}
.dh-ok{border:1px solid rgba(22,163,74,.4);background:rgba(22,163,74,.07);
  border-radius:12px;padding:13px 15px;margin:0 0 16px;font-size:12.5px}
@media(max-width:700px){
  .dh-tbl thead{display:none}
  .dh-tbl,.dh-tbl tbody,.dh-tbl tr{display:block;width:100%}
  .dh-tbl tr{padding:10px 0;border-bottom:1px solid rgba(128,128,128,.16)}
  .dh-tbl td{display:block;border:0;padding:1px 0}
  .dh-tbl td:nth-child(1){font-size:13px;font-weight:800}
  .dh-tbl td:nth-child(2){display:inline;margin-top:4px}
  .dh-tbl td:nth-child(3){display:inline;margin-left:8px;font-size:11px}
  .dh-tbl td:nth-child(4),.dh-tbl td:nth-child(5){font-size:11px;
    opacity:.72;margin-top:3px}
}
"""


def build():
    rs = F.all_status()
    sm = F.summary()
    bad = [r for r in rs if r["status"] != "FRESH"]

    parts = [f"<style>{CSS}</style>",
             "<h2>數據健康 <small>Data Health</small></h2>",
             '<p class="crumb">每個數據源嘅真實更新時間｜'
             '過期嘅源會喺所屬頁面標示警告，唔會被當成即時數據</p>']

    # ── KPI ──
    parts.append('<div class="dh-top">')
    for n, l, c in ((sm["fresh"], "即時", "#16a34a"),
                    (sm["stale"], "過期", "#ea580c"),
                    (sm["missing"], "缺失", "#dc2626"),
                    (sm["total"], "總數", "#64748b")):
        parts.append(f'<div class="dh-kpi"><div class="n" style="color:{c}">'
                     f'{n}</div><div class="l">{l}</div></div>')
    parts.append('</div>')

    # ── 警示 ──
    if sm["stale"] or sm["missing"]:
        names = "、".join(f'<b>{r["label"]}</b>' for r in bad)
        parts.append(
            f'<div class="dh-warn">⚠️ <b>{len(bad)} 個數據源有問題</b>：'
            f'{names}<br>'
            '呢啲數據**唔可以**當成今日嘅資料用。'
            '如果相關頁面仲顯示「今日」，嗰個就係假更新 —— 請即刻同我講。'
            '</div>')
    else:
        parts.append('<div class="dh-ok">✓ 全部數據源都係最新'
                     '（每個都喺容許時間內更新過）</div>')

    # ── 詳表 ──
    parts.append('<table class="dh-tbl"><thead><tr>'
                 '<th>數據源</th><th>狀態</th><th>日齡</th>'
                 '<th>負責 job</th><th>用喺邊</th>'
                 '</tr></thead><tbody>')
    order = {"MISSING": 0, "STALE": 1, "FRESH": 2}
    for r in sorted(rs, key=lambda x: (order[x["status"]], -(x["age"] or 0))):
        age = f'{r["age"]} 日' if r["age"] is not None else "—"
        parts.append(
            f'<tr><td><b>{r["label"]}</b></td>'
            f'<td>{F.badge(r)}</td>'
            f'<td>{age}</td>'
            f'<td style="opacity:.8">{r.get("producer") or "—"}</td>'
            f'<td style="opacity:.65">{r.get("used") or "—"}</td></tr>')
    parts.append('</tbody></table>')

    parts.append(
        '<div class="note" style="margin-top:16px;font-size:12px;'
        'line-height:1.8">'
        '<b>判定規則（寫死喺 freshness.py，唔可以事後改）</b><br>'
        'FRESH = 檔案存在，而且日齡 ≤ 該源嘅 max_age<br>'
        'STALE = 檔案存在但超過 max_age（通常代表 job 冇跑）<br>'
        'MISSING = 完全搵唔到檔案<br>'
        '<br><b>為什麼用日曆日而唔係交易日？</b> '
        '交易日需要市假日曆，容易出錯；日曆日 + 寬鬆門檻更安全。'
        '週末會出現 STALE（週五數據在週日 age=2），所以 max_age 已預留。'
        '</div>')
    return ("數據健康", "".join(parts))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    t, b = build()
    print(f"{t}: {len(b)} bytes")
    for r in F.all_status():
        print(f'  {r["status"]:<8}{r["label"]}')
