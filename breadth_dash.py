# -*- coding: utf-8 -*-
"""breadth_dash.py — 廣度 × 期望值 Dashboard（Market Regime 用）

內容
  ① MMTW / MMFI 兩條電平（同頁頂數字一致，唔另計）
  ② 升跌比 4 分組 → EV(R) / 勝率 / n 嘅橫向棒圖
  ③ 今日升跌比 vs 歷史分位 → 一句判決
  ④ 相關係數（負 = 越高越差）

資料
  docs/regime_live.json  → mmtw / mmfi
  output/mm_edge.json    → 分組 EV（mm_edge.py 產出）
  data/scan_prices.pkl   → 今日升跌比
"""
from __future__ import annotations

import html as _h
import io
import json
import os
import pickle

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = r"C:/Users/rain0/trading-os"
REG = os.path.join(HERE, "docs", "regime_live.json")
EDGE = os.path.join(LIVE, "output", "mm_edge.json")


def _load(p):
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return None


def _today_ratio():
    """由 scan_prices 計最新一日升跌比（同 mm_edge 同一把尺）。"""
    try:
        with io.open(os.path.join(HERE, "data", "scan_prices.pkl"), "rb") as f:
            px = pickle.load(f)
        up = dn = 0
        for _, bars in px.items():
            if len(bars) < 2:
                continue
            c0, c1 = float(bars[-2][4]), float(bars[-1][4])
            if not c0:
                continue
            chg = (c1 / c0 - 1) * 100
            if chg >= 4:
                up += 1
            elif chg <= -4:
                dn += 1
        return up, dn, (up / max(1, dn))
    except Exception:                                        # noqa: BLE001
        return None, None, None


def _meter(label, val, colour, note):
    v = max(0.0, min(100.0, float(val))) if val is not None else 0.0
    return (f'<div style="flex:1;min-width:230px">'
            f'<div style="font-size:11px;opacity:.62;font-weight:700;'
            f'letter-spacing:.04em">{_h.escape(label)}</div>'
            f'<div style="font-size:26px;font-weight:800;color:{colour};'
            f'line-height:1.15">{v:.1f}%</div>'
            f'<div style="height:7px;background:rgba(148,163,184,.22);'
            f'border-radius:4px;margin:6px 0 4px"><span style="display:block;'
            f'height:7px;width:{v:.1f}%;background:{colour};border-radius:4px">'
            f'</span></div>'
            f'<div style="font-size:10.5px;opacity:.6">{_h.escape(note)}</div>'
            f'</div>')


def _bars(by_ratio, corr):
    if not by_ratio:
        return '<div class="dim">DATA_UNAVAILABLE</div>'
    order = sorted(by_ratio.items(), key=lambda kv: kv[0])
    evs = [v["ev"] for _, v in order if v.get("ev") is not None]
    lo, hi = min(evs + [0]), max(evs + [0])
    rng = (hi - lo) or 0.1
    W, rowH = 700, 44
    lab_w, zero, right = 96, 300, 176   # 左標籤 / 0R 位置 / 右邊文字區
    span = zero - lab_w - 8             # 負值可用寬度
    H = rowH * len(order) + 30
    P = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="min-width:560px;max-width:{W}px" '
         f'role="img" aria-label="升跌比 vs 期望值">']
    P.append(f'<line x1="{zero}" y1="6" x2="{zero}" y2="{H-18}" '
             f'stroke="#475569" stroke-width="1" stroke-dasharray="3 3"/>')
    P.append(f'<text x="{zero}" y="{H-4}" fill="#94a3b8" font-size="10" '
             f'text-anchor="middle">0R</text>')
    for i, (k, v) in enumerate(order):
        y = 14 + i * rowH
        ev = v.get("ev") or 0.0
        w = abs(ev) / rng * span * 0.9
        col = "#22c55e" if ev > 0 else "#ef4444"
        x = zero if ev >= 0 else zero - w
        P.append(f'<text x="0" y="{y+13}" fill="#cbd5e1" font-size="11.5">'
                 f'{_h.escape(k)}</text>')
        P.append(f'<rect x="{x:.1f}" y="{y+2}" width="{max(w,2):.1f}" height="16" '
                 f'fill="{col}" fill-opacity="0.9" rx="2"/>')
        P.append(f'<text x="{zero+10}" y="{y+14}" fill="#e2e8f0" font-size="11">'
                 f'{ev:+.2f}R　n={v.get("n")}　勝 {v.get("wr")}%</text>')
    P.append('</svg>')
    corr_txt = (f'相關係數 {corr:+.3f}（負 = 升跌比越高，期望值越差）'
                if isinstance(corr, (int, float)) else '')
    return "".join(P) + f'<div style="font-size:10.5px;opacity:.6;margin-top:2px">{corr_txt}</div>'


def card_html() -> str:
    reg = _load(REG) or {}
    edge = _load(EDGE) or {}
    mmtw, mmfi = reg.get("mmtw"), reg.get("mmfi")
    up, dn, ratio = _today_ratio()

    out = ['<div class="card"><h2>📊 廣度 × 期望值 '
           '<small>升跌比越高，突破期望值越差</small></h2>'
           '<div style="padding:12px 14px">']
    out.append('<div style="display:flex;gap:18px;flex-wrap:wrap;margin-bottom:10px">')
    out.append(_meter("MMTW（% above 20MA）", mmtw,
                      "#22c55e" if (mmtw or 0) >= 50 else "#f59e0b", "短線廣度"))
    out.append(_meter("MMFI（% above 50MA）", mmfi,
                      "#22c55e" if (mmfi or 0) >= 50 else "#f97316", "中期參與度"))
    if ratio is not None:
        col = "#ef4444" if ratio > 3.7 else ("#f59e0b" if ratio > 1.6 else "#22c55e")
        out.append(f'<div style="flex:1;min-width:200px">'
                   f'<div style="font-size:11px;opacity:.62;font-weight:700;'
                   f'letter-spacing:.04em">今日升跌比（4%）</div>'
                   f'<div style="font-size:26px;font-weight:800;color:{col};'
                   f'line-height:1.15">{ratio:.2f}</div>'
                   f'<div style="font-size:10.5px;opacity:.6">升 {up} 隻／跌 {dn} 隻'
                   f'（scan 277 隻宇宙）</div></div>')
    out.append('</div>')

    out.append('<div style="font-size:11px;opacity:.62;font-weight:700;'
               'letter-spacing:.04em;margin:6px 0 2px">'
               '升跌比分組 → 10 日期望值（1 ATR 止蝕・T+1 開盤）</div>')
    out.append(_bars(edge.get("by_ratio") or {}, edge.get("corr")))
    out.append('<div class="pf-note" style="margin-top:8px">'
               f'樣本 {edge.get("n", 0)} 筆／{edge.get("days", 0)} 個交易日。'
               '升跌比用 scan 宇宙計，唔係全美股；同日多股高度相關，'
               '有效樣本遠少於 n。<b>未經樣本外測試，屬假設。</b></div>')
    out.append('</div></div>')
    return "".join(out)
