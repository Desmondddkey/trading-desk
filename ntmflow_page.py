# -*- coding: utf-8 -*-
"""ntmflow_page.py — QQQ 近月期權 NTM 資金流（RAE 自 @TailThatWagsDog）

上：QQQ 收市線（藍 = 多頭極端生效、紅 = 空頭極端生效、灰 = 中性）
下：Call / Put 名義金額柱，標比率
"""
from __future__ import annotations

import html as _h
import io
import json
import os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "ntmflow.json")
COL = {"LONG": "#2f6fb3", "SHORT": "#c0392b", "NEUTRAL": "#9aa0a6"}
TXT = {"LONG": "多頭極端（藍）", "SHORT": "空頭極端（紅）", "NEUTRAL": "中性（未夠樣本／未到極端）"}


def _esc(x):
    return _h.escape(str(x if x is not None else ""))


def strip():
    """每日流程頁頂部用的一行摘要。"""
    if not os.path.exists(SRC):
        return ""
    with io.open(SRC, encoding="utf-8") as f:
        d = json.load(f)
    cur, sig = d.get("latest") or {}, d.get("signal", "NEUTRAL")
    n = d.get("n", 0)
    note = (f"· 累積 {n}/{d.get('min_n', 20)} 日" if n < d.get("min_n", 20)
            else f"· 極端 {d.get('lo')}–{d.get('hi')}")
    return (f'<div style="border:1px solid #d8d2c4;border-radius:8px;padding:9px 12px;'
            f'margin:0 0 10px;background:#fff;font-size:12.5px">'
            f'<b>QQQ 近月期權</b>　Call ${cur.get("call_usd")}M　'
            f'Put ${cur.get("put_usd")}M　比率 <b>{cur.get("ratio")}</b>　'
            f'<span style="color:{COL.get(sig, "#666")};font-weight:700">'
            f'{TXT.get(sig, sig)}</span>'
            f'<span style="opacity:.7">　{_esc(cur.get("expiry"))}（{cur.get("dte")} 日）'
            f'{note}</span></div>')


def _chart(d):
    hist = d.get("history") or []
    qqq = {x["d"]: x["c"] for x in (d.get("qqq") or [])}
    if not hist:
        return '<div class="dim">未夠數據</div>'

    rows = []
    state = "NEUTRAL"
    for h in hist:
        r = h["ratio"]
        if d.get("hi") and r >= d["hi"]:
            state = "LONG"
        elif d.get("lo") and r <= d["lo"]:
            state = "SHORT"
        rows.append((h["date"], qqq.get(h["date"]), h["call_usd"] / 1e6,
                     h["put_usd"] / 1e6, r, state))

    W, H = 1100, 460
    L, R, T, B = 54, 64, 20, 34
    TOPB = 250
    BART, BARB = 300, 420
    prices = [r[1] for r in rows if r[1]]
    pmin = min(prices) if prices else 0
    pmax = max(prices) if prices else 1
    mx = max(15000, max(max(r[2], r[3]) for r in rows) or 1)   # 固定下限 $15B
    n = len(rows)

    def X(i):
        return L + (W - L - R) * (i / max(1, n - 1))

    def Y(v):
        return TOPB - (v - pmin) / max(1e-9, pmax - pmin) * (TOPB - T)

    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-width:820px;max-width:{W}px;'
         f'background:#fff" role="img" aria-label="QQQ 期權 NTM 資金流">'
         f'<rect width="{W}" height="{H}" fill="#fff"/>']
    # 價格線：逐日按狀態上色
    for i in range(1, n):
        if rows[i][1] is None or rows[i - 1][1] is None:
            continue
        P.append(f'<line x1="{X(i-1):.1f}" y1="{Y(rows[i-1][1]):.1f}" '
                 f'x2="{X(i):.1f}" y2="{Y(rows[i][1]):.1f}" '
                 f'stroke="{COL[rows[i][5]]}" stroke-width="2"/>')
    # 柱
    bw = max(3, (W - L - R) / max(1, n) * 0.34)
    for i, r in enumerate(rows):
        hc = r[2] / mx * (BARB - BART)
        hp = r[3] / mx * (BARB - BART)
        P.append(f'<rect x="{X(i)-bw:.1f}" y="{BARB-hc:.1f}" width="{bw:.1f}" '
                 f'height="{hc:.1f}" fill="#2f6fb3" opacity=".85"/>')
        P.append(f'<rect x="{X(i)+1:.1f}" y="{BARB-hp:.1f}" width="{bw:.1f}" '
                 f'height="{hp:.1f}" fill="#c0392b" opacity=".85"/>')
    P.append(f'<line x1="{L}" y1="{BARB}" x2="{W-R}" y2="{BARB}" stroke="#cfc9bb"/>')
    P.append(f'<text x="{L}" y="{TOPB+22}" fill="#8b8578" font-size="11">'
             f'Call（藍）／Put（紅）名義金額，百萬美元</text>')
    P.append(f'<text x="{W-R+6}" y="{T+10}" fill="#8b8578" font-size="10.5">'
             f'{pmax:,.0f}</text>')
    P.append(f'<text x="{W-R+6}" y="{TOPB}" fill="#8b8578" font-size="10.5">'
             f'{pmin:,.0f}</text>')
    P.append(f'<text x="{L}" y="{H-8}" fill="#8b8578" font-size="10.5">'
             f'{_esc(rows[0][0])}</text>')
    P.append(f'<text x="{W-R}" y="{H-8}" fill="#8b8578" font-size="10.5" '
             f'text-anchor="end">{_esc(rows[-1][0])}</text>')
    P.append('</svg>')
    return "".join(P)


def build():
    if not os.path.exists(SRC):
        return ("期權資金流", '<div class="dim">DATA_UNAVAILABLE：未跑 ntmflow.py</div>')
    with io.open(SRC, encoding="utf-8") as f:
        d = json.load(f)
    cur = d.get("latest") or {}
    sig = d.get("signal", "NEUTRAL")
    n = d.get("n", 0)

    P = ['<h2>🌊 期權資金流 <small>QQQ 近月 NTM Call / Put 名義金額</small></h2>']
    P.append(f'<p class="crumb">資料日 {_esc(d.get("as_of"))}｜到期 {_esc(cur.get("expiry"))}'
             f'（{cur.get("dte")} 日）｜累積 {n} 個觀察'
             f'{"（需 " + str(d.get("min_n")) + " 日才判極端）" if n < d.get("min_n", 20) else ""}</p>')

    P.append('<div class="pf-mini2"><table><thead><tr><th>項目</th>'
             '<th class="n">今日</th><th>判讀</th></tr></thead><tbody>')
    P.append(f'<tr><td>Call 名義</td><td class="n">${cur.get("call_usd")}M</td>'
             f'<td>近價（±2%）未平倉 × 100 × 行使價</td></tr>')
    P.append(f'<tr><td>Put 名義</td><td class="n">${cur.get("put_usd")}M</td>'
             f'<td>同上</td></tr>')
    P.append(f'<tr><td>比率 Call÷Put</td><td class="n">{cur.get("ratio")}</td>'
             f'<td>高 = 追多；低 = 買保險</td></tr>')
    P.append(f'<tr><td>訊號</td>'
             f'<td class="n" style="color:{COL.get(sig)};font-weight:700">{sig}</td>'
             f'<td>{TXT.get(sig, "")}</td></tr>')
    if d.get("hi"):
        P.append(f'<tr><td>極端門檻</td><td class="n">{d.get("lo")} – {d.get("hi")}</td>'
                 f'<td>10 / 90 百分位（累積樣本）</td></tr>')
    P.append('</tbody></table></div>')

    P.append('<h3 style="margin-top:14px">圖表</h3>')
    if n < d.get("min_n", 20):
        P.append(f'<div class="pf-note">累積第 {n}／{d.get("min_n")} 日：'
                 '歷史期權鏈無法回補，所以圖由今日開始長；夠 20 日才會出藍／紅狀態。</div>')
    P.append(_chart(d))
    P.append('<div class="pf-note">顏色：藍 = 多頭極端生效、紅 = 空頭極端生效、'
             '灰 = 中性。訊號持續到相反極端出現（跟原 ThinkScript 邏輯）。</div>')

    P.append('<h3 style="margin-top:14px">歷史</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr><th>日期</th><th>到期</th>'
             '<th class="n">DTE</th><th class="n">Call $M</th><th class="n">Put $M</th>'
             '<th class="n">比率</th></tr></thead><tbody>')
    for h in (d.get("history") or [])[-20:][::-1]:
        P.append(f'<tr><td>{_esc(h["date"])}</td><td>{_esc(h["expiry"])}</td>'
                 f'<td class="n">{h["dte"]}</td>'
                 f'<td class="n">{h["call_usd"]/1e6:.1f}</td>'
                 f'<td class="n">{h["put_usd"]/1e6:.1f}</td>'
                 f'<td class="n">{h["ratio"]:.2f}</td></tr>')
    P.append('</tbody></table></div>')

    P.append(f'<div class="pf-note">{_esc(d.get("rule"))}<br>'
             f'來源：{_esc(d.get("source"))}｜'
             '限制：yfinance 只有當日快照，無法回補歷史期權鏈，所以本頁由 2026-11-05 起累積；'
             '未夠樣本前唔會出藍／紅。</div>')
    return ("期權資金流", "".join(P))


def main():
    t, b = build()
    print(f"{t} — {len(b):,} chars")


if __name__ == "__main__":
    main()
