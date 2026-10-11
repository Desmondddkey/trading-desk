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

TABS = [
    ("desk", "🖥", "交易台", "desk.html"),
    ("briefing", "📋", "簡報", None),
    ("leaders", "🚀", "領導股", None),
    ("week", "⚡", "最強 1 週", None),
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
    """Python 版迷你折線（RS 板用），同 JS 版 spark() 同意義。"""
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
nav{display:flex;gap:4px;overflow-x:auto;padding-bottom:2px;scrollbar-width:thin}
nav a,nav span.tab{flex:0 0 auto;display:inline-flex;align-items:center;gap:6px;
 padding:8px 13px 9px;border-radius:9px 9px 0 0;font-size:13.5px;color:#9fb0cc;
 text-decoration:none;border:1px solid transparent;border-bottom:none;white-space:nowrap}
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
.cand{border:1px solid #1e2a44;border-radius:8px;padding:6px 4px 5px;text-align:center;background:#0d1424}
.cand .tk{font-size:11.5px;font-weight:700;color:#cfe4ff;margin-top:3px}
.cand .mini{min-height:66px;display:flex;align-items:center;justify-content:center}
.cand:hover{border-color:#4a90d9}
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
"""

SITENAV_LINKS = [
    ("desk.html", "🖥", "交易台", True),
    ("index.html", "📋", "簡報", False),
    ("leaders.html", "🚀", "領導股", False),
    ("week.html", "⚡", "最強 1 週", False),
    ("rsboard.html", "📊", "RS 板", False),
    ("method.html", "🧩", "方法分類", False),
    ("cycle.html", "🌀", "成長週期", False),
    ("setups.html", "📐", "Setups", False),
]


def sitenav_html():
    links = "".join(
        f'<a href="{h}" class="{"on" if on else ""}"><span>{i}</span>{t}</a>'
        for h, i, t, on in SITENAV_LINKS)
    return f'<style>{SITENAV_CSS}</style><nav class="sitenav">{links}</nav>'


def inject_nav(html):
    """喺 desk.html（我哋個 dashboard，冇導航）頂部加返網站導航。

    ⚠ 之前 desk.html 係獨立頁，冇 link 返去其他分頁 → 用戶一入交易台就跳唔走。
    呢度喺 <body> 之後插一條自帶 CSS 嘅導航（用 .sitenav 前綴，唔會撞 dashboard 嘅 CSS）。
    """
    marker = "<body>"
    if marker in html:
        return html.replace(marker, marker + sitenav_html(), 1)
    return sitenav_html() + html


def nav_html(active):
    """導航：除咗交易台（desk.html 係獨立大檔），其餘全部係自己嘅 .html 檔。

    ⚠ 之前用 `<a href="#key">` 係錯嘅 —— 內容唔喺同一頁，click 咗冇嘢發生。
    修法：直接鏈去真檔（leaders.html、week.html…），click 即轉跳。
    """
    out = []
    for key, icon, label, href in TABS:
        target = href or f"{key}.html"
        cls = "on" if key == active else ""
        out.append(f'<a href="{target}" class="{cls}"><span>{icon}</span>{label}</a>')
    return "".join(out)



def page(active, title, body, payload, extra_head=""):
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · 交易台</title>
<style>{CSS}</style>{extra_head}</head><body>
<div class="wrap">
<header class="top">
 <h1>📈 Desmond · 交易台</h1>
 <p class="crumb">繁體中文版｜骨架蒸餾自 <a href="https://i-manage-risk.github.io/NEL/index.html" target="_blank" rel="noopener">NEL · Market console</a>（逆向工程）｜資料 <code>{payload.get('_generated','?')}</code></p>
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
</body></html>"""


def build():
    os.makedirs(SITE, exist_ok=True)
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    pages = {}

    scan = load_scan()
    brief = load_briefing()
    rsb = load_rsboard()
    meth = load_methods()
    gen = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    base = {"_generated": gen}

    # ── 簡報 ──
    reg = brief.get("regime") or {}
    bt = reg.get("breadth") or {}
    lx = reg.get("ix_lights") or {}
    b = brief.get("breadth") or {}
    q = brief.get("queue") or []
    kpi = [
        ("資料日期", reg.get("date") or b.get("as_of") or "—", "#e8eef8"),
        ("SPY / QQQ / IWM", " ".join(str(lx.get(k, "—")) for k in ("SPY", "QQQ", "IWM")), "#9fd4ff"),
        ("站上 50MA", pct(bt.get("above50")), "#4ade80"),
        ("站上 200MA", pct(bt.get("above200")), "#4ade80"),
        ("新高 / 新低", f'{num(bt.get("new_highs"),0)} / {num(bt.get("new_lows"),0)}', "#9fd4ff"),
        ("VIX", f'{reg.get("vix_light","—")}', "#e8eef8"),
        ("圖表隊列", len(q), "#9fd4ff"),
    ]
    kpi_html = "".join(f'<div class="kpi"><div class="k">{k}</div>'
                       f'<div class="v" style="color:{c}">{v}</div></div>' for k, v, c in kpi)
    note = (f'<div class="warn"><b>{esc(reg.get("core_question") or "")}</b><br>'
            f'廣度：{esc(reg.get("breadth_note") or b.get("status") or "—")}<br>'
            f'領導：{esc((reg.get("lead") or {}).get("text") or "—")}　·　'
            f'VIX：{esc(reg.get("vix_note") or "—")}</div>')
    qrows = "".join(
        f'<tr><td class="l"><span class="tk">{esc(r["t"])}</span></td>'
        f'<td>{num(r.get("close"),2)}</td><td>{sgn(r.get("x"),2)}</td>'
        f'<td>{sgn(r.get("y"),2)}</td>'
        f'<td>{"★" if r.get("box") else "—"}</td><td>{num(r.get("stack"),0)}</td></tr>'
        for r in q)
    brief_body = f"""
{note}
<div class="kpis">{kpi_html}</div>
<div class="grid2">
 <div class="card"><h2>市場狀態 <small>{esc(brief.get("regime_src") or "—")}</small></h2>
  <div class="body"><div class="note">原始 JSON（唔加工，避免我二次演繹）：</div>
  <pre style="white-space:pre-wrap;font-size:11.5px;color:#9fb0cc;max-height:340px;overflow:auto">{esc(json.dumps(reg, ensure_ascii=False, indent=1)[:2400])}</pre></div></div>
 <div class="card"><h2>廣度歷史 <small>{esc(brief.get("breadth_src") or "—")}</small></h2>
  <div class="body"><pre style="white-space:pre-wrap;font-size:11.5px;color:#9fb0cc;max-height:340px;overflow:auto">{esc(json.dumps(b, ensure_ascii=False, indent=1)[:2400])}</pre></div></div>
</div>
<div class="card"><h2>今日圖表隊列 <small>{esc(brief.get("rs_src") or "")}</small></h2>
 <div class="body"><div class="scroll"><table><thead><tr><th class="l">代號</th><th>收市</th>
 <th>X（21EMA）</th><th>Y（ATRX）</th><th>買入區</th><th>疊加</th></tr></thead>
 <tbody>{qrows or '<tr><td colspan=6 class="dim">今日冇快照</td></tr>'}</tbody></table></div>
 <div class="note">X/Y 單位係 ATR：X=(收市−21EMA)/ATR14，Y=(收市−50SMA)/ATR14。
 買入區＝X∈[−0.5,+1] 且 Y∈[0,+4]。</div></div></div>"""
    pages["briefing"] = ("簡報", brief_body, base)

    # ── 領導股（NEL）──
    if scan:
        c = scan["counts"]
        th = scan["thresholds"]
        # 圖表牆（一次過睇哂所有 NEL 圖）
        chart_tickers = [r["symbol"] for r in sorted(
            scan["nel"], key=lambda r: -(r["perf"].get("3m") or -99))][:48]
        try:
            wall = charts.grid_html(charts.build_grid(chart_tickers))
        except Exception as e:                               # noqa: BLE001
            wall = (f'<div class="warn">圖表牆取唔到：{type(e).__name__}'
                    f'（yfinance 限流或離線？）。</div>')
        def table(rows, extra=True):
            tr = []
            for r in rows:
                p = r["perf"]
                tr.append(
                    f'<tr><td class="l"><span class="tk">{esc(r["symbol"])}</span>'
                    f'<div class="dim" style="font-size:10.5px">{esc(r["industry"])}</div></td>'
                    f'<td>{pct(p.get("1w"))}</td><td>{pct(p.get("1m"))}</td>'
                    f'<td>{pct(p.get("3m"))}</td><td>{pct(p.get("6m"))}</td>'
                    f'<td>{pct(p.get("1y"))}</td>'
                    + (f'<td>{num(r["extension"],2)}×</td><td>{pct(r["adr"],1)}</td>'
                       f'<td>{money(r["dvol"])}</td>' if extra else "")
                    + f'<td>{pct(r.get("off52w"),1)}</td></tr>')
            return tr
        head = ('<tr><th class="l">代號 / 行業</th><th>1週</th><th>1月</th><th>3月</th>'
                '<th>6月</th><th>1年</th><th>延伸</th><th>ADR%</th><th>成交額</th>'
                '<th>距52週高</th></tr>')
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
 <div class="note">門檻：成交額 &gt; ${th["min_dollar_vol"]//10**6}M、ADR &gt; {th["min_adr"]}%、
 10 日平均量 &gt; {th["min_avg_vol"]//1000}K、行業唔可以有 Biotech、四個窗口各取前 {int(th["top_frac"]*100)}%。</div></div></div>
<div class="card"><h2>動能池（未過延伸閘） <small>{len(mom)} 隻</small></h2>
 <div class="body"><div class="scroll"><table id="t-mom"><thead>{head}</thead><tbody>{"".join(table(mom))}</tbody></table></div></div></div>
<div class="card"><h2>領導股按行業 <small>{len(byind)} 個行業</small></h2>
 <div class="body"><table><thead><tr><th class="l">行業</th><th>NEL 隻數</th><th class="l">成員</th></tr></thead>
 <tbody>{ind_html or '<tr><td colspan=3 class="dim">—</td></tr>'}</tbody></table></div></div>"""
        pages["leaders"] = ("領導股", leaders_body, base | {"scan": scan})

        # ── 最強 1 週 ──
        wk = scan.get("week") or []
        wrows = "".join(
            f'<tr><td>{i+1}</td><td class="l"><span class="tk">{esc(r["symbol"])}</span>'
            f'<div class="dim" style="font-size:10.5px">{esc(r["industry"])}</div></td>'
            f'<td class="pos">{pct(r["perf"].get("1w"))}</td>'
            f'<td>{pct(r["perf"].get("1m"))}</td><td>{pct(r["perf"].get("3m"))}</td>'
            f'<td>{num(r["extension"],2)}×</td><td>{pct(r["adr"],1)}</td>'
            f'<td>{money(r["dvol"])}</td><td>{pct(r.get("off52w"),1)}</td></tr>'
            for i, r in enumerate(wk))
        pages["week"] = ("最強 1 週", f"""
<div class="card"><h2>本週最強嘅流動性股 <small>流動池 {len(scan["universe"])} 隻之中，按 1 週表現排</small></h2>
 <div class="body"><div class="note">「流動性」＝成交額 &gt; ${th["min_dollar_vol"]//10**6}M 且
 ADR &gt; {th["min_adr"]}% 且 10 日平均量 &gt; {th["min_avg_vol"]//1000}K。呢個係<b>全市場</b>掃描，
 唔係我哋自己嘅 103 隻池。</div>
 <div class="scroll"><table><thead><tr><th>#</th><th class="l">代號 / 行業</th>
 <th>1週</th><th>1月</th><th>3月</th><th>延伸</th><th>ADR%</th><th>成交額</th><th>距52週高</th>
 </tr></thead><tbody>{wrows}</tbody></table></div></div></div>""", base)

        # ── 方法分類 ──
        mrows = ""
        for g in (meth or {}).get("groups", []):
            mrows += (f'<tr><td class="l" colspan="5" style="background:#0d1424;'
                      f'font-weight:700;color:#9fd4ff">{esc(g["label"])}（{len(g["rows"])} 隻）</td></tr>')
            for r in sorted(g["rows"], key=lambda z: -(z.get("score") or 0)):
                rs = "、".join((r.get("reasons") or [])[:2])
                mrows += (f'<tr><td class="l"><span class="tk">{esc(r.get("ticker"))}</span></td>'
                          f'<td>{num(r.get("score"),0)}</td>'
                          f'<td class="l">{esc(r.get("watch_price") or "—")}</td>'
                          f'<td class="l">{esc(r.get("invalidation") or "—")}</td>'
                          f'<td class="l dim">{esc(rs)}</td></tr>')
        pages["method"] = ("方法分類", f"""
<div class="card"><h2>Layer 2 · 每個方法各自一個清單 <small>{esc((meth or {}).get("src") or "冇快照")}</small></h2>
 <div class="body"><div class="note">Focus ＝ 已經起動、等入場；Stalk ＝ 未起動、放觀察名單。
 呢度<b>照原樣分組</b>，唔重新判斷，避免我二次演繹。</div>
 <div class="scroll"><table><thead><tr><th class="l">代號</th><th>分數</th>
 <th class="l">觸發條件</th><th class="l">失效條件</th><th class="l">理由</th></tr></thead>
 <tbody>{mrows or '<tr><td colspan=5 class="dim">冇 Layer2 快照</td></tr>'}</tbody></table></div></div></div>""", base)

    # ── RS 板 ──
    if rsb:
        mx = max(abs(r["ex1m"]) for r in rsb["rows"]) or 1
        rr = "".join(
            f'<tr><td>{i+1}</td><td class="l"><span class="tk">{esc(r["etf"])}</span> '
            f'<span class="dim">{esc(r["name"])}</span></td>'
            f'<td class="l dim">{esc(r["sector"])}</td>'
            f'<td><b>{r["thrust"]:.0f}%</b></td>'
            f'<td class="l">{spark_svg(r["spark"])}</td>'
            f'<td class="l">{bar(r["ex1m"], mx, r["ex1m"] < 0)} '
            f'<span class="{tone(r["ex1m"])}">{sgn(r["ex1m"],1)}%</span></td>'
            f'<td>{sgn(r["r1d"],2)}%</td><td>{pct(r["r1m"],1)}</td>'
            f'<td>{pct(r["off52w"],1)}</td><td>{r["pct"]}</td></tr>'
            for i, r in enumerate(rsb["rows"]))
        pages["rsboard"] = ("RS 板", f"""
<div class="warn">⚠ <b>呢個係我嘅定義，唔係 Jeff Sun 嘅原文數字</b>。
 Jeff 嘅 <code>RS Thrust Rate %</code> 我未取得原文定義，所以呢個板用我寫死喺
 <code>build_site.py</code> 嘅版本（見下面註解）。要對得住佢原文，就要有佢嘅定義。</div>
<div class="card"><h2>ETF 群組相對強度 <small>資料至 {esc(rsb["as_of"])}｜SPY 1 個月 {pct(rsb["spy1m"],1)}</small></h2>
 <div class="body"><table><thead><tr><th>#</th><th class="l">ETF / 名稱</th><th class="l">板塊</th>
 <th>推力率</th><th class="l">1月超額走勢（30日）</th><th class="l">1月超額（百分位）</th><th>日變</th><th>1月</th><th>距52週高</th>
 <th>RS 百分位</th></tr></thead><tbody>{rr}</tbody></table>
 <div class="note"><b>推力率</b>＝最近 30 個交易日之中，呢隻 ETF 嘅 21 日回報贏 SPY 嘅比例。
 <b>1月超額走勢</b>＝每日「21 日回報 − SPY 21 日回報」嘅迷你折線（綠＝近月整體領先、紅＝落後）。
 <b>RS 百分位</b>＝1 個月超額回報喺全部群組之中嘅排名百分位。
 全部係我自己定義（Jeff 原文未取得），只可以做相對比較，唔可以當佢嘅數。</div></div></div>""", base)

    # ── 未接分頁 ──
    pages["cycle"] = ("成長週期", """
<div class="card"><h2>🌀 Growth Cycle · 未接</h2><div class="body">
<div class="todo"><b>狀態：掌握定義，等 Desmond 確認一個參數。</b><br><br>
由你俾嘅 Lab Report 圖蒸餾出嚟嘅模型：<br>
① 成長／價值比率（兩條線）→ ② 攞<b>週線</b>高低點嘅 <b>EMA10</b> 做「風險閘」帶<br>
③ 收市<b>升穿</b>帶 ＝ risk-on；<b>跌穿</b>帶 ＝ risk-off；<b>帶內</b> ＝ 維持上一邊（避免來回鋸）<br>
④ 六個區：RISK-OFF → PROBE → RAMP UP → TRIM 或 HOLD → RELOAD → 回落<br><br>
<b>我需要你答一句：</b>「成長／價值比率」用邊兩條？<br>
（我見過嘅可能：<code>IWF/IWD</code>（羅素 1000 成長／價值）、<code>IWY/IWX</code>、
<code>VUG/VTV</code>、或者你自己嘅組合）</div></div></div>""", base)

    pages["setups"] = ("Setups", """
<div class="card"><h2>📐 Setups · 未接</h2><div class="body">
<div class="todo"><b>狀態：等 Desmond 確認三個欄位嘅出處。</b><br><br>
你圖裏面嘅 Lab Report「The Plan」每一行有：<br>
① 買入線 / 等待線 / 目標 / 止蝕<br>
② 一條<b>由 −3 到 +5 ATR</b> 嘅橫向帶，標出「邊次收市落喺買入區」、「用咗幾成」、
   「虛線 ＝ 最舊嗰次收市」、「實線 ＝ 用得最多嗰次」、「綠 ＝ 同一 session、最早落喺帶內嗰個」<br>
③ 右邊一個迷你方塊圖：最近 30 次收市有幾次落喺帶內 + 恢復日期 + 量／價標籤<br><br>
①②我哋已經有（<code>daily_plan.stop_plan()</code>、<code>rs_select</code>），
③ 需要每次收市嘅落帶記錄 —— 要開始累積。<br>
<b>我需要你答一句：</b>「虛線／實線」同「綠方格」係邊個規則計出嚟（你自己嘅，
定係來自某篇文章）？冇原文我就唔敢砌，砌錯會誤導你自己。</div></div></div>""", base)

    # ── 交易台（我原本嘅 dashboard）──
    src_desk = os.path.join(LAB, "output", f"dashboard_{datetime.date.today().isoformat()}.html")
    if not os.path.exists(src_desk):
        cands = sorted(glob.glob(os.path.join(LAB, "output", "dashboard_*.html")))
        src_desk = cands[-1] if cands else None
    if src_desk:
        with io.open(src_desk, encoding="utf-8") as f:
            desk_html = f.read()
        desk_html = inject_nav(desk_html)
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
