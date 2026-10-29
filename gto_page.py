# -*- coding: utf-8 -*-
"""gto_page.py — GTO 手牌分析頁（Daily Scan 選股 EV 分桶）"""
from __future__ import annotations

import html as _h
import io
import json
import os

SRC = r"C:/Users/rain0/trading-os/output/gto_daily.json"

LABELS = [
    ("by_src", "來源（FOCUS vs STALK）", "Focus 同 Stalk 係兩個唔同嘅手牌類別，唔可以混為一談。"),
    ("by_x", "X = (價 − 21EMA) / ATR14", "X < 0 = 喺 21EMA 之下（回調）；X ≥ 2 = 遠離均線（追高）。"),
    ("by_dist", "距 52 週高", "買喺高位（0～−3%）定係買深度回調，歷史上差別最大。"),
    ("by_ext", "EXT = (價 − 50MA) / ATR14", "離 50 日均線幾多個 ATR。"),
    ("by_rvol", "RVOL（當日成交量 / 50 日均量）", "爆量追入嘅結果。"),
    ("by_tight", "TIGHT（10 日箱體收縮）", "≥70 樣本太少，只列唔判。"),
    ("by_dow", "星期幾", "同一個 range 按星期分層。"),
]


def _esc(x):
    return _h.escape(str(x if x is not None else ""))


def render_html() -> str:
    if not os.path.exists(SRC):
        return '<div class="dim">DATA_UNAVAILABLE</div>'
    with io.open(SRC, encoding="utf-8") as f:
        d = json.load(f)
    b = d.get("base") or {}
    P = ['<h2>🎲 GTO 手牌分析 <small>Daily Scan 選股 EV</small></h2>']
    P.append(f'<p class="crumb">樣本 {d.get("n_obs")} 筆／{d.get("n_days")} 個交易日｜'
             f'入場 T+1 開盤｜止蝕 1 ATR（R 分母下限 0.5%）｜'
             f'持有 {d["criteria"]["hold_days"]} 日｜判準 n≥{d["criteria"]["min_n"]}、'
             f'EV≥+{d["criteria"]["min_ev"]}R、t≥{d["criteria"]["t_crit"]}</p>')

    P.append('<div class="pf-mini2"><table><thead><tr><th>基準（全部候選）</th>'
             '<th class="n">n</th><th class="n">EV(R)</th><th class="n">勝率</th>'
             '<th class="n">贏輸比</th><th class="n">t</th><th>判定</th></tr></thead><tbody>')
    P.append(f'<tr><td>全部</td><td class="n">{b.get("n")}</td>'
             f'<td class="n">{b.get("ev_r"):+.2f}</td><td class="n">{b.get("wr")}%</td>'
             f'<td class="n">{b.get("rr")}</td><td class="n">{b.get("t"):+.2f}</td>'
             f'<td>{_esc(b.get("play"))}</td></tr></tbody></table></div>')

    for key, title, note in LABELS:
        g = d.get(key) or {}
        if not g:
            continue
        P.append(f'<h3 style="margin-top:16px">{_esc(title)}</h3>')
        P.append('<div class="pf-mini2"><table><thead><tr><th>類別</th>'
                 '<th class="n">n</th><th class="n">EV(R)</th><th class="n">勝率</th>'
                 '<th class="n">贏輸比</th><th class="n">Kelly</th>'
                 '<th class="n">倉%</th><th class="n">t</th><th>判定</th>'
                 '</tr></thead><tbody>')
        for k, v in g.items():
            if not v:
                continue
            col = "#22c55e" if v["play"] == "打" else ("#f97316" if v["play"] == "觀察" else "#94a3b8")
            P.append(f'<tr><td>{_esc(k)}</td><td class="n">{v["n"]}</td>'
                     f'<td class="n">{v["ev_r"]:+.2f}</td>'
                     f'<td class="n">{v["wr"]}%</td>'
                     f'<td class="n">{v["rr"]}</td>'
                     f'<td class="n">{v["kelly"]:+.2f}</td>'
                     f'<td class="n">{v["size_pct"]}</td>'
                     f'<td class="n">{v["t"]:+.2f}</td>'
                     f'<td style="color:{col};font-weight:700">{v["play"]}</td></tr>')
        P.append('</tbody></table></div>')
        P.append(f'<div class="pf-note">{_esc(note)}</div>')

    P.append('<div class="pf-note">⚠️ 只有 16 個交易日樣本，同一日多隻股高度相關 —— '
             '呢啲數字係<b>假設</b>，唔係已證實 edge。要向前累積到每格 n≥30 再判。</div>')
    return "".join(P)
