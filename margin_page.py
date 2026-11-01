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
    """照原圖重畫：淺底、左軸 0.4–1.8、右軸 200–800、粉色回撤帶、虛線引線標註。"""
    q = d.get("qqq_daily") or []
    s = d.get("series") or []
    if len(q) < 60 or not s:
        return '<div class="dim">DATA_UNAVAILABLE</div>'

    W, H = 1400, 900
    L, R = 96, 112
    TOP, BOT = 96, 590          # 上圖區域
    BAR_T, BAR_B = 660, 800     # 下圖柱區域
    PAPER, INK, MUTED = "#fdfbf7", "#2b2b2b", "#8a8279"
    ORANGE, GREY, BAND = "#c2743a", "#5b6472", "#f6e2e2"

    dates = [x["d"] for x in q]
    n = len(dates)

    def X(i):
        return L + (W - L - R) * (i / max(1, n - 1))

    def YD(v):                  # 債務 0.4–1.8
        return BOT - (v - 0.4) / (1.8 - 0.4) * (BOT - TOP)

    def YQ(v):                  # QQQ 200–800
        return BOT - (v - 200) / (800 - 200) * (BOT - TOP)

    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-width:900px;max-width:{W}px;'
         f'background:{PAPER}" role="img" aria-labelledby="mg-title">'
         f'<title id="mg-title">保證金債務 × QQQ（2022–2026）</title>']
    P.append(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')

    # 粉色回撤帶（跨兩個面板）
    for st, tr, en, pct in (d.get("drawdowns") or []):
        try:
            i0 = dates.index(st) if st in dates else next(i for i, x in enumerate(dates) if x >= st)
            i1 = (dates.index(en) if en and en in dates
                  else next((i for i, x in enumerate(dates) if en and x >= en), n - 1))
        except Exception:                                    # noqa: BLE001
            continue
        x0, x1 = X(i0), X(i1)
        P.append(f'<rect x="{x0:.1f}" y="{TOP-10}" width="{max(2, x1-x0):.1f}" '
                 f'height="{BAR_B-TOP+10}" fill="{BAND}" fill-opacity="0.55"/>')
        if x1 - x0 > 46:
            P.append(f'<text x="{(x0+x1)/2:.1f}" y="{TOP+18}" fill="#b4483f" '
                     f'font-size="15" text-anchor="middle">{pct:.1f}%</text>')

    # 網格 + 左軸（債務）
    for v in (0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8):
        y = YD(v)
        P.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" '
                 f'stroke="#e7e1d8" stroke-width="1"/>')
        P.append(f'<text x="{L-12}" y="{y+5:.1f}" fill="{MUTED}" font-size="15" '
                 f'text-anchor="end">{v:.1f}</text>')
    # 右軸（QQQ）
    for v in (200, 300, 400, 500, 600, 700, 800):
        y = YQ(v)
        P.append(f'<text x="{W-R+12}" y="{y+5:.1f}" fill="{MUTED}" font-size="15">{v}</text>')

    # 年份刻度
    seen = set()
    for i, dd in enumerate(dates):
        y = dd[:4]
        if y not in seen and dd[5:7] == "01" and i > 0:
            seen.add(y)
            P.append(f'<line x1="{X(i):.1f}" y1="{BOT}" x2="{X(i):.1f}" y2="{BOT+8}" '
                     f'stroke="#cfc7bb"/>')
            P.append(f'<text x="{X(i):.1f}" y="{BAR_B+30}" fill="{MUTED}" font-size="15" '
                     f'text-anchor="middle">{y}</text>')

    # QQQ 線
    pts = " ".join(f"{X(i):.1f},{YQ(x['c']):.1f}" for i, x in enumerate(q))
    P.append(f'<polyline points="{pts}" fill="none" stroke="{GREY}" stroke-width="1.5"/>')

    # 債務線（月度對齊到該月最後交易日）
    mpts = []
    for x in s:
        idxs = [i for i, dd in enumerate(dates) if dd.startswith(x["ym"])]
        if idxs:
            mpts.append(f"{X(idxs[-1]):.1f},{YD(x['debit_tn']):.1f}")
    P.append(f'<polyline points="{" ".join(mpts)}" fill="none" stroke="{ORANGE}" '
             f'stroke-width="3"/>')

    # 註解（虛線引線 + 文字）
    def note(date_str, text, dx=0, dy=-26, anchor="start"):
        try:
            i = dates.index(date_str) if date_str in dates else \
                next(j for j, x in enumerate(dates) if x >= date_str)
        except Exception:                                    # noqa: BLE001
            return
        x, y = X(i), YQ(q[i]["c"])
        P.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x+dx:.1f}" y2="{y+dy:.1f}" '
                 f'stroke="#b9b1a5" stroke-width="1" stroke-dasharray="3 3"/>')
        P.append(f'<text x="{x+dx:.1f}" y="{y+dy-6:.1f}" fill="#6b6257" font-size="15" '
                 f'text-anchor="{anchor}">{_esc(text)}</text>')

    note("2022-12-28", "2022.12 低點 260.10", dx=40, dy=34, anchor="start")
    note(d.get("qqq_date", ""), f'QQQ {d.get("qqq_last")}', dx=-96, dy=30, anchor="end")
    if d.get("peak_ym"):
        pk = [x for x in s if x["ym"] == d["peak_ym"]]
        if pk:
            i = next((j for j, dd in enumerate(dates) if dd.startswith(d["peak_ym"])), None)
            if i:
                P.append(f'<text x="{X(i)-12:.1f}" y="{YD(pk[-1]["debit_tn"])-18:.1f}" '
                         f'fill="{ORANGE}" font-size="15" text-anchor="end">'
                         f'{d["peak_ym"]} 高點 {d["peak_tn"]:.3f}</text>')
    last = s[-1]
    i_last = next((j for j, dd in enumerate(dates) if dd.startswith(last["ym"])), n - 1)
    P.append(f'<text x="{X(i_last)-10:.1f}" y="{YD(last["debit_tn"])+22:.1f}" '
             f'fill="{ORANGE}" font-size="15" text-anchor="end">'
             f'{last["ym"]} {last["debit_tn"]:.3f}</text>')

    # 下圖：月度增減
    vals = [(x["ym"], x["mom_tn"]) for x in s if x["mom_tn"] is not None]
    if vals:
        mx = max(abs(v) for _, v in vals) or 1
        mid = (BAR_T + BAR_B) / 2
        P.append(f'<line x1="{L}" y1="{mid:.1f}" x2="{W-R}" y2="{mid:.1f}" '
                 f'stroke="#cfc7bb"/>')
        bw = (W - L - R) / max(1, len(vals))
        for k, (ym, v) in enumerate(vals):
            idxs = [i for i, dd in enumerate(dates) if dd.startswith(ym)]
            if not idxs:
                continue
            cx = X(idxs[-1])
            h = abs(v) / mx * (BAR_B - BAR_T) / 2 * 0.9
            y = mid - h if v > 0 else mid
            col = "#a3b18a" if v > 0 else "#c0605a"
            P.append(f'<rect x="{cx-bw*0.32:.1f}" y="{y:.1f}" width="{bw*0.64:.1f}" '
                     f'height="{max(h,1.5):.1f}" fill="{col}" rx="1"/>')
        P.append(f'<text x="{L-12}" y="{BAR_T+12}" fill="{MUTED}" font-size="14" '
                 f'text-anchor="end">+{mx*1000:.0f}十億</text>')
        P.append(f'<text x="{L-12}" y="{BAR_B}" fill="{MUTED}" font-size="14" '
                 f'text-anchor="end">−{mx*1000:.0f}十億</text>')

    # 標題
    P.append(f'<text x="{L}" y="46" fill="{INK}" font-size="24" font-weight="700">'
             f'QQQ × 保證金債務：槓桿的收縮與回補</text>')
    P.append(f'<text x="{L}" y="72" fill="{MUTED}" font-size="15">2022–2026｜'
             f'QQQ 日收市至 {_esc(d.get("qqq_date"))}｜FINRA 月度債務至 '
             f'{_esc(d.get("as_of"))}</text>')
    P.append(f'<text x="{W-R}" y="46" fill="{ORANGE}" font-size="30" font-weight="800" '
             f'text-anchor="end">{d["level_tn"]:.3f} 萬億美元</text>')
    P.append(f'<text x="{W-R}" y="72" fill="{MUTED}" font-size="15" text-anchor="end">'
             f'{_esc(d["as_of"])} 保證金債務｜距 6 月高位 {d["from_peak_pct"]:+.1f}%</text>')
    P.append(f'<line x1="{L+470}" y1="72" x2="{L+504}" y2="72" stroke="{ORANGE}" '
             f'stroke-width="3"/>')
    P.append(f'<text x="{L+510}" y="77" fill="{MUTED}" font-size="14">保證金債務</text>')
    P.append(f'<line x1="{L+594}" y1="72" x2="{L+628}" y2="72" stroke="{GREY}" '
             f'stroke-width="1.5"/>')
    P.append(f'<text x="{L+634}" y="77" fill="{MUTED}" font-size="14">QQQ</text>')
    P.append(f'<rect x="{L+680}" y="64" width="16" height="10" fill="{BAND}"/>')
    P.append(f'<text x="{L+702}" y="77" fill="{MUTED}" font-size="14">回撤≥7%</text>')
    P.append(f'<text x="{L}" y="{BAR_T-14}" fill="{INK}" font-size="16">'
             f'保證金債務月度增減（負值 = 融資收縮）</text>')
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
