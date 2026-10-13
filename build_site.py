#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_site.py — 交易台網站產生器（NEL 逆向工程之後嘅 Desmond 繁體版）

架構（跟 NEL：細 HTML ＋ 大 JSON ＋ 一支 JS 渲染器；但呢度全部 inline，
所以 file:// 同 GitHub Pages 都開得，唔需要 server）：

    data/*.json  ──┐
    trading-os output ──┤→ build_site.py → site/index.html（單檔）
    lab output    ──┘                   → site/desk.html（我嘅交易台）
                                        → site/assets/(css,js,json)

分頁（v1 已接真數據）
  🖥 交易台      我原本嗰個 dashboard（位置圖／輪動／風險／日期回溯）
  📋 簡報        Regime ＋ 廣度 ＋ 最強主題 ＋ 今日圖表隊列
  🚀 領導股      NEL 等效掃描（全市場，參考 i-manage-risk/NEL）
  ⚡ 最強 1 週    流動性達標之中，本週最強
  📊 RS 板       ETF 群組相對強度板
  🧩 方法分類    Layer1+2 每個選股方法各自一個清單
  🌀 成長週期    Growth Cycle（未接，見 STATUS）
  📐 Setups      每日計劃卡（未接，見 STATUS）

⚠ 資料來源全部唯讀；呢個腳本只寫自己嘅 site/。
"""
import argparse
import datetime
import glob
import io
import json
import math
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SITE = os.path.join(HERE, "docs")
LIVE = r"C:\Users\rain0\trading-os"
LAB = r"C:\Users\rain0\trading-os-lab"
sys.path.insert(0, LIVE)
sys.path.insert(0, LAB)

import charts  # noqa: E402  （迷你 K 線牆，純 Python SVG）
import extras  # noqa: E402  （RS 板全表＋成長週期，跟圖片實現）
import stdcols as _std  # noqa: E402  （Item 2：統一所有列表欄位）
import tvhover  # noqa: E402  （Item 8：hover 代號彈 TradingView 圖）
import nel_pages as _np  # noqa: E402  （Item 1：NEL 五頁蒸餾）

EN_LABELS = {"desk": "Opportunity", "briefing": "Market Brief", "leaders": "Leaders",
             "week": "Week Strongest", "rsboard": "RS Board", "method": "Methods",
             "cycle": "Growth Cycle", "setups": "Setups"}

TABS = [
    ("desk", "🖥", "機會", "desk.html"),
    ("briefing", "📋", "市場簡報", None),
    ("leaders", "🚀", "領導股", None),
    ("cm", "🎯", "1CM 回調", None),
    ("week", "⚡", "最強 1 週", None),
    ("themes", "🧩", "Themes", None),
    ("sectors", "🏭", "Sectors", None),
    ("breadth", "🌊", "Breadth", None),
    ("positioning", "🎯", "Positioning", None),
    ("review", "⏪", "Review", None),
    ("rsboard", "📊", "RS 板", None),
    ("method", "🧩", "方法分類", None),
    ("cycle", "🌀", "成長週期", None),
    ("setups", "📐", "Setups", None),
]


def log(*a):
    print(*a, flush=True)


# ── Python 版格式化（同名同義嘅 JS 版本喺 JS 字串度，兩邊要一致）──
def _fin(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def num(v, d=1):
    return f"{v:,.{d}f}" if _fin(v) else "—"


def sgn(v, d=1):
    return ("+" if v > 0 else "") + f"{v:,.{d}f}" if _fin(v) else "—"


def pct(v, d=1):
    return (("+" if v > 0 else "") + f"{v:,.{d}f}%") if _fin(v) else "—"


def esc(v):
    return (str("" if v is None else v)
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def money(v):
    if not _fin(v):
        return "—"
    if v >= 1e9:
        return f"${v/1e9:,.1f}B"
    if v >= 1e6:
        return f"${v/1e6:,.1f}M"
    if v >= 1e3:
        return f"${v/1e3:,.0f}K"
    return f"${v:,.0f}"


def bar(v, mx, neg=False):
    """橫向長條（同 JS 版 bar() 同意義：最長 60px）。"""
    if not _fin(v):
        return ""
    w = max(2, min(60, abs(v) / (mx or 1) * 60))
    return (f'<span class="bar{" neg" if neg else ""}" '
            f'style="width:{w:.0f}px;opacity:.8"></span>')


def tone(v):
    return "pos" if _fin(v) and v > 0 else ("neg" if _fin(v) and v < 0 else "dim")


LIGHT_MAP = {"🟢": '<span style="color:#16a34a;font-weight:700">●</span>',
             "🔴": '<span style="color:#dc2626;font-weight:700">●</span>',
             "🟠": '<span style="color:#f59e0b;font-weight:700">●</span>',
             "🟡": '<span style="color:#eab308;font-weight:700">●</span>'}


def light(v):
    s = str(v)
    return LIGHT_MAP.get(s, esc(s))


def tv_link(ticker, name=""):
    """代號 → TradingView 連結。

    Item 8：`data-sym` 係 hover 彈 widget 用嘅（TradingView 要 `EXCHANGE:SYMBOL`
    或者裸 symbol；裸 symbol 會自動揀，所以照傳代號）。
    """
    t = str(ticker).strip().upper()
    if not t or t in ("—", "N/A"):
        return esc(str(ticker))
    url = f"https://www.tradingview.com/chart/?symbol={t}"
    return (f'<a class="tv" href="{url}" target="_blank" rel="noopener" '
            f'data-sym="{esc(t)}" '
            f'title="{esc(name or t)} — hover 睇圖｜click 開 TradingView">'
            f'{esc(t)}<span class="tvs">↗</span></a>')


def render_insight(reg):
    """把 market_insight JSON 轉做乾淨表格（唔再 raw dump —— 修亂碼）。"""
    bt = reg.get("breadth") or {}
    lx = reg.get("ix_lights") or {}
    ix = "　".join(f'<b>{esc(k)}</b> {light(lx.get(k, "—"))}'
                   for k in ("SPY", "QQQ", "IWM"))
    lines = [
        ("日期", reg.get("date")),
        ("指數燈", ix),
        ("站上 20/50/200MA",
         f'{num(bt.get("above20"))}% / {num(bt.get("above50"))}% / {num(bt.get("above200"))}%'),
        ("新高 / 新低", f'{num(bt.get("new_highs"), 0)} / {num(bt.get("new_lows"), 0)}'),
        ("廣度判斷", esc(reg.get("breadth_note") or "—")),
        ("領導", esc((reg.get("lead") or {}).get("text") or "—")),
        ("VIX", esc(reg.get("vix_note") or "—")),
    ]
    rows = "".join(f'<tr><td class="l" style="color:#64748b;white-space:nowrap">{k}</td>'
                   f'<td class="l">{v}</td></tr>' for k, v in lines if v)
    return f'<table>{rows}</table>'


def render_breadth(b):
    """把 breadth JSON 轉做乾淨表格（修亂碼）。"""
    po = b.get("posture") or {}
    lines = [
        ("資料", esc(b.get("as_of") or "—")),
        ("範圍", esc(b.get("universe") or "—")),
        ("Regime", esc(po.get("regime") or "—")),
        ("Posture", esc(po.get("posture") or "—")),
        ("備註", esc("；".join(po.get("notes") or []))),
        ("多空比", num(po.get("ls_ratio"), 2)),
        ("ADL", num(po.get("adl"), 1)),
        ("新高新低淨值", num(po.get("nnnl"), 1)),
        ("站上 40MA", f'{num(po.get("pct40ma"))}%'),
    ]
    rows = "".join(f'<tr><td class="l" style="color:#64748b;white-space:nowrap">{k}</td>'
                   f'<td class="l">{v}</td></tr>' for k, v in lines if v)
    return f'<table>{rows}</table>'



def jload(p, default=None):
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return default


def newest(pattern):
    fs = sorted(glob.glob(pattern))
    return fs[-1] if fs else None


# ═══════════════════════ ① 市場掃描（NEL 等效）═══════════════════════
def load_scan():
    return jload(os.path.join(DATA, "market_scan.json"))


# ═══════════════════════ ② 簡報 ═══════════════════════
def load_briefing():
    out = {"date": datetime.date.today().isoformat()}
    # 市場狀態：market_insight_<YYYYMMDD>.json（唯一實作：layer3b_market_insight.py）
    p = newest(os.path.join(LIVE, "output", "market_insight_*.json"))
    if p:
        out["regime"] = jload(p) or {}
        out["regime_src"] = os.path.basename(p)
    # 廣度歷史（breadth_<date>.json）
    p2 = newest(os.path.join(LIVE, "output", "breadth_*.json"))
    if p2:
        d = jload(p2) or {}
        out["breadth"] = {k: d.get(k) for k in
                          ("as_of", "universe", "regime", "posture", "status",
                           "pct40ma", "ls_ratio_proxy", "spy_close")}
        out["breadth_src"] = os.path.basename(p2)
    # 今日圖表隊列（rs_select，圖示用）
    rs = jload(os.path.join(LIVE, "output",
                            f"rs_select_{datetime.date.today().isoformat()}.json"))
    if not rs:
        p3 = newest(os.path.join(LIVE, "output", "rs_select_*.json"))
        rs = jload(p3) if p3 else None
        out["rs_src"] = os.path.basename(p3) if p3 else None
    else:
        out["rs_src"] = f"rs_select_{datetime.date.today().isoformat()}.json"
    if rs:
        rows = [r for r in rs.get("rows", []) if r.get("gate_pass")]
        rows.sort(key=lambda r: (-(r.get("stack_n") or 0), abs(r.get("x") or 0)))
        out["queue"] = [{"t": r["ticker"], "x": r.get("x"), "y": r.get("y"),
                         "box": r.get("in_buy_box"), "stack": r.get("stack_n"),
                         "close": r.get("close")} for r in rows[:24]]
    return out


# ═══════════════════════ ③ RS 板（ETF 群組）═══════════════════════
def spark_svg(vals, w=86, h=22):
    vals = [v for v in vals if _fin(v)]
    if len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    rg = (mx - mn) or 1
    pts = [f"{i/(len(vals)-1)*w:.0f},{h-(v-mn)/rg*h:.0f}"
           for i, v in enumerate(vals)]
    col = "#4ade80" if vals[-1] >= vals[0] else "#f87171"
    return (f'<svg width="{w}" height="{h}" style="vertical-align:middle">'
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="{col}" '
            f'stroke-width="1.5"/></svg>')


def cycle_svg(series, w=920, h=280):
    """成長週期圖：比率（綠線）＋ 上軌／下軌（灰線）＋ 軌內陰影（藍）。"""
    ratio = series["ratio"]
    up = series["up"]
    dn = series["dn"]
    n = len(ratio)
    lo = min(dn)
    hi = max(up)
    rg = (hi - lo) or 1
    pad = 12

    def X(i):
        return pad + i / (n - 1) * (w - 2 * pad)

    def Y(v):
        return pad + (1 - (v - lo) / rg) * (h - 2 * pad)

    def pts(s):
        return " ".join(f"{X(i):.0f},{Y(v):.0f}" for i, v in enumerate(s))

    band = (" ".join(f"{X(i):.0f},{Y(up[i]):.0f}" for i in range(n)) + " " +
            " ".join(f"{X(n - 1 - i):.0f},{Y(dn[n - 1 - i]):.0f}" for i in range(n)))
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" '
            f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
            f'<polygon points="{band}" fill="#2563eb" opacity=".12"/>'
            f'<polyline points="{pts(up)}" fill="none" stroke="#8ea0bf" stroke-width="1.2"/>'
            f'<polyline points="{pts(dn)}" fill="none" stroke="#8ea0bf" stroke-width="1.2"/>'
            f'<polyline points="{pts(ratio)}" fill="none" stroke="#22c55e" stroke-width="1.8"/>'
            f'</svg>')


def rs_table(rows):
    """RS 板表（指數／群組／板塊共用）。"""
    mx = max((abs(r["ex1m"]) for r in rows), default=1) or 1
    out = []
    for i, r in enumerate(rows):
        out.append(
            f'<tr><td>{i+1}</td><td class="l"><span class="tk">{tv_link(r["etf"], r["name"])}</span> '
            f'<span class="dim">{esc(r["name"])}</span></td>'
            f'<td><b>{r["thrust"]:.0f}%</b></td>'
            f'<td class="l">{spark_svg(r["spark"])}</td>'
            f'<td class="l">{bar(r["ex1m"], mx, r["ex1m"] < 0)} '
            f'<span class="{tone(r["ex1m"])}">{sgn(r["ex1m"],1)}%</span></td>'
            f'<td>{r["pct"]}</td>'
            f'<td>{pct(r["off52w"],1)}</td></tr>')
    return "".join(out)


def load_rsboard():
    """ETF 群組 RS 板。定義寫死喺度，唔准事後改：
       RS Thrust Rate % = 最近 30 個交易日之中，ETF 21 日回報贏 SPY 嘅比例
       1-Mth RS %       = 1 個月超額回報嘅百分位排名
       %Intraday/%1D    = 同上一收市比（呢度用最新兩支）
       %1M / %Off52WH   = 1 個月回報 ／ 距 52 週高
    """
    import rotation_map as R
    import pandas as pd
    try:
        d = R.fetch()
    except Exception as e:                                   # noqa: BLE001
        log(f"⚠ RS 板冇數據：{e}")
        return None
    try:
        spy = d["SPY"].dropna(subset=["Close"])["Close"]
    except Exception:                                        # noqa: BLE001
        return None
    spy1m = float(spy.iloc[-1] / spy.iloc[-22] - 1) * 100
    rows = []
    for name, tk, sector in R.IND:
        try:
            c = d[tk].dropna(subset=["Close"])["Close"]
        except Exception:                                    # noqa: BLE001
            continue
        if len(c) < 70:
            continue
        r1 = c / c.shift(21) - 1
        s1 = spy / spy.shift(21) - 1
        tail = min(30, len(r1) - 1)
        thrust = float((r1.iloc[-tail:] > s1.iloc[-tail:]).mean() * 100)
        r1m = float(c.iloc[-1] / c.iloc[-22] - 1) * 100
        r1d = float(c.iloc[-1] / c.iloc[-2] - 1) * 100
        hh = float(c.tail(252).max())
        spark = [round(float(v), 1) for v in (r1 - s1).tail(30).tolist()
                 if math.isfinite(v)]
        rows.append({"name": name, "etf": tk, "sector": sector,
                     "thrust": round(thrust, 0), "ex1m": round(r1m - spy1m, 1),
                     "r1m": round(r1m, 1), "r1d": round(r1d, 2),
                     "off52w": round((float(c.iloc[-1]) / hh - 1) * 100, 1) if hh else None,
                     "spark": spark})
    if not rows:
        return None
    rows.sort(key=lambda r: (-r["thrust"], -r["ex1m"]))
    ex = sorted(r["ex1m"] for r in rows)
    for r in rows:
        r["pct"] = round(sum(1 for v in ex if v <= r["ex1m"]) / len(ex) * 100)
    return {"as_of": str(d.index.max().date()), "rows": rows, "spy1m": round(spy1m, 1)}


# ═══════════════════════ ④ 方法分類（Layer1+2）═══════════════════════
def band_svg(y, w=230, h=18):
    """ATR 帶（−3 到 +5）：買入區 0..+4 綠、過度延伸 >4 紅、低於 0 灰。
    位置點跟區上色：綠＝買入區、橙＝延伸、紅＝低於 0。"""
    lo, hi = -3.0, 5.0

    def X(v):
        return (v - lo) / (hi - lo) * w
    y = max(lo, min(hi, y))
    z = X(0.0)
    four = X(4.0)
    mark = X(y)
    pos_col = "#22c55e" if 0 <= y <= 4 else ("#f59e0b" if y > 4 else "#ef4444")
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" '
            f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
            f'<rect x="{z:.0f}" y="2" width="{four-z:.0f}" height="{h-4}" '
            f'fill="#22c55e" opacity=".20"/>'
            f'<rect x="{four:.0f}" y="2" width="{X(hi)-four:.0f}" height="{h-4}" '
            f'fill="#ef4444" opacity=".12"/>'
            f'<line x1="{z:.0f}" y1="1" x2="{z:.0f}" y2="{h-1}" stroke="#8ea0bf" stroke-width="1"/>'
            f'<line x1="{four:.0f}" y1="1" x2="{four:.0f}" y2="{h-1}" '
            f'stroke="#f59e0b" stroke-width="1" stroke-dasharray="3 2"/>'
            f'<circle cx="{mark:.0f}" cy="{h/2:.0f}" r="3.5" fill="{pos_col}"/>'
            f'</svg>')


def load_setups():
    """The Plan：讀 rs_select 快照嘅 gate-pass 名單，砌 ATR 帶＋買入／失效線。"""
    p = os.path.join(LIVE, "output",
                     f"rs_select_{datetime.date.today().isoformat()}.json")
    if not os.path.exists(p):
        p = newest(os.path.join(LIVE, "output", "rs_select_*.json"))
    rs = jload(p) if p else None
    if not rs:
        return None
    rows = [r for r in rs.get("rows", []) if r.get("gate_pass")]
    rows.sort(key=lambda r: (-(r.get("stack_n") or 0), abs(r.get("x") or 0)))
    return {"src": os.path.basename(p), "rows": rows}


def load_methods():
    """Layer2 快照裏面每個方法各自一個清單。

    L2 產物結構：focus_list / stalk_list，每行有 bucket、score、reasons、
    watch_price、invalidation。呢度照原樣分組，唔重新判斷。
    """
    p = None
    for f in sorted(glob.glob(os.path.join(LIVE, "output", "layer2_*.json"))):
        b = os.path.basename(f)
        if b.startswith("layer2_") and b[7:15].isdigit():
            p = f
    if not p:
        return None
    d = jload(p) or {}
    out = {"src": os.path.basename(p), "as_of": d.get("as_of"), "groups": []}
    for bucket, label in (("focus_list", "Focus（重點）"), ("stalk_list", "Stalk（觀察）")):
        items = d.get(bucket) or []
        if items:
            out["groups"].append({"label": label, "rows": items})
    return out


# ═══════════════════════ CSS / JS ═══════════════════════
CSS = """
*{box-sizing:border-box}
body{margin:0;background:#070b16;color:#e8eef8;
 font-family:"Segoe UI","Microsoft JhengHei",system-ui,-apple-system,"Noto Sans TC",sans-serif;
 -webkit-text-size-adjust:100%}
a{color:#7cc4ff}
.wrap{max-width:1420px;margin:0 auto;padding:0 14px 60px}
header.top{position:sticky;top:0;z-index:50;background:#080d1aee;border-bottom:1px solid #1c2740;
 backdrop-filter:blur(9px);margin:0 -14px 18px;padding:10px 14px 0}
h1{font-size:19px;margin:0 0 2px;letter-spacing:.4px}
.crumb{color:#6e80a0;font-size:11.5px;margin:0 0 9px}
/* 導覽：桌面要 wrap，唔可以靠橫向 scroll ——
   ★ 2026-10-13 修（Desmond 用 Control Glass 睇到「方法分類」被切一半）：
   原本只有 overflow-x:auto，冇 flex-wrap → 默認 nowrap →
   14 個 link 需要 1433px 但容器 1213px → 最後 1-2 個被切斷，
   而 Chrome 隱藏 scrollbar → 完全冇提示。
   縮 padding/font 都補唔到 220px 差額（實測只夠縮 ~170px）→ 一定要 wrap。
   手機（≤768px）維持 nowrap + scroll（拇指滑動係自然嘅）。 */
nav{display:flex;flex-wrap:wrap;gap:4px;padding-bottom:2px}
nav a,nav span.tab{flex:0 0 auto;display:inline-flex;align-items:center;gap:6px;
 padding:7px 11px 8px;border-radius:9px;font-size:13px;color:#9fb0cc;
 text-decoration:none;border:1px solid transparent;white-space:nowrap}
nav a:hover{background:#121c31;color:#e8eef8}
nav a.on{background:#0f1729;border-color:#1e2a44;color:#e8eef8;font-weight:700}
nav span.off{opacity:.45}
.card{background:#0f1729;border:1px solid #1e2a44;border-radius:11px;margin:0 0 15px;
 box-shadow:0 2px 14px rgba(0,0,0,.32)}
.card h2{font-size:15.5px;margin:0;padding:11px 14px;border-bottom:1px solid #1e2a44;
 background:#0d1424;border-radius:11px 11px 0 0;display:flex;justify-content:space-between;
 align-items:center;gap:10px}
.card h2 small{font-weight:400;color:#7f90ad;font-size:11.5px}
.card .body{padding:12px 14px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}
@media(max-width:1080px){.grid2,.grid3{grid-template-columns:1fr}}
/* ── Item 9：手機版（空間節省）── */
@media(max-width:700px){
  body{padding:9px 8px;font-size:12.5px}
  .card{border-radius:9px;margin-bottom:10px}
  .card>h2{font-size:13px;padding:9px 11px;gap:5px}
  .card>h2 small{display:none}
  .card>.body{padding:0}
  .scroll{max-height:none;overflow-x:auto;-webkit-overflow-scrolling:touch}
  table{font-size:11px;min-width:0}
  th,td{padding:4px 5px;white-space:nowrap}
  th{font-size:10px;letter-spacing:0}
  /* 第一欄黏住左邊，橫向捲都睇得到代號 */
  th:first-child,td:first-child{position:sticky;left:0;z-index:2;
    background:#0f1729;box-shadow:1px 0 0 #1e2a44}
  html[data-theme="light"] th:first-child,
  html[data-theme="light"] td:first-child{background:#fff}
  .tk{font-size:11.5px}
  .rsmini,.spark{display:none}     /* 迷你圖喺手機太細，索性收起省位 */
  .kpi{min-width:74px;padding:6px 9px}
  .kpi .v{font-size:15px}
  .kpis{gap:6px;margin-bottom:9px}
  nav.gnav,nav{overflow-x:auto;flex-wrap:nowrap;
    -webkit-overflow-scrolling:touch;padding-bottom:4px}
  nav.gnav a,nav a{white-space:nowrap;flex:0 0 auto}
  .note{font-size:10.5px;line-height:1.6}
  .chartwall{grid-template-columns:repeat(auto-fill,minmax(60px,1fr));gap:6px}
  footer{margin-top:12px;font-size:10.5px}
}
@media(max-width:420px){
  body{padding:6px 5px;font-size:12px}
  th,td{padding:3px 4px}
  .kpi{min-width:62px}
}
.kpis{display:flex;flex-wrap:wrap;gap:9px;margin:0 0 14px}
.kpi{background:#0f1729;border:1px solid #1e2a44;border-radius:9px;padding:8px 12px;min-width:96px}
.kpi .k{font-size:10.5px;color:#7f90ad;letter-spacing:.5px}
.kpi .v{font-size:17px;font-weight:700;margin-top:2px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{padding:5px 7px;text-align:right;border-bottom:1px solid #16203a}
th{color:#8296b4;font-weight:600;font-size:11px;background:#0d1424;position:sticky;top:0}
td.l,th.l{text-align:left}
tr:hover td{background:#131c30}
.tk{font-weight:700;color:#cfe4ff}
.tv{color:#cfe4ff;text-decoration:none;border-bottom:1px dotted #4a90d9;font-weight:700}
.tv:hover{color:#4ade80;border-color:#4ade80}
.tv .tvs{opacity:0;font-size:10px;margin-left:3px}
.tv:hover .tvs{opacity:1}
.pos{color:#4ade80}.neg{color:#f87171}.dim{color:#7f90ad}
.badge{display:inline-block;padding:1px 7px;border-radius:20px;font-size:10.5px;font-weight:700}
.bar{height:8px;border-radius:4px;display:inline-block;vertical-align:middle;background:#22c55e}
.bar.neg{background:#ef4444}
.note{color:#7f90ad;font-size:11.5px;margin-top:9px;line-height:1.65}
.warn{background:#3a2410;border:1px solid #a0620f;color:#fbc06a;border-radius:9px;
 padding:9px 12px;font-size:12.5px;margin:0 0 13px;line-height:1.6}
.ok{background:#0f2a1a;border:1px solid #2c7a4b;color:#7fe0a3;border-radius:9px;
 padding:9px 12px;font-size:12.5px;margin:0 0 13px}
.filters{display:flex;flex-wrap:wrap;gap:7px;margin:0 0 11px;align-items:center}
input[type=search],select{background:#16203a;color:#e8eef8;border:1px solid #2a3a5c;
 border-radius:7px;padding:6px 10px;font-size:13px;font-family:inherit}
button{background:#16203a;color:#c7d4ea;border:1px solid #2a3a5c;border-radius:7px;
 padding:6px 11px;font-size:12.5px;cursor:pointer;font-family:inherit}
button:hover{background:#1d2a49}
button.on{background:#2b6cb0;border-color:#4a90d9;color:#fff;font-weight:700}
.scroll{max-height:70vh;overflow:auto}
footer{color:#5f708c;font-size:11.5px;margin-top:22px;line-height:1.7}
code{background:#16203a;padding:1px 5px;border-radius:4px;font-size:11.5px}
.todo{background:#141d33;border:1px dashed #35507e;border-radius:10px;padding:14px;color:#9fb0cc;
 font-size:13px;line-height:1.75}
.chartwall{display:grid;grid-template-columns:repeat(auto-fill,minmax(74px,1fr));gap:9px}
.cand{border:1px solid #1e2a44;border-radius:8px;padding:6px 4px 5px;text-align:center;background:#0d1424;display:block;text-decoration:none;color:inherit}
.cand .tk{font-size:11.5px;font-weight:700;color:#cfe4ff;margin-top:3px}
.cand .mini{min-height:66px;display:flex;align-items:center;justify-content:center}
.cand:hover{border-color:#4a90d9}
.tk.hl{color:#22c55e;text-shadow:0 0 10px rgba(34,197,94,.4)}
tr.buyrow td{background:rgba(34,197,94,.07)}
.controls{display:flex;gap:6px;align-items:center;margin-left:auto;flex:0 0 auto}
.controls button{border-radius:7px;padding:5px 10px;font-size:12px}

/* ── 淺色主題（默認）── */
html[data-theme="light"] body{background:#f6f8fb;color:#1a2433}
html[data-theme="light"] a{color:#2563eb}
html[data-theme="light"] header.top{background:#ffffffee;border-bottom:1px solid #e3e8f0}
html[data-theme="light"] .crumb{color:#64748b}
html[data-theme="light"] nav a{color:#64748b}
html[data-theme="light"] nav a:hover{background:#eef2f8;color:#111827}
html[data-theme="light"] nav a.on{background:#ffffff;border-color:#dbe2ec;color:#111827}
html[data-theme="light"] .card{background:#ffffff;border-color:#e3e8f0;box-shadow:0 1px 6px rgba(15,23,42,.06)}
html[data-theme="light"] .card h2{background:#f1f5f9;border-color:#e3e8f0;color:#111827}
html[data-theme="light"] .card h2 small{color:#64748b}
html[data-theme="light"] .kpi{background:#ffffff;border-color:#e3e8f0}
html[data-theme="light"] .kpi .k{color:#64748b}
html[data-theme="light"] .kpi .v{color:#111827}
html[data-theme="light"] .bar-nav{background:#ffffff;border-color:#e3e8f0}
html[data-theme="light"] select,html[data-theme="light"] input[type=search]{background:#ffffff;color:#1a2433;border-color:#d0d7e2}
html[data-theme="light"] button{background:#ffffff;color:#334155;border-color:#d0d7e2}
html[data-theme="light"] button:hover{background:#f1f5f9}
html[data-theme="light"] button.on{background:#2563eb;border-color:#2563eb;color:#fff}
html[data-theme="light"] th{color:#64748b;background:#f1f5f9}
html[data-theme="light"] td{border-color:#eef2f8}
html[data-theme="light"] tr:hover td{background:#f6f9fc}
html[data-theme="light"] .tk{color:#0b63ce}
html[data-theme="light"] .tk.hl{color:#16a34a;text-shadow:none}
html[data-theme="light"] .tv{color:#0b63ce;border-color:#93c5fd}
html[data-theme="light"] .tv:hover{color:#16a34a;border-color:#16a34a}
html[data-theme="light"] tr.buyrow td{background:rgba(34,197,94,.06)}
html[data-theme="light"] .dim{color:#94a3b8}
html[data-theme="light"] .note{color:#64748b}
html[data-theme="light"] footer{color:#64748b}
html[data-theme="light"] code{background:#eef2f8}
html[data-theme="light"] .todo{background:#f6f8fb;border-color:#cbd5e1;color:#475569}
html[data-theme="light"] .cand{background:#ffffff;border-color:#e3e8f0}
html[data-theme="light"] .cand .tk{color:#0b63ce}
html[data-theme="light"] .sitenav{background:#ffffffee;border-color:#e3e8f0}
html[data-theme="light"] .sitenav a{color:#64748b}
html[data-theme="light"] .sitenav a:hover{background:#eef2f8;color:#111827}
html[data-theme="light"] .sitenav a.on{background:#2563eb;color:#fff}
"""

JS = """
function q(s,r){return (r||document).querySelector(s);}
function qa(s,r){return Array.from((r||document).querySelectorAll(s));}
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function fin(v){return v!==null&&v!==undefined&&v!==''&&isFinite(Number(v));}
function fmt(v,d){d=(d===undefined?1:d);return fin(v)?Number(v).toLocaleString(undefined,{maximumFractionDigits:d}):'—';}
function pct(v,d){return fin(v)?(v>0?'+':'')+fmt(v,d)+'%':'—';}
function sgn(v,d){return fin(v)?(v>0?'+':'')+fmt(v,d):'—';}
function num(v,d){return fin(v)?fmt(v,d):'—';}
function money(v){if(!fin(v))return '—';return v>=1e9?'$'+fmt(v/1e9,1)+'B':v>=1e6?'$'+fmt(v/1e6,1)+'M':v>=1e3?'$'+fmt(v/1e3,0)+'K':'$'+fmt(v,0);}
function cls(v){return fin(v)?(v>0?'pos':(v<0?'neg':'')):'';}
function spark(vals,w,h){
  if(!vals||vals.length<2)return '';
  w=w||90;h=h||22;
  var mn=Math.min.apply(null,vals),mx=Math.max.apply(null,vals),rg=(mx-mn)||1;
  var pts=vals.map(function(v,i){return [i/(vals.length-1)*w, h-(v-mn)/rg*h];});
  var d=pts.map(function(p,i){return (i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1);}).join(' ');
  return '<svg width="'+w+'" height="'+h+'" style="vertical-align:middle"><path d="'+d+
    '" fill="none" stroke="'+(vals[vals.length-1]>=vals[0]?'#4ade80':'#f87171')+'" stroke-width="1.6"/></svg>';
}
function bar(v,mx,neg){
  if(!fin(v))return '';
  var w=Math.max(2,Math.min(60,Math.abs(v)/(mx||1)*60));
  return '<span class="bar'+(neg?' neg':'')+'" style="width:'+w.toFixed(0)+'px;opacity:.8"></span>';
}
function tone(v){return v>0?'pos':(v<0?'neg':'dim');}
"""


# ═══════════════════════ 頁面產生 ═══════════════════════
SITENAV_CSS = """
.sitenav{position:sticky;top:0;z-index:9999;display:flex;flex-wrap:wrap;gap:4px;
 background:#080d1a;border-bottom:1px solid #1c2740;padding:9px 14px 10px;margin:0;
 font-family:"Segoe UI","Microsoft JhengHei",system-ui,sans-serif}
.sitenav a{display:inline-flex;align-items:center;gap:5px;padding:7px 12px 8px;
 border-radius:8px;font-size:13px;color:#9fb0cc;text-decoration:none;white-space:nowrap}
.sitenav a:hover{background:#121c31;color:#e8eef8}
.sitenav a.on{background:#2b6cb0;color:#fff;font-weight:700}
.sitenav button{margin-left:auto;border-radius:7px;padding:5px 10px;font-size:12px;
 background:#16203a;color:#c7d4ea;border:1px solid #2a3a5c;cursor:pointer;font-family:inherit}
"""

DESK_LIGHT_CSS = """
html[data-theme="light"] body{background:#f6f8fb;color:#1a2433}
html[data-theme="light"] .sub{color:#64748b}
html[data-theme="light"] h1,html[data-theme="light"] h2,html[data-theme="light"] h3{color:#111827}
html[data-theme="light"] .card{background:#ffffff;border-color:#e3e8f0;box-shadow:0 1px 6px rgba(15,23,42,.06)}
html[data-theme="light"] .card h2{background:#f1f5f9;border-color:#e3e8f0;color:#111827}
html[data-theme="light"] .kpi{background:#ffffff;border-color:#e3e8f0}
html[data-theme="light"] .kpi .k{color:#64748b}
html[data-theme="light"] .kpi .v{color:#111827}
html[data-theme="light"] .bar-nav{background:#ffffff;border-color:#e3e8f0}
html[data-theme="light"] select,html[data-theme="light"] input{background:#ffffff;color:#1a2433;border-color:#d0d7e2}
html[data-theme="light"] button{background:#ffffff;color:#334155;border-color:#d0d7e2}
html[data-theme="light"] button:hover{background:#f1f5f9}
html[data-theme="light"] button.on{background:#2563eb;border-color:#2563eb;color:#fff}
html[data-theme="light"] th{color:#64748b;background:#f1f5f9}
html[data-theme="light"] td{border-color:#eef2f8}
html[data-theme="light"] tr:hover td{background:#f6f9fc}
html[data-theme="light"] .note{color:#64748b}
html[data-theme="light"] footer{color:#64748b}
html[data-theme="light"] code{background:#eef2f8;color:#334155}
html[data-theme="light"] .pos{color:#16a34a}
html[data-theme="light"] .neg{color:#dc2626}
html[data-theme="light"] svg text{fill:#334155}
"""

DESK_THEME_JS = """
(function(){
  function store(k,f){try{return JSON.parse(localStorage.getItem('desk-'+k))??f;}catch(e){return f;}}
  function save(k,v){try{localStorage.setItem('desk-'+k,JSON.stringify(v));}catch(e){}}
  var THEME=store('theme','light');
  function apply(){
    document.documentElement.setAttribute('data-theme',THEME);
    var tb=document.getElementById('themebtn'); if(tb) tb.textContent = THEME==='light'?'🌙 深色':'☀️ 淺色';
  }
  function boot(){
    var tb=document.getElementById('themebtn');
    if(tb) tb.addEventListener('click',function(){THEME=THEME==='light'?'dark':'light';save('theme',THEME);apply();});
    apply();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
"""

SITENAV_LINKS = [
    ("desk.html", "🖥", "機會", True),
    ("index.html", "📋", "市場簡報", False),
    ("leaders.html", "🚀", "領導股", False),
    ("cm.html", "🎯", "1CM 回調", False),
    ("week.html", "⚡", "最強 1 週", False),
    ("themes.html", "🧩", "Themes", False),
    ("sectors.html", "🏭", "Sectors", False),
    ("breadth.html", "🌊", "Breadth", False),
    ("positioning.html", "🎯", "Positioning", False),
    ("review.html", "⏪", "Review", False),
    ("rsboard.html", "📊", "RS 板", False),
    ("method.html", "🧩", "方法分類", False),
    ("cycle.html", "🌀", "成長週期", False),
    ("setups.html", "📐", "Setups", False),
]


def sitenav_html():
    links = "".join(
        f'<a href="{h}" class="{"on" if on else ""}"><span>{i}</span>{t}</a>'
        for h, i, t, on in SITENAV_LINKS)
    return (f'<style>{SITENAV_CSS}</style>'
            f'<nav class="sitenav">{links}<button id="themebtn">🌙 深色</button></nav>')


def inject_nav(html):
    """喺 desk.html 頂部加返網站導航＋主題一致化。

    ⚠ 之前 desk.html 係獨立頁（dashboard.py 生成），硬編碼深色，冇 link 返去其他分頁。
    呢度做三件事：① 插導航 ② 設 data-theme=light（默認淺色，同網站一致）
    ③ 注入淺色 CSS 覆寫 + 主題切換 JS，令「機會」頁同網站其他頁一樣跟 theme。
    """
    # 設默認淺色主題
    if '<html lang="zh-Hant">' in html:
        html = html.replace('<html lang="zh-Hant">', '<html lang="zh-Hant" data-theme="light">', 1)
    elif '<html>' in html:
        html = html.replace('<html>', '<html data-theme="light">', 1)
    inject = (f'<style>{DESK_LIGHT_CSS}</style>' + sitenav_html() +
              f'<script>{DESK_THEME_JS}</script>')
    marker = "<body>"
    if marker in html:
        return html.replace(marker, marker + inject, 1)
    return inject + html


def nav_html(active):
    """導航：除咗交易台（desk.html 係獨立大檔），其餘全部係自己嘅 .html 檔。

    ⚠ 之前用 `<a href="#key">` 係錯嘅 —— 內容唔喺同一頁，click 咗冇嘢發生。
    修法：直接鏈去真檔（leaders.html、week.html…），click 即轉跳。
    label 有 `data-i18n`，配合中／英切換。
    """
    out = []
    for key, icon, label, href in TABS:
        target = href or f"{key}.html"
        cls = "on" if key == active else ""
        out.append(f'<a href="{target}" class="{cls}"><span>{icon}</span>'
                   f'<span data-i18n="nav_{key}">{label}</span></a>')
    return "".join(out)



def i18n_json():
    d = {"h1": {"zh": "Desmond · 交易台", "en": "Desmond · Trading Desk"}}
    for key, icon, label, href in TABS:
        d[f"nav_{key}"] = {"zh": label, "en": EN_LABELS.get(key, label)}
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


def page(active, title, body, payload, extra_head=""):
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"""<!doctype html><html lang="zh-Hant" data-theme="light"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · 交易台</title>
<style>{CSS}{tvhover.TVHOVER_CSS}</style>{extra_head}</head><body>
<div class="wrap">
<header class="top">
 <div style="display:flex;align-items:flex-start;gap:10px">
  <div style="flex:1 1 auto">
   <h1>📈 <span>Desmond · 交易台</span></h1>
   <p class="crumb">繁體中文版｜骨架蒸餾自 <a href="https://i-manage-risk.github.io/NEL/index.html" target="_blank" rel="noopener">NEL · Market console</a>（逆向工程）｜資料 <code>{payload.get('_generated','?')}</code></p>
  </div>
  <div class="controls">
   <button id="themebtn" title="切換主題 / theme">🌙 深色</button>
  </div>
 </div>
 <nav>{nav_html(active)}</nav>
</header>
{body}
<footer>
 所有資料唯讀、研究用途，<b>非買入指令</b>。入場要另行符合 ORH + RVOL 規則；倉位由
 <code>daily_plan.stop_plan()</code> 決定。<br>
 產生器 <code>trading-os-web/build_site.py</code>｜掃描 <code>scan_market.py</code>
 ｜交易台 <code>trading-os-lab/dashboard.py</code>
</footer>
</div>
<script>var D={data};{JS}
document.addEventListener('DOMContentLoaded',function(){{ if(window.PAGE) PAGE(); }});</script>
<script>{THEME_LANG_JS}</script>
<script>{tvhover.TVHOVER_JS}</script>
</body></html>"""


THEME_LANG_JS = """
(function(){
  function store(k,f){try{return JSON.parse(localStorage.getItem('desk-'+k))??f;}catch(e){return f;}}
  function save(k,v){try{localStorage.setItem('desk-'+k,JSON.stringify(v));}catch(e){}}
  // ★ 2026-10-11 Desmond：「移除英文版選項」→ 永久 zh-Hant，冇 LANG 切換。
  var THEME=store('theme','light');
  function apply(){
    document.documentElement.setAttribute('data-theme',THEME);
    var tb=document.getElementById('themebtn');
    if(tb) tb.textContent = THEME==='light'?'🌙 深色':'☀️ 淺色';
  }
  function boot(){
    var tb=document.getElementById('themebtn');
    if(tb) tb.addEventListener('click',function(){THEME=THEME==='light'?'dark':'light';save('theme',THEME);apply();});
    apply();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
"""


def build():
    os.makedirs(SITE, exist_ok=True)
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    pages = {}

    scan = load_scan()
    brief = load_briefing()
    meth = load_methods()
    gen = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    base = {"_generated": gen}
    # ★ Item 2 統一欄位：呢三個要喺【所有】頁之前定義，因為 briefing/setups/week 都用。
    _kell = _cm = None
    cmres = {}
    kstage = {}

    # ── 簡報 ──
    reg = brief.get("regime") or {}
    bt = reg.get("breadth") or {}
    lx = reg.get("ix_lights") or {}
    b = brief.get("breadth") or {}
    q = brief.get("queue") or []
    kpi = [
        ("資料日期", reg.get("date") or b.get("as_of") or "—", "#e8eef8"),
        ("SPY / QQQ / IWM", " ".join(light(lx.get(k, "—")) for k in ("SPY", "QQQ", "IWM")), "#9fd4ff"),
        ("站上 50MA", pct(bt.get("above50")), "#4ade80"),
        ("站上 200MA", pct(bt.get("above200")), "#4ade80"),
        ("新高 / 新低", f'{num(bt.get("new_highs"),0)} / {num(bt.get("new_lows"),0)}', "#9fd4ff"),
        ("VIX", f'{light(reg.get("vix_light","—"))}', "#e8eef8"),
        ("圖表隊列", len(q), "#9fd4ff"),
    ]
    kpi_html = "".join(f'<div class="kpi"><div class="k">{k}</div>'
                       f'<div class="v" style="color:{c}">{v}</div></div>' for k, v, c in kpi)
    note = (f'<div class="warn"><b>{esc(reg.get("core_question") or "")}</b><br>'
            f'廣度：{esc(reg.get("breadth_note") or b.get("status") or "—")}<br>'
            f'領導：{esc((reg.get("lead") or {}).get("text") or "—")}　·　'
            f'VIX：{esc(reg.get("vix_note") or "—")}</div>')
    # ★ 統一欄位：briefing 都要有 Kell 階段 + 1CM 評級（Item 2）
    try:
        if _kell is None:
            import kell as _kell
    except Exception:                                        # noqa: BLE001
        _kell = None
    try:
        if _cm is None:
            import cm as _cm
    except Exception:                                        # noqa: BLE001
        _cm = None
    try:
        if _kell and q:
            kstage_b = _kell.stages([r["t"] for r in q][:120])
        else:
            kstage_b = {}
    except Exception:                                        # noqa: BLE001
        kstage_b = {}
    if not cmres and _cm and q:
        try:
            cmres = _cm.classify([r["t"] for r in q])
        except Exception:                                    # noqa: BLE001
            cmres = {}

    def _qrow(r):
        tr_cls = " class=buyrow" if r.get("box") else ""
        tk_cls = "tk hl" if r.get("box") else "tk"
        zone = "★ 買入區" if r.get("box") else "—"
        sym = r["t"]
        kc = (_kell.chip(sym, (kstage_b or {}).get(sym)) if _kell else "—")
        cc = (_cm.chip(sym, cmres.get(sym)) if _cm else "—")
        return (f'<tr{tr_cls}><td class="l"><span class="{tk_cls}">{tv_link(sym)}</span></td>'
                f'<td>{num(r.get("close"),2)}</td><td>{sgn(r.get("x"),2)}</td>'
                f'<td>{sgn(r.get("y"),2)}</td><td>{band_svg(r.get("y") or 0)}</td>'
                f'<td>{zone}</td>'
                f'<td>{num(r.get("stack"),0)}</td>'
                f'<td>{kc}</td><td>{cc}</td></tr>')
    qrows = "".join(_qrow(r) for r in q)
    brief_body = f"""
{note}
<div class="kpis">{kpi_html}</div>
<div class="grid2">
 <div class="card"><h2>市場狀態 <small>{esc(brief.get("regime_src") or "—")}</small></h2>
  <div class="body">{render_insight(reg) if reg else '<div class="dim">冇快照</div>'}</div></div>
 <div class="card"><h2>廣度歷史 <small>{esc(brief.get("breadth_src") or "—")}</small></h2>
  <div class="body">{render_breadth(b) if b else '<div class="dim">冇快照</div>'}</div></div>
</div>
<div class="card"><h2>今日圖表隊列 <small>{esc(brief.get("rs_src") or "")}</small></h2>
 <div class="body"><div class="scroll"><table><thead><tr><th class="l">代號 / 行業</th><th>收市</th>
 <th>X（21EMA）</th><th>Y（ATRX）</th><th>ATR 帶</th><th>買入區</th><th>疊加</th>
 <th>Kell 階段</th><th>1CM 評級</th></tr></thead>
 <tbody>{qrows or '<tr><td colspan=9 class="dim">今日冇快照</td></tr>'}</tbody></table></div>
 <div class="note">X/Y 單位係 ATR：X=(收市−21EMA)/ATR14，Y=(收市−50SMA)/ATR14。
 買入區＝X∈[−0.5,+1] 且 Y∈[0,+4]。<b>「Kell 階段」同「1CM 評級」嘅定義同領導股頁完全一樣</b>
 （統一規格）—— Kell 六階段睇 <a href="cycle.html">成長週期</a>，
 1CM 睇 <a href="cm.html">1CM 回調</a>。</div></div></div>"""
    pages["briefing"] = ("市場簡報", brief_body, base)

    # ── 領導股（NEL）──
    if scan:
        c = scan["counts"]
        th = scan["thresholds"]
        # 圖表牆（一次過睇哂所有 NEL 圖）
        chart_tickers = [r["symbol"] for r in sorted(
            scan["nel"], key=lambda r: -(r["perf"].get("3m") or -99))][:48]
        try:
            wall = charts.grid_html(charts.build_grid(chart_tickers))
            rs_map = charts.rs_lookup(chart_tickers)
        except Exception as e:                               # noqa: BLE001
            wall = (f'<div class="warn">圖表牆取唔到：{type(e).__name__}'
                    f'（yfinance 限流或離線？）。</div>')
            rs_map = {}
        # ★ Oliver Kell 六階段（item 7）—— 用 kell.py，同 lab 版同一個分類器。
        # ⚠ 一定要喺 def table / head 之前賦值（closure 求值次序）。
        _kell = _cm = None       # 預設，令後面 setups / week 唔會 UnboundLocal
        cmres = {}
        try:
            import kell as _kell
            kstage = _kell.stages([r["symbol"] for r in scan["nel"]][:120])
        except Exception as _e:                              # noqa: BLE001
            _kell, kstage = None, {}
            log(f"⚠ Kell 階段取唔到：{type(_e).__name__}")
        def table(rows, extra=True):
            tr = []
            for r in rows:
                p = r["perf"]
                tr.append(
                    f'<tr><td class="l"><span class="tk">{tv_link(r["symbol"], r.get("industry"))}</span>'
                    f'<div class="dim" style="font-size:10.5px">{esc(r["industry"])}</div></td>'
                    + charts.rs_col(rs_map.get(r["symbol"], {}))
                    + f'<td>{pct(p.get("1w"))}</td><td>{pct(p.get("1m"))}</td>'
                    f'<td>{pct(p.get("3m"))}</td><td>{pct(p.get("6m"))}</td>'
                    f'<td>{pct(p.get("1y"))}</td>'
                    + (f'<td>{num(r["extension"],2)}×</td><td>{pct(r["adr"],1)}</td>'
                       f'<td>{money(r["dvol"])}</td>' if extra else "")
                    + f'<td>{pct(r.get("off52w"),1)}</td>'
                    + (f'<td>{_kell.chip(r["symbol"], kstage.get(r["symbol"]))}</td>'
                       if _kell else "")
                    + f'<td>{_cm.chip(r["symbol"], cmres.get(r["symbol"])) if _cm else "—"}</td>'
                    + '</tr>')
            return tr
        head = ('<tr><th class="l">代號 / 行業</th><th>RS-D</th><th>RS-W</th>'
                '<th>1週</th><th>1月</th><th>3月</th>'
                '<th>6月</th><th>1年</th><th>延伸</th><th>ADR%</th><th>成交額</th>'
                '<th>距52週高</th>'
                + ('<th>Kell 階段</th>' if _kell else "") + '<th>1CM 評級</th></tr>')
        nel = sorted(scan["nel"], key=lambda r: -(r["perf"].get("3m") or -99))
        mom = sorted(scan["momentum"], key=lambda r: -(r["perf"].get("3m") or -99))
        # 按行業分組
        byind = {}
        for r in nel:
            byind.setdefault(r["industry"], []).append(r)
        ind_html = "".join(
            f'<tr><td class="l">{esc(k)}</td><td>{len(v)}</td>'
            f'<td class="l">{esc("、".join(x["symbol"] for x in sorted(v, key=lambda z: -(z["perf"].get("3m") or -99))))}</td></tr>'
            for k, v in sorted(byind.items(), key=lambda kv: -len(kv[1])))
        leaders_body = f"""
<div class="warn">⚠ <b>同 NEL 唔完全一樣</b>：NEL 用 TradingView 網頁版匯出嘅
 <code>average_dollar_volume_30d</code> 同 <code>ADRP</code>；我哋用 Python 套件打同一個 API，
 成交額自己計（<code>收市 × 10 日平均量</code>），而套件嘅 <code>ADRP</code> 同網頁版有出入。
 實測對佢 2026-10-11 公佈嘅 32 隻 NEL：<b>中 19 隻</b>。差異已記錄，唔會當自己係原版。</div>
<div class="kpis">
 <div class="kpi"><div class="k">流動池</div><div class="v">{c["raw"]}</div></div>
 <div class="kpi"><div class="k">動能池（四窗前 5%）</div><div class="v" style="color:#9fd4ff">{c["momentum"]}</div></div>
 <div class="kpi"><div class="k">NEL（延伸 ≤{th["max_extension"]}×）</div><div class="v" style="color:#4ade80">{c["nel"]}</div></div>
</div>
<div class="card"><h2>圖表牆 · 一次過睇哂所有 NEL <small>迷你 K 線 ＋ 50SMA ＋ ADR%（90 日，最後 40 支）</small></h2>
 <div class="body">{wall}
 <div class="note">點解係「最後 40 支」：90 支喺 58px 闊會變成色塊。SMA50 線喺圖上畫出嚟，只係參考，唔係入場信號。</div></div></div>
<div class="card"><h2>NEL · 非延伸領導股 <small>{len(nel)} 隻｜延伸 ≤ {th["max_extension"]}×</small></h2>
 <div class="body"><div class="filters"><input type="search" id="f" placeholder="篩選代號／行業…"></div>
 <div class="scroll"><table id="t-nel"><thead>{head}</thead><tbody>{"".join(table(nel))}</tbody></table></div>
 {(_kell.legend_html() if _kell else "")}
 <div class="note">門檻：成交額 &gt; ${th["min_dollar_vol"]//10**6}M、ADR &gt; {th["min_adr"]}%、
 10 日平均量 &gt; {th["min_avg_vol"]//1000}K、行業唔可以有 Biotech、四個窗口各取前 {int(th["top_frac"]*100)}%。</div></div></div>
<div class="card"><h2>動能池（未過延伸閘） <small>{len(mom)} 隻</small></h2>
 <div class="body"><div class="scroll"><table id="t-mom"><thead>{head}</thead><tbody>{"".join(table(mom))}</tbody></table></div></div></div>
<div class="card"><h2>領導股按行業 <small>{len(byind)} 個行業</small></h2>
 <div class="body"><table><thead><tr><th class="l">行業</th><th>NEL 隻數</th><th class="l">成員</th></tr></thead>
 <tbody>{ind_html or '<tr><td colspan=3 class="dim">—</td></tr>'}</tbody></table></div></div>"""
        pages["leaders"] = ("領導股",
                            (f"<style>{_kell.KELL_CSS}</style>" if _kell else "") + leaders_body,
                            base | {"scan": scan})
        # ── 1CM 回調（1chartmaster RS Leader Pullback Buy）──
        try:
            import cm as _cm
            cmres = _cm.classify([r["symbol"] for r in scan["nel"]])
        except Exception as _e:                              # noqa: BLE001
            _cm, cmres = None, {}
            log(f"⚠ 1CM 分類取唔到：{type(_e).__name__}")
        if _cm and cmres:
            ranked = sorted(cmres.values(),
                            key=lambda x: (-x["n"], abs(x["sup_dist"] or 99)))
            top = [x for x in ranked if x["n"] >= 4]
            rest = [x for x in ranked if x["n"] < 4]
            nel_ind = {r["symbol"]: r.get("industry", "") for r in scan["nel"]}
            def cmrow(r):
                ind = nel_ind.get(r["ticker"], "")
                return (f'<tr><td class="l"><span class="tk">'
                        f'{tv_link(r["ticker"], ind)}</span>'
                        f'<div class="dim" style="font-size:10.5px">{esc(ind)}</div></td>'
                        f'<td>{_cm.chip(r["ticker"], r)}</td>'
                        f'{_cm.detail_cells(r)}'
                        f'<td>{num(r["close"], 2)}</td></tr>')
            cmhead = ('<tr><th class="l">代號 / 行業</th><th>1CM 評級</th>'
                      '<th>L1 RS 領導</th><th>L2 回調支撐</th><th>L3 量縮</th>'
                      '<th>L4 買家守</th><th>L5 風險窄</th><th>收市</th></tr>')
            cm_body = f"""
<div class="warn">🎯 <b>1chartmaster「RS Leader Pullback Buy」</b>——
 呢個分頁係由 Desmond 嘅訂閱證據庫蒸餾出嚟（read-only），
 <b>唔係我哋原創</b>。原文：「you track Relative Strength (RS) leaders and buy
 them when they <b>pull back into structural support</b>」。</div>
<style>{_cm.CM_CSS}</style>
<div class="kpis">
 <div class="kpi"><div class="k">A 級以上（≥4/5）</div>
  <div class="v" style="color:#4ade80">{len(top)}</div></div>
 <div class="kpi"><div class="k">掃描池（NEL）</div>
  <div class="v">{len(cmres)}</div></div>
 <div class="kpi"><div class="k">五條件全中</div>
  <div class="v" style="color:#22c55e">{sum(1 for x in cmres.values() if x["n"] == 5)}</div></div>
</div>
{_cm.legend_html()}
<div class="card"><h2>A 級設置 <small>≥4/5 條件｜按條件數再按距支撐排序</small></h2>
 <div class="body"><div class="scroll"><table><thead>{cmhead}</thead>
 <tbody>{"".join(cmrow(r) for r in top) or '<tr><td colspan=8 class="dim">今日冇 A 級設置</td></tr>'}</tbody>
 </table></div></div></div>
<div class="card"><h2>B 級觀察名單 <small>&lt;4/5</small></h2>
 <div class="body"><div class="scroll"><table><thead>{cmhead}</thead>
 <tbody>{"".join(cmrow(r) for r in rest) or '<tr><td colspan=8 class="dim">—</td></tr>'}</tbody>
 </table></div></div></div>"""
            pages["cm"] = ("1CM 回調", cm_body, base | {"cm": cmres})
        # ── 最強 1 週 ──（Item 2：統一欄位）—
        wk = scan.get("week") or []
        std_ctx = {
            "tv_link": tv_link, "rs_col": charts.rs_col, "band_svg": band_svg,
            "rs_map": {r.get("symbol"): r.get("rs") for r in wk},
            "kstage": (_kell.stages([r["symbol"] for r in wk][:120])
                       if _kell and wk else {}),
            "cm": _cm, "cmres": cmres,
            "kell": _kell,
        }
        wk_keys = ["rank", "name", "1w", "1m", "3m", "ext", "adr",
                   "dvol", "off52", "kell", "cm"]
        pages["week"] = ("最強 1 週", f"""
<div class="card"><h2>本週最強嘅流動性股 <small>流動池 {len(scan["universe"])} 隻之中，按 1 週表現排</small></h2>
 <div class="body"><div class="note">「流動性」＝成交額 &gt; ${th["min_dollar_vol"]//10**6}M 且
 ADR &gt; {th["min_adr"]}% 且 10 日平均量 &gt; {th["min_avg_vol"]//1000}K。呢個係<b>全市場</b>掃描，
 唔係我哋自己嘅 103 隻池。<br>
 <b>欄位定義同領導股頁完全一樣</b>（統一規格）—— 「延伸」＝(收市−50SMA)÷ATR14 倍數，
 「距52週高」＝負數代表仍低於 52 週高。</div>
 {_std.table_html(wk_keys, wk, std_ctx, empty="今日冇數據")}</div></div>""",
            base | {"scan": scan})

        # ── 方法分類 ──
        mrows = ""
        for g in (meth or {}).get("groups", []):
            mrows += (f'<tr><td class="l" colspan="5" style="background:#0d1424;'
                      f'font-weight:700;color:#9fd4ff">{esc(g["label"])}（{len(g["rows"])} 隻）</td></tr>')
            for r in sorted(g["rows"], key=lambda z: -(z.get("score") or 0)):
                rs = "、".join((r.get("reasons") or [])[:2])
                ind = r.get("industry") or ""
                atrx = r.get("atrx")
                if atrx is None:
                    atrx = r.get("extension")
                lbl = ("過度延伸 ⚠" if (atrx or 0) > 4
                       else "買入區" if 0 <= (atrx or -99) <= 4
                       else "偏低")
                mrows += (f'<tr><td class="l"><span class="tk">'
                          f'{tv_link(r.get("ticker"), ind)}</span>'
                          f'<div class="dim" style="font-size:10.5px">{esc(ind)}</div></td>'
                          f'<td>{num(r.get("score"),0)}</td>'
                          f'<td>{num(atrx,2)}×</td><td>{esc(lbl)}</td>'
                          f'<td class="l">{esc(r.get("watch_price") or "—")}</td>'
                          f'<td class="l">{esc(r.get("invalidation") or "—")}</td>'
                          f'<td class="l dim">{esc(rs)}</td></tr>')
        pages["method"] = ("方法分類", f"""
<div class="card"><h2>Layer 2 · 每個方法各自一個清單 <small>{esc((meth or {}).get("src") or "冇快照")}</small></h2>
 <div class="body"><div class="note">Focus ＝ 已經起動、等入場；Stalk ＝ 未起動、放觀察名單。
 呢度<b>照原樣分組</b>，唔重新判斷，避免我二次演繹。<br>
 <b>ATRX</b> ＝ (收市 − 50SMA) ÷ ATR14（同領導股頁「延伸」<b>係同一個數</b>，只係呢邊要你睇住
 4 呢條線：<b>&gt;4 ＝ 硬刪</b>、0–4 ＝ 買入區、&lt;0 ＝ 仲喺 50MA 之下）。</div>
 <div class="scroll"><table><thead><tr><th class="l">代號 / 行業</th><th>分數</th>
 <th>ATRX</th><th>位置</th><th class="l">觸發條件</th><th class="l">失效條件</th>
 <th class="l">理由</th></tr></thead>
 <tbody>{mrows or '<tr><td colspan=7 class="dim">冇 Layer2 快照</td></tr>'}</tbody></table></div></div></div>""", base)

    # ── Item 1：NEL 五頁蒸餾（Themes／Sectors／Breadth／Positioning／Review）──
    # ★ 每頁用 nel_pages.py 嘅唯一實作，呢度只負責寫入 pages dict。
    #   唔准喺呢度重算任何公式（EDGE-036 教訓：同一個概念只可以一個實作）。
    try:
        _ohlc_df = _np._ohlc()
        for _key, _title, _fn in (
                ("themes", "Themes", lambda: _np.themes_page(_ohlc_df)),
                ("sectors", "Sectors", lambda: _np.sectors_page(_ohlc_df)),
                ("breadth", "Breadth", _np.breadth_page),
                ("positioning", "Positioning", _np.positioning_page),
                ("review", "Review", _np.review_page)):
            try:
                pages[_key] = (_title, _fn(), base)
            except Exception as _e2:                         # noqa: BLE001
                log(f"⚠ {_title} 頁失敗：{type(_e2).__name__}")
                pages[_key] = (_title, _np._unavail(_title, str(_e2)), base)
    except Exception as _e1:                                 # noqa: BLE001
        log(f"⚠ NEL 五頁整體失敗：{type(_e1).__name__}")

    # ── RS 板（跟圖片 2/4：指數／群組／板塊三個表）──
    rsb_full = extras.rsboard_full()
    if rsb_full:
        head = ('<table><thead><tr><th>#</th><th class="l">ETF / 名稱</th>'
                '<th>推力率</th><th class="l">1月超額走勢（30日）</th>'
                '<th class="l">1月超額</th><th>RS 百分位</th><th>距52週高</th></tr></thead><tbody>')

        def one(title, rows):
            return (f'<div class="card"><h2>{title} <small>{len(rows)} 隻</small></h2>'
                    f'<div class="body"><div class="scroll">{head}{rs_table(rows)}'
                    f'</tbody></table></div></div></div>')

        rs_body = ("<div class=\"warn\">⚠ RS 推力率係<b>我嘅定義</b>（Jeff Sun 原文未取得）："
                   "最近 30 個交易日之中，ETF 嘅 21 日回報贏 SPY 嘅比例。唔會扮係佢嘅數。</div>"
                   + one("指數 Index", rsb_full["index"])
                   + one("群組 Group", rsb_full["group"])
                   + one("板塊 Sector", rsb_full["sector"])
                   + f'<div class="note">推力率＝30 日內 21 日回報贏 SPY 嘅日數比例（0–100）。'
                     f'走勢＝每日超額回報迷你線（綠＝領先、紅＝落後）。'
                     f'RS 百分位＝1 月超額喺本表嘅排名。'
                     f'資料至 <b>{esc(rsb_full["as_of"])}</b>，SPY 1 月 {pct(rsb_full["spy1m"],1)}。</div>')
        pages["rsboard"] = ("RS 板", rs_body, base)

    # ── 成長週期（跟圖片 6：IWF/IWD 風險閘）──
    gc = extras.growth_cycle()
    if gc:
        ph = gc["phase"]
        phc = {"RISK-OFF": "#ef4444", "PROBE": "#f59e0b", "RAMP UP": "#22c55e",
               "TRIM/HOLD": "#0ea5e9", "RELOAD": "#a78bfa"}.get(ph, "#94a3b8")
        side_txt = "RISK-ON" if gc["side"] == "on" else "RISK-OFF"
        side_c = "#22c55e" if gc["side"] == "on" else "#ef4444"
        cy_body = (
            '<div class="kpis">'
            f'<div class="kpi"><div class="k">現時階段</div><div class="v" style="color:{phc}">{esc(ph)}</div></div>'
            f'<div class="kpi"><div class="k">方向</div><div class="v" style="color:{side_c}">{side_txt}</div></div>'
            f'<div class="kpi"><div class="k">比率 IWF÷IWD</div><div class="v">{gc["ratio"]}</div></div>'
            f'<div class="kpi"><div class="k">上軌／下軌</div><div class="v">{gc["up"]} / {gc["dn"]}</div></div>'
            '</div>'
            f'<div class="card"><h2>成長／價值 風險閘 '
            f'<small>IWF {gc["iwf"]} ／ IWD {gc["iwd"]}｜至 {esc(gc["as_of"])}</small></h2>'
            f'<div class="body">{cycle_svg(gc["series"])}'
            '<div class="note">綠線＝IWF÷IWD 比率（週收市）；灰線＝週高低 EMA10 風險閘；'
            '藍色陰影＝閘帶。收市升穿上軌＝risk-on、跌穿下軌＝risk-off、軌內＝維持上一邊。'
            '六個階段：RISK-OFF → PROBE → RAMP UP → TRIM/HOLD → RELOAD → 回落。'
            '⚠ 模型由你圖片蒸餾，用 <b>IWF/IWD</b>（羅素 1000 成長÷價值）—— 你之前話「你決定」。</div></div></div>')
        pages["cycle"] = ("成長週期", cy_body, base)

    st = load_setups()
    if st:
        pl_rows = []
        for r in st["rows"]:
            pl_rows.append(
                f'<tr><td class="l"><span class="tk">{tv_link(r["ticker"])}</span></td>'
                f'<td>{num(r.get("close"),2)}</td>'
                f'<td class="l">{esc(r.get("watch_price") or "—")}</td>'
                f'<td class="l">{esc(r.get("invalidation") or "—")}</td>'
                f'<td>{sgn(r.get("x"),2)}</td><td>{sgn(r.get("y"),2)}</td>'
                f'<td>{band_svg(r.get("y") or 0)}</td></tr>')
        setups_body = (
            f'<div class="card"><h2>The Plan · 每日計劃 <small>{esc(st["src"])}</small></h2>'
            f'<div class="body">'
            + _std.table_html(
                ["name", "close", "watch_f", "inv_f", "x", "y", "band", "kell", "cm"],
                st["rows"],
                {"tv_link": tv_link, "band_svg": band_svg,
                 "kell": _kell, "cm": _cm, "cmres": cmres,
                 "kstage": (_kell.stages([r["ticker"] for r in st["rows"]][:120])
                            if _kell and st.get("rows") else {})},
                empty="今日冇計劃")
            + '<div class="note">ATR 帶：−3 到 +5 ATR，灰線＝50SMA（0）、'
            '虛線＝+4（週線過度延伸）、綠區＝買入區（0..+4）、藍點＝而家位置。'
            '買入線／失效線來自 <code>rs_select</code>（10MA／20MA）。'
            '<b>欄位定義同領導股頁一致</b>（統一規格）。'
            '⚠ 「虛線＝最舊收市／實線＝用得最多／綠方格＝最早落帶」呢三個視覺係你原創規則，'
            '要你講一句先砌得準 —— 而家呢條帶係淨位置，冇嗰三樣。</div></div></div>')
        pages["setups"] = ("Setups", setups_body, base)

    # ── 交易台（我原本嘅 dashboard）──
    src_desk = os.path.join(LAB, "output", f"dashboard_{datetime.date.today().isoformat()}.html")
    if not os.path.exists(src_desk):
        cands = sorted(glob.glob(os.path.join(LAB, "output", "dashboard_*.html")))
        src_desk = cands[-1] if cands else None
    if src_desk:
        with io.open(src_desk, encoding="utf-8") as f:
            desk_html = f.read()
        desk_html = inject_nav(desk_html)
        # 標題都要改名（機會 = 之前嘅交易台）
        desk_html = desk_html.replace("📊 交易台 · TRADING DESK", "📊 機會 · OPPORTUNITY DESK")
        desk_html = desk_html.replace("<title>交易台", "<title>機會")
        with io.open(os.path.join(SITE, "desk.html"), "w", encoding="utf-8") as f:
            f.write(desk_html)
        log(f"✓ desk.html ← {os.path.basename(src_desk)}（已加網站導航）")
    else:
        log("⚠ 搵唔到 dashboard HTML —— desk 分頁會係空")

    for key, (title, body, payload) in pages.items():
        p = os.path.join(SITE, f"{key}.html")
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(page(key, title, body, payload))
        log(f"✓ {os.path.basename(p)} ({os.path.getsize(p)//1024} KB)")

    # index = 簡報
    shutil.copy2(os.path.join(SITE, "briefing.html"), os.path.join(SITE, "index.html"))
    log("✓ index.html（＝簡報）")
    return 0


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.parse_args(argv if argv is not None else sys.argv[1:])
    return build()


if __name__ == "__main__":
    sys.exit(main())
