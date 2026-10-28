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
import weekly_gate as _wg  # noqa: E402
import datetime
import glob
import io
import json
import math
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# ★ 每次 build 一個時間戳：寫入每頁（顯示喺側欄）＋ docs/version.json
#   前端 fetch version.json，發現版本唔同就自己 reload 一次，
#   所以 Desmond 用返原來條 link 就永遠睇到最新，唔需要加 ?v=
BUILD_TS = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
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

EN_LABELS = {"regime_mri": "Market Regime", "rocketstock": "RocketStock", "livefeeds": "Live Feeds", "dailyscan": "Daily Scan", "leadermap": "RS Leader Map", "earnings": "Earnings", "external": "External", "desk": "Opportunity", "briefing": "Market Brief", "leaders": "Leaders",
             "week": "Week Strongest", "rsboard": "RS Board", "method": "Methods",
             "cycle": "Growth Cycle", "setups": "Setups",
             "regime": "Setup x Regime", "calculator": "Position Sizing"}

TABS = [
    ("dailyscan", "", "Daily Scan", None),
    ("desk", "", "機會", "desk.html"),
    ("briefing", "", "市場簡報", None),
    ("leaders", "", "RS Leader", None),
    ("cm", "", "RS Pullback", None),
    ("week", "", "Weekly MM", None),
    ("themes", "", "Themes", None),
    ("sectors", "", "Sectors", None),
    ("breadth", "", "Breadth", None),
    ("positioning", "", "Positioning", None),
    ("calculator", "", "倉位計算機", None),
    ("review", "", "Review", None),
    ("rsboard", "", "RS 板", None),
    ("vantharp", "", "Van Tharp 五法", None),
    ("optledger", "", "優化帳本", None),
    ("setupfactory", "", "Setup Factory", None),
    ("cycle", "", "成長週期", None),
    ("setups", "", "Setups", None),
    ("regime", "", "Setup×Regime", None),
    ("regime_mri", "", "MARKET REGIME", None),
    ("rocketstock", "", "RocketStock", None),
    ("livefeeds", "", "外部即時數據", None),
    ("mm", "", "Market Monitor", None),
    ("bee50", "", "Stockbee 50", None),
    ("jeffsun", "", "Jeff Sun Mom.", None),
    ("ndx", "", "納指權重股", None),
    ("jobboard", "", "廚房看板", None),
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
    """把 breadth JSON 轉做乾淨表格。

    ★ 2026-10-19 修 bug（Desmond：「breadth 放入市場簡報」）：
      原本全部用 `posture.xxx` 讀 → 但實際結構係：
        pct40ma / ls_ratio_proxy  = 頂層 float
        adl / nnnl                = 頂層 dict {"value": ...}
        regime / posture          = 頂層 str + dict
      結果只有 Regime / Posture 顯示到，其餘 7 行全部空白。
    """
    po = b.get("posture") or {}
    if not isinstance(po, dict):
        po = {}

    def _val(x, k="value"):
        """dict → 取 value；純量 → 原值。"""
        if isinstance(x, dict):
            return x.get(k)
        return x

    lines = [
        ("資料", esc(b.get("as_of") or "—")),
        ("範圍", esc(b.get("universe") or "—")),
        ("Regime", esc(b.get("regime") or po.get("regime") or "—")),
        ("Posture", esc(po.get("posture") or "—")),
        ("狀態", esc(b.get("status") or "—")),
        ("多空比", num(b.get("ls_ratio_proxy") or po.get("ls_ratio"), 2)),
        ("ADL", num(_val(b.get("adl")), 1)),
        ("新高新低淨值", num(_val(b.get("nnnl")), 1)),
        ("站上 40MA", f'{num(b.get("pct40ma"))}%'),
        ("SPY 收市", num(b.get("spy_close"), 2)),
        ("備註", esc("；".join(po.get("notes") or po.get("warnings") or []))),
    ]
    rows = "".join(f'<tr><td class="l" style="color:#64748b;white-space:nowrap">{k}</td>'
                   f'<td class="l">{v}</td></tr>' for k, v in lines if v)
    return f'<table>{rows}</table>'


def render_stockbee_breadth(sb):
    """Stockbee Market Monitor 最新一日（升4%/跌4% 家數）—— 補入市場簡報。

    ★ Desmond 2026-10-19：「breadth 放入市場簡報」。
      我哋自己嘅 breadth 係 pct40ma/ADL，但 Jeff Sun/Stockbee 方法用嘅係
      「今日幾多隻升 4%+ / 跌 4%+」。兩把尺唔可以混用，所以並排顯示。
    """
    if not sb:
        return '<div class="dim">DATA_UNAVAILABLE（Stockbee 抓唔到）</div>'
    up, dn = sb.get("up4"), sb.get("down4")
    ratio = (up / dn) if (up is not None and dn) else None
    rows = [
        ("日期", esc(sb.get("date") or "—")),
        ("升 4%+ 家數", f'<b class="up">{int(up) if up is not None else "—"}</b>'),
        ("跌 4%+ 家數", f'<b class="dn">{int(dn) if dn is not None else "—"}</b>'),
        ("升/跌 比", f'<b>{ratio:.2f}</b>' if ratio else "—"),
        ("5 日比率", num(sb.get("r5"), 2)),
        ("10 日比率", num(sb.get("r10"), 2)),
        ("升 25%+ (季)", num(sb.get("up25q"), 0)),
        ("跌 25%+ (季)", num(sb.get("down25q"), 0)),
    ]
    out = "".join(f'<tr><td class="l" style="color:#64748b;white-space:nowrap">{k}</td>'
                  f'<td class="l">{v}</td></tr>' for k, v in rows if v and v != "—")
    return f'<table>{out}</table>'



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
        # ★ 2026-10-19：原本白名單漏咗 adl / nnnl，令市場簡報嘅
        #   「ADL」「新高新低淨值」兩行永遠空白（Desmond 見到嘅「有d無更新」）。
        out["breadth"] = {k: d.get(k) for k in
                          ("as_of", "universe", "regime", "posture", "status",
                           "pct40ma", "ls_ratio_proxy", "spy_close",
                           "adl", "nnnl", "series")}
        out["breadth_src"] = os.path.basename(p2)
    # 今日圖表隊列（rs_select）
    # ★ 2026-10-20 修假更新：舊版搵唔到今日檔就靜靜用 newest()，但標題照寫「今日」
    #   實測 rs_select_2026-10-11.json（8 日前）被當成今日顯示。
    #   現在一律經 freshness.status()，並把真實狀態帶去 UI。
    try:
        import freshness as _fr
        _rsd, _rsst = _fr.load("rs_select")
    except Exception:                                        # noqa: BLE001
        _rsd, _rsst = None, dict(status="MISSING", age=None, mtime=None,
                                 path=None)
    out["rs_status"] = _rsst.get("status")
    out["rs_age"] = _rsst.get("age")
    out["rs_mtime"] = _rsst.get("mtime")
    out["rs_src"] = (os.path.basename(_rsst["path"])
                     if _rsst.get("path") else None)
    rs = _rsd
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
html{background:#070b16}
html[data-theme="light"]{background:#ffffff}
body{margin:0;background:#070b16;color:#e8eef8;
 font-family:"Segoe UI","Microsoft JhengHei",system-ui,-apple-system,"Noto Sans TC",sans-serif;
 -webkit-text-size-adjust:100%}
a{color:#7cc4ff}
.wrap{max-width:1420px;margin:0 auto;padding:0 14px 60px}
header.top{position:sticky;top:0;z-index:50;background:#080d1aee;border-bottom:1px solid #1c2740;
 backdrop-filter:blur(9px);margin:0 -14px 18px;padding:10px 14px 0}
h1{font-size:20px;margin:0 0 2px;letter-spacing:.4px}
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
 padding:7px 11px 8px;border-radius:8px;font-size:12.5px;color:#9fb0cc;
 text-decoration:none;border:1px solid transparent;white-space:nowrap}
nav a:hover{background:#121c31;color:#e8eef8}
nav a.on{background:#0f1729;border-color:#1e2a44;color:#e8eef8;font-weight:700}
nav span.off{opacity:.45}
.card{background:#0f1729;border:1px solid #1e2a44;border-radius:10px;margin:0 0 16px}
.card h2{font-size:14px;margin:0;padding:11px 14px;border-bottom:1px solid #1e2a44;
 background:#0d1424;border-radius:10px 11px 0 0;display:flex;justify-content:space-between;
 align-items:center;gap:10px}
.card h2 small{font-weight:400;color:#7f90ad;font-size:11.5px}
.card .body{padding:12px 14px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}
@media(max-width:1080px){.grid2,.grid3{grid-template-columns:1fr}}
/* ── Item 9：手機版（空間節省）── */
@media(max-width:700px){
  body{padding:9px 8px;font-size:12.5px}
  .card{border-radius:8px;margin-bottom:10px}
  .card>h2{font-size:12.5px;padding:9px 11px;gap:5px}
  .card>h2 small{display:none}
  .card>.body{padding:0}
  .scroll{max-height:none;overflow-x:auto;-webkit-overflow-scrolling:touch}
  table{font-size:10.5px;min-width:0}
  th,td{padding:4px 5px;white-space:nowrap}
  th{font-size:10px;letter-spacing:0}
  /* 第一欄黏住左邊，橫向捲都睇得到代號 */
  th:first-child,td:first-child{position:sticky;left:0;z-index:2;
    background:#0f1729;}
  html[data-theme="light"] th:first-child,
  html[data-theme="light"] td:first-child{background:#fff}
  .tk{font-size:11.5px}
  .rsmini,.spark{display:none}     /* 迷你圖喺手機太細，索性收起省位 */
  .kpi{min-width:74px;padding:6px 9px}
  .kpi .v{font-size:14px}
  .kpis{gap:6px;margin-bottom:9px}
  nav.gnav,nav{overflow-x:auto;flex-wrap:nowrap;
    -webkit-overflow-scrolling:touch;padding-bottom:4px}
  nav.gnav a,nav a{white-space:nowrap;flex:0 0 auto}
  .note{font-size:10.5px;line-height:1.6}
  .chartwall{grid-template-columns:repeat(auto-fill,minmax(60px,1fr));gap:6px}
  footer{margin-top:12px;font-size:10.5px}
}
@media(max-width:420px){
  body{padding:6px 5px;font-size:11.5px}
  th,td{padding:3px 4px}
  .kpi{min-width:62px}
}
.kpis{display:flex;flex-wrap:wrap;gap:0;margin:0 0 14px;
  border:1px solid #1e2a44;border-radius:10px;overflow:hidden;background:#0f1729}
html[data-theme="light"] .kpis{border-color:#e3e8f0;background:#fff}
.kpi{background:transparent;border:0;border-left:1px solid #1e2a44;
  border-radius:0;padding:10px 14px;min-width:112px;flex:1 1 0}
.kpi:first-child{border-left:0}
html[data-theme="light"] .kpi{border-left-color:#e3e8f0}
.kpi .k{font-size:11.5px;opacity:.62;margin-bottom:3px}
.kpi .v{font-size:26px;font-weight:600;line-height:1.15}
.kpi .k{font-size:10.5px;color:#7f90ad;letter-spacing:.5px}
.kpi .v{font-size:17px;font-weight:700;margin-top:2px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{padding:5px 7px;text-align:left;border-bottom:1px solid #16203a}
th{color:#8296b4;font-weight:600;font-size:10.5px;background:#0d1424;position:sticky;top:0}
td.l,th.l{text-align:left}
tr:hover td{background:#131c30}
.tk{font-weight:700;color:#cfe4ff}
.tv{color:#cfe4ff;text-decoration:none;border-bottom:1px dotted #4a90d9;font-weight:700}
.tv:hover{color:#4ade80;border-color:#4ade80}
.tv .tvs{opacity:0;font-size:10px;margin-left:3px}
.tv:hover .tvs{opacity:1}
.pos{color:#4ade80}.neg{color:#f87171}.dim{color:#7f90ad}
.badge{display:inline-block;padding:1px 7px;border-radius:999px;font-size:10.5px;font-weight:700}
.bar{height:8px;border-radius:4px;display:inline-block;vertical-align:middle;background:#22c55e}
.bar.neg{background:#ef4444}
.note{color:#7f90ad;font-size:11.5px;margin-top:9px;line-height:1.65}
.warn{background:#3a2410;border:1px solid #a0620f;color:#fbc06a;border-radius:8px;
 padding:9px 12px;font-size:12.5px;margin:0 0 13px;line-height:1.6}
.ok{background:#0f2a1a;border:1px solid #2c7a4b;color:#7fe0a3;border-radius:8px;
 padding:9px 12px;font-size:12.5px;margin:0 0 13px}
.filters{display:flex;flex-wrap:wrap;gap:7px;margin:0 0 11px;align-items:center}
input[type=search],select{background:#16203a;color:#e8eef8;border:1px solid #2a3a5c;
 border-radius:8px;padding:6px 10px;font-size:12.5px;font-family:inherit}
button{background:#16203a;color:#c7d4ea;border:1px solid #2a3a5c;border-radius:8px;
 padding:6px 11px;font-size:12.5px;cursor:pointer;font-family:inherit}
button:hover{background:#1d2a49}
button.on{background:#2b6cb0;border-color:#4a90d9;color:#fff;font-weight:700}
.scroll{max-height:70vh;overflow:auto}
footer{color:#5f708c;font-size:11.5px;margin-top:22px;line-height:1.7}
table,.kpi,.num,td{font-variant-numeric:tabular-nums}
code{background:#16203a;padding:1px 5px;border-radius:4px;font-size:11.5px}
.todo{background:#141d33;border:1px dashed #35507e;border-radius:10px;padding:14px;color:#9fb0cc;
 font-size:12.5px;line-height:1.75}
.chartwall{display:grid;grid-template-columns:repeat(auto-fill,minmax(74px,1fr));gap:9px}
.cand{border:1px solid #1e2a44;border-radius:8px;padding:6px 4px 5px;text-align:center;background:#0d1424;display:block;text-decoration:none;color:inherit}
.cand .tk{font-size:11.5px;font-weight:700;color:#cfe4ff;margin-top:3px}
.cand .mini{min-height:66px;display:flex;align-items:center;justify-content:center}
.cand:hover{border-color:#4a90d9}
.tk.hl{color:#22c55e;text-shadow:0 0 10px rgba(34,197,94,.4)}
tr.buyrow td{background:rgba(34,197,94,.07)}
.controls{display:flex;gap:6px;align-items:center;margin-left:auto;flex:0 0 auto}
.controls button{border-radius:8px;padding:5px 10px;font-size:11.5px}

/* ── 淺色主題（默認）── */
html[data-theme="light"] body{background:#f6f8fb;color:#1a2433}
html[data-theme="light"] a{color:#2563eb}
html[data-theme="light"] header.top{background:#ffffffee;border-bottom:1px solid #e3e8f0}
html[data-theme="light"] .crumb{color:#64748b}
html[data-theme="light"] nav a{color:#64748b}
html[data-theme="light"] nav a:hover{background:#eef2f8;color:#111827}
html[data-theme="light"] nav a.on{background:#ffffff;border-color:#dbe2ec;color:#111827}
html[data-theme="light"] .card{background:#ffffff;border-color:#e3e8f0;}
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
 border-radius:8px;font-size:12.5px;color:#9fb0cc;text-decoration:none;white-space:nowrap}
.sitenav a:hover{background:#121c31;color:#e8eef8}
.sitenav a.on{background:#2b6cb0;color:#fff;font-weight:700}
.sitenav button{margin-left:auto;border-radius:8px;padding:5px 10px;font-size:11.5px;
 background:#16203a;color:#c7d4ea;border:1px solid #2a3a5c;cursor:pointer;font-family:inherit}
"""

DESK_LIGHT_CSS = """
html[data-theme="light"] body{background:#f6f8fb;color:#1a2433}
html[data-theme="light"] .sub{color:#64748b}
html[data-theme="light"] h1,html[data-theme="light"] h2,html[data-theme="light"] h3{color:#111827}
html[data-theme="light"] .card{background:#ffffff;border-color:#e3e8f0;}
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
    ("leaders.html", "🚀", "RS Leader", False),
    ("cm.html", "🎯", "RS Pullback", False),
    ("week.html", "⚡", "Weekly MM", False),
    ("themes.html", "🧩", "Themes", False),
    ("sectors.html", "🏭", "Sectors", False),
    ("breadth.html", "🌊", "Breadth", False),
    ("positioning.html", "🎯", "Positioning", False),
    ("review.html", "⏪", "Review", False),
    ("rsboard.html", "📊", "RS 板", False),
    ("cycle.html", "🌀", "成長週期", False),
    ("setups.html", "📐", "Setups", False),
]


SIDEBAR_CSS = """
/* ═══ 左側導航（Desmond 2026-10-19：所有頁面選擇 bar 放左邊，方便手機） ═══ */
#sb{position:fixed;left:0;top:0;bottom:0;width:236px;z-index:9000;
  overflow-y:auto;overflow-x:hidden;padding:14px 10px 20px;
  background:#0b1220;border-right:1px solid #1e2a44;
  display:flex;flex-direction:column;gap:2px;
  transition:transform .22s ease}
html[data-theme="light"] #sb{background:#ffffff;border-right:1px solid #e3e8f0}
/* ★ 2026-10-20 Desmond：LOG BOOK 貼側欄最底（唔屬任何分組） */
#sb .sbbtm{margin-top:auto;padding-top:10px;
  border-top:1px solid rgba(128,128,128,.22)}
#sb .brand{font-size:14px;font-weight:700;letter-spacing:.04em;
  padding:6px 10px 12px;display:flex;align-items:baseline;gap:7px;
  color:inherit;text-decoration:none;flex-wrap:wrap}
#sb .bld{font-size:10px;font-weight:600;letter-spacing:0;opacity:.42;
  font-family:ui-monospace,monospace;margin-left:auto}
#sb .gw{margin:0}
#sb .grp{font-size:14px;font-weight:800;letter-spacing:.01em;
  text-transform:none;opacity:1;padding:11px 11px 7px;cursor:pointer;
  list-style:none;display:flex;align-items:center;gap:7px;
  user-select:none;color:inherit}
#sb .grp::-webkit-details-marker{display:none}
#sb .grp::before{content:"▸";font-size:10px;opacity:.55;
  transition:transform .15s;display:inline-block}
#sb .gw[open]>.grp::before{transform:rotate(90deg)}
#sb .grp:hover{color:#e8eef8}
html[data-theme="light"] #sb .grp:hover{color:#111827}
#sb .gl{padding:0 0 4px}
/* pinned 可展開分組（MODEL BOOK）*/
#sb .pinfold>.grp{padding:9px 11px;font-size:14px}
#sb .pinfold{margin:2px 0}
#sb a{display:flex;align-items:center;gap:9px;padding:9px 11px;border-radius:8px;
  font-size:14px;text-decoration:none;color:#9fb0cc;line-height:1.25}
#sb a:hover{background:#121c31;color:#e8eef8}
#sb a.on{background:#1d4ed8;color:#fff;font-weight:700}
html[data-theme="light"] #sb a{color:#4a5568}
html[data-theme="light"] #sb a:hover{background:#eef2f8;color:#111827}
html[data-theme="light"] #sb a.on{background:#2563eb;color:#fff}
#sb a span.i{flex:0 0 18px;text-align:center;font-size:14px}
#sb .spacer{flex:1 1 auto;min-height:14px}
#sb button{margin:8px 6px 0;padding:8px;border-radius:8px;border:1px solid #2a3346;
  background:#121c31;color:#e8eef8;font-size:12.5px;cursor:pointer;font-family:inherit}
/* ★ 深淺色按鈕：標題下面、細粒、左對齊（Desmond 2026-10-19） */
#sb #themebtn{margin:0 10px 12px;padding:6px 10px;border-radius:8px;
  font-size:11.5px;align-self:flex-start;background:transparent;
  border:1px solid #2a3346;color:#8fa0bd;letter-spacing:.02em}
#sb #themebtn:hover{background:#121c31;color:#e8eef8}
html[data-theme="light"] #sb #themebtn{background:transparent;
  border-color:#dbe2ec;color:#64748b}
html[data-theme="light"] #sb #themebtn:hover{background:#f3f6fa;color:#1a2433}
html[data-theme="light"] #sb button{background:#f3f6fa;border-color:#dbe2ec;color:#1a2433}

/* ★ 2026-10-19 側欄收合（Desmond：左邊加個小球可以縮個欄） */
#sbtoggle{position:fixed;left:236px;top:14px;z-index:9100;
  width:26px;height:26px;border-radius:50%;border:1px solid #4b5563;
  background:#0f1729;color:#9fb0cc;font-size:10.5px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  transition:left .22s ease,background .15s;font-family:inherit;padding:0}
#sbtoggle:hover{background:#1d4ed8;color:#fff;border-color:#1d4ed8}
html[data-theme="light"] #sbtoggle{background:#fff;border-color:#cbd5e1;
  color:#64748b}
html[data-theme="light"] #sbtoggle:hover{background:#2563eb;color:#fff}
#sb.collapsed{width:62px}
#sb.collapsed .brand{font-size:0;padding:10px 0;text-align:center}
#sb.collapsed .brand::before{content:"📈";font-size:17px}
#sb.collapsed #themebtn{display:none}
#sb.collapsed .grp{font-size:0;padding:8px 0;border-top:1px solid #1e2a44;
  margin:4px 8px}
#sb.collapsed a{justify-content:center;padding:9px 0}
#sb.collapsed a .lbl{display:none}
#sb.collapsed a .ab{display:block!important}
#sb a .ab{display:none!important;font-size:10.5px;font-weight:700;letter-spacing:.02em}
/* ★ 修（2026-10-19）：#sbtoggle 係 #sb 嘅兄弟節點，唔係後代，
   `#sb.collapsed #sbtoggle` 永遠 match 唔到 → 改用 body class */
body.sb-collapsed #sbtoggle{left:62px}

#navtoggle{display:none;position:fixed;left:10px;top:10px;z-index:9100;
  width:42px;height:42px;border-radius:10px;border:1px solid #2a3346;
  background:#0b1220ee;color:#e8eef8;font-size:20px;cursor:pointer;
  align-items:center;justify-content:center;line-height:1}
html[data-theme="light"] #navtoggle{background:#ffffffee;border-color:#dbe2ec;color:#1a2433}
#navoverlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:8999}
#navoverlay.show{display:block}
/* 桌面：內容右移 */
@media(min-width:901px){
  body{padding-left:236px}
  /* desk.html 自己嘅頂部 nav 隱藏（已由 sidebar 取代） */
  nav.sitenav{display:none!important}
}
/* 手機：sidebar 變 drawer */
@media(max-width:900px){
  #sb{transform:translateX(-100%);
      padding-top:56px}
  #sb.open{transform:translateX(0)}
  #navtoggle{display:flex}
  body{padding-left:0}
  header.top{padding-top:56px}
  /* ★ 2026-10-19 Desmond：「小圓球可以跟住左邊隱藏時一齊收入」
     drawer 關閉時圓球一齊滑出畫面，唔會浮喺中間。 */
  #sbtoggle{left:0;top:14px;
    transform:translateX(-58px);opacity:0;pointer-events:none;
    transition:transform .22s ease,opacity .18s ease}
  body.drawer-open #sbtoggle{
    transform:translateX(202px);opacity:1;pointer-events:auto}
  body.drawer-open.sb-collapsed #sbtoggle{transform:translateX(28px)}
}

/* ══════════════════════════════════════════════════════════════
   ★ 2026-10-19 Desmond：「深色版我想風格改成 CLAUDE 既風格顏色」
   Claude（Anthropic）深色配色：
     頁面底 #1F1E1D｜卡片 #262624｜浮起 #30302E｜邊框 #3E3E38
     主文字 #FAF9F5（奶白）｜次文字 #B7B5A9｜弱 #8B8A82
     強調 #D97757（赤陶橙）｜綠 #7DBE8A｜紅 #E2816D
   ★ 只覆寫深色（light 模式由上方 html[data-theme="light"] 控制）
   ══════════════════════════════════════════════════════════════ */
html[data-theme="dark"] body{background:#1F1E1D;color:#FAF9F5}
html[data-theme="dark"] a{color:#D97757}
html[data-theme="dark"] header.top{background:#262624E6;
  border-bottom:1px solid #3E3E38}
html[data-theme="dark"] .crumb{color:#8B8A82}
html[data-theme="dark"] .card{background:#262624;border-color:#3E3E38;
  }
html[data-theme="dark"] .card h2{background:#30302E;border-color:#3E3E38;
  color:#FAF9F5}
html[data-theme="dark"] .card h2 small{color:#B7B5A9}
html[data-theme="dark"] .kpi{background:#262624;border-color:#3E3E38}
html[data-theme="dark"] .kpi .k{color:#8B8A82}
html[data-theme="dark"] th{background:#30302E;color:#B7B5A9;
  border-color:#3E3E38}
html[data-theme="dark"] td{border-color:#33332F}
html[data-theme="dark"] tr:hover td{background:#2C2C29}
html[data-theme="dark"] .tk{color:#FAF9F5}
html[data-theme="dark"] .dim{color:#8B8A82}
html[data-theme="dark"] .note{color:#B7B5A9}
html[data-theme="dark"] .up{color:#7DBE8A}
html[data-theme="dark"] .dn{color:#E2816D}
html[data-theme="dark"] .buyrow td{background:rgba(217,119,87,.10)}
html[data-theme="dark"] .hl{color:#D97757}
html[data-theme="dark"] code{background:#30302E;color:#E8C4B0}
/* 側欄 */
html[data-theme="dark"] #sb{background:#262624;
  border-right:1px solid #3E3E38;}
html[data-theme="dark"] #sb .brand{color:#FAF9F5}
html[data-theme="dark"] #sb .grp{color:#8B8A82;border-top-color:#38382F}
html[data-theme="dark"] #sb a{color:#B7B5A9}
html[data-theme="dark"] #sb a:hover{background:#30302E;color:#FAF9F5}
html[data-theme="dark"] #sb a.on{background:#3A2E28;color:#F0A882;
  border-left:2px solid #D97757}
html[data-theme="dark"] #sbtoggle{background:#30302E;border-color:#4A4A42;
  color:#B7B5A9}
html[data-theme="dark"] #sbtoggle:hover{background:#D97757;color:#1F1E1D;
  border-color:#D97757}
html[data-theme="dark"] #navtoggle{background:#262624EE;
  border-color:#3E3E38;color:#FAF9F5}
html[data-theme="dark"] #themebtn{background:#30302E;color:#B7B5A9}
/* 按鈕 / 分頁 */
html[data-theme="dark"] nav a{color:#B7B5A9}
html[data-theme="dark"] nav a:hover{background:#30302E;color:#FAF9F5}
html[data-theme="dark"] nav a.on{background:#3A2E28;border-color:#D97757;
  color:#F0A882}
/* 統計數字仍用色碼但調暖 */
html[data-theme="dark"] .jb-ok,.html[data-theme="dark"] .kn-ok{color:#7DBE8A}
html[data-theme="dark"] .pos{color:#7DBE8A}
html[data-theme="dark"] .neg{color:#E2816D}
html[data-theme="dark"] .bar{background:#7DBE8A}
html[data-theme="dark"] .tk.hl{color:#E8A07E;
  text-shadow:0 0 10px rgba(217,119,87,.35)}
html[data-theme="dark"] .tv:hover{color:#D97757;border-color:#D97757}
html[data-theme="dark"] .up,html[data-theme="dark"] .g{color:#7DBE8A}
html[data-theme="dark"] .dn,html[data-theme="dark"] .r{color:#E2816D}
html[data-theme="dark"] .mark{background:#D97757;color:#1F1E1D}
html[data-theme="dark"] button,html[data-theme="dark"] .btn{
  background:#30302E;border-color:#4A4A42;color:#FAF9F5}
html[data-theme="dark"] button:hover{background:#3A3A35}
html[data-theme="dark"] button.on,html[data-theme="dark"] .btn.pri{
  background:#D97757;border-color:#D97757;color:#1F1E1D}
html[data-theme="dark"] input,html[data-theme="dark"] select{
  background:#30302E;border-color:#4A4A42;color:#FAF9F5}
html[data-theme="dark"] .scroll::-webkit-scrollbar-thumb{background:#4A4A42}
html[data-theme="dark"] ::selection{background:#D97757;color:#1F1E1D}
html[data-theme="dark"] .jb-err{color:#E2816D}
/* ══════════════════════════════════════════════════════════════
   ★ 2026-10-19 Desmond：「3, 4」
   ③ 赤陶橙用得更重（標題、按鈕、選中項全部橙）
   ④ 淺色版也改成 Claude 淺色
   Claude 淺色：底 #FAF9F5｜卡片 #FFFFFF｜邊框 #E3E1DA
                主字 #1F1E1D｜次字 #6B6A63｜強調 #D97757
   ══════════════════════════════════════════════════════════════ */
/* ── ③ 深色：橙加得更重 ── */
html[data-theme="dark"] .card h2{
  color:#F0A882;border-bottom-color:#4A3A32}
html[data-theme="dark"] .card h2 small{color:#B7B5A9}
html[data-theme="dark"] .kpi .v{color:#FAF9F5}
html[data-theme="dark"] #sb a.on{background:#3A2E28;color:#F0A882;
  border-left:3px solid #D97757;font-weight:700}
html[data-theme="dark"] #sb .brand{color:#F0A882}
html[data-theme="dark"] nav a.on{background:#3A2E28;border-color:#D97757;
  color:#F0A882;font-weight:700}
html[data-theme="dark"] .tk.hl{color:#D97757}
html[data-theme="dark"] .hl{color:#D97757;font-weight:800}
html[data-theme="dark"] .jb-group>summary{color:#F0A882}
html[data-theme="dark"] .jb-card{border-color:#3E3E38}
html[data-theme="dark"] .jb-chip{border-color:#4A4A42;color:#B7B5A9}
html[data-theme="dark"] .seg button.on,
html[data-theme="dark"] .c-seg button.on{
  background:#D97757!important;border-color:#D97757!important;
  color:#1F1E1D!important;font-weight:800}
html[data-theme="dark"] .badge,html[data-theme="dark"] .pill{
  background:#3A2E28;border-color:#D97757;color:#F0A882}

/* ── ④ 淺色版改成 Claude 淺色 ── */
html[data-theme="light"] body{background:#FAF9F5;color:#1F1E1D}
html[data-theme="light"] a{color:#C4633F}
html[data-theme="light"] header.top{background:#FAF9F5EE;
  border-bottom:1px solid #E3E1DA}
html[data-theme="light"] .crumb{color:#6B6A63}
html[data-theme="light"] .card{background:#FFFFFF;border-color:#E3E1DA;
  }
html[data-theme="light"] .card h2{background:#F4F2ED;
  border-color:#E3E1DA;color:#1F1E1D}
html[data-theme="light"] .card h2 small{color:#6B6A63}
html[data-theme="light"] .kpi{background:#FFFFFF;border-color:#E3E1DA}
html[data-theme="light"] .kpi .k{color:#6B6A63}
html[data-theme="light"] th{background:#F4F2ED;color:#6B6A63;
  border-color:#E3E1DA}
html[data-theme="light"] td{border-color:#EFEDE7}
html[data-theme="light"] tr:hover td{background:#FAF8F4}
html[data-theme="light"] .tk{color:#1F1E1D}
html[data-theme="light"] .dim{color:#8E8C84}
html[data-theme="light"] .note{color:#6B6A63}
html[data-theme="light"] .pos,html[data-theme="light"] .up{color:#2E7D4F}
html[data-theme="light"] .neg,html[data-theme="light"] .dn{color:#C0402C}
html[data-theme="light"] .bar{background:#D97757}
html[data-theme="light"] .tk.hl{color:#D97757;text-shadow:none}
html[data-theme="light"] .hl{color:#C4633F;font-weight:800}
html[data-theme="light"] .buyrow td{background:rgba(217,119,87,.07)}
html[data-theme="light"] code{background:#F4F2ED;color:#8A4A32}
html[data-theme="light"] #sb{background:#F4F2ED;border-right:1px solid #E3E1DA}
html[data-theme="light"] #sb .brand{color:#C4633F}
html[data-theme="light"] #sb .grp{color:#8E8C84;border-top-color:#E3E1DA}
html[data-theme="light"] #sb a{color:#4A4842}
html[data-theme="light"] #sb a:hover{background:#EAE7E0;color:#1F1E1D}
html[data-theme="light"] #sb a.on{background:#F7E9E3;color:#C4633F;
  border-left:3px solid #D97757;font-weight:700}
html[data-theme="light"] #sbtoggle{background:#FFFFFF;border-color:#DAD9D4;
  color:#6B6A63}
html[data-theme="light"] #sbtoggle:hover{background:#D97757;color:#fff;
  border-color:#D97757}
html[data-theme="light"] nav a{color:#6B6A63}
html[data-theme="light"] nav a:hover{background:#F4F2ED;color:#1F1E1D}
html[data-theme="light"] nav a.on{background:#F7E9E3;border-color:#D97757;
  color:#C4633F;font-weight:700}
html[data-theme="light"] button,html[data-theme="light"] .btn{
  background:#FFFFFF;border-color:#DAD9D4;color:#1F1E1D}
html[data-theme="light"] button:hover{background:#F4F2ED}
html[data-theme="light"] button.on,html[data-theme="light"] .btn.pri,
html[data-theme="light"] .seg button.on{
  background:#D97757!important;border-color:#D97757!important;
  color:#FFFFFF!important;font-weight:800}
html[data-theme="light"] .jb-group>summary{color:#C4633F}
html[data-theme="light"] .jb-card{border-color:#E3E1DA;
  background:#FFFFFF}

"""

SIDEBAR_LINKS = [
    # 2026-10-19 方案 C：5 個分組；廚房看板獨立最頂；PLAYBOOK 最底
    # ★ 2026-10-24 Desmond：「每日流程放最頂」
    ("_pinned", "", "每日流程", "process.html"),
    ("_pinned", "", "收工標準", "finish.html"),
    ("_pinned", "", "廚房看板", "jobboard.html"),
    ("_pinned", "", "DATABASE", "datahealth.html"),

    ("_grp", "市場"),
    ("_link", None, "MARKET REGIME", "regime_mri.html"),
    ("_link", None, "市場簡報", "index.html"),
    ("_link", None, "Breadth", "breadth.html"),
    ("_link", None, "Market Monitor", "mm.html"),

    # ★ 2026-10-24 Desmond：「加多個主題 放市場下面；RS板改名 RS THEME」
    ("_grp", "主題"),
    ("_link", None, "RS THEME", "rsboard.html"),
    ("_link", None, "Sectors", "sectors.html"),

    # ★ 2026-10-24 Jeff Sun 決策漏斗：環境→個股→計劃→觸發→風險→edge 庫
    #   原則：計劃先於觸發（pivot/stop/size 寫好先准 Alert）；只做 A+
    # ★ 2026-10-24 Desmond 指定排位：
    #   Daily Scan > Alert (Set up alert) > 領導股 (RS leader) >
    #   RS Before Price > 1CM 回調 (RS Pullback) > 最強 1 週 (Weekly MM)
    ("_grp", "選股"),
    ("_link", None, "Daily Scan", "dailyscan.html"),
    ("_link", None, "Setup Alert", "alerts.html"),
    ("_link", None, "RS Leader", "leaders.html"),
    ("_link", None, "RS Before Price", "rsbeforeprice.html"),
    ("_link", None, "RS Pullback", "cm.html"),
    ("_link", None, "Weekly MM", "week.html"),
    # ── 其餘（維持原本相對次序）──
    ("_link", None, "RS Leader 位置圖", "leadermap.html"),
    ("_link", None, "RS Daily Scan", "rsscan.html"),
    ("_link", None, "沙灘球反應", "beachball.html"),
    ("_link", None, "投降儀表", "feargauge.html"),
    ("_link", None, "肥球掃描（J Law）", "fatpitch.html"),
    ("_link", None, "Tight Range", "tightscan.html"),
    ("_link", None, "The Plan", "setups.html"),
    ("_ext", None, "財報（Finviz）", "https://finviz.com/calendar/earnings/season-preview?view=list&sort=marketCap"),
    ("_link", None, "YOYO Ball", "yoyo_ball.html"),
    ("_link", None, "Setup 矩陣", "regime.html"),

    ("_grp", "成績"),
    ("_link", None, "Think in R", "thinkinr.html"),
    ("_link", None, "Backtest", "backtest.html"),
    ("_link", None, "系統審計", "audit.html"),
    ("_link", None, "Edge Improving", "edgeimprove.html"),
    ("_link", None, "Positioning", "positioning.html"),
    ("_link", None, "Review", "review.html"),
    ("_link", None, "覆盤（R／期望值）", "review2.html"),
    ("_link", None, "倉位計算機", "calculator.html"),

    ("_grp", "方法"),
    ("_link", None, "Van Tharp 五法", "vantharp.html"),
    ("_link", None, "優化帳本", "optledger.html"),
    ("_link", None, "Setup Factory", "setupfactory.html"),
    ("_link", None, "成長週期", "cycle.html"),

    ("_grp", "PLAYBOOK"),
    ("_ext", "", "Jeff Sun 工具/流程", "https://jfsrev.substack.com/p/my-trading-tools-process-routine"),
    ("_ext", "", "PrimeTrading 手冊", "https://traderslab.gitbook.io/primetrading"),
    ("_ext", "", "Qullamaggie", "https://qullamaggie.net/"),
    ("_ext", "", "QM 3 個 setups", "https://qullamaggie.com/my-3-timeless-setups-that-have-made-me-tens-of-millions/"),
    ("_ext", "", "Alex Desjardins 方法", "https://qullamaggie.net/alex-desjardinss-method/"),

    # ★ 2026-10-28 Desmond：MODEL BOOK 放喺 PLAYBOOK 同外部數據中間，唔要 emoji
    ("_fold", "", "MODEL BOOK", "modelbook.html", [
        ("概覽", "modelbook.html"),
        ("Top 250 US Gainers", "mb_top250.html"),
        ("量化案例庫", "modelbook.html#cases"),
    ]),

    # ★ 2026-10-23 Desmond：「外部數據放到 PLAYBOOK 下一行」+ 合併 8→2
    ("_grp", "外部數據"),
    ("_link", None, "外部數據源", "external.html"),
    ("_link", None, "Market Pulse", "levelup.html"),

    # ★ 2026-10-20 Desmond：LOG BOOK 貼側欄最底，唔屬於任何分組
    ("_bottom", "", "LOG BOOK", "logbook.html"),
]

SIDEBAR_JS = """
(function(){
  var sb=document.getElementById('sb'), tg=document.getElementById('sbtoggle');
  if(!sb||!tg) return;
  var KEY='desk-sb-collapsed';
  function apply(c){
    sb.classList.toggle('collapsed', c);
    document.body.classList.toggle('sb-collapsed', c);
    tg.innerHTML = c ? '&rsaquo;' : '&lsaquo;';
    tg.title = c ? '展開側欄' : '收合側欄';
    try{localStorage.setItem(KEY, c?'1':'0');}catch(e){}
  }
  tg.addEventListener('click', function(){ apply(!sb.classList.contains('collapsed')); });
  var st='0';
  try{st=localStorage.getItem(KEY)||'0';}catch(e){}
  apply(st==='1');
})();


(function(){
  var sb=document.getElementById('sb'), tg=document.getElementById('navtoggle'),
      ov=document.getElementById('navoverlay');
  if(!sb||!tg) return;
  function open(){sb.classList.add('open');
    document.body.classList.add('drawer-open');
    if(ov)ov.classList.add('show');
    tg.setAttribute('aria-expanded','true');}
  function close(){sb.classList.remove('open');
    document.body.classList.remove('drawer-open');
    if(ov)ov.classList.remove('show');
    tg.setAttribute('aria-expanded','false');}
  tg.addEventListener('click',function(e){e.stopPropagation();
    sb.classList.contains('open')?close():open();});
  if(ov) ov.addEventListener('click',close);
  sb.querySelectorAll('a').forEach(function(a){
    a.addEventListener('click',function(){ if(window.innerWidth<=900) close(); });
  });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape') close(); });
})();
"""


def sidebar_html(active=""):
    # 左側導航 HTML（active = 檔名，例如 'desk.html'）
    # ★ 2026-10-19 Desmond：「全部標題太細 用返同下面相同既字」「使用粗體」
    #   「如果無禁入去佢會自動收起」
    #   → 分組標題同連結一樣字級（13.5px）＋粗體，每組係 <details>，
    #     只有「當前頁所屬組」預設展開，其餘自動收起。
    def _link(label, href, cls="", extra=""):
        on = ' class="on"' if href == active else ""
        ab = label[:2] if len(label) > 1 else label[:1]
        return (f'<a href="{href}"{on}{extra}>'
                f'<span class="ab">{esc(ab)}</span>'
                f'<span class="lbl">{label}</span></a>')

    head = []
    bottom = []           # ★ 唔屬於任何分組，貼側欄最底
    groups = []            # [(name, [html...])]
    cur = None
    for row in SIDEBAR_LINKS:
        kind = row[0]
        if kind == "_grp":
            cur = (row[1], [])
            groups.append(cur)
        elif kind == "_ext":
            _, icon, label, href = row
            html = (f'<a href="{href}" target="_blank" rel="noopener" '
                    f'class="ext-link"><span class="i">{icon}</span>'
                    f'<span class="lbl">{label}</span></a>')
            (cur[1] if cur else head).append(html)
        elif kind == "_fold":
            # ★ 2026-10-24 Desmond：「MODEL BOOK 左邊禁一下 → 下面出下選分頁」
            #   pinned 位置嘅可展開分組：<details> 一撳就開，子項就係分頁。
            _, icon, label, href, kids = row
            is_open = any(h == active for _l, h in kids) if active else False
            gl = "".join(
                '<a href="%s"%s><span class="ab">%s</span>'
                '<span class="lbl">%s</span></a>'
                % (h, ' class="on"' if h == active else "",
                   esc(l[:2]), esc(l))
                for l, h in kids)
            fold_html = (f'<details class="gw pinfold"{" open" if is_open else ""}>'
                         f'<summary class="grp">{icon} {esc(label)}</summary>'
                         f'<div class="gl">{gl}</div></details>')
            # ★ 2026-10-24：_fold 唔再永遠擺最頂 ——
            #   喺分組入面就擺喺該分組（跟 SIDEBAR_LINKS 位置），否則擺 head。
            (cur[1] if cur else head).append(fold_html)
        elif kind == "_pinned":
            _, icon, label, href = row
            on = ' class="on"' if href == active else ""
            head.append(f'<a href="{href}"{on} data-pin="1">'
                        f'<span class="i">{icon}</span>'
                        f'<span class="lbl">{label}</span></a>')
        elif kind == "_bottom":
            _, icon, label, href = row
            bottom.append(_link(label, href, extra=' data-bottom="1"'))
            cur = None
        else:                                              # _link
            _, _ic, label, href = row
            (cur[1] if cur else head).append(_link(label, href))
    # ★ 每組係 <details>：只有「當前頁所屬組」預設展開，其餘自動收起
    body = []
    for name, links in groups:
        is_open = any(f'href="{active}"' in h for h in links) if active else False
        body.append(
            f'<details class="gw"{" open" if is_open else ""}>'
            f'<summary class="grp">{name}</summary>'
            '<div class="gl">' + "".join(links) + '</div></details>')
    # ★ 深淺色選項移到標題下面（原本喺最底，要捲到底才撳到）
    return ('<button id="navtoggle" aria-label="選單" aria-expanded="false">☰</button>'
            '<div id="navoverlay"></div>'
            '<button id="sbtoggle" title="收合側欄">&lsaquo;</button>'
            '<aside id="sb">'
            '<a class="brand" href="index.html">HI! Desmond'
            f'<span class="bld">{__import__("datetime").datetime.now().strftime("%m-%d %H:%M")}</span>'
            '</a>'
            '<button id="themebtn">🌙 深色</button>'
            + "".join(head) + "".join(body)
            + ('<div class="sbbtm">' + "".join(bottom) + '</div>'
               if bottom else '')
            + '</aside>')


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
    # ★ desk.html 自己有個 themebtn → 改名避免同 sidebar 撞 ID（sidebar 嗰個係唯一控制）
    html = html.replace('id="themebtn"', 'id="themebtn-old" style="display:none"', 1)

    inject = (f'<style>{DESK_LIGHT_CSS}{SIDEBAR_CSS}</style>'
              + sidebar_html("desk.html") +
              f'<script>{DESK_THEME_JS}</script>'
              f'<script>{SIDEBAR_JS}</script>')
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
    # ★ LOG BOOK：只喺 logbook.html 自己一頁顯示，其他頁唔加
    LOGBOOK = ""
    return f"""<!doctype html><html lang="zh-Hant" data-theme="light"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · 交易台</title>
<script>/* ★ 2026-10-24 修「閃白」：喺 CSS 之前先套用已存主題，
   否則 dark 用戶會先見到 light 一幀（FOUC）。key = desk-theme（JSON 字串）。*/
(function(){{try{{
  var v=localStorage.getItem('desk-theme');
  if(v){{try{{v=JSON.parse(v);}}catch(e){{}}
    if(v==='dark'||v==='light')document.documentElement.setAttribute('data-theme',v);}}
}}catch(e){{}}}})();</script>
<link rel="stylesheet" href="site.css?v={BUILD_TS}">{extra_head}</head><body>
<script>
/* ★ 自動更新：用返原來網址，頁面發現有新 build 就自己 reload 一次
   唔會迴圈：sessionStorage 記住已 reload 過嘅版本 */
(function(){{
  var BV="{BUILD_TS}";
  try{{
    if(sessionStorage.getItem('hv')===BV) return;
  }}catch(e){{}}
  fetch('version.json?t='+Date.now(),{{cache:'no-store'}})
    .then(function(r){{return r.ok?r.json():null;}})
    .then(function(d){{
      if(!d||!d.v||d.v===BV) return;
      /* ★ 2026-10-25 修「無限 reload」：如果今次 session 已經為呢個版本 reload 過，
         就唔好再 reload。舊檔（BV 落後）以前會同 version.json 永遠唔相等 → 無限迴圈。*/
      try{{
        if(sessionStorage.getItem('hv')===d.v) return;
        sessionStorage.setItem('hv',d.v);
      }}catch(e){{}}
      var u=new URL(location.href);
      u.searchParams.set('v',d.v.replace(/\\D/g,''));
      location.replace(u.toString());
    }})
    .catch(function(){{}});
}})();
</script>
{sidebar_html("index.html" if active == "briefing" else (active + ".html" if active else ""))}
<div class="wrap">
<header class="top">
 <div style="display:flex;align-items:flex-start;gap:10px">
  <div style="flex:1 1 auto">
   <h1><span>HI! Desmond</span></h1>
   <p class="crumb">繁體中文版｜骨架蒸餾自 <a href="https://i-manage-risk.github.io/NEL/index.html" target="_blank" rel="noopener">NEL · Market console</a>（逆向工程）｜資料 <code>{payload.get('_generated','?')}</code></p>
  </div>
 </div>
</header>
{body}
{LOGBOOK}
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
<script>{SIDEBAR_JS}</script>
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


def _champion_card():
    """Champion 組合 hero（Desmond 2026-10-24）：每日 top-3 模擬資金曲線。

    數據：sim_ledger/fleet/champion/（equity.csv + trades.jsonl）
         ＋ output/today_six.json（今日 3 條 / 0 單）
    """
    import csv as _csv
    led = r"C:/Users/rain0/trading-os/sim_ledger/fleet/champion"
    eq = os.path.join(led, "equity.csv")
    tr = os.path.join(led, "trades.jsonl")
    nav, nav_date = None, ""
    if os.path.exists(eq):
        try:
            with io.open(eq, encoding="utf-8") as f:
                rows = list(_csv.DictReader(f))
            if rows:
                nav = float(rows[-1].get("equity") or 0)
                nav_date = rows[-1].get("date") or ""
        except Exception:                                     # noqa: BLE001
            pass
    rs = []
    if os.path.exists(tr):
        for line in io.open(tr, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                v = json.loads(line).get("r")
                if v is not None:
                    rs.append(float(v))
            except Exception:                                 # noqa: BLE001
                continue
    n = len(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    wr = (len(wins) / n * 100) if n else 0
    avg_w = (sum(wins) / len(wins)) if wins else 0
    avg_l = (sum(losses) / len(losses)) if losses else 0
    payoff = (avg_w / abs(avg_l)) if avg_l else float("inf")
    tot_r = sum(rs)
    ret = ((nav / 100000 - 1) * 100) if nav else 0.0
    ret_cls = "#7DBE8A" if ret >= 0 else "#E88A8A"

    ts = r"C:/Users/rain0/trading-os/output/today_six.json"
    today, veto = [], ""
    if os.path.exists(ts):
        try:
            d = json.load(io.open(ts, encoding="utf-8"))
            regime = d.get("regime")
            cap = d.get("trade_cap")
            if regime == "BEAR" or cap == 0:
                veto = f"regime={regime}／cap={cap} → 0 單（坐定定）"
            else:
                picks = sorted(d.get("picks") or [],
                               key=lambda p: (p.get("dist_pivot_atr") or 99))
                for p in picks[:3]:
                    today.append((p.get("ticker"), p.get("close"),
                                  p.get("pivot"), p.get("rs_1m")))
        except Exception:                                     # noqa: BLE001
            pass

    payoff_s = "∞" if payoff == float("inf") else f"{payoff:.2f}"
    h = ['<div class="card" style="border-left:4px solid #E8A33D">'
         '<div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap">'
         '<h2 style="margin:0;padding:0;background:transparent;border:0;'
         'font-size:20px">Champion 組合 '
         '<small style="font-size:12.5px;font-weight:400">每日 top-3｜paper</small></h2>'
         f'<span style="font-size:11.5px;opacity:.65">數據截至 {esc(nav_date)}</span>'
         '</div>']
    if nav:
        h.append(f'<div style="font-size:26px;font-weight:800;color:{ret_cls}">'
                 f'${nav:,.0f}　<span style="font-size:14px">{ret:+.2f}%</span></div>')
        h.append('<div class="kpis" style="margin:8px 0 10px">')
        for _l, _v, _c in (("單數", f"{n}", ""),
                           ("勝率", f"{wr:.0f}%", ""),
                           ("贏輸比", f"{payoff_s}", ""),
                           ("總 R", f"{tot_r:+.2f}", ret_cls)):
            h.append(f'<div class="kpi"><div class="k">{_l}</div>'
                     f'<div class="v" style="color:{_c}">{_v}</div></div>')
        h.append('</div>')
    else:
        h.append('<div class="dim">Champion 帳本未結算</div>')
    h.append('<div style="margin:4px 0 2px;font-size:11.5px;opacity:.7">今日 3 條</div>')
    if veto:
        h.append(f'<div style="color:#E8A33D;font-weight:700">🛑 {esc(veto)}</div>')
    elif today:
        for t, c, piv, r1 in today:
            h.append(f'<div style="margin:3px 0;font-size:12.5px">'
                     f'<b>{esc(t)}</b>　收 {esc(c)}｜pivot {esc(piv)}'
                     f'（RS 1M {esc(r1) if r1 is not None else "—"}%）</div>')
    else:
        h.append('<div class="dim">今日冇 today_six.json</div>')
    h.append('<img src="fleet_equity.png" alt="資金曲線" '
             'style="width:100%;max-width:100%;border-radius:8px;margin-top:8px;'
             'border:1px solid rgba(128,128,128,.25)">')
    h.append('<div style="margin-top:8px;font-size:11.5px;opacity:.6">'
             '出場階梯 = 2R 減 33% → ATRX8 減 33% → 拖 10EMA 全清（SOUL §4.3）。'
             '熊市 0 單，唔硬做。</div></div>')
    return "".join(h)


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
        ("站上 50MA", pct(bt.get("above50")), "#7DBE8A"),
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
    # ★ Stockbee Market Monitor（升4%/跌4% 家數）—— Desmond 2026-10-19
    try:
        import newfeeds as _nf2
        _sbf = _nf2.load_all().get("mm")
    except Exception:                                        # noqa: BLE001
        _sbf = None
    # ★ 2026-10-19 Desmond：「放入去市場簡報」—— 成長/價值風險閘搬入簡報
    _gc = None
    try:
        _gc = extras.growth_cycle()
    except Exception:                                        # noqa: BLE001
        _gc = None
    _gc_card = ""
    if _gc:
        _ph = _gc["phase"]
        _phc = {"RISK-OFF": "#ef4444", "PROBE": "#f59e0b",
                "RAMP UP": "#22c55e", "TRIM/HOLD": "#0ea5e9",
                "RELOAD": "#a78bfa"}.get(_ph, "#94a3b8")
        _side = "RISK-ON" if _gc["side"] == "on" else "RISK-OFF"
        _sidec = "#22c55e" if _gc["side"] == "on" else "#ef4444"
        _gc_card = (
            '<div class="card"><h2>成長／價值 風險閘 '
            f'<small>IWF {_gc["iwf"]} ／ IWD {_gc["iwd"]}'
             f'｜週線最後完整週 {esc(_gc["as_of"])}</small></h2>'
            '<div class="body">'
            '<div class="kpis" style="margin-bottom:10px">'
            f'<div class="kpi"><div class="k">現時階段</div>'
            f'<div class="v" style="color:{_phc}">{esc(_ph)}</div></div>'
            f'<div class="kpi"><div class="k">方向</div>'
            f'<div class="v" style="color:{_sidec}">{_side}</div></div>'
            f'<div class="kpi"><div class="k">比率 IWF÷IWD</div>'
            f'<div class="v">{_gc["ratio"]}</div></div>'
            f'<div class="kpi"><div class="k">上軌／下軌</div>'
            f'<div class="v">{_gc["up"]} / {_gc["dn"]}</div></div>'
            '</div>'
            f'{cycle_svg(_gc["series"])}'
            '<div class="note">綠線＝IWF÷IWD 比率（週收市）；灰線＝週高低 EMA10 風險閘；'
            '藍色陰影＝閘帶。收市升穿上軌＝risk-on、跌穿下軌＝risk-off、軌內＝維持上一邊。'
            '六個階段：RISK-OFF → PROBE → RAMP UP → TRIM/HOLD → RELOAD → 回落。'
            '⚠ 模型由你圖片蒸餾，用 <b>IWF/IWD</b>（羅素 1000 成長÷價值）。'
            '<a href="cycle.html">完整頁 →</a></div></div></div>')

    # ★ 圖表隊列標題：永遠顯示真實狀態，唔准扮「今日」
    _rs_st = brief.get("rs_status")
    if _rs_st == "MISSING":
        _qhead = "⛔ 圖表隊列（冇數據）"
        _qnote = ("<div style=\"color:#dc2626;font-weight:700;margin-bottom:8px\">"
                  "⛔ 搵唔到任何 rs_select 檔案 —— 呢個功能冇數據，"
                  "下面唔會有股票。</div>")
    elif _rs_st == "STALE":
        _age = brief.get("rs_age")
        _mt = brief.get("rs_mtime") or "?"
        _qhead = f"⚠️ 圖表隊列（過期 {_age} 日）"
        _qnote = ("<div style=\"color:#dc2626;font-weight:700;margin-bottom:8px\">"
                  f"⚠️ 呢啲股票係 <b>{_mt}</b> 嘅數據，已經 <b>{_age} 日</b> "
                  "冇更新 —— <b>唔係今日嘅名單</b>。"
                  "rs_select 冇對應嘅 cron job，所以一直唔會更新。</div>")
    else:
        _qhead = "圖表隊列"
        _qnote = ""

    # ★ 2026-10-20 Desmond：市場簡報 - RS THEMES 改用新 Google Sheet
    #   呢個 Sheet 嘅公式靠 add-on 即時算，匯出全部 #N/A（XLK 481 行冇數）
    #   → 唯一可行係 iframe 原貌（htmlembed 無 X-Frame-Options）
    _themes_sid = "1TDiU6Wt0YYoJ1YPEtcwqWY4UU8FMj1vLLYFxQitg6oE"
    _themes_gid = "634720175"
    _themes = (
        '<div class="card"><h2>RS THEMES <small>原 Sheet 即時（iframe）</small></h2>'
        '<div class="body">'
        '<div class="note">資料直接來自 Desmond 指定嘅 Google Sheet，'
        '由 Google 即時計算 —— <b>網站唔會快取、唔會造假</b>。'
        '如果你想睇其他分頁（XLK/XLF/…），喺下面嘅 Sheet 自己切換。</div>'
        f'<iframe src="https://docs.google.com/spreadsheets/d/{_themes_sid}'
        f'/htmlembed?gid={_themes_gid}&amp;widget=true&amp;headers=false" '
        'style="width:100%;height:620px;border:0;border-radius:10px;'
        'background:#fff" loading="lazy" referrerpolicy="no-referrer">'
        '</iframe>'
        f'<div style="margin-top:8px;font-size:11.5px;opacity:.6">'
        f'Sheet ID <code>{_themes_sid[:12]}…</code>｜gid {_themes_gid}'
        '｜嵌入失敗時請直接開原 Sheet</div>'
        '</div></div>')

    # ★ 2026-10-20 Desmond：Wishing Wealth GMI（Dr. Wish）外部數據
    try:
        import wishingwealth as _ww
        _gmi_card = _ww.card_html()
    except Exception as _e18:
        _gmi_card = (f'<div class="warn">Wishing Wealth 讀唔到：'
                     f'{type(_e18).__name__}</div>')

    # ★ pulse 模式：最頂「The Read」+「明日要睇咩」（Desmond 2026-10-23 參考 levelup.net/pulse）
    _above50 = bt.get("above50")
    _strength = ("強" if _fin(_above50) and _above50 >= 60 else
                 "中性" if _fin(_above50) and _above50 >= 40 else
                 "弱" if _fin(_above50) else "—")
    _lead_txt = (reg.get("lead") or {}).get("text") or "—"
    _read = (f"大市<strong style=\"color:#7DBE8A\">{_strength}</strong>"
             f"（{pct(_above50)} 企 50MA 上、"
             f"{pct(bt.get('above200'))} 企 200MA 上）。"
             f"領導：{esc(_lead_txt)}。{esc(reg.get('vix_note') or '')}")
    _watch = [
        (esc(reg.get("core_question") or "今日冇核心問題"), "核心問題"),
        (esc(reg.get("breadth_note") or b.get("status") or "—"), "廣度"),
        (f"新高 {num(bt.get('new_highs'), 0)} / 新低 {num(bt.get('new_lows'), 0)}"
         f"｜{esc(_lead_txt)}", "要睇"),
    ]
    _pulse = (
        '<div class="card" style="border-left:4px solid #7DBE8A">'
        '<h2>📖 The Read <small>今日一句話</small></h2>'
        f'<div class="body" style="font-size:14px;line-height:1.8">{_read}</div></div>'
        '<div class="card"><h2>👀 明日要睇咩</h2><div class="body">'
        + "".join(f'<div style="margin:7px 0;font-size:14px">'
                  f'<b>{l}</b>　·　{t}</div>' for t, l in _watch)
        + '</div></div>')

    brief_body = f"""
{_champion_card()}
{_pulse}
{_gmi_card}
{_themes}
{note}
{_gc_card}
<div class="kpis">{kpi_html}</div>
<div class="grid2">
 <div class="card"><h2>市場狀態 <small>{esc(brief.get("regime_src") or "—")}</small></h2>
  <div class="body">{render_insight(reg) if reg else '<div class="dim">冇快照</div>'}</div></div>
 <div class="card"><h2>廣度歷史（我哋自己） <small>{esc(brief.get("breadth_src") or "—")}</small></h2>
  <div class="body">{render_breadth(b) if b else '<div class="dim">冇快照</div>'}</div></div>
</div>
<div class="card"><h2>🌊 Stockbee 廣度 <small>升 4%+ / 跌 4%+ 家數｜呢把尺同上面唔同，唔可以混用</small></h2>
 <div class="body">{render_stockbee_breadth(_sbf)}</div></div>
<div class="card"><h2>{_qhead} <small>{esc(brief.get("rs_mtime") or "")}</small></h2>
 <div class="body">{_qnote}<div class="scroll"><table><thead><tr><th class="l">代號 / 行業</th><th>收市</th>
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
            # ★ 2026-10-20 Desmond：RS-D / RS-W 要應用到「選股」全部列表
            #   所以一次過抓齊所有列表嘅股票，唔止 48 隻 NEL
            _all = set(chart_tickers)
            for _v in scan.values():
                if isinstance(_v, list):
                    for _r in _v:
                        if isinstance(_r, dict) and _r.get("symbol"):
                            _all.add(_r["symbol"])
            rs_map = charts.rs_lookup(sorted(_all))
            # ★ 同一批股票嘅標準統計（表現/延伸/ADR/成交額/距52週高）
            #   令所有列表都可以出同一組欄位，唔會得個「—」
            stats = charts.stats_lookup(sorted(_all))
            log(f"✓ RS 迷你圖：{len(rs_map)}/{len(_all)} 隻有數據"
                f"｜統計：{len(stats)} 隻")
        except Exception as e:                               # noqa: BLE001
            wall = (f'<div class="warn">圖表牆取唔到：{type(e).__name__}'
                    f'（yfinance 限流或離線？）。</div>')
            rs_map = {}
            stats = {}
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
                    + f'<td>{_cm.chip(r["symbol"], cmres.get(r["symbol"])) if _cm else "—"}'
                    + (_wg.badge((cmres.get(r["symbol"]) or {}).get("w10")) if _cm else '')
                    + '</td>'
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
        pages["leaders"] = ("RS Leader",
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
            # ★ 2026-10-28 Desmond 選 1：貼W10 變硬性過濾（週線 10SMA 進場點）
            _wgv = [x for x in ranked
                    if (x.get("w10") or {}).get("label") in ("貼W10", "接近")]
            _wg_drop = len(ranked) - len(_wgv)
            ranked = _wgv
            top = [x for x in ranked if x["n"] >= 4]
            rest = [x for x in ranked if x["n"] < 4]
            nel_ind = {r["symbol"]: r.get("industry", "") for r in scan["nel"]}
            def cmrow(r):
                ind = nel_ind.get(r["ticker"], "")
                st_ = stats.get(r["ticker"], {})
                p = st_.get("perf") or {}

                def _pf(k):
                    v = p.get(k)
                    return (f'<td class="{tone(v)}">{pct(v)}</td>'
                            if v is not None else '<td class="dim">—</td>')
                ext = st_.get("extension")
                adr = st_.get("adr")
                dv = st_.get("dvol")
                o52 = st_.get("off52w")
                return (f'<tr><td class="l"><span class="tk">'
                        f'{tv_link(r["ticker"], ind)}</span>'
                        f'<div class="dim" style="font-size:10.5px">{esc(ind)}</div></td>'
                        # ★ 同領導股完全同一組欄位
                        + charts.rs_col(rs_map.get(r["ticker"], {}))
                        + _pf("1w") + _pf("1m") + _pf("3m")
                        + _pf("6m") + _pf("1y")
                        + f'<td>{num(ext, 2)}×</td>'
                        f'<td>{pct(adr, 1)}</td>'
                        f'<td>{money(dv)}</td>'
                        f'<td class="{"pos" if (o52 or 0) > -3 else "neg"}">'
                        f'{pct(o52, 1)}</td>'
                        f'<td>{_cm.chip(r["ticker"], r)}'
                        f'{_wg.badge(r.get("w10"))}</td>'
                        f'{_cm.detail_cells(r)}'
                        f'<td>{num(r["close"], 2)}</td></tr>')
            cmhead = ('<tr><th class="l">代號 / 行業</th>'
                      '<th>RS-D</th><th>RS-W</th>'
                      '<th>1週</th><th>1月</th><th>3月</th>'
                      '<th>6月</th><th>1年</th>'
                      '<th>延伸</th><th>ADR%</th><th>成交額</th><th>距52週高</th>'
                      '<th>1CM 評級</th>'
                      '<th>L1 RS 領導</th><th>L2 回調支撐</th><th>L3 量縮</th>'
                      '<th>L4 買家守</th><th>L5 風險窄</th><th>收市</th></tr>')
            cm_body = f"""
<div class="warn">🎯 <b>1chartmaster「RS Leader Pullback Buy」</b>——
 呢個分頁係由 Desmond 嘅訂閱證據庫蒸餾出嚟（read-only），
 <b>唔係我哋原創</b>。原文：「you track Relative Strength (RS) leaders and buy
 them when they <b>pull back into structural support</b>」。</div>
<style>{_cm.CM_CSS}</style>
<div class="warn" style="border-left-color:#22c55e">
 <b>週線 10SMA 進場閘（已生效）</b>——只列「貼W10」或「接近」嘅股：
 距週線 10SMA ≤ ±3% 且 W10 上升。今日過濾走 <b>{_wg_drop}</b> 隻。
 <span style="opacity:.75">原文：「if things are not at the optimal entry point on the
 weekly, maybe I shouldn't swing it on the daily.」</span></div>
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
 <tbody>{"".join(cmrow(r) for r in top) or '<tr><td colspan=8 class="dim">今日冇 A 級設置（週線 10SMA 過濾後）</td></tr>'}</tbody>
 </table></div></div></div>
<div class="card"><h2>B 級觀察名單 <small>&lt;4/5</small></h2>
 <div class="body"><div class="scroll"><table><thead>{cmhead}</thead>
 <tbody>{"".join(cmrow(r) for r in rest) or '<tr><td colspan=8 class="dim">—</td></tr>'}</tbody>
 </table></div></div></div>"""
            pages["cm"] = ("RS Pullback", cm_body, base | {"cm": cmres})
        # ── 最強 1 週 ──（Item 2：統一欄位）—
        wk = scan.get("week") or []
        std_ctx = {
            "tv_link": tv_link, "rs_col": charts.rs_col, "band_svg": band_svg,
            # ★ 用全站共用 rs_map（唔再係 r.get("rs")，嗰個根本唔存在）
            "rs_map": rs_map,
            "kstage": (_kell.stages([r["symbol"] for r in wk][:120])
                       if _kell and wk else {}),
            "cm": _cm, "cmres": cmres,
            "kell": _kell,
        }
        # ★ 2026-10-20 Desmond「全部列表都要咁做」
        #   欄位同「領導股」完全一致，一個都唔少
        wk_keys = ["rank", "name", "rsd", "rsw",
                   "1w", "1m", "3m", "6m", "1y",
                   "ext", "adr", "rvol", "off52", "kell", "cm"]
        pages["week"] = ("Weekly MM", f"""
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
        # ★ 2026-10-28 Desmond：移除「方法分類」頁（連側欄）
        _ = mrows  # 保留計算但唔輸出

    # ── Setup Factory（2026-10-22 Desmond：1ChartMaster 蒸餾）──
    try:
        import setupfactory_page as _sf
        _sf_title, _sf_body = _sf.build()
        pages["setupfactory"] = (_sf_title, _sf_body, base)
    except Exception as _esf:                                # noqa: BLE001
        pages["setupfactory"] = (
            "Setup Factory",
            f'<div class="card"><div class="body"><div class="warn">'
            f'讀唔到：{type(_esf).__name__}: {_esf}</div></div></div>', base)

    # ── 優化帳本（2026-10-22 Desmond：「我想用錢同你既優化做掛勾」）──
    try:
        import optledger_page as _ol
        _ol_title, _ol_body = _ol.build()
        pages["optledger"] = (_ol_title, _ol_body, base)
    except Exception as _eol:                                # noqa: BLE001
        pages["optledger"] = (
            "優化帳本",
            f'<div class="card"><div class="body"><div class="warn">'
            f'讀唔到：{type(_eol).__name__}: {_eol}</div></div></div>', base)

    # ── Van K. Tharp 五法（2026-10-22 Desmond 貼文）──
    #   每條都接到現有模組，並寫明「做唔做到」+「每次問自己咩」。
    try:
        import vantharp_page as _vt
        _vt_title, _vt_body = _vt.build()
        pages["vantharp"] = (_vt_title, _vt_body, base)
    except Exception as _evt:                                # noqa: BLE001
        pages["vantharp"] = (
            "Van K. Tharp 五法",
            f'<div class="card"><div class="body"><div class="warn">'
            f'讀唔到：{type(_evt).__name__}: {_evt}</div></div></div>', base)

    # ── Item 1：NEL 五頁蒸餾（Themes／Sectors／Breadth／Positioning／Review）──
    # ★ 每頁用 nel_pages.py 嘅唯一實作，呢度只負責寫入 pages dict。
    #   唔准喺呢度重算任何公式（EDGE-036 教訓：同一個概念只可以一個實作）。
    try:
        _ohlc_df = _np._ohlc()
        for _key, _title, _fn in (
                ("sectors", "Sectors", lambda: _np.sectors_page(_ohlc_df)),
                ("breadth", "Breadth", _np.breadth_page),
                ("positioning", "Positioning", _np.positioning_page),
                ("review", "Review", _np.review_page),
                ("review2", "覆盤", None)):
            try:
                if _key == "review2":
                    import review_page as _rv
                    pages[_key] = _rv.build() + (base,)
                else:
                    pages[_key] = (_title, _fn(), base)
            except Exception as _e2:                         # noqa: BLE001
                log(f"⚠ {_title} 頁失敗：{type(_e2).__name__}")
                pages[_key] = (_title, _np._unavail(_title, str(_e2)), base)
    except Exception as _e1:                                 # noqa: BLE001
        log(f"⚠ NEL 五頁整體失敗：{type(_e1).__name__}")

    # ── 🧮 倉位計算機（Desmond 2026-10-19）──
    # ★ 純前端 JS 計算，唔需要數據 → 永遠可用
    #   數學對照過 lonestocktrader 截圖（69 股 / 0.66R / 99.33 階梯 全部吻合）
    try:
        import calculator as _calc
        pages["calculator"] = ("倉位計算機", _calc.calc_page(), base)
    except Exception as _e3:                                 # noqa: BLE001
        log(f"⚠ 計算機頁失敗：{type(_e3).__name__}: {_e3}")

    # ── 外部數據源（Desmond 2026-10-19）──
    try:
        import external_page as _xp
        _t3, _b3 = _xp.build()
        pages["external"] = (_t3, _b3, base)
        log(f"✓ external.html ({len(_b3)//1024} KB)")
    except Exception as _e9:                                 # noqa: BLE001
        log(f"⚠ 外部數據源失敗：{type(_e9).__name__}: {_e9}")

    # ── 財報日曆（Desmond 2026-10-19）──
    try:
        import earnings_page as _ep   # noqa: F401  (2026-10-25：內容移走，改用 Finviz)
        _t2, _b2 = _ep.build()
        # pages["earnings"] 已停用（Desmond 2026-10-25：改用 Finviz 財報日曆）
        log("· earnings.html 已停用（改用 Finviz）")
    except Exception as _e8:                                 # noqa: BLE001
        log(f"⚠ 財報日曆失敗：{type(_e8).__name__}: {_e8}")


    # ── YOYO Ball（Desmond 2026-10-20：先證明盈利才出 alert）──
    try:
        import yoyo_page as _yp
        _yt, _yb = _yp.build()
        pages["yoyo_ball"] = (_yt, _yb, base)
        log(f'✓ yoyo_ball.html ({len(_yb)//1024} KB)')
    except Exception as _e17:
        log(f'⚠ YOYO 頁失敗：{type(_e17).__name__}: {_e17}')

    # ── Edge Improving（Desmond 2026-10-20：針對實盤做強弱分析）──
    try:
        import edge_page as _ep
        _et, _eb = _ep.build()
        pages["edgeimprove"] = (_et, _eb, base)
        log(f'✓ edgeimprove.html ({len(_eb)//1024} KB)')
    except Exception as _e20:
        log(f'⚠ Edge 頁失敗：{type(_e20).__name__}: {_e20}')

    # ── Model Book（Desmond 2026-10-20：Notion KB + 心理學分析）──
    #    ＋ 2026-10-22 加入量化案例庫（mb_page.py，2,377 個真實案例）
    try:
        import modelbook_page as _mb
        _mt, _mbb = _mb.build()
        try:
            import mb_page as _mbq
            _lib = _mbq.block()
            if _lib:
                _mbb = _mbb + _lib
                log("✓ modelbook 加量化案例庫")
        except Exception as _e22:
            log(f"⚠ 案例庫區塊失敗：{type(_e22).__name__}: {_e22}")
        # ★ 2026-10-24 加 anchor：側欄 MODEL BOOK → 量化案例庫
        _mbb = _mbb.replace('<h3>📚 Model Book — 量化案例庫</h3>',
                            '<h3 id="cases">📚 Model Book — 量化案例庫</h3>')
        pages["modelbook"] = (_mt, _mbb, base)
        log(f'✓ modelbook.html ({len(_mbb)//1024} KB)')
    except Exception as _e21:
        log(f'⚠ Model Book 頁失敗：{type(_e21).__name__}: {_e21}')

    # ── 系統審計（Desmond 2026-10-21：我淨係要見到你賺幾多錢）──
    try:
        import audit_page as _au
        _aut, _aub = _au.build()
        pages["audit"] = (_aut, _aub, base)
        log(f'✓ audit.html ({len(_aub)//1024} KB)')
    except Exception as _e26:
        log(f'⚠ 系統審計頁失敗：{type(_e26).__name__}: {_e26}')

    # ── Backtest（Desmond 2026-10-21：淨係出位置無回測好無用）──
    try:
        import backtest_page as _bt
        _btt, _btb = _bt.build()
        pages["backtest"] = (_btt, _btb, base)
        log(f'✓ backtest.html ({len(_btb)//1024} KB)')
    except Exception as _e25:
        log(f'⚠ Backtest 頁失敗：{type(_e25).__name__}: {_e25}')

    # ── Market Pulse（Desmond 2026-10-20：加外部數據 leveluptools）──
    try:
        import levelup as _lu
        _lut, _lub = _lu.build()
        pages["levelup"] = (_lut, _lub, base)
        log(f'✓ levelup.html ({len(_lub)//1024} KB)')
    except Exception as _e24:
        log(f'⚠ Market Pulse 頁失敗：{type(_e24).__name__}: {_e24}')

    # ── RS Before Price（Desmond 2026-10-20：1ChartMaster 訊號）──
    try:
        import rs_before_price as _rb
        _rbt, _rbb = _rb.build()
        pages["rsbeforeprice"] = (_rbt, _rbb, base)
        log(f'✓ rsbeforeprice.html ({len(_rbb)//1024} KB)')
    except Exception as _e23:
        log(f'⚠ RS Before Price 頁失敗：{type(_e23).__name__}: {_e23}')

    # ── Think in R（Desmond 2026-10-20：4R 格仔牆）──
    try:
        import thinkinr_page as _tr
        _tt, _tb = _tr.build()
        pages["thinkinr"] = (_tt, _tb, base)
        log(f'✓ thinkinr.html ({len(_tb)//1024} KB)')
    except Exception as _e22:
        log(f'⚠ Think in R 頁失敗：{type(_e22).__name__}: {_e22}')

    # ── 數據健康後台（Desmond 2026-10-20：唔想有假更新）──
    try:
        import datahealth as _dh
        _dht, _dhb = _dh.build()
        pages["datahealth"] = (_dht, _dhb, base)
        _sm = __import__("freshness").summary()
        log(f'✓ datahealth.html（即時 {_sm["fresh"]}／過期 {_sm["stale"]}'
            f'／缺失 {_sm["missing"]}）')
    except Exception as _e16:                                # noqa: BLE001
        log(f"⚠ 數據健康失敗：{type(_e16).__name__}: {_e16}")

    # ── ALERTS 分類總覽（Desmond 2026-10-19）──
    try:
        import alerts_page as _al
        import alerts_feed as _af
        _at, _ab = _al.build()
        _feed = _af.render_html()          # ★ 所有 job 訊號放最頂
        pages["alerts"] = (_at, _feed + _ab, base)
        log(f"✓ alerts.html ({_al.load().__len__()} 筆)")
    except Exception as _e15:                                # noqa: BLE001
        log(f"⚠ ALERTS 失敗：{type(_e15).__name__}: {_e15}")

    # ── LOG BOOK（Desmond 2026-10-19：最底留個更新記錄表）──
    try:
        import logbook as _lbk
        _lt, _lbody = _lbk.build_full()
        pages["logbook"] = (_lt, _lbody, base)
        log(f"✓ logbook.html ({_lbody.count('<tr>')} 條)")
    except Exception as _e14:                                # noqa: BLE001
        log(f"⚠ LOG BOOK 失敗：{type(_e14).__name__}: {_e14}")

    # ── MARKET REGIME MRI（Desmond 2026-10-19）──
    try:
        import market_regime as _mrg
        _mt, _mb = _mrg.build()
        pages["regime_mri"] = (_mt, _mb, base)
        log(f"✓ regime_mri.html ({len(_mb)//1024} KB)")
    except Exception as _e13:                                # noqa: BLE001
        log(f"⚠ MARKET REGIME 失敗：{type(_e13).__name__}: {_e13}")

    # ── ★ 2026-10-23 移除 rocketstock / livefeeds（外部數據合併入 external.html）──

    # ── Daily Scan（Desmond 2026-10-19：L1 + L2）──
    try:
        import dailyscan as _ds
        _td, _bd = _ds.build()
        pages["dailyscan"] = (_td, _bd, base)
        log(f"✓ dailyscan.html ({len(_bd)//1024} KB)")
        # ★ 2026-10-24 歷史快照（日期選擇器用）：最近 6 個交易日
        try:
            for _d in _ds.available_days()[1:5]:
                _th, _bh = _ds.build(_d)
                pages[f"dailyscan_{_d}"] = (_th, _bh, base)
                log(f"✓ dailyscan_{_d}.html ({len(_bh)//1024} KB)")
        except Exception as _eh:                            # noqa: BLE001
            log(f"⚠ 歷史 Daily Scan 失敗：{type(_eh).__name__}: {_eh}")
    except Exception as _e10:                                # noqa: BLE001
        log(f"⚠ Daily Scan 失敗：{type(_e10).__name__}: {_e10}")

    # ── ★ 2026-10-24 RS Daily Scan（放喺 Daily Scan 下面）──
    try:
        import rs_scan as _rss
        _rt, _rb = _rss.build()
        pages["rsscan"] = (_rt, _rb, base)
        log(f"✓ rsscan.html ({len(_rb)//1024} KB)")
        # ★ 2026-10-24：每日快照各出一頁，令「上一日／下一日」真係跳得
        for _snap in _rss._all_snaps()[-10:]:
            _d = os.path.basename(_snap)[10:20]
            try:
                _t2, _b2 = _rss.build(snap=_snap)
                pages[f"rsscan_{_d}"] = (_t2, _b2, base)
            except Exception as _e2:                        # noqa: BLE001
                log(f"⚠ rsscan {_d} 失敗：{type(_e2).__name__}")
        log(f"✓ rsscan 快照頁 {min(10, len(_rss._all_snaps()))} 個")
    except Exception as _e14:                                # noqa: BLE001
        log(f"⚠ RS Daily Scan 失敗：{type(_e14).__name__}: {_e14}")

    # ── 沙灘球反應（2026-10-25）──
    try:
        import beachball_page as _bb
        _bt, _bbody = _bb.build()
        pages["beachball"] = (_bt, _bbody, base)
        log(f"✓ beachball.html ({len(_bbody)//1024} KB)")
    except Exception as _eb:                            # noqa: BLE001
        log(f"⚠ beachball 失敗：{type(_eb).__name__}: {_eb}")

    # ── 投降／過熱儀表（2026-10-25）──
    try:
        import fear_gauge_page as _fg
        _fgt, _fgb = _fg.build()
        pages["feargauge"] = (_fgt, _fgb, base)
        log(f"✓ feargauge.html ({len(_fgb)//1024} KB)")
    except Exception as _e:                                  # noqa: BLE001
        log(f"⚠ feargauge：{type(_e).__name__}")
    try:
        import fatpitch_page as _fp
        _fpb = _fp.render_html()
        pages["fatpitch"] = ("肥球掃描（J Law）", _fpb, base)
        log(f"✓ fatpitch.html ({len(_fpb)//1024} KB)")
    except Exception as _ef:                            # noqa: BLE001
        log(f"⚠ 肥球掃描失敗：{type(_ef).__name__}: {_ef}")

    # ── Tight Range 全市場掃描（2026-10-27）──
    try:
        import tightscan_page as _ts
        _tst, _tsb = _ts.build()
        pages["tightscan"] = (_tst, _tsb, base)
        log(f"✓ tightscan.html ({len(_tsb)//1024} KB)")
    except Exception as _ets:                           # noqa: BLE001
        log(f"⚠ Tight Range 失敗：{type(_ets).__name__}: {_ets}")

    # ── ★ 2026-10-24 收工標準（Definition of Done，機器自動檢查）──
    try:
        import finish_line as _fl
        _ft, _fb = _fl.build()
        pages["finish"] = (_ft, _fb, base)
        log("✓ finish.html（收工標準）")
    except Exception as _efl:                            # noqa: BLE001
        log(f"⚠ 收工標準失敗：{type(_efl).__name__}: {_efl}")

    # ── ★ 2026-10-24 每日流程（Jeff Sun 決策漏斗）──
    try:
        import process_page as _pf
        _pt, _pb = _pf.build()
        pages["process"] = (_pt, _pb, base)
        log(f"✓ process.html ({len(_pb)//1024} KB)")
    except Exception as _e15:                                # noqa: BLE001
        log(f"⚠ 每日流程失敗：{type(_e15).__name__}: {_e15}")

    # ── ★ 2026-10-24 Top 250 US Gainers（MODEL BOOK 子分頁）──
    try:
        import mb_top250_page as _t2
        _t2h = _t2.block()
        pages["mb_top250"] = ("Top 250 US Gainers", _t2h, base)
        log(f'✓ mb_top250.html ({len(_t2h)//1024} KB)')
    except Exception as _e16:                                # noqa: BLE001
        log(f"⚠ Top 250 失敗：{type(_e16).__name__}: {_e16}")

    # ── RS Leader 位置圖（Desmond 2026-10-19：加日期選取器）──
    try:
        import leadermap as _lm
        _title, _body = _lm.build()
        pages["leadermap"] = (_title, _body, base)
        log(f"✓ leadermap.html ({len(_body)//1024} KB)")
    except Exception as _e7:                                 # noqa: BLE001
        log(f"⚠ RS Leader 位置圖失敗：{type(_e7).__name__}: {_e7}")

    # ── ★ 2026-10-20 拆分「機會」頁 → 三個獨立頁 ──
    try:
        _dp = json.load(io.open(os.path.join(HERE, "cache", "desk_parts.json"),
                                encoding="utf-8"))
        _st = _dp.get("styles") or ""
        _parts = _dp.get("parts") or {}
        for _k, _lbl in (("leadermap", "RS Leader 位置圖"),
                         ("sectors", "Sectors · 行業 RS"),
                         ) :  # 2026-10-25 Desmond：移除 ATRX 風險頁
            if _k in _parts:
                _body = f"{_st}" + _parts[_k]
                if _k == "sectors":
                    # ★ 2026-10-27 Desmond：RS GROUP MOVE 放最頂；移除「行業輪動 資金去邊」區塊
                    _top = ""
                    try:
                        import group_rs_page as _grs
                        _top = _grs.card() or ""
                    except Exception as _eg:              # noqa: BLE001
                        log(f"⚠ RS GROUP MOVE 失敗：{type(_eg).__name__}")
                    _tbl = ""
                    try:
                        import rotation_block as _rot
                        _tbl = _rot.build()
                    except Exception as _er:              # noqa: BLE001
                        log(f"⚠ 行業 RS 表失敗：{type(_er).__name__}: {_er}")
                    # ★ 2026-10-27：整段「② 行業輪動 —— 資金去邊」（NEL 版）
                    #   由 Desmond 指定移除；留返 group card + 我哋自己嘅行業 RS 表
                    _body = f"{_st}" + _top + _tbl
                pages[_k] = (_lbl, _body, base)
                log(f"✓ {_k}.html ({len(_body)//1024} KB)")
    except Exception as _e19:
        log(f"⚠ 拆分頁失敗：{type(_e19).__name__}: {_e19}")

    # ── 廚房看板（Desmond 2026-10-19：所有 job 狀態）──
    try:
        import jobboard as _jb
        _jobs, _jerr = _jb.load_jobs()
        if _jobs:
            _body = _jb.build(_jobs, _jb.load_exec(), _jb.load_incidents())
            # ★ 所有 Alert 分類：直接放喺廚房看板最底（Desmond 2026-10-19）
            try:
                import alerts_page as _alp
                _abody = _alp.build()[1]
                _body = (_body +
                         '<div style="margin-top:22px;padding-top:6px;'
                         'border-top:2px solid rgba(217,119,87,.35)">'
                         + _abody + '</div>')
            except Exception:                                # noqa: BLE001
                pass
            pages["jobboard"] = ("廚房看板", _body, base)
            log(f"✓ jobboard.html ({len(_body)//1024} KB, {len(_jobs)} jobs)")
    except Exception as _e6:                                 # noqa: BLE001
        log(f"⚠ 廚房看板失敗：{type(_e6).__name__}: {_e6}")

    # ── 四個外部數據源（Desmond 2026-10-19）──
    # Market Monitor / Stockbee 50 / Sector RS / Jeff Sun Momentum
    # ★ 3 個用 iframe 嵌原表；Market Monitor 封鎖 iframe → 自己 render
    try:
        import newfeeds as _nf
        import newfeeds_pages as _nfp
        _feeds = _nf.load_all()
        for _k, (_title, _fn) in _nfp.PAGES.items():
            try:
                pages[_k] = (_title, _fn(_feeds.get(_k)), base)
            except Exception as _e4:                         # noqa: BLE001
                log(f"⚠ {_k} 頁失敗：{type(_e4).__name__}: {_e4}")
                pages[_k] = (_title, _nfp._unavail(_title, str(_e4)), base)
    except Exception as _e5:                                 # noqa: BLE001
        log(f"⚠ 外部數據源整體失敗：{type(_e5).__name__}: {_e5}")

    # ── RS THEME（2026-10-24 大改：階段/分/1週/1個月/3個月、左對齊、緊湊、無橫向 scroll）──
    try:
        import rstheme_page as _rt
        _rtt, _rtb = _rt.build()
        pages["rsboard"] = (_rtt, _rtb, base)
        log(f'✓ rsboard.html（RS THEME）{len(_rtb)//1024} KB')
    except Exception as _e17:                                # noqa: BLE001
        log(f"⚠ RS THEME 失敗：{type(_e17).__name__}: {_e17}")

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
            f'<small>IWF {gc["iwf"]} ／ IWD {gc["iwd"]}'
             f'｜週線最後完整週 {esc(gc["as_of"])}</small></h2>'
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
                ["name", "close", "watch_p", "inv_p", "x", "y", "band", "kell", "cm"],
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
        pages["setups"] = ("The Plan", setups_body, base)

    # ── ★ Setup × Regime 矩陣（Desmond 2026-10-15 要求）──
    _rg = None
    for _p in (os.path.join(LIVE, "output", "setup_regime_backtest.json"),
               os.path.join(LAB, "output", "setup_regime_backtest.json")):
        if os.path.exists(_p):
            try:
                with io.open(_p, encoding="utf-8") as f:
                    _rg = json.load(f)
                _rg["_src"] = os.path.basename(_p)
                break
            except Exception:
                pass
    if _rg and _rg.get("cells"):
        _cells = _rg["cells"]
        _setups = sorted({k.split("|")[0] for k in _cells})
        _regs = sorted({k.split("|")[1] for k in _cells})
        _minc = _rg.get("min_cell", 30)
        _tot = _rg.get("total", 0)
        # 搵每格最大值（用嚟上色深淺）
        _mx = max((abs(v["mean_r"]) for v in _cells.values()), default=1) or 1
        _h = ['<div class="card"><h2>🎲 Setup × Regime 矩陣'
              f' <small>{esc(_rg["_src"])}｜{_rg.get("years","?")} 年｜'
              f'{_tot:,} 單</small></h2><div class="body">']
        _h.append('<div class="note">★ 核心洞察：<b>唔係問「邊個 setup 最好」，'
                  '係問「邊個 setup 喺邊個 regime 最好」</b>。'
                  '同一批 setup 訊號，喺唔同市場階段嘅平均 R 差天共地。'
                  '市場階段決定回報分佈 —— 呢個就係 Portfolio-T 嘅邏輯。'
                  f'<br>判準：n ≥ {_minc} 才准當結論（SOUL §8.14）｜'
                  '止蝕 1.0 ATR｜出場 = 日線收市跌穿 10EMA（EDGE-034 ACTIVE）｜'
                  '持倉上限 20 日。⚠ 未扣成本。</div>')
        _h.append('<table class="t"><thead><tr><th class="l">Setup</th>')
        for _r in _regs:
            _h.append(f'<th>{esc(_r)}</th>')
        _h.append('<th>最佳</th></tr></thead><tbody>')
        _rows_rank = []
        for _s in _setups:
            _h.append(f'<tr><td class="l"><b>{esc(_s)}</b></td>')
            _best = None
            for _r in _regs:
                _c = _cells.get(f"{_s}|{_r}")
                if not _c or _c["n"] < _minc:
                    _n = _c["n"] if _c else 0
                    _h.append(f'<td style="opacity:.35">—<br>'
                              f'<small>n={_n}</small></td>')
                    continue
                _m = _c["mean_r"]
                _inten = min(0.55, abs(_m) / _mx * 0.55)
                _bg = (f"rgba(35,134,54,{_inten:.2f})" if _m > 0
                       else f"rgba(218,54,51,{_inten:.2f})")
                _h.append(f'<td style="background:{_bg}">'
                          f'<b>{_m:+.2f}R</b><br>'
                          f'<small>n={_c["n"]}｜勝率 {_c["win_pct"]:.0f}%</small></td>')
                _rows_rank.append((_s, _r, _m, _c["n"], _c["win_pct"]))
                if _best is None or _m > _best[1]:
                    _best = (_r, _m)
            _h.append('<td>' + (f'<b>{esc(_best[0])}</b> {_best[1]:+.2f}R'
                                if _best else '—') + '</td></tr>')
        _h.append('</tbody></table>')
        # 排名
        if _rows_rank:
            _rows_rank.sort(key=lambda x: -x[2])
            _h.append('<h3 style="margin-top:18px">★ 有效組合排名'
                      f'（n ≥ {_minc}）</h3><table class="t"><thead><tr>'
                      '<th class="l">#</th><th class="l">Setup</th>'
                      '<th class="l">Regime</th><th>平均 R</th>'
                      '<th>n</th><th>勝率</th></tr></thead><tbody>')
            for _i, (_s, _r, _m, _n, _w) in enumerate(_rows_rank[:12], 1):
                _h.append(f'<tr><td class="l">{_i}</td>'
                          f'<td class="l"><b>{esc(_s)}</b></td>'
                          f'<td class="l">{esc(_r)}</td>'
                          f'<td><b>{_m:+.3f}R</b></td><td>{_n}</td>'
                          f'<td>{_w:.1f}%</td></tr>')
            _h.append('</tbody></table>')
            _b = _rows_rank[0]
            _h.append(f'<div class="note" style="margin-top:14px">'
                      f'★★ <b>數據答案</b>：目前最強組合 = '
                      f'<b>{esc(_b[0])} × {esc(_b[1])}</b>'
                      f'（{_b[2]:+.3f}R｜n={_b[3]}｜勝率 {_b[4]:.1f}%）。'
                      f'<br>⚠ 但記住：呢個係 <b>3 年</b> 樣本、'
                      f'未扣成本。要向前累積到 n≥200 才可以當定論。</div>')
        else:
            _h.append(f'<div class="note">⚠ 冇任何組合達到 n ≥ {_minc}'
                      '—— 樣本不足，唔可以出結論。</div>')
        _h.append('</div></div>')
        pages["regime"] = ("Setup × Regime", "".join(_h), base)

    # ── ★ 2026-10-23 移除 desk.html（舊「機會」頁，已由 split_desk → leadermap/sectors/atrxrisk 取代）──
    #    dashboard 內容仍然經 split_desk.py → desk_parts.json → 三頁獨立展示，唔再出 desk.html

    # ── ★ 2026-10-25 Desmond：「叫你排版好慢」→ 樣式抽出 site.css
    #    之後改 docs/site.css 再 refresh 就見到，唔需要等 build。
    #    （下次 build 會覆蓋 → 滿意就打返入 generator）
    _css = CSS + SIDEBAR_CSS + tvhover.TVHOVER_CSS
    with io.open(os.path.join(SITE, "site.css"), "w", encoding="utf-8") as _f:
        _f.write(_css)
    log(f"✓ site.css ({len(_css)//1024} KB)")

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
    rc = build()
    # ★ 寫 version.json：前端每頁 fetch 呢個檔，發現版本唔同就自動 reload
    #   咁 Desmond 用返原本條 link 就永遠睇到最新，唔需要記住 ?v=
    try:
        import json as _json
        vp = os.path.join(SITE, "version.json")
        with open(vp, "w", encoding="utf-8") as f:
            _json.dump({"v": BUILD_TS,
                        "ts": __import__("time").time()},
                       f, ensure_ascii=False)
        print(f"✓ version.json  {BUILD_TS}")
    except Exception as e:                                   # noqa: BLE001
        print(f"⚠ version.json 失敗: {e}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
