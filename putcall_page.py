# -*- coding: utf-8 -*-
"""putcall_page.py — Put/Call Ratio 頁（照 Brian G / @alphacharts 圖重畫）

版面：上 SPX（右軸）／下 Equity P/C ratio + 250 日均線（右軸）
      豎虛線 = SPX 回撤底部附近的 P/C 高峰（賣壓高峰）
"""
from __future__ import annotations

import html as _h
import io
import json
import os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "putcall.json")
ZSRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "putcall_zone.json")


def _esc(x):
    return _h.escape(str(x if x is not None else ""))


def _chart(d, z=None):
    ser = d.get("series") or []
    if len(ser) < 200:
        return '<div class="dim">DATA_UNAVAILABLE：未夠數據（需要 200 日以上）</div>'

    W, H = 1180, 720
    L, R = 14, 76
    SPX_T, SPX_B = 26, 402
    PC_T, PC_B = 452, 668
    INK, MUTED = "#1b2430", "#8b8578"
    NAVY, PURPLE, GREY, RED = "#1f3a5f", "#6d58a6", "#9aa0a6", "#a8443c"

    xs = [s["d"] for s in ser]
    n = len(xs)

    def X(i):
        return L + (W - L - R) * (i / max(1, n - 1))

    spx = [s["spx"] for s in ser if s["spx"]]
    smin, smax = min(spx), max(spx)

    def YS(v):
        return SPX_B - (v - smin) / max(1e-9, smax - smin) * (SPX_B - SPX_T)

    # 照原圖固定軸：0.45 – 1.05（超出的值照畫但被裁在框內）
    pmin, pmax = 0.45, 1.05

    def YP(v):
        return PC_B - (v - pmin) / max(1e-9, pmax - pmin) * (PC_B - PC_T)

    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-width:900px;max-width:{W}px;'
         f'background:#fff" role="img" aria-labelledby="pc-title">'
         f'<title id="pc-title">SPX 與 CBOE Equity Put/Call Ratio（250 日均線）</title>']
    P.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')

    # P/C 水平格線 + 右軸
    step = 0.05
    v = 0.45
    while v <= pmax + 1e-9:
        y = YP(v)
        P.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" '
                 f'stroke="#eceae4" stroke-width="1"/>')
        P.append(f'<text x="{W-R+6}" y="{y+4:.1f}" fill="{MUTED}" font-size="10.5">'
                 f'{v:.3f}</text>')
        v += step

    # SPX 線
    pts = " ".join(f"{X(i):.1f},{YS(s['spx']):.1f}"
                   for i, s in enumerate(ser) if s["spx"])
    P.append(f'<polyline points="{pts}" fill="none" stroke="{NAVY}" stroke-width="1.1"/>')

    # SPX 右軸（照原圖：右邊標價位）
    for lv in (700, 1000, 2000, 3000, 4000, 5000, 6000, 7000):
        if smin <= lv <= smax:
            y = YS(lv)
            P.append(f'<text x="{W-R+6}" y="{y+4:.1f}" fill="{MUTED}" font-size="10.5">'
                     f'{lv:,}</text>')

    # P/C 線 + 250 日均線
    ppts = " ".join(f"{X(i):.1f},{YP(s['pc']):.1f}" for i, s in enumerate(ser))
    P.append(f'<polyline points="{ppts}" fill="none" stroke="{PURPLE}" stroke-width="0.9"/>')
    mpts = " ".join(f"{X(i):.1f},{YP(s['ma']):.1f}"
                    for i, s in enumerate(ser) if s["ma"] is not None)
    P.append(f'<polyline points="{mpts}" fill="none" stroke="#7a7468" stroke-width="1.4"/>')

    # 賣壓高峰豎虛線（跨兩個面板）
    pos = {s: i for i, s in enumerate(xs)}
    for ev in (d.get("climax") or []):
        if ev["d"] not in pos:
            continue
        x = X(pos[ev["d"]])
        P.append(f'<line x1="{x:.1f}" y1="{SPX_T}" x2="{x:.1f}" y2="{PC_B}" '
                 f'stroke="{RED}" stroke-width="0.9" stroke-dasharray="2 3" '
                 f'opacity="0.85"/>')
        lab = ev["d"][:4] + "." + ev["d"][5:7]
        P.append(f'<text x="{x+3:.1f}" y="{SPX_T+11}" fill="{RED}" font-size="9.5" '
                 f'opacity="0.9">{lab}</text>')

    # ── 逆向區間：門檻線 + 穿越事件（putcall_zone.py 驗證）──
    if z and z.get("threshold"):
        thr = float(z["threshold"])
        if pmin <= thr <= pmax:
            yy = YP(thr)
            P.append(f'<line x1="{L}" y1="{yy:.1f}" x2="{W-R}" y2="{yy:.1f}" '
                     f'stroke="#2e7d32" stroke-width="1.3" stroke-dasharray="5 4"/>')
            lx, ly = W - R - 250, yy - 6
            P.append(f'<rect x="{lx-4}" y="{ly-10}" width="252" height="14" fill="#fff" opacity="0.92"/>')
            P.append(f'<text x="{lx}" y="{ly}" fill="#2e7d32" font-size="10">'
                     f'逆向區間門檻 P/C ≥ {thr:.3f}（第 {z.get("pctile")} 百分位）</text>')
        for ev in (z.get("events") or [])[-8:]:
            if ev.get("d") not in pos:
                continue
            x = X(pos[ev["d"]])
            P.append(f'<line x1="{x:.1f}" y1="{PC_T}" x2="{x:.1f}" y2="{PC_B}" '
                     f'stroke="#2e7d32" stroke-width="0.7" stroke-dasharray="2 3" '
                     f'opacity="0.55"/>')

    # 年份刻度
    seen = set()
    for i, s in enumerate(ser):
        y = s["d"][:4]
        if y not in seen and s["d"][5:7] == "01" and i > 30:
            seen.add(y)
            P.append(f'<line x1="{X(i):.1f}" y1="{PC_B}" x2="{X(i):.1f}" y2="{PC_B+5}" '
                     f'stroke="#cfc9bb"/>')
            P.append(f'<text x="{X(i):.1f}" y="{PC_B+20}" fill="{MUTED}" font-size="11" '
                     f'text-anchor="middle">{y}</text>')

    # 標題與來源（照原圖排版）
    P.append(f'<text x="{L}" y="16" fill="{INK}" font-size="13" font-weight="700">'
             f'SPX (Daily)</text>')
    P.append(f'<text x="{L+82}" y="16" fill="{INK}" font-size="12">'
             f'CBOE Equity Put/Call Ratio, 250-DMA</text>')
    cur = d.get("latest") or {}
    P.append(f'<text x="{L+470}" y="16" fill="{INK}" font-size="11.5">'
             f'{_esc(d.get("as_of"))}　P/C {cur.get("pc")}　250DMA {cur.get("ma250")}</text>')
    P.append(f'<text x="{L}" y="{H-6}" fill="#9a948a" font-size="10">'
             f'來源：{_esc(d.get("source"))}</text>')
    P.append('</svg>')
    return "".join(P)


def build():
    if not os.path.exists(SRC):
        return ("Put/Call Ratio", '<div class="dim">DATA_UNAVAILABLE：未跑 putcall.py</div>')
    with io.open(SRC, encoding="utf-8") as f:
        d = json.load(f)
    z = None
    if os.path.exists(ZSRC):
        try:
            with io.open(ZSRC, encoding="utf-8") as f:
                z = json.load(f)
        except (OSError, ValueError):
            z = None
    cur = d.get("latest") or {}
    ser = d.get("series") or []

    P = ['<h2>📉 Put/Call Ratio <small>CBOE Equity，250 日均線</small></h2>']
    P.append(f'<p class="crumb">資料日至 {_esc(d.get("as_of"))}｜'
             f'{len(ser)} 個交易日｜{len(d.get("climax") or [])} 個賣壓高峰標記</p>')

    pc, ma = cur.get("pc"), cur.get("ma250")
    ratio_txt = ""
    if pc and ma:
        ratio_txt = f"（{pc / ma:.2f}× 250 日均線）"
    P.append('<div class="pf-mini2"><table><thead><tr><th>今日</th>'
             '<th class="n">數值</th><th>判讀</th></tr></thead><tbody>')
    P.append(f'<tr><td>Equity P/C</td><td class="n">{pc}</td>'
             f'<td>{ratio_txt}</td></tr>')
    P.append(f'<tr><td>250 日均線</td><td class="n">{ma}</td>'
             f'<td>{"高於" if pc and ma and pc > ma else "低於"}均線 = '
             f'{"恐慌偏多" if pc and ma and pc > ma else "情緒偏貪"}</td></tr>')
    P.append(f'<tr><td>近 3 年百分位</td><td class="n">{cur.get("pct3y")}%</td>'
             f'<td>100% = 3 年來最高（最恐慌）</td></tr>')
    P.append(f'<tr><td>SPX</td><td class="n">{cur.get("spx")}</td>'
             f'<td>對照上圖</td></tr>')
    P.append('</tbody></table></div>')

    if z:
        st20 = (z.get("stats") or {}).get("fwd20") or {}
        st40 = (z.get("stats") or {}).get("fwd40") or {}
        b20 = (z.get("baseline") or {}).get("20") or {}
        b40 = (z.get("baseline") or {}).get("40") or {}
        verdict = "未見 edge"
        if st20.get("avg") is not None and b20.get("avg") is not None:
            if st20["avg"] - b20["avg"] > 0.5 and st20.get("win", 0) >= 60:
                verdict = "逆向區間有 edge（20 日）"
        P.append('<h3 style="margin-top:14px">散戶買 put 逆向區間（第 %s 百分位）</h3>' % z.get("pctile"))
        P.append('<div class="pf-mini2"><table><thead><tr><th>項目</th>'
                 '<th class="n">數值</th><th>對照基率</th></tr></thead><tbody>')
        P.append(f'<tr><td>門檻 P/C</td><td class="n">≥ {z.get("threshold")}</td>'
                 f'<td>全歷史第 {z.get("pctile")} 百分位（唔用絕對值）</td></tr>')
        P.append(f'<tr><td>今日</td><td class="n">{z.get("current_pc")}</td>'
                 f'<td>{"✅ 在區間內" if z.get("in_zone") else "未到門檻"}</td></tr>')
        P.append(f'<tr><td>事件數</td><td class="n">{z.get("n_events")}</td>'
                 f'<td>由下向上穿越，{z.get("cooldown")} 日冷卻</td></tr>')
        P.append(f'<tr><td>之後 20 日</td><td class="n">{st20.get("avg")}%（贏 {st20.get("win")}%）</td>'
                 f'<td>{b20.get("avg")}%（贏 {b20.get("win")}%）｜n={st20.get("n")}</td></tr>')
        P.append(f'<tr><td>之後 40 日</td><td class="n">{st40.get("avg")}%（贏 {st40.get("win")}%）</td>'
                 f'<td>{b40.get("avg")}%（贏 {b40.get("win")}%）｜n={st40.get("n")}</td></tr>')
        P.append(f'<tr><td><b>判決</b></td><td class="n">{verdict}</td>'
                 f'<td>{_esc(z.get("note"))}</td></tr>')
        P.append('</tbody></table></div>')

    P.append('<h3 style="margin-top:14px">圖表</h3>')
    P.append(_chart(d, z))

    P.append('<h3 style="margin-top:14px">最近 12 個交易日</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr><th>日期</th>'
             '<th class="n">P/C</th><th class="n">250DMA</th>'
             '<th class="n">偏離</th><th class="n">SPX</th></tr></thead><tbody>')
    for s in ser[-12:][::-1]:
        dev = (f'{s["pc"] / s["ma"]:.2f}×' if s.get("ma") else "—")
        P.append(f'<tr><td>{_esc(s["d"])}</td><td class="n">{s["pc"]}</td>'
                 f'<td class="n">{s["ma"] if s["ma"] is not None else "—"}</td>'
                 f'<td class="n">{dev}</td><td class="n">{s["spx"] or "—"}</td></tr>')
    P.append('</tbody></table></div>')

    P.append(f'<div class="pf-note">{_esc(d.get("rule"))}。'
             '讀法：P/C 衝高 = 買 put 的人多 = 恐慌；歷史上高峰常貼近 SPX 底部，'
             '所以豎線是「事後標記的賣壓高峰」，不是預測訊號。</div>')
    return ("Put/Call Ratio", "".join(P))


def main():
    t, b = build()
    print(f"{t} — {len(b):,} chars")


if __name__ == "__main__":
    main()
