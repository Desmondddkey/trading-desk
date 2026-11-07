# -*- coding: utf-8 -*-
"""sector_rot2_page.py — 行業輪動 v2（同一份數據，第二種睇法）

v1（sectorrot.html）：Rank Up/Down 卡 + 兩張排序表。
v2（呢頁）：熱力圖（11 行業 × 4 個時框）＋ 排名動能（3M 排名 vs 1M 排名）＋ 52 週高距離。

數據：output/sector_rot.json（sector_rot.py 平日 17:10 更新）
"""
from __future__ import annotations

import html as _h
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "output", "sector_rot.json")

SECTORS = ["XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLB", "XLU", "XLRE", "XLC"]

CSS = """
.s2-heat{display:grid;grid-template-columns:92px repeat(4,1fr);gap:2px;font-size:12px}
.s2-heat .h{font-size:10px;opacity:.55;font-weight:800;letter-spacing:.05em;
  padding:4px 6px;text-transform:uppercase}
.s2-cell{padding:7px 6px;border-radius:4px;text-align:right;font-variant-numeric:tabular-nums;
  font-weight:700;background:rgba(148,163,184,.08)}
.s2-name{padding:7px 6px;font-weight:800;font-size:12px;background:transparent}
.s2-tbl{width:100%;border-collapse:collapse;font-size:12px}
.s2-tbl th{text-align:left;font-size:10px;letter-spacing:.05em;opacity:.55;font-weight:800;
  padding:4px 7px;border-bottom:1px solid rgba(148,163,184,.25);white-space:nowrap}
.s2-tbl td{padding:3px 7px;border-bottom:1px solid rgba(148,163,184,.1);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.s2-tbl td.n,.s2-tbl th.n{text-align:right}
.s2-note{font-size:10.5px;opacity:.6;line-height:1.6;margin-top:8px}
.up{color:#2f8f5b;font-weight:700}.dn{color:#a04a44;font-weight:700}
"""


def _load():
    try:
        with io.open(SRC, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return None


def _heat_bg(v, mx):
    if v is None:
        return "rgba(148,163,184,.08)"
    a = min(0.85, 0.12 + abs(v) / max(mx, 0.01) * 0.7)
    return (f"rgba(47,143,91,{a:.2f})" if v > 0 else f"rgba(160,74,68,{a:.2f})")


def build():
    snap = _load()
    if not snap:
        return ("行業輪動 v2", '<div class="card"><div class="body">'
                                'DATA_UNAVAILABLE — 未跑 sector_rot.py。</div></div>')
    rows = snap.get("rows") or []
    by = {r["t"]: r for r in rows}
    sect = [by[t] for t in SECTORS if t in by]
    ind = [r for r in rows if r["t"] not in SECTORS]

    L = [f"<style>{CSS}</style>"]

    # ① 熱力圖
    mx = max([abs(r.get(k) or 0) for r in sect for k in ("r1d", "r1w", "r1m", "r3m")] or [1])
    L.append('<div class="card"><h2>行業熱力圖 <small>11 個行業 × 1D / 1W / 1M / 3M 回報</small></h2>'
             '<div class="body"><div class="s2-heat">')
    L.append('<div class="h"></div><div class="h">1 日</div><div class="h">1 週</div>'
             '<div class="h">1 月</div><div class="h">3 月</div>')
    for r in sect:
        L.append(f'<div class="s2-name">{_h.escape(r["t"])}</div>')
        for k in ("r1d", "r1w", "r1m", "r3m"):
            v = r.get(k)
            L.append(f'<div class="s2-cell" style="background:{_heat_bg(v, mx)}">'
                     f'{"" if v is None else f"{v:+.1f}%"}</div>')
    L.append('</div>')
    L.append('<div class="s2-note">顏色深淺 = 幅度（同一把尺）。綠 = 正回報，紅 = 負回報。'
             '睇「邊個時框開始轉」比重視單日更早。</div></div></div>')

    # ② 排名動能
    ind2 = [r for r in ind if r.get("rs_1m") is not None and r.get("rs_now") is not None]
    ind2.sort(key=lambda r: (r["rs_1m"] - r["rs_now"]), reverse=True)
    L.append('<div class="card"><h2>排名動能 <small>1 個月排名 − 3 個月排名（正 = 升緊）</small></h2>'
             '<div class="body"><div class="tscroll"><table class="s2-tbl"><thead><tr>'
             '<th>Ticker</th><th>Name</th><th class="n">3M 排</th><th class="n">1M 排</th>'
             '<th class="n">變化</th><th class="n">1M</th><th class="n">3M</th>'
             '<th class="n">距 52 高</th></tr></thead><tbody>')
    for r in ind2[:14]:
        d = r["rs_1m"] - r["rs_now"]
        cls = "up" if d > 0 else "dn" if d < 0 else ""
        L.append(f'<tr><td><b>{_h.escape(r["t"])}</b></td>'
                 f'<td style="opacity:.7">{_h.escape(r["n"])}</td>'
                 f'<td class="n">{int(r["rs_now"])}</td><td class="n">{int(r["rs_1m"])}</td>'
                 f'<td class="n {cls}">{d:+.0f}</td>'
                 f'<td class="n">{r["r1m"]:+.1f}%</td><td class="n">{r["r3m"]:+.1f}%</td>'
                 f'<td class="n">{r["d52"]:+.1f}%</td></tr>')
    L.append('</tbody></table></div>')
    L.append('<div class="s2-note">只列前 14（升幅最大）。排名係組內百分位，'
             '所以「3M 排 90、1M 排 40」= 曾經好強但已經轉弱。</div></div></div>')

    # ③ 距 52 週高
    L.append('<div class="card"><h2>距 52 週高 <small>越接近 0 越強</small></h2>'
             '<div class="body"><div class="tscroll"><table class="s2-tbl"><thead><tr>'
             '<th>Ticker</th><th>Name</th><th class="n">距 52 高</th><th class="n">1M</th>'
             '<th class="n">3M</th></tr></thead><tbody>')
    for r in sorted([x for x in rows if x.get("d52") is not None],
                    key=lambda x: x["d52"], reverse=True)[:12]:
        L.append(f'<tr><td><b>{_h.escape(r["t"])}</b></td>'
                 f'<td style="opacity:.7">{_h.escape(r["n"])}</td>'
                 f'<td class="n">{r["d52"]:+.1f}%</td>'
                 f'<td class="n">{r["r1m"]:+.1f}%</td>'
                 f'<td class="n">{r["r3m"]:+.1f}%</td></tr>')
    L.append('</tbody></table></div></div></div>')
    return ("行業輪動 v2", "".join(L))


if __name__ == "__main__":
    print(build()[0])
