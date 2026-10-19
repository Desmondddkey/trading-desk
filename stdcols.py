#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stdcols.py — 統一所有列表嘅欄位（Desmond 2026-10-11「統一所有列表顯示內容」）

問題（改動前實測）：
```
頁          第一欄        RS-D/W  Kell  1CM  延伸  ADR%  成交額  距52高  ATR帶  X/Y
briefing    代號            ✗      ✗    ✗    ✗     ✗     ✗      ✗     ✓    ✓
leaders     代號 / 行業      ✓      ✓    ✗    ✓     ✓     ✓      ✓     ✗    ✗
week        代號 / 行業      ✗      ✗    ✗    ✓     ✓     ✓      ✓     ✗    ✗
setups      代號            ✗      ✗    ✗    ✗     ✗     ✗      ✗     ✓    ✓
method      代號            ✗      ✗    ✗    ✗     ✗     ✗      ✗     ✗    ✗
cm          代號            ✗      ✗    ✓    ✗     ✗     ✗      ✗     ✗    ✗
```
→ 同一個概念（例如「距 52 週高」）喺唔同頁有唔同顯示，讀者冇可能比較。

★ 統一規格（所有股票表都用呢套）：
```
第一欄   代號 / 行業     ← 永遠係「代號（連結 TV）+ 灰色行業」兩行
RS 欄    RS-D, RS-W      ← 比率迷你圖（比率 = 股價 ÷ SPY，50 bar）
表現欄   1週, 1月, 3月, 6月, 1年
風險欄   延伸（ATRX 倍數）, ADR%, 距52週高
量能欄   成交額
位置欄   X（21EMA）, Y（ATRX）, ATR 帶
分類欄   疊加, Kell 階段, 1CM 評級
```
唔同頁可以**少幾欄**（例如 method 冇 X/Y），但**同一欄嘅定義同格式必須完全一樣**。
"""
import html
import re as _html


def esc(s):
    return _html.escape(str(s if s is not None else ""))


def num(v, d=1):
    try:
        return f"{float(v):,.{d}f}"
    except (TypeError, ValueError):
        return "—"


def pct(v, d=1):
    try:
        return f"{float(v):+,.{d}f}%"
    except (TypeError, ValueError):
        return "—"


def money(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    for cut, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(v) >= cut:
            return f"{v/cut:,.1f}{suf}"
    return f"{v:,.0f}"


def tone(v, invert=False):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "dim"
    good = (v < 0) if invert else (v > 0)
    return "pos" if good else ("neg" if v else "dim")


# ── 標準表頭 ─────────────────────────────────────────────────
# key → (顯示文字, 對齊)
STD_HEADS = [
    ("rank",     "#"),
    ("name",     "代號 / 行業"),
    ("close",    "收市"),
    ("watch_f",  "買入線"),
    ("inv_f",    "失效線"),
    ("rsd",      "RS-D"),
    ("rsw",      "RS-W"),
    ("1w",       "1週"),
    ("1m",       "1月"),
    ("3m",       "3月"),
    ("6m",       "6月"),
    ("1y",       "1年"),
    ("ext",      "延伸"),
    ("adr",      "ADR%"),
    ("dvol",     "成交額"),
    ("off52",    "距52週高"),
    ("x",        "X（21EMA）"),
    ("y",        "Y（ATRX）"),
    ("band",     "ATR 帶"),
    ("stack",    "疊加"),
    ("kell",     "Kell 階段"),
    ("cm",       "1CM 評級"),
]


def head_html(keys, first_left=True):
    """按 keys 次序砌 <tr> 表頭。"""
    out = []
    for k in keys:
        lbl = dict(STD_HEADS).get(k, k)
        cls = ' class="l"' if (k == "name" and first_left) else ""
        out.append(f"<th{cls}>{lbl}</th>")
    return "<tr>" + "".join(out) + "</tr>"


# ── 標準儲存格 ───────────────────────────────────────────────
def cell(key, r, ctx):
    """砌一格。

    ctx 係一個 dict，可以帶：
      rs_map   {sym: {}}      RS 迷你圖數據
      kstage   {sym: {}}      Kell 階段
      cmres    {sym: {}}      1CM 評級
      i        排名（由 0 起）
    全部 optional —— 冇就出 —，唔會爆。
    """
    if key == "rank":
        return f"<td>{ctx.get('i', 0) + 1}</td>"
    if key == "name":
        sym = r.get("symbol") or r.get("ticker") or r.get("etf") or "?"
        ind = r.get("industry") or r.get("sector") or r.get("name") or ""
        link = ctx.get("tv_link")
        t = link(sym, ind) if link else esc(sym)
        return (f'<td class="l"><span class="tk">{t}</span>'
                f'<div class="dim" style="font-size:10.5px">{esc(ind)}</div></td>')
    if key == "close":
        return f'<td>{num(r.get("close"), 2)}</td>'
    if key in ("watch_f", "inv_f"):
        v = r.get("watch_price") if key == "watch_f" else r.get("invalidation")
        lbl = "買入線" if key == "watch_f" else "失效線"
        return f'<td class="l">{esc(v) if v else "—"}</td>'
    if key in ("watch_p", "inv_p"):
        # ★ 2026-10-19：手機上長句把表格擠爆 → 只顯示數字，原文入 title
        raw = r.get("watch_price") if key == "watch_p" else r.get("invalidation")
        px = _first_num(raw)
        if px is None:
            return '<td>—</td>'
        cls = "" if key == "watch_p" else "dim"
        return (f'<td class="{cls}" title="{esc(raw or "")}">'
                f'{px:,.2f}</td>')
    if key in ("rsd", "rsw"):
        col = ctx.get("rs_col")
        rs = (ctx.get("rs_map") or {}).get(r.get("symbol") or r.get("ticker"), {})
        return col(rs) if col else "<td>—</td>"
    if key in ("1w", "1m", "3m", "6m", "1y"):
        p = r.get("perf") or {}
        v = p.get(key) if isinstance(p, dict) else r.get(key)
        return f'<td class="{tone(v)}">{pct(v)}</td>'
    if key == "ext":
        return f"<td>{num(r.get('extension'), 2)}×</td>"
    if key == "adr":
        return f"<td>{pct(r.get('adr'), 1)}</td>"
    if key == "dvol":
        return f"<td>{money(r.get('dvol'))}</td>"
    if key == "off52":
        return f'<td class="{tone(r.get("off52w"), invert=True)}">{pct(r.get("off52w"), 1)}</td>'
    if key == "x":
        return f'<td class="{tone(r.get("x"))}">{num(r.get("x"), 2)}</td>'
    if key == "y":
        return f"<td>{num(r.get('y'), 2)}</td>"
    if key == "band":
        band = ctx.get("band_svg")
        return f"<td>{band(r.get('y') or 0)}</td>" if band else "<td>—</td>"
    if key == "stack":
        return f"<td>{num(r.get('stack'), 0)}</td>"
    if key == "kell":
        k = ctx.get("kell")
        d = (ctx.get("kstage") or {}).get(r.get("symbol") or r.get("ticker"))
        return f"<td>{k.chip(r.get('symbol') or r.get('ticker'), d) if k else '—'}</td>"
    if key == "cm":
        c = ctx.get("cm")
        d = (ctx.get("cmres") or {}).get(r.get("symbol") or r.get("ticker"))
        return f"<td>{c.chip(r.get('symbol') or r.get('ticker'), d) if c else '—'}</td>"
    return "<td>—</td>"


def row_html(keys, r, ctx, i=0):
    c = dict(ctx)
    c["i"] = i
    return "<tr>" + "".join(cell(k, r, c) for k in keys) + "</tr>"


def table_html(keys, rows, ctx, empty="—"):
    """完整表（thead + tbody）。"""
    body = "".join(row_html(keys, r, ctx, i) for i, r in enumerate(rows))
    if not body:
        body = f'<tr><td colspan="{len(keys)}" class="dim">{esc(empty)}</td></tr>'
    return (f"<div class=\"scroll\"><table><thead>{head_html(keys)}</thead>"
            f"<tbody>{body}</tbody></table></div>")


# ── 常用欄位組合 ─────────────────────────────────────────────
SET_FULL = ["rank", "name", "rsd", "rsw", "1w", "1m", "3m", "6m", "1y",
            "ext", "adr", "dvol", "off52", "kell", "cm"]
SET_WEEK = ["rank", "name", "rsd", "rsw", "1w", "1m", "3m", "ext", "adr",
            "dvol", "off52", "kell", "cm"]
SET_POS = ["name", "x", "y", "band", "stack", "kell", "cm"]
SET_PLAN = ["name", "close", "x", "y", "band", "kell", "cm"]
STD_CSS = """
.stdnote{font-size:11.5px;color:#8fa3c8;margin:6px 0 0;line-height:1.7}
"""
