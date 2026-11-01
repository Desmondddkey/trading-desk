# -*- coding: utf-8 -*-
"""margin_page.py — 保證金債務 × QQQ（RAE 重建版，讀 output/margin_debt.json）"""
from __future__ import annotations

import datetime as dt
import html as _h
import io
import json
import os

SRC = r"C:/Users/rain0/trading-os/output/margin_debt.json"
PAPER, INK, MUTED, ORANGE, RULE = "#0f1115", "#e5e7eb", "#94a3b8", "#c2743a", "#2a2f3a"


def _esc(x):
    return _h.escape(str(x if x is not None else ""))


def _chart(d):
    q = d.get("qqq_daily") or []
    s = d.get("series") or []
    if len(q) < 60 or not s:
        return '<div class="dim">DATA_UNAVAILABLE</div>'

    W, H = 940, 380
    L, R, T, B = 54, 58, 22, 34
    qs = [x["c"] for x in q]
    qmin, qmax = min(qs), max(qs)
    ms = [x["debit_tn"] for x in s]
    mmin, mmax = min(ms), max(ms)

    def X(i, n):
        return L + (W - L - R) * (i / max(1, n - 1))

    def YQ(v):
        return T + (H - T - B) * (1 - (v - qmin) / max(1e-9, qmax - qmin))

    def YM(v):
        return T + (H - T - B) * (1 - (v - mmin) / max(1e-9, mmax - mmin))

    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-width:700px;max-width:{W}px" '
         f'role="img" aria-labelledby="mg-title"><title id="mg-title">'
         f'保證金債務與 QQQ</title>']
    P.append(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')

    # 陰影：QQQ 回撤 ≥7%
    ddays = [x["d"] for x in q]
    for st, tr, en, pct in (d.get("drawdowns") or []):
        try:
            i0 = ddays.index(st) if st in ddays else next(i for i, x in enumerate(ddays) if x >= st)
            i1 = (ddays.index(en) if en and en in ddays
                  else next((i for i, x in enumerate(ddays) if en and x >= en), len(ddays) - 1))
            P.append(f'<rect x="{X(i0, len(q)):.1f}" y="{T}" '
                     f'width="{max(2, X(i1, len(q)) - X(i0, len(q))):.1f}" '
                     f'height="{H-T-B}" fill="#ef4444" fill-opacity="0.07"/>')
        except Exception:                                    # noqa: BLE001
            continue

    # QQQ 線
    pts = " ".join(f"{X(i, len(q)):.1f},{YQ(v):.1f}" for i, v in enumerate(qs))
    P.append(f'<polyline points="{pts}" fill="none" stroke="#9aa8bd" stroke-width="1.3"/>')

    # 債務線（月度 → 對齊到該月最後一個交易日）
    mpts = []
    for x in s:
        ym = x["ym"]
        idxs = [i for i, dd in enumerate(ddays) if dd.startswith(ym)]
        if idxs:
            mpts.append(f"{X(idxs[-1], len(q)):.1f},{YM(x['debit_tn']):.1f}")
    P.append(f'<polyline points="{" ".join(mpts)}" fill="none" stroke="{ORANGE}" '
             f'stroke-width="2.2"/>')

    # 軸標
    P.append(f'<text x="{L-6}" y="{T+10}" fill="{ORANGE}" font-size="10.5" '
             f'text-anchor="end">{mmax:.2f}</text>')
    P.append(f'<text x="{L-6}" y="{H-B}" fill="{ORANGE}" font-size="10.5" '
             f'text-anchor="end">{mmin:.2f}</text>')
    P.append(f'<text x="{W-6}" y="{T+10}" fill="{MUTED}" font-size="10.5" '
             f'text-anchor="end">{qmax:,.0f}</text>')
    P.append(f'<text x="{W-6}" y="{H-B}" fill="{MUTED}" font-size="10.5" '
             f'text-anchor="end">{qmin:,.0f}</text>')
    P.append(f'<text x="{L}" y="{H-10}" fill="{MUTED}" font-size="9.5">{ddays[0]}</text>')
    P.append(f'<text x="{W-R}" y="{H-10}" fill="{MUTED}" font-size="9.5" '
             f'text-anchor="end">{ddays[-1]}</text>')
    P.append(f'<text x="{L}" y="{T-6}" fill="{ORANGE}" font-size="10">'
             f'橙線 = FINRA 保證金債務（月度，萬億）</text>')
    P.append(f'<text x="{L+250}" y="{T-6}" fill="{MUTED}" font-size="10">'
             f'灰線 = QQQ 收市｜紅影 = 回撤 ≥7%</text>')
    P.append('</svg>')
    return "".join(P)


def _bars(d):
    s = d.get("series") or []
    if not s:
        return ""
    vals = [x["mom_tn"] for x in s if x["mom_tn"] is not None]
    if not vals:
        return ""
    mx = max(abs(v) for v in vals) or 1
    W, H = 940, 110
    bw = (W - 40) / len(vals)
    mid = H / 2
    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px" '
         f'role="img" aria-label="月度增減"><rect width="{W}" height="{H}" fill="{PAPER}"/>']
    P.append(f'<line x1="20" y1="{mid}" x2="{W-20}" y2="{mid}" stroke="{RULE}"/>')
    for i, v in enumerate(vals):
        h = abs(v) / mx * (mid - 12)
        x = 20 + i * bw + bw * 0.15
        y = mid - h if v > 0 else mid
        col = "#a3b18a" if v > 0 else "#c0605a"
        P.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw*0.7:.1f}" '
                 f'height="{max(h,1):.1f}" fill="{col}" rx="1.5"/>')
    P.append('</svg>')
    return "".join(P)


def build():
    if not os.path.exists(SRC):
        return ("保證金債務", '<div class="dim">DATA_UNAVAILABLE</div>')
    with io.open(SRC, encoding="utf-8") as f:
        d = json.load(f)
    r = d.get("recovery") or {}

    P = ['<h2>💳 保證金債務 × QQQ <small>槓桿的收縮與回補</small></h2>']
    P.append(f'<p class="crumb">資料：FINRA 官方 xlsx（月度，{_esc(d["as_of"])}）｜'
             f'QQQ {_esc(d["qqq_date"])} 收 {d["qqq_last"]}｜'
             '每週自動重算（FINRA 每月中更新）</p>')

    P.append('<div class="pf-mini2"><table><thead><tr>'
             '<th>保證金債務</th><th class="n">數值</th><th>意義</th></tr></thead><tbody>')
    P.append(f'<tr><td>{_esc(d["as_of"])} 餘額</td>'
             f'<td class="n">{d["level_tn"]:.3f} 萬億</td>'
             f'<td>環比 {d["mom_pct"]:+.1f}%（{d["mom_tn"]*1000:+.0f} 億）</td></tr>')
    P.append(f'<tr><td>歷史高位</td><td class="n">{d["peak_tn"]:.3f} 萬億</td>'
             f'<td>{_esc(d["peak_ym"])}；現距峰 {d["from_peak_pct"]:+.1f}%</td></tr>')
    if r:
        P.append(f'<tr><td>本輪回撤</td>'
                 f'<td class="n">{r["drop_pct"]:+.2f}%</td>'
                 f'<td>{_esc(r["peak_ym"])} 峰 → {_esc(r["trough_ym"])} 底</td></tr>')
        P.append(f'<tr><td>回補比例</td>'
                 f'<td class="n">{r["recovered_pct"]}%</td>'
                 f'<td>{"未完全回補" if (r["recovered_pct"] or 0) < 100 else "已回補"}</td></tr>')
    P.append('</tbody></table></div>')

    P.append('<h3 style="margin-top:14px">債務 vs QQQ</h3>')
    P.append(_chart(d))
    P.append('<h3 style="margin-top:10px">月度增減（負 = 去槓桿）</h3>')
    P.append(_bars(d))

    P.append('<h3 style="margin-top:14px">歷史收縮事件（月度跌幅 ≥4%）</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr><th>月份</th>'
             '<th class="n">跌幅</th><th class="n">水平</th></tr></thead><tbody>')
    for x in (d.get("shrinks") or [])[-6:]:
        P.append(f'<tr><td>{_esc(x["ym"])}</td>'
                 f'<td class="n" style="color:#ef4444">{x["pct"]:+.2f}%</td>'
                 f'<td class="n">{x["level"]:.3f} 萬億</td></tr>')
    P.append('</tbody></table></div>')

    P.append('<h3 style="margin-top:14px">QQQ 主要回撤（≥7%）</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr><th>開始</th><th>底部</th>'
             '<th>收復</th><th class="n">跌幅</th></tr></thead><tbody>')
    for st, tr, en, pct in (d.get("drawdowns") or [])[-5:]:
        P.append(f'<tr><td>{_esc(st)}</td><td>{_esc(tr)}</td>'
                 f'<td>{_esc(en) if en else "未收復"}</td>'
                 f'<td class="n" style="color:#ef4444">{pct}%</td></tr>')
    P.append('</tbody></table></div>')

    P.append('<div class="pf-note">判讀（同原圖一致）：<b>唔可以因為 QQQ 下跌就話槓桿已清</b>。'
             '要等 FINRA 下一期債務數據（每月中公布）才知 10 月回調有冇伴隨去槓桿。</div>')
    P.append(f'<div class="pf-note">來源與限制：{_esc(d.get("source"))}｜'
             f'{_esc(d.get("rule"))}｜FINRA 為全市場客戶保證金（非 QQQ 專屬），'
             '所以只可以當「整體槓桿」背景，唔可以逐隻股對應。</div>')
    return ("保證金債務", "".join(P))


def main():
    t, b = build()
    print(f"{t} — {len(b):,} chars")


if __name__ == "__main__":
    main()
