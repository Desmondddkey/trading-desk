# -*- coding: utf-8 -*-
"""nel.py — v1 Market Console（NEL 排版 × 我哋數據層）。

4 個 tab：今日 / 大市 / 名單 / 工具
所有數字由既有產物讀取，缺失顯示 —（唔當 0）：
  trading-os/output/breadth_*.json      → environment
  trading-os/output/market_insight_*.json → tape / breadth / vix
  trading-os/output/_dashboard_history.jsonl → regime / trade_cap
  trading-os/budget_gate.state()        → 配額（唯一實作）
  trading-os-web/data/screener.json     → 名單 / sector 聚合
  trading-os-web/data/positioning.json  → COT 大戶倉位（CFTC）
"""
from __future__ import annotations

import glob
import io
import json
import os
import statistics as st
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
TS = r"C:\Users\rain0\trading-os"
if TS not in sys.path:
    sys.path.insert(0, TS)

CSS = """
.nx{max-width:1180px;margin:0 auto;padding:0 14px 40px}
.nx-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;
  padding:14px 0 10px;border-bottom:1px solid rgba(148,163,184,.25);flex-wrap:wrap}
.nx-brand{font-size:15px;font-weight:800;letter-spacing:.06em}
.nx-meta{font-size:11px;opacity:.6;font-variant-numeric:tabular-nums}
.nx-tabs{display:flex;gap:6px;flex-wrap:wrap;padding:10px 0 4px}
.nx-tabs a{font-size:12.5px;font-weight:700;padding:5px 11px;border-radius:999px;
  border:1px solid rgba(148,163,184,.3);text-decoration:none;color:inherit;opacity:.72}
.nx-tabs a.on{background:rgba(59,130,246,.16);border-color:rgba(59,130,246,.55);opacity:1}
.nx-tabs a:hover{opacity:1}
.nx-sec{margin:18px 0 6px}
.nx-sec h2{margin:0 0 8px;font-size:11px;letter-spacing:.13em;font-weight:800;opacity:.62;
  text-transform:uppercase;display:flex;justify-content:space-between;align-items:baseline}
.nx-sec h2 span{font-size:10.5px;letter-spacing:0;opacity:.8;font-weight:600}
.nx-grid{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.nx-card{border:1px solid rgba(148,163,184,.22);border-radius:9px;padding:9px 11px;
  background:rgba(148,163,184,.05)}
.nx-card .k{font-size:10px;letter-spacing:.06em;opacity:.6;font-weight:700}
.nx-card .v{font-size:22px;font-weight:800;line-height:1.2;font-variant-numeric:tabular-nums}
.nx-card .s{font-size:10.5px;opacity:.62;margin-top:2px}
.nx-card.good .v{color:#3ddc97}.nx-card.bad .v{color:#ff6b6b}.nx-card.warn .v{color:#f5c542}
.nx-tbl{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums}
.nx-tbl th{text-align:left;font-size:10px;letter-spacing:.05em;opacity:.6;font-weight:700;
  padding:5px 6px;border-bottom:1px solid rgba(148,163,184,.32);white-space:nowrap}
.nx-tbl td{padding:4px 6px;border-bottom:1px solid rgba(148,163,184,.09);white-space:nowrap}
.nx-tbl a{color:inherit;text-decoration:none;font-weight:800}
.nx-tbl a:hover{color:#f97316}
.nx-tbl tr.hi td{background:rgba(61,220,151,.06)}
.nx-pos{color:#3ddc97}.nx-neg{color:#ff8b8b}.nx-dim{opacity:.55}
.nx-hero{border:1px solid rgba(245,197,66,.4);background:rgba(245,197,66,.1);
  border-radius:14px;padding:16px 18px;margin:14px 0 6px}
.nx-hero .lamp{font-size:34px;font-weight:800;line-height:1.05;margin:2px 0 2px;color:#f5c542}
.nx-hero .dir{font-size:16px;font-weight:700;opacity:.85;margin:0 0 12px}
.nx-hero .vd{font-size:24px;font-weight:800;margin:0 0 6px}
.nx-hero .sig{font-size:13px;line-height:1.5;margin:0;opacity:.85}
.nx-note{font-size:11px;opacity:.56;line-height:1.6;margin:6px 0 0}
.nx-pill{display:inline-block;border:1px solid rgba(148,163,184,.3);border-radius:999px;
  padding:2px 8px;font-size:11.5px;font-weight:700;margin:0 4px 4px 0}
.nx-pill.hot{border-color:rgba(245,197,66,.55);color:#f5c542}
.nx-pill.short{border-color:rgba(255,107,107,.5);color:#ff8b8b}
.nx-pill.long{border-color:rgba(61,220,151,.5);color:#3ddc97}
@media(max-width:640px){.nx-card .v{font-size:18px}}
"""


def _j(p, d=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return d


def _latest(pat):
    fs = sorted(glob.glob(pat))
    return fs[-1] if fs else None


def _f(v, n=1, plus=False):
    if v is None:
        return "—"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    return f"{v:+.{n}f}" if plus else f"{v:.{n}f}"


def _cls(v):
    if v is None:
        return ""
    return "nx-pos" if v > 0 else ("nx-neg" if v < 0 else "")


SECTOR_ZH = {
    "Retail Trade": "零售", "Consumer Durables": "耐用消費",
    "Consumer Non-Durables": "必需消費", "Health Technology": "醫療科技",
    "Communications": "通訊", "Energy Minerals": "能源",
    "Technology Services": "科技服務", "Electronic Technology": "電子科技",
    "Finance": "金融", "Producer Manufacturing": "工業製造",
    "Non-Energy Minerals": "非能源礦產", "Process Industries": "化工",
    "Distribution Services": "分銷", "Consumer Services": "消費服務",
    "Transportation": "運輸", "Health Services": "醫療服務",
    "Utilities": "公用", "Commercial Services": "商業服務",
    "Industrial Services": "工業服務", "Miscellaneous": "其他",
}


def _zh_sector(s):
    return SECTOR_ZH.get(s, s)


def _load():
    _bp = _latest(os.path.join(TS, "output", "breadth_*.json"))
    br = (_j(_bp, {}) or {}) if _bp else {}
    if _bp:
        br["_file"] = os.path.basename(_bp)
    ins = _j(_latest(os.path.join(TS, "output", "market_insight_*.json")) or "", {}) or {}
    dash = {}
    try:
        ls = [l for l in io.open(os.path.join(TS, "output", "_dashboard_history.jsonl"),
                                 encoding="utf-8") if l.strip()]
        dash = json.loads(ls[-1]) if ls else {}
    except OSError:
        pass
    try:
        import budget_gate
        bud = budget_gate.state()
    except Exception:                                            # noqa: BLE001
        bud = {}
    scr = _j(os.path.join(HERE, "data", "screener.json"), {}) or {}
    pos = _j(os.path.join(HERE, "data", "positioning.json"), {}) or {}
    return br, ins, dash, bud, scr, pos


def _key_shots(rows):
    out = []
    for r in rows:
        rs, ax = r.get("rs"), r.get("atrx")
        d52 = r.get("d52w", r.get("off52_tv"))
        tg = r.get("tight")
        if None in (rs, ax, d52, tg):
            continue
        if rs >= 90 and 0 <= ax <= 4 and d52 >= -10 and tg >= 45:
            out.append(r)
    out.sort(key=lambda x: -(x.get("rs") or 0))
    return out


def _sector_agg(rows):
    g = {}
    for r in rows:
        s = r.get("sector") or "—"
        if s == "—":
            continue
        d = g.setdefault(s, {"rs": [], "m1": [], "n": 0})
        d["n"] += 1
        if r.get("rs") is not None:
            d["rs"].append(r["rs"])
        m1 = (r.get("perf") or {}).get("1m")
        if m1 is not None:
            d["m1"].append(m1)
    out = []
    for s, d in g.items():
        if d["n"] < 3:
            continue
        out.append({"sector": s, "n": d["n"],
                    "rs": round(st.median(d["rs"]), 0) if d["rs"] else None,
                    "m1": round(st.mean(d["m1"]), 1) if d["m1"] else None})
    out.sort(key=lambda x: -(x["m1"] if x["m1"] is not None else -99))
    return out


def build():
    br, ins, dash, bud, scr, pos = _load()
    rows = scr.get("rows") or []
    ks = _key_shots(rows)
    day = (br.get("as_of") or "")[:10] or scr.get("as_of") or date.today().isoformat()
    regime = dash.get("regime") or br.get("regime") or "—"
    cap = dash.get("trade_cap")
    lamp = "綠燈" if regime == "BULL" else ("黃燈" if regime == "CHOP" else "紅燈")
    verdict = ("唔做新多" if cap == 0 else
               f"可以做 {cap} 單（只做 A+）" if isinstance(cap, int) else "—")
    status = br.get("status") or "—"

    P = [f"<style>{CSS}</style>", '<div class="nx">']
    P.append(f'<div class="nx-head"><span class="nx-brand">MARKET CONSOLE</span>'
             f'<span class="nx-meta">{day}｜{br.get("_file", "—")}'
             f'｜screener {scr.get("as_of", "—")}</span></div>')
    _tab_items = [("today", "今日"), ("market", "大市"), ("list", "名單"), ("tools", "工具")]
    _tab_html = []
    for _h, _n in _tab_items:
        _acl = ' class="on"' if _h == "today" else ""
        _tab_html.append(f'<a href="#{_h}"{_acl}>{_n}</a>')
    P.append('<div class="nx-tabs">' + "".join(_tab_html) + '</div>')

    # ── 今日 ────────────────────────────────────────────
    P.append('<div id="today" class="nx-sec"><h2>今日 <span>做定唔做</span></h2>')
    P.append(f'<div class="nx-hero"><div class="nx-card-k" style="font-size:10px;letter-spacing:.12em;'
             f'opacity:.65;font-weight:700">今日燈</div>'
             f'<p class="lamp">{lamp}</p><p class="dir">{regime}</p>'
             f'<p class="vd">{verdict}</p>'
             f'<p class="sig">{status}｜關鍵球 {len(ks)} 隻｜配額 剩 {bud.get("left", "—")}'
             f'｜SPY {_f(dash.get("spy_close") or br.get("spy_close"), 2)}</p></div>')
    if ks:
        P.append('<div style="margin:8px 0 0">' + "".join(
            f'<span class="nx-pill hot">{r["t"]} RS{int(r["rs"])}</span>' for r in ks) + '</div>')
    P.append(f'<p class="nx-note">關鍵球＝RS≥90、ATRX 0–4、距52高≥−10、TIGHT≥45。'
             f'配額 {bud.get("quota", "—")}（{bud.get("regime", "—")}）｜已用 {bud.get("used", "—")}。'
             f'連蝕 2 單停手；10:30 ET 後收工。</p></div>')

    # ── 大市 ────────────────────────────────────────────
    P.append('<div id="market" class="nx-sec"><h2>Environment <span>參與度</span></h2>')
    P.append('<div class="nx-grid">')
    env = [("ADL", _f((br.get("adl") or {}).get("value"), 1), "10日累計"),
           ("新高新低淨值", _f((br.get("nnnl") or {}).get("value"), 1), "20日新高−新低"),
           ("站上 40MA", _f(br.get("pct40ma"), 1) + "%", br.get("universe", "")),
           ("多空比", _f(br.get("ls_ratio_proxy"), 2), "proxy"),
           ("SPY 收市", _f(br.get("spy_close"), 2), "breadth 檔"),
           ("Posture", (br.get("posture") or {}).get("posture", "—"), br.get("regime", ""))]
    for k, v, s in env:
        P.append(f'<div class="nx-card"><div class="k">{k}</div><div class="v">{v}</div>'
                 f'<div class="s">{s}</div></div>')
    P.append('</div>')

    # tape
    ix = ins.get("indices") or {}
    if ix:
        P.append('<div class="nx-sec"><h2>Tape <span>指數 vs 均線</span></h2>'
                 '<table class="nx-tbl"><thead><tr><th>指數</th><th>收市</th>'
                 '<th>vs 20MA</th><th>vs 50MA</th><th>vs 200MA</th></tr></thead><tbody>')
        for sym in ("SPY", "QQQ", "IWM", "DIA"):
            d = ix.get(sym)
            if not d or d.get("last") is None:
                continue
            last = d["last"]
            cells = []
            for ma in ("ma20", "ma50", "ma200"):
                m = d.get(ma)
                cells.append(f'{_f(100*(last/m-1),1,True)}%' if m else "—")
            P.append(f'<tr><td><b>{sym}</b></td><td>{_f(last,2)}</td>'
                     + "".join(f'<td>{c}</td>' for c in cells) + '</tr>')
        P.append('</tbody></table><p class="nx-note">紅色＝跌穿該均線；綠色＝站上。</p></div>')

    # breadth from insight
    b = ins.get("breadth") or {}
    if b:
        P.append('<div class="nx-sec"><h2>Breadth <span>% 站上均線</span></h2><div class="nx-grid">')
        for k, v in [("20MA", b.get("above20")), ("50MA", b.get("above50")),
                     ("200MA", b.get("above200")), ("20日新高", b.get("new_highs")),
                     ("20日新低", b.get("new_lows"))]:
            P.append(f'<div class="nx-card"><div class="k">{k}</div>'
                     f'<div class="v">{_f(v,1) if isinstance(v,float) else (v if v is not None else "—")}</div></div>')
        P.append('</div></div>')

    # sector
    secs = _sector_agg(rows)
    if secs:
        P.append('<div class="nx-sec"><h2>Sector <span>本池聚合（中位 RS／平均 1M）</span></h2>'
                 '<table class="nx-tbl"><thead><tr><th>板塊</th><th>隻數</th>'
                 '<th>中位 RS</th><th>平均 1M</th></tr></thead><tbody>')
        for s in secs[:4] + secs[-2:]:
            P.append(f'<tr><td>{_zh_sector(s["sector"])}</td><td>{s["n"]}</td>'
                     f'<td>{_f(s["rs"],0)}</td>'
                     f'<td class="{_cls(s["m1"])}">{_f(s["m1"],1,True)}%</td></tr>')
        P.append('</tbody></table><p class="nx-note">Top4 + Bottom2。'
                 '聚合自本地 731 隻有 OHLC 嘅股票，唔係官方 sector ETF。</p></div>')

    # positioning
    ms = pos.get("markets") or []
    if ms:
        P.append('<div class="nx-sec"><h2>Positioning <span>COT 大戶倉位（CFTC）</span></h2>'
                 '<div>')
        for m in ms:
            lg = (m.get("participants") or {}).get("large") or {}
            c = m.get("crowded") or "—"
            cls = "short" if "Short" in c else ("long" if "Long" in c else "")
            P.append(f'<span class="nx-pill {cls}">{m["etf"]} {c}</span>')
        P.append('</div><table class="nx-tbl"><thead><tr><th>市場</th><th>ETF</th>'
                 '<th>大戶淨倉</th><th>5年百分位</th><th>狀態</th><th>報告日</th></tr></thead><tbody>')
        for m in ms:
            lg = (m.get("participants") or {}).get("large") or {}
            P.append(f'<tr><td>{m.get("name","—")}</td><td>{m.get("etf","—")}</td>'
                     f'<td class="{_cls(lg.get("net"))}">{lg.get("net", "—")}</td>'
                     f'<td>{_f(lg.get("idx5y"),0)}</td><td>{m.get("crowded","—")}</td>'
                     f'<td class="nx-dim">{m.get("date","—")}</td></tr>')
        P.append('</tbody></table><p class="nx-note">'
                 f'來源 {pos.get("source","CFTC")}｜抓取 {str(pos.get("fetchedAt",""))[:16]}。'
                 '百分位＝大戶淨倉相對 5 年歷史；≤10 擁擠空、≥90 擁擠多。</p></div>')
    else:
        P.append('<div class="nx-sec"><h2>Positioning</h2>'
                 '<p class="nx-note">DATA_UNAVAILABLE — 未跑 positioning.py</p></div>')

    # ── 名單 ────────────────────────────────────────────
    P.append('<div id="list" class="nx-sec"><h2>名單 <span>關鍵球 A+</span></h2>')
    if ks:
        P.append('<table class="nx-tbl"><thead><tr><th>代號</th><th>價</th><th>RS</th>'
                 '<th>ATRX</th><th>距52高</th><th>TIGHT</th><th>止蝕</th><th>距 pivot</th>'
                 '</tr></thead><tbody>')
        for r in ks[:20]:
            d52 = r.get("d52w", r.get("off52_tv"))
            P.append(f'<tr class="hi"><td><a href="https://www.tradingview.com/chart/?symbol={r["t"]}"'
                     f' target="_blank" rel="noopener">{r["t"]}</a></td>'
                     f'<td>{_f(r.get("close"),2)}</td><td>{int(r["rs"])}</td>'
                     f'<td>{_f(r.get("atrx"),1)}</td><td>{_f(d52,1)}%</td>'
                     f'<td>{_f(r.get("tight"),0)}</td><td>{_f(r.get("stop"),2)}</td>'
                     f'<td>{_f(r.get("dist_pivot"),1)}%</td></tr>')
        P.append('</tbody></table>')
    else:
        P.append('<p class="nx-note">今日冇 A+ 候選 —— 等於今日可以唔做。</p>')
    P.append('<p class="nx-note">完整 744 隻篩選：<a href="screener.html">Stock Screener</a>｜'
             '季度名單：<a href="peg.html">PEG 清單</a>｜觸發：<a href="alerts.html">Setup Alert</a></p></div>')

    # ── 工具 ────────────────────────────────────────────
    P.append('<div id="tools" class="nx-sec"><h2>工具 <span>內頁入口</span></h2><div class="nx-grid">')
    groups = [("選股", [("Stock Screener", "screener.html"), ("Stock Wall", "screenwall.html"),
                       ("PEG 清單", "peg.html"), ("Setup Alert", "alerts.html"),
                       ("Daily Scan", "dailyscan.html"), ("RS 新高", "rsnewhigh.html")]),
              ("大市", [("環境熱力圖", "regimeheat.html"), ("市場簡報", "index.html"),
                       ("Market Monitor", "mm.html"), ("成長週期", "cycle.html")]),
              ("成績", [("Review", "review.html"), ("Think in R", "thinkinr.html"),
                       ("Backtest", "backtest.html"), ("系統審計", "audit.html")]),
              ("流程", [("每日流程", "process.html"), ("使用手冊", "howto.html"),
                       ("倉位計算機", "calculator.html")])]
    for g, items in groups:
        P.append(f'<div class="nx-card"><div class="k">{g}</div>')
        P.append("".join(f'<div style="margin:4px 0"><a href="{h}" '
                         f'style="color:inherit;text-decoration:none;font-size:12.5px">{n}</a></div>'
                         for n, h in items))
        P.append('</div>')
    P.append('</div></div>')

    P.append('<p class="nx-note" style="margin-top:20px">全部唯讀、研究用途，非買入指令。'
             '缺失顯示 —，唔會當 0。v0 備份：git tag v0-20261116。</p></div>')
    return ("Market Console", "".join(P))
