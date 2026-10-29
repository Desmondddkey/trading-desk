# -*- coding: utf-8 -*-
"""topwatch_page.py — 市場頂部觀察（數據自算，每日 build 時刷新）

Desmond 2026-10-30：把「美股見頂未」嘅判斷做成一個固定網站頁，
用 diagram-design 規格畫兩個圖：
  ① 五大指數距 52 週高（橫棒 + 50MA 標記）
  ② 標普觸發階梯（前高 / 橙線 / 200MA，現價一個點）

資料：yfinance 日線（1 年）＋ regime_live.json（MMTW／MMFI）
"""
from __future__ import annotations

import html as _h
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "docs", "regime_live.json")

IDX = [("^GSPC", "S&P 500"), ("^NDX", "Nasdaq 100"),
       ("^IXIC", "Nasdaq 綜指"), ("^DJI", "道瓊斯"),
       ("^RUT", "羅素 2000")]

PAPER, INK, MUTED, ACCENT, RULE = "#0f1115", "#e5e7eb", "#94a3b8", "#f97316", "#2a2f3a"


def _esc(x):
    return _h.escape(str(x))


def _data():
    import yfinance as yf
    out = {}
    for sym, name in IDX:
        try:
            d = yf.download(sym, period="2y", interval="1d", progress=False,
                            auto_adjust=False)
            if hasattr(d.columns, "levels"):
                d.columns = [c[0] for c in d.columns]
            d = d.dropna(subset=["Close"])
            c = d["Close"]
            px = float(c.iloc[-1])
            hi = float(c.tail(252).max())
            out[sym] = {"name": name, "px": px, "hi": hi,
                        "off": (px / hi - 1) * 100,
                        "ma50": float(c.tail(50).mean()),
                        "ma200": float(c.tail(200).mean())}
        except Exception:                                    # noqa: BLE001
            continue
    return out


def _bars(data):
    """① 距 52 週高棒圖：0 = 前高，向左延伸到 −15%。"""
    W, rowH, top = 660, 42, 30
    H = top + rowH * len(data) + 24
    lab, right = 120, 150
    x0, x1 = lab, W - right
    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-width:560px;max-width:{W}px" '
         f'role="img" aria-labelledby="tw1"><title id="tw1">五大指數距 52 週高</title>']
    P.append(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
    for pct in (-15, -10, -5, 0):
        x = x1 + pct / 15 * (x1 - x0)
        P.append(f'<line x1="{x:.1f}" y1="{top-14}" x2="{x:.1f}" y2="{H-22}" '
                 f'stroke="{RULE}" stroke-width="1" stroke-dasharray="2 4"/>')
        P.append(f'<text x="{x:.1f}" y="{H-8}" fill="{MUTED}" font-size="10" '
                 f'text-anchor="middle">{pct}%</text>')
    for i, (sym, v) in enumerate(data.items()):
        y = top + i * rowH
        w = max(2.0, abs(v["off"]) / 15 * (x1 - x0))
        P.append(f'<text x="0" y="{y+14}" fill="{INK}" font-size="12">{_esc(v["name"])}</text>')
        P.append(f'<rect x="{x1-w:.1f}" y="{y+3}" width="{w:.1f}" height="15" rx="2" '
                 f'fill="{ACCENT}" fill-opacity="0.75"/>')
        _pxtxt = f'{v["px"]:,.0f}'
        P.append(f'<text x="{x1+8}" y="{y+15}" fill="{INK}" font-size="11">'
                 f'{v["off"]:+.1f}%　{_pxtxt}</text>')
    P.append('</svg>')
    return "".join(P)


def _ladder(spx):
    """② 標普觸發階梯：前高 / 橙線 / 200MA + 現價。"""
    if not spx:
        return ""
    hi, px, ma200 = spx["hi"], spx["px"], spx["ma200"]
    trig = 7612.0                       # 2026-10-23 低點（Claude 提出嘅箱體下沿）
    lo = min(ma200, trig) * 0.985
    top = hi * 1.008
    W, H = 660, 300
    y0, y1 = 30, H - 40

    def Y(v):
        return y1 - (v - lo) / (top - lo) * (y1 - y0)

    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-width:560px;max-width:{W}px" '
         f'role="img" aria-labelledby="tw2"><title id="tw2">標普觸發階梯</title>']
    P.append(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
    for val, lab, col, dash in ((hi, f'前高 {hi:,.0f}', MUTED, "4 4"),
                                (trig, f'橙線 {trig:,.0f}', ACCENT, ""),
                                (ma200, f'200MA {ma200:,.0f}', "#ef4444", "2 4")):
        y = Y(val)
        P.append(f'<line x1="150" y1="{y:.1f}" x2="{W-120}" y2="{y:.1f}" stroke="{col}" '
                 f'stroke-width="1.4" stroke-dasharray="{dash}"/>')
        P.append(f'<text x="0" y="{y+4:.1f}" fill="{col}" font-size="11.5">{_esc(lab)}</text>')
    yp = Y(px)
    P.append(f'<circle cx="{W-100}" cy="{yp:.1f}" r="6" fill="#22c55e"/>')
    P.append(f'<text x="{W-100}" y="{yp-12:.1f}" fill="#22c55e" font-size="12" '
             f'text-anchor="middle">{px:,.0f}</text>')
    P.append(f'<line x1="150" y1="{yp:.1f}" x2="{W-110}" y2="{yp:.1f}" '
             f'stroke="#22c55e" stroke-width="1" stroke-opacity="0.35"/>')
    P.append('</svg>')
    return "".join(P)


def build():
    data = _data()
    reg = {}
    try:
        with io.open(REG, encoding="utf-8") as f:
            reg = json.load(f)
    except Exception:                                        # noqa: BLE001
        pass
    spx = data.get("^GSPC")
    mmtw, mmfi = reg.get("mmtw"), reg.get("mmfi")

    P = ['<h2>🏔 頂部觀察 <small>唔預測，只定觸發</small></h2>']
    P.append('<p class="crumb">由 yfinance 日線即時計｜每次 build 更新｜'
             '黃／橙／紅三級觸發寫死，唔准事後改</p>')

    P.append('<div class="pf-mini2"><table><thead><tr><th>指標</th>'
             '<th class="n">現值</th><th>判讀</th></tr></thead><tbody>')
    P.append(f'<tr><td>MMTW（% above 20MA）</td><td class="n">'
             f'{mmtw if mmtw is not None else "—"}</td>'
             f'<td>{"中性" if (mmtw or 0) >= 50 else "偏弱"}</td></tr>')
    P.append(f'<tr><td>MMFI（% above 50MA）</td><td class="n">'
             f'{mmfi if mmfi is not None else "—"}</td>'
             f'<td>{"轉弱" if (mmfi or 0) < 45 else "健康"}</td></tr>')
    if spx:
        P.append(f'<tr><td>標普 vs 50MA</td><td class="n">'
                 f'{(spx["px"]/spx["ma50"]-1)*100:+.1f}%</td>'
                 f'<td>{"守住" if spx["px"] > spx["ma50"] else "失守"}</td></tr>')
    P.append('</tbody></table></div>')

    P.append('<h3 style="margin-top:16px">① 五大指數距 52 週高</h3>')
    P.append(_bars(data))
    P.append('<div class="pf-note">棒越短 = 越貼前高。'
             '全部仍在 200MA 之上 = 未確認熊市。</div>')

    P.append('<h3 style="margin-top:16px">② 標普觸發階梯</h3>')
    P.append(_ladder(spx))
    P.append('<div class="pf-note">綠點 = 現價。跌穿橙線 = 倉位減半；'
             '跌穿 200MA = 全清。</div>')

    P.append('<h3 style="margin-top:16px">③ 觸發規則</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr><th>級別</th><th>觸發</th>'
             '<th>動作</th></tr></thead><tbody>')
    P.append('<tr><td style="color:#eab308;font-weight:700">🟡 黃</td>'
             '<td>Nasdaq 連續 5 日低於 50MA ＋ MMFI &lt; 40%</td>'
             '<td>只做 A+；油門維持 0.2%</td></tr>')
    P.append('<tr><td style="color:#f97316;font-weight:700">🟠 橙</td>'
             '<td>S&amp;P 收市跌破 7,612</td><td>倉位 × 0.5；停開新倉</td></tr>')
    P.append('<tr><td style="color:#ef4444;font-weight:700">🔴 紅</td>'
             '<td>S&amp;P 收市跌破 200MA 或 VIX &gt; 30</td>'
             '<td>全清，等廣度修復</td></tr>')
    P.append('</tbody></table></div>')
    P.append('<div class="pf-note">現況：黃燈已亮（納指在 50MA 之下、MMFI 41%），'
             '橙燈未到。呢頁只列條件，唔會替你決定。</div>')
    return ("頂部觀察", "".join(P))


def main():
    t, b = build()
    print(f"{t} — {len(b):,} chars")


if __name__ == "__main__":
    main()
