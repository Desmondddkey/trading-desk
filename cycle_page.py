# -*- coding: utf-8 -*-
"""cycle_page.py — 成長週期頁（讀 output/cycle.json）"""
from __future__ import annotations

import html as _h
import io
import json
import os

SRC = r"C:/Users/rain0/trading-os/output/cycle.json"

COL = {
    "RISK-OFF": "#ef4444", "PROBE": "#f59e0b", "RAMP UP": "#22c55e",
    "TRIM": "#eab308", "HOLD": "#38bdf8", "RELOAD": "#a855f7",
}
MEAN = {
    "RISK-OFF": "錢去價值；成長弱、建現金；新倉要細、止蝕要緊",
    "PROBE": "成長喺線下轉上；結構未過。小注試探，唔加",
    "RAMP UP": "剛確認 risk-on，測試區突破；可以加倉",
    "TRIM": "伸展中；分段止賺，保留核心",
    "HOLD": "伸展但消化中；留住贏家，拖止蝕",
    "RELOAD": "上升趨勢中回調；支撐位重新加",
}


def _esc(x):
    return _h.escape(str(x if x is not None else ""))


def _strip(hist):
    """近 260 日 zone 色帶。"""
    if not hist:
        return ""
    W, H = 920, 46
    n = len(hist)
    bw = W / n
    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px" '
         f'role="img" aria-label="成長週期歷史">']
    P.append(f'<rect width="{W}" height="{H}" fill="#0f1115"/>')
    for i, x in enumerate(hist):
        P.append(f'<rect x="{i*bw:.2f}" y="8" width="{max(bw,0.7):.2f}" height="26" '
                 f'fill="{COL.get(x["zone"], "#475569")}" fill-opacity="0.9"/>')
    P.append(f'<text x="2" y="44" fill="#94a3b8" font-size="9.5">{_esc(hist[0]["date"])}</text>')
    P.append(f'<text x="{W-2}" y="44" fill="#94a3b8" font-size="9.5" '
             f'text-anchor="end">{_esc(hist[-1]["date"])}</text>')
    P.append('</svg>')
    return "".join(P)


def build():
    if not os.path.exists(SRC):
        return ("成長週期", '<div class="dim">DATA_UNAVAILABLE：未跑 growth_cycle.py</div>')
    with io.open(SRC, encoding="utf-8") as f:
        d = json.load(f)
    cur = d["current"]
    z = cur["zone"]
    col = COL.get(z, "#94a3b8")

    P = ['<h2>🌀 成長週期 <small>而家應該幾積極？</small></h2>']
    P.append('<p class="crumb">閘門＝成長/價值（IWF÷IWD）10 週結構｜'
             '動能＝比率 10 日變化｜延伸＝(比率−EMA)÷半軌寬｜'
             f'資料日 {_esc(d["as_of"])}</p>')

    P.append('<div class="card"><div style="padding:12px 14px">'
             f'<div style="font-size:26px;font-weight:800;color:{col};line-height:1.1">'
             f'{_esc(z)}</div>'
             f'<div style="font-size:12px;opacity:.8;margin-top:4px">'
             f'{_esc(MEAN.get(z, ""))}</div>'
             '<div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:10px;'
             'font-size:11.5px">'
             f'<div>閘門 <b>{_esc(cur["gate"])}</b></div>'
             f'<div>動能 <b>{cur["mom"]:+.2f}%</b>（10 日）</div>'
             f'<div>延伸 <b>{cur["ext"]:+.2f}</b>（≥1.5 = 伸展）</div>'
             f'<div>區內 <b>{cur["days_in_zone"]}</b> 日</div>'
             '</div></div></div>')

    P.append('<h3 style="margin-top:16px">六個區（由左至右）</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr><th>區</th><th>意思</th>'
             '<th class="n">之後 10 日 SPY 平均</th><th class="n">勝率</th>'
             '<th class="n">n</th></tr></thead><tbody>')
    for k in ("RISK-OFF", "PROBE", "RAMP UP", "TRIM", "HOLD", "RELOAD"):
        v = (d.get("zones") or {}).get(k) or {}
        cur_mark = " ◀ 而家" if k == z else ""
        P.append(f'<tr><td style="color:{COL[k]};font-weight:700">{k}{cur_mark}</td>'
                 f'<td>{_esc(MEAN[k])}</td>'
                 f'<td class="n">{v.get("mean", "—")}{"%" if v.get("mean") is not None else ""}</td>'
                 f'<td class="n">{v.get("wr", "—")}{"%" if v.get("wr") is not None else ""}</td>'
                 f'<td class="n">{v.get("n", 0)}</td></tr>')
    P.append('</tbody></table></div>')
    P.append('<div class="pf-note">⚠ 之後表現係 2012 年至今嘅歷史統計，'
             '唔係預測；同一個區喺不同年代表現可以差好遠。</div>')

    P.append('<h3 style="margin-top:16px">近 260 個交易日</h3>')
    P.append(_strip(d.get("history") or []))
    P.append('<div class="pf-note">色帶 = 當日所屬區。'
             '留意區與區之間通常有次序：RISK-OFF → PROBE → RAMP UP → TRIM/HOLD → RELOAD。</div>')

    P.append('<h3 style="margin-top:16px">同其他頁點接</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr><th>區</th>'
             '<th>油門</th><th>睇邊頁</th></tr></thead><tbody>')
    P.append('<tr><td>RISK-OFF / PROBE</td><td>0.2% 探路，唔加</td>'
             '<td>頂部觀察、投降儀表</td></tr>')
    P.append('<tr><td>RAMP UP</td><td>可加到 0.5%；到 +1R 才全倉</td>'
             '<td>肥波總覽、Daily Scan</td></tr>')
    P.append('<tr><td>TRIM / HOLD</td><td>唔加新倉；分段止賺</td>'
             '<td>覆盤、Alerts</td></tr>')
    P.append('<tr><td>RELOAD</td><td>回調至支撐再加</td>'
             '<td>RS Daily Scan、Setups</td></tr>')
    P.append('</tbody></table></div>')
    P.append(f'<div class="pf-note">規則（寫死）：{_esc(d.get("rule"))}</div>')
    return ("成長週期", "".join(P))


def main():
    t, b = build()
    print(f"{t} — {len(b):,} chars")


if __name__ == "__main__":
    main()
