# -*- coding: utf-8 -*-
"""fatpitch_page.py — 肥球掃描頁（J Law 式單一事件錯價）

顯示：① 系統性風險閘門 ② 今日掃描全部標的（含唔合格原因）
     ③ 回測統計（誠實標示未證實）
"""
from __future__ import annotations

import html as _h
import io
import json
import os
import datetime as _dt

DATA = r"C:/Users/rain0/trading-os/output"


def _load(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return None
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return None


def _esc(x):
    return _h.escape(str(x if x is not None else ""))


def render_html() -> str:
    d = _load("fat_pitch.json") or {}
    bt = _load("fat_pitch_backtest.json") or {}
    rows = d.get("rows") or []
    vix = d.get("vix") or {}
    gate = d.get("gate_systemic")
    passed = [r for r in rows if r.get("pass")]

    P = []
    P.append('<h2>🎯 肥球掃描 <small>J Law：等一個賠率明顯站在我這邊的機會</small></h2>')

    # ① 閘門
    gtxt = "✅ 可以搵肥球" if gate else "🛑 系統性風險 → 今日唔做"
    P.append('<div class="pf-mini2"><table><thead><tr><th>系統性風險閘</th>'
             '<th class="n">VIX</th><th class="n">VIX 單日</th>'
             '<th class="n">合格候選</th><th>判定</th></tr></thead><tbody>')
    P.append(f'<tr><td>VIX&lt;30 且 單日&lt;+20%</td>'
             f'<td class="n">{vix.get("vix", "—")}</td>'
             f'<td class="n">{vix.get("vix_chg", "—")}%</td>'
             f'<td class="n">{len(passed)} / {d.get("n_scanned", 0)}</td>'
             f'<td>{gtxt}</td></tr></tbody></table></div>')

    # ② 今日表
    if rows:
        P.append('<div class="pf-mini2" style="margin-top:10px"><table><thead><tr>'
                 '<th>代號</th><th class="n">跳空%</th><th class="n">z</th>'
                 '<th class="n">σ%</th><th class="n">現價</th>'
                 '<th class="n">止蝕 1ATR</th><th class="n">目標 50%回補</th>'
                 '<th class="n">R:R</th><th>狀態</th></tr></thead><tbody>')
        for r in rows[:24]:
            st = "✅ 候選" if r.get("pass") else _esc(r.get("reason"))
            P.append('<tr>'
                     f'<td><a class="tv" data-sym="{_esc(r["ticker"])}" '
                     f'href="https://www.tradingview.com/chart/?symbol={_esc(r["ticker"])}" '
                     f'target="_blank" rel="noopener">{_esc(r["ticker"])}</a></td>'
                     f'<td class="n">{r.get("gap_pct")}</td>'
                     f'<td class="n">{r.get("z")}</td>'
                     f'<td class="n">{r.get("sigma_pct")}</td>'
                     f'<td class="n">{r.get("px")}</td>'
                     f'<td class="n">{r.get("stop", "—")}</td>'
                     f'<td class="n">{r.get("target", "—")}</td>'
                     f'<td class="n">{r.get("rr", "—")}</td>'
                     f'<td>{st}</td></tr>')
        P.append('</tbody></table></div>')
    else:
        P.append('<div class="dim">DATA_UNAVAILABLE — 未跑掃描</div>')

    # ③ 回測
    if bt:
        v = bt.get("verdict", "—")
        col = "#22c55e" if v == "有 edge" else "#f97316"
        P.append('<h3 style="margin-top:16px">回測（5 年・同一規則）</h3>')
        P.append('<div class="pf-mini2"><table><thead><tr>'
                 '<th class="n">n</th><th class="n">平均 R</th>'
                 '<th class="n">中位 R</th><th class="n">t</th>'
                 '<th class="n">勝率</th><th class="n">贏輸比</th>'
                 '<th>判決</th></tr></thead><tbody>')
        P.append(f'<tr><td class="n">{bt.get("n")}</td>'
                 f'<td class="n">{bt.get("mean_r")}</td>'
                 f'<td class="n">{bt.get("median_r")}</td>'
                 f'<td class="n">{bt.get("t")}</td>'
                 f'<td class="n">{bt.get("wr")}%</td>'
                 f'<td class="n">{bt.get("payoff")}</td>'
                 f'<td style="color:{col};font-weight:700">{_esc(v)}</td></tr>')
        P.append('</tbody></table></div>')
        P.append('<div class="pf-note">判準事先寫死：n ≥ 30、平均 R &gt; +0.10、'
                 't ≥ 1.96 才算「有 edge」。目前 t ≈ 1.01 → <b>未證實</b>，'
                 '所以只作觀察，唔會自動入場。</div>')

    P.append('<div class="pf-note">入場：跳空 ≤ −5% 且 z ≤ −2.5，系統性風險過濾通過 → 開盤入。'
             '出場：回補 50% 跳空 ／ 跌 1 ATR ／ 5 日時間停。'
             '呢個規則嘅弱點：機械過濾捉唔到「催化劑係唔係一次性」——'
             '而後者正係 J Law 嘅核心判斷。</div>')
    return "".join(P)
