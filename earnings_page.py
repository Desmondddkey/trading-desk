# -*- coding: utf-8 -*-
"""earnings_page.py — 財報日曆頁（Desmond 2026-10-19）

★ 需求：「Rae 呢個出黎 我想針對財報」（貼咗富途業績日曆截圖）

★ 第一性原理：財報係【二元事件】，唔係參考資料。
    持倉遇財報 = 一晚可以 −20%，止蝕單會跳空穿 → 必須減倉或對沖
    候選 D ≤ 5 = 入場等於買彩票（EDGE-008 blackout）

頁面結構：
  ① 你嘅持倉 / 候選有財報（最重要，紅框）
  ② 逐日曆表（盤前 / 盤後 分開）
  ③ 判定說明（EDGE-008）
"""
import datetime as dt
import html as _h
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TO = r"C:\Users\rain0\trading-os"


def _esc(v):
    return _h.escape(str(v)) if v is not None else ""


CSS = """
.er-hit{border:1px solid rgba(192,38,43,.55);background:rgba(192,38,43,.07)}
.er-day{border:1px solid rgba(128,128,128,.28);border-radius:10px;
  overflow:hidden;margin:0 0 12px}
.er-day>h3{margin:0;padding:11px 15px;font-size:14px;
  background:rgba(128,128,128,.09);font-weight:700;
  display:flex;align-items:center;gap:9px}
.er-day>h3 .n{margin-left:auto;font-size:11.5px;opacity:.6;font-weight:400}
.er-when{display:inline-block;font-size:10.5px;padding:2px 7px;border-radius:999px;
  border:1px solid rgba(128,128,128,.4);margin-right:7px;opacity:.85}
.er-when.pre{background:rgba(37,99,235,.14);border-color:rgba(37,99,235,.45)}
.er-when.post{background:rgba(147,51,234,.14);border-color:rgba(147,51,234,.45)}
.er-list{padding:6px 14px 10px}
.er-row{display:grid;grid-template-columns:64px 54px 1fr 56px 86px;
  gap:10px;align-items:center;padding:7px 0;
  border-bottom:1px solid rgba(128,128,128,.12);font-size:12.5px}
.er-row:last-child{border-bottom:0}
.er-tk{font-family:ui-monospace,monospace;font-size:14px}
.er-nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  opacity:.85;font-size:12.5px}
/* ★ 手機：唔橫滑，改成兩行 */
@media(max-width:700px){
  .er-row{grid-template-columns:auto auto 1fr auto;row-gap:2px;
    column-gap:8px;padding:8px 0}
  .er-row>.er-nm{grid-column:1/-1;order:9;font-size:11.5px;opacity:.62}
  .er-mc{font-size:11.5px}
  .er-eps{font-size:11.5px}
}
.er-sym{font-weight:700}
.er-held{color:#c0262b;font-weight:800}
.er-watch{color:#b45309;font-weight:800}
[data-theme="dark"] .er-held{color:#ff9a9d}
[data-theme="dark"] .er-watch{color:#fbc06a}
.er-mc{opacity:.62;font-size:11.5px}
.er-eps{opacity:.72;font-size:11.5px}
.er-alert{border-radius:10px;padding:13px 16px;margin:0 0 14px;font-size:12.5px;
  line-height:1.75}
.er-alert.bad{background:rgba(192,38,43,.1);border:1px solid rgba(192,38,43,.5)}
.er-alert.warn{background:rgba(224,168,0,.1);border:1px solid rgba(224,168,0,.5)}
.er-legend{font-size:11.5px;line-height:1.9;opacity:.8}
"""


def load():
    """讀最新 earnings_*.json。"""
    import glob
    fs = sorted(glob.glob(os.path.join(TO, "output", "earnings_*.json")))
    if not fs:
        return None, None
    p = fs[-1]
    try:
        return json.load(io.open(p, encoding="utf-8")), os.path.basename(p)
    except (OSError, ValueError):
        return None, os.path.basename(p)


def build():
    rows, src = load()
    if not rows:
        return ("財報日曆",
                '<div class="er-alert bad">⛔ <b>DATA_UNAVAILABLE</b><br>'
                '搵唔到 <code>output/earnings_*.json</code>。'
                '跑 <code>python earnings_calendar.py</code>。'
                '★ Missing ≠ Zero。</div>')

    today = dt.date.today()
    held = [r for r in rows if r.get("held")]
    watch = [r for r in rows if r.get("watch")]

    parts = [f'<style>{CSS}</style>']
    parts.append('<h2>📊 財報日曆 <small>EDGE-008 二元風險判定</small></h2>')
    parts.append(
        f'<p class="crumb">來源 <code>{_esc(src)}</code>｜'
        f'生成 {_esc(today)}｜市值 ≥ $2B｜'
        '唯讀研究用途，<b>非買入指令</b></p>')

    # ① 持倉 / 候選中招
    if held:
        parts.append('<div class="er-alert bad"><b>🚨 你嘅持倉有財報</b><br>'
                     '財報係二元事件：一晚可以 −20%，止蝕單會跳空穿。'
                     '<b>考慮財報前減倉或對沖。</b><br><br>')
        for r in held:
            parts.append(f'· <b>{_esc(r["sym"])}</b> {_esc(r["date"])} '
                         f'{_esc(r["when"])}（D+{r["d"]}）'
                         f'— {_esc(r["name"][:34])}<br>')
        parts.append('</div>')

    if watch:
        parts.append('<div class="er-alert warn"><b>👀 你嘅候選有財報</b><br>'
                     'D ≤ 5 交易日 = <b>EARNINGS_BLACKOUT</b>，'
                     '根據 EDGE-008 唔可以入場。<br><br>')
        for r in watch:
            parts.append(f'· <b>{_esc(r["sym"])}</b> {_esc(r["date"])} '
                         f'{_esc(r["when"])}（D+{r["d"]}）<br>')
        parts.append('</div>')

    # ② 逐日
    by_date = {}
    for r in rows:
        by_date.setdefault(r["date"], []).append(r)

    for d in sorted(by_date):
        grp = by_date[d]
        wd = dt.date.fromisoformat(d).strftime("%A")
        pre = [r for r in grp if r["when"] == "盤前"]
        post = [r for r in grp if r["when"] == "盤後"]
        other = [r for r in grp if r["when"] not in ("盤前", "盤後")]
        parts.append(f'<div class="er-day"><h3>📅 {_esc(d)}（{wd}）'
                     f'<span class="n">{len(grp)} 隻</span></h3>'
                     '<div class="er-list">')
        for r in pre + post + other:
            cls = ("er-held" if r.get("held") else
                   "er-watch" if r.get("watch") else "er-sym")
            wcls = ("pre" if r["when"] == "盤前" else
                    "post" if r["when"] == "盤後" else "")
            mc = f'${r["mcap"]/1e9:,.0f}B' if r.get("mcap") else "—"
            eps = r.get("eps_fc") or "—"
            if eps in ("N/A", ""):
                eps = "—"
            parts.append(
                f'<div class="er-row">'
                f'<span class="er-when {wcls}">{_esc(r["when"])}</span>'
                f'<b class="{cls} er-tk">{_esc(r["sym"])}</b>'
                f'<span class="er-nm">{_esc(r["name"][:44])}</span>'
                f'<span class="er-mc">{mc}</span>'
                f'<span class="er-eps">EPS {_esc(eps)}</span>'
                '</div>')
        parts.append('</div></div>')

    # ③ 判定說明
    parts.append('<div class="card"><h2>★ 判定規則（EDGE-008）</h2>'
                 '<div class="body"><div class="er-legend">'
                 'D = 距今幾個<b>交易日</b>（唔計週末）<br>'
                 '<b>D ≤ 5</b> → ⛔ <code>EARNINGS_BLACKOUT</code>'
                 '：唔可以入場；持倉要減／對沖<br>'
                 '<b>6 ≤ D ≤ 10</b> → ⚠️ <code>EARNINGS_SOON</code>'
                 '：可以入但唔可以重倉<br>'
                 '<b>D &gt; 10</b> → ✅ <code>OK_ND</code>：冇財報風險<br><br>'
                 '★ 為什麼財報係硬性限制：止蝕單喺跳空時唔會成交，'
                 '你嘅 3% 止蝕可以變成 −25%。'
                 '</div></div></div>')
    return ("財報日曆", "".join(parts))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    title, body = build()
    out = os.path.join(HERE, "earnings_body.html")
    io.open(out, "w", encoding="utf-8").write(body)
    print(f"✓ earnings body {len(body):,} 字 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
