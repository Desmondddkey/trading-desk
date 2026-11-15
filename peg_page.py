# -*- coding: utf-8 -*-
"""peg_page.py — PEG 清單（iain @ohiain 2026-11-14）：每季追蹤最強名單，
等佢哋回調到 9/21EMA 附近，再等一個可執行嘅進場點。

規則（來源帖文）
  1. 每季建立一次清單（唔係每日換）
  2. 追蹤最強（RS 高）嘅股票
  3. 標記並整合到 9 / 21EMA
  4. 等回調到 EMA 附近（距 9EMA／21EMA ≤ 1 ATR）＝ 可執行進場點
  5. 用明確風險執行（止蝕／股數由 screener 同一條規則）

數據：data/screener.json（screener_extra.py 已計 RS / d9 / d21 / atr / adr / dvol）
"""
from __future__ import annotations

import io
import json
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "screener.json")

SEED = ["U", "XYZ", "CVNA", "FROG", "ZETA", "APP", "GKOS", "REGN"]
MIN_RS = 85
MIN_ADR = 3.0
MIN_DVOL = 20.0
TOP_N = 30

CSS = """
.pg-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:0 0 4px}
.pg-head h2{margin:0;font-size:19px;font-weight:800}
.pg-meta{font-size:11px;opacity:.6}
.pg-rule{font-size:11.5px;line-height:1.85;opacity:.75;margin:6px 0 10px;max-width:900px}
.pg-tbl{width:100%;border-collapse:separate;border-spacing:0;font-size:12.5px}
.pg-tbl th{position:sticky;top:0;z-index:2;background:#0b1220;text-align:left;
  font-size:10.5px;font-weight:800;letter-spacing:.04em;opacity:.75;padding:6px 7px;
  border-bottom:1px solid rgba(148,163,184,.3);white-space:nowrap;cursor:pointer}
.pg-tbl td{padding:3px 7px;border-bottom:1px solid rgba(148,163,184,.10);
  white-space:nowrap;font-variant-numeric:tabular-nums}
html[data-theme="light"] .pg-tbl th{background:#f6f8fb}
.pg-tk{font-weight:800;text-decoration:none;color:inherit}
.pg-tk:hover{color:#f97316}
.pg-nm{max-width:230px;overflow:hidden;text-overflow:ellipsis;opacity:.75}
.pg-ready{color:#22c55e;font-weight:700}
.pg-note{font-size:10.5px;line-height:1.7;opacity:.62;margin-top:10px;max-width:900px}
.pg-seed{font-size:10px;border:1px solid rgba(59,130,246,.5);color:#3b82f6;
  border-radius:3px;padding:0 3px;margin-left:4px}
"""


def _load(p, d):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return d


def _q(d=None):
    d = d or date.today()
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


PQ = os.path.join(HERE, "data", "peg_quarter.json")


def _quarter_members(pick):
    """每季凍結一次名單：季內只更新價格／距離，唔換馬（帖文要求）。"""
    q = _q()
    try:
        d = json.load(io.open(PQ, encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if d.get("quarter") == q and d.get("members"):
        return set(d["members"]), q, True
    members = [r["t"] for r in pick]
    try:
        with io.open(PQ, "w", encoding="utf-8") as f:
            json.dump({"quarter": q, "members": members,
                       "created": date.today().isoformat()}, f,
                      ensure_ascii=False, indent=1)
    except OSError:
        pass
    return set(members), q, False


def build():
    d = _load(SRC, {})
    rows = d.get("rows") or []
    if not rows:
        return ("PEG 清單", "<p>DATA_UNAVAILABLE — 未跑 screener_cache.py / screener_extra.py</p>")

    pick = []
    for r in rows:
        rs = r.get("rs")
        if rs is None or rs < MIN_RS:
            continue
        if (r.get("adr") or 0) < MIN_ADR or (r.get("dvol_m") or 0) < MIN_DVOL:
            continue
        if r.get("close") is None:
            continue
        if r.get("above50") == 0:
            continue                                   # 跌穿 50MA 直接剔走
        pick.append(r)
    pick.sort(key=lambda x: (-(x.get("rs") or 0), abs(x.get("d21") or 99)))
    pick = pick[:TOP_N]
    members, q, frozen = _quarter_members(pick)
    by_t = {r["t"]: r for r in rows}
    sel = [by_t[t] for t in members if t in by_t]
    sel.sort(key=lambda x: (-(x.get("rs") or 0), abs(x.get("d21") or 99)))

    body = [f"<style>{CSS}</style>", '<div class="card">']
    body.append('<div class="pg-head"><h2>PEG 清單</h2>'
                f'<span class="pg-meta">{q}｜{len(sel)} 隻｜資料 {d.get("as_of")}'
                f'｜{"已凍結（季內唔換馬）" if frozen else "本季名單已建立"}</span></div>')
    body.append('<p class="pg-rule">'
                '每季建立一次：追蹤最強（RS ≥85）嘅股票，標記並整合到 9／21EMA，'
                '等佢哋回調到 EMA 附近（距 9EMA 或 21EMA ≤ 1 ATR）就是可執行進場點，'
                '再用明確風險（3% 上限／LOD、0.5% 風險）執行。<br>'
                '「可入場」＝現價距 9EMA 或 21EMA ≤ 0.5 ATR（貼線）；0.5–1.0 ATR＝接近；'
                '>1 ATR＝等回調。跌穿 50MA 直接剔走。'
                '</p>')

    body.append('<table class="pg-tbl"><thead><tr>'
                + "".join(f"<th>{h}</th>" for h in
                          ["代號", "名稱", "板塊", "價", "距9EMA", "距21EMA", "RS",
                           "距52高%", "ADR%", "成交額$M", "狀態"])
                + "</tr></thead><tbody>")
    for r in sel:
        d9, d21 = r.get("d9"), r.get("d21")
        near = min(abs(d9) if d9 is not None else 99, abs(d21) if d21 is not None else 99)
        seed = '<span class="pg-seed">帖文例子</span>' if r["t"] in SEED else ""
        if r.get("above50") == 0:
            state = "跌穿50MA"
        elif near <= 0.5:
            state = '<span class="pg-ready">可入場</span>'
        elif near <= 1.0:
            state = "接近"
        else:
            state = "等回調"
        body.append(
            f'<tr><td><a class="pg-tk" href="https://www.tradingview.com/chart/?symbol={r["t"]}"'
            f' target="_blank" rel="noopener" data-sym="{r["t"]}">{r["t"]}</a>{seed}</td>'
            f'<td class="pg-nm">{_esc(r.get("name"))}</td>'
            f'<td class="pg-nm">{_esc(r.get("industry") or r.get("sector"))}</td>'
            f'<td>{_n(r.get("close"), 2)}</td>'
            f'<td>{_n(d9, 2)}</td><td>{_n(d21, 2)}</td>'
            f'<td>{_n(r.get("rs"), 0)}</td><td>{_n(r.get("d52w"), 1)}</td>'
            f'<td>{_n(r.get("adr"), 1)}</td><td>{_n(r.get("dvol_m"), 0)}</td>'
            f'<td>{state}</td></tr>')
    body.append('</tbody></table>')
    body.append(
        '<p class="pg-note">① 距離單位＝ATR（0 = 貼住條線；+1 = 高 1 個 ATR）。'
        '② 名單每季更新；中間只更新價格同距離，唔會因為一日走勢換馬。'
        '③ 上表只列出 RS ≥85、ADR ≥3%、成交額 ≥$20M 嘅名單；'
        '剔走嘅係流動性／波幅不足，唔係睇淡。'
        '④ 止蝕／股數用 Stock Screener 同一條規則（3% 上限、LOD、0.5% 風險）。</p>')
    body.append('</div>')
    return ("PEG 清單", "".join(body))


def _n(v, d=1, plus=False):
    if v is None or v == "":
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    return f"{f:+.{d}f}" if plus else f"{f:.{d}f}"


def _esc(x):
    import html
    return html.escape(str(x if x is not None else ""))
