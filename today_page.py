# -*- coding: utf-8 -*-
"""today_page.py — 手機首頁「今日 / 大市 / 名單 / 工具」（Desmond 2026-11-16 設計稿）。

所有數字由既有產物讀取，冇一個係手打死數：
  breadth_YYYYMMDD.json            → regime / posture / ADL / NNNL / %40MA / SPY
  output/_dashboard_history.jsonl  → regime / trade_cap / 5DMA / 新高新低
  trading-os-web/data/screener.json→ 關鍵球候選（RS/ATRX/距52高/TIGHT）
  trading-os/budget_gate.state()   → 配額（唯一實作，唔喺度再計）
缺失一律顯示 —（Missing ≠ Zero）。
"""
from __future__ import annotations

import glob
import io
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
TS = r"C:\Users\rain0\trading-os"
if TS not in sys.path:
    sys.path.insert(0, TS)

CSS = """
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
.tt-wrap{max-width:560px;margin:0 auto;padding:8px 14px 30px;font-family:inherit}
.tt-top{display:flex;align-items:baseline;justify-content:space-between;padding:8px 0 10px;
  border-bottom:1px solid rgba(148,163,184,.22);margin-bottom:14px}
.tt-brand{font-size:13px;font-weight:700;letter-spacing:.08em;opacity:.75}
.tt-asof{font-size:11.5px;opacity:.6;font-variant-numeric:tabular-nums}
.tt-hero{border:1px solid rgba(245,197,66,.42);background:rgba(245,197,66,.12);
  border-radius:16px;padding:18px 18px 16px;margin:0 0 12px}
.tt-k{font-size:11.5px;letter-spacing:.14em;font-weight:800;opacity:.8;margin:0 0 3px}
.tt-lamp{font-size:40px;line-height:1;font-weight:800;letter-spacing:-.02em;margin:0 0 4px;color:#f5c542}
.tt-dir{font-size:19px;font-weight:800;margin:0 0 14px}
.tt-verdict{font-size:30px;font-weight:800;margin:0 0 8px;letter-spacing:-.02em}
.tt-signal{font-size:15px;line-height:1.5;margin:0}
.tt-meta{font-size:12.5px;opacity:.68;margin:12px 0 0;line-height:1.6;font-variant-numeric:tabular-nums}
.tt-block{background:rgba(148,163,184,.07);border:1px solid rgba(148,163,184,.2);
  border-radius:13px;padding:13px 15px;margin:0 0 10px}
.tt-block h3{margin:0 0 9px;font-size:11.5px;letter-spacing:.08em;opacity:.7;font-weight:800}
.tt-kv{display:flex;justify-content:space-between;gap:10px;padding:6px 0;font-size:14px;
  border-bottom:1px solid rgba(148,163,184,.12)}
.tt-kv:last-child{border-bottom:0}
.tt-kv .k{opacity:.68}
.tt-kv .v{font-weight:700;font-variant-numeric:tabular-nums}
.tt-pills{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.tt-pill{background:rgba(148,163,184,.12);border:1px solid rgba(148,163,184,.28);
  border-radius:999px;padding:4px 9px;font-size:13px;font-weight:700}
.tt-pill.hot{border-color:rgba(245,197,66,.5);color:#f5c542}
.tt-pill.bad{color:#ff8b8b;border-color:rgba(255,107,107,.4)}
.tt-note{font-size:12px;opacity:.62;line-height:1.6;margin:8px 0 0}
.tt-next{font-size:15px;line-height:1.5;margin:0}
.tt-tbl{width:100%;border-collapse:collapse;font-size:12.5px;font-variant-numeric:tabular-nums}
.tt-tbl th{text-align:left;font-size:10px;letter-spacing:.04em;opacity:.66;padding:5px 5px;
  border-bottom:1px solid rgba(148,163,184,.3);white-space:nowrap}
.tt-tbl td{padding:4px 5px;border-bottom:1px solid rgba(148,163,184,.1);white-space:nowrap}
.tt-tbl a{color:inherit;text-decoration:none;font-weight:800}
.tt-tbl a:hover{color:#f97316}
.tt-foot{font-size:11px;opacity:.5;line-height:1.6;margin-top:16px}
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


def _breadth():
    p = _latest(os.path.join(TS, "output", "breadth_*.json"))
    d = _j(p, {}) if p else {}
    return d, (os.path.basename(p) if p else None)


def _dash():
    p = os.path.join(TS, "output", "_dashboard_history.jsonl")
    try:
        lines = [l for l in io.open(p, encoding="utf-8") if l.strip()]
    except OSError:
        return {}
    try:
        return json.loads(lines[-1])
    except (IndexError, ValueError):
        return {}


def _budget():
    try:
        import budget_gate
        return budget_gate.state()
    except Exception:                                            # noqa: BLE001
        return {}


def _screen():
    return _j(os.path.join(HERE, "data", "screener.json"), {}) or {}


def _insight():
    p = _latest(os.path.join(TS, "output", "market_insight_*.json"))
    return (_j(p, {}) or {}) if p else {}


def _key_shots(rows, n=6):
    out = []
    for r in rows:
        rs, ax, d52, tg = r.get("rs"), r.get("atrx"), r.get("d52w"), r.get("tight")
        if None in (rs, ax, d52, tg):
            continue
        if rs >= 90 and 0 <= ax <= 4 and d52 >= -10 and tg >= 45:
            out.append(r)
    out.sort(key=lambda x: -(x.get("rs") or 0))
    return out[:n]


def build():
    br, brf = _breadth()
    dash = _dash()
    bud = _budget()
    scr = _screen()
    ins = _insight()
    rows = scr.get("rows") or []
    day = (br.get("as_of") or "")[:10] or scr.get("as_of") or dash.get("date") or date.today().isoformat()

    regime = dash.get("regime") or br.get("regime") or "—"
    cap = dash.get("trade_cap")
    lamp, lc = ("綠燈", "#3ddc97") if regime == "BULL" else (
        ("黃燈", "#f5c542") if regime == "CHOP" else ("紅燈", "#ff6b6b"))
    verdict = ("可以做（A+ 一單）" if cap == 1 else
               "可以做到 %s 單" % cap if isinstance(cap, int) and cap > 1 else
               ("唔做新多" if cap == 0 else "—"))
    ks = _key_shots(rows)
    status = br.get("status") or "—"

    P = [f"<style>{CSS}</style>", '<div class="tt-wrap">']
    P.append(f'<div class="tt-top"><span class="tt-brand">交易台 · 今日</span>'
             f'<span class="tt-asof">{day}｜{brf or "—"}</span></div>')

    # ── 今日 ──────────────────────────────────────────────
    P.append(f'<div class="tt-hero"><p class="tt-k">今日燈</p>'
             f'<p class="tt-lamp" style="color:{lc}">{lamp}</p>'
             f'<p class="tt-dir">{regime}</p>'
             f'<p class="tt-k">做定唔做</p>'
             f'<p class="tt-verdict">{verdict}</p>'
             f'<p class="tt-signal">{status}｜關鍵球候選 {len(ks)} 隻｜'
             f'配額 剩 {bud.get("left", "—")}</p>'
             f'<p class="tt-meta">SPY {_f(dash.get("spy_close") or br.get("spy_close"), 2)}'
             f'｜5DMA {_f(dash.get("spy_5dma"), 2)}'
             f'｜新高／新低 {dash.get("nh", "—")}／{dash.get("nl", "—")}<br>'
             f'QQQ 距52高 {_f(dash.get("qqq_off_52wh_pct"), 1)}%'
             f'｜%40MA {_f(br.get("pct40ma"), 1)}%</p></div>')

    P.append('<div class="tt-block"><h3>關鍵球（四條全中）</h3>')
    if ks:
        P.append('<div class="tt-pills">' + "".join(
            f'<span class="tt-pill hot">{r["t"]} RS{int(r["rs"])}</span>' for r in ks) + '</div>')
    else:
        P.append('<p class="tt-note" style="margin:0">今日冇 A+ 候選 —— 唔等於要入場，等於今日可以唔做。</p>')
    P.append('<p class="tt-note">RS≥90、ATRX 0–4、距52高≥−10、TIGHT≥45。'
             '候選數本身就係信息：得 2 隻就唔應該做 6 單。</p></div>')

    bud_line = ("配額 %s（%s）｜已用 %s｜剩 %s｜%s" % (
        bud.get("quota", "—"), bud.get("regime", "—"), bud.get("used", "—"),
        bud.get("left", "—"), "收工" if bud.get("closed") else "可以做（只做 A+）")
        if bud else "配額：—")
    P.append('<div class="tt-block"><h3>下一步</h3>'
             f'<p class="tt-next">{bud_line}</p>'
             '<p class="tt-note">連蝕 2 單 → 當日停手；10:30 ET 後一律收工。'
             '關鍵球風險 0.5%（≤0.6%）、非關鍵球 0.2% 探路。</p></div>')

    # ── 大市 ──────────────────────────────────────────────
    P.append('<div class="tt-block"><h3>廣度主尺（自己計）</h3>')
    for k, v in [("Regime／Posture", f'{br.get("regime","—")}／{(br.get("posture") or {}).get("posture","—")}'),
                 ("多空比", _f(br.get("ls_ratio_proxy"), 2)),
                 ("ADL", _f((br.get("adl") or {}).get("value"), 1)),
                 ("新高新低淨值", _f((br.get("nnnl") or {}).get("value"), 1)),
                 ("站上 40MA", _f(br.get("pct40ma"), 1) + "%"),
                 ("SPY 收市", _f(br.get("spy_close"), 2))]:
        P.append(f'<div class="tt-kv"><span class="k">{k}</span><span class="v">{v}</span></div>')
    P.append(f'<p class="tt-note">範圍 {br.get("universe","—")}。呢把係主尺；'
             'Stockbee 4% 尺係另一把，唔可以加減。</p></div>')

    if ins:
        _b = ins.get("breadth") or {}
        _v = ins.get("vix") or {}
        P.append('<div class="tt-block"><h3>市場簡報</h3>')
        for k, v in [("日期", ins.get("date", "—")),
                     ("站上 20/50/200MA", f'{_f(_b.get("above20"),1)}%／{_f(_b.get("above50"),1)}%／{_f(_b.get("above200"),1)}%'),
                     ("新高／新低（20日）", f'{_b.get("new_highs","—")}／{_b.get("new_lows","—")}'),
                     ("VIX", f'{_f(_v.get("last"),2)}（10MA {_f(_v.get("ma10"),2)}）'),
                     ("領導", (ins.get("lead") or {}).get("text", "—")),
                     ("姿態", ins.get("posture_label", "—"))]:
            P.append(f'<div class="tt-kv"><span class="k">{k}</span><span class="v">{v}</span></div>')
        P.append('</div>')

    # ── 名單 ──────────────────────────────────────────────
    P.append('<div class="tt-block"><h3>關鍵球清單</h3>')
    if ks:
        P.append('<table class="tt-tbl"><thead><tr><th>代號</th><th>價</th><th>RS</th>'
                 '<th>ATRX</th><th>距52高</th><th>TIGHT</th></tr></thead><tbody>')
        for r in ks:
            P.append(f'<tr><td><a href="https://www.tradingview.com/chart/?symbol={r["t"]}"'
                     f' target="_blank" rel="noopener">{r["t"]}</a></td>'
                     f'<td>{_f(r.get("close"), 2)}</td><td>{int(r["rs"])}</td>'
                     f'<td>{_f(r.get("atrx"), 1)}</td><td>{_f(r.get("d52w"), 1)}%</td>'
                     f'<td>{_f(r.get("tight"), 0)}</td></tr>')
        P.append('</tbody></table>')
    else:
        P.append('<p class="tt-note" style="margin:0">— 今日冇</p>')
    P.append('<p class="tt-note">完整篩選、止蝕／股數：開 Stock Screener。'
             '距52高負數＝離高位幾遠。</p></div>')

    # ── 工具 ──────────────────────────────────────────────
    links = [("選股", [("Stock Screener", "screener.html"), ("Stock Wall", "screenwall.html"),
                       ("PEG 清單", "peg.html"), ("Setup Alert", "alerts.html"),
                       ("Daily Scan", "dailyscan.html"), ("RS 新高", "rsnewhigh.html")]),
             ("大市", [("環境熱力圖", "regimeheat.html"), ("市場簡報", "index.html"),
                       ("Market Monitor", "mm.html"), ("成長週期", "cycle.html")]),
             ("成績", [("Review", "review.html"), ("Think in R", "thinkinr.html"),
                       ("Backtest", "backtest.html"), ("系統審計", "audit.html")]),
             ("流程", [("每日流程", "process.html"), ("使用手冊", "howto.html"),
                       ("倉位計算機", "calculator.html")])]
    for g, items in links:
        P.append(f'<div class="tt-block"><h3>{g}</h3><div class="tt-pills">')
        P.append("".join(f'<a class="tt-pill" href="{h}">{n}</a>' for n, h in items))
        P.append('</div></div>')

    P.append('<p class="tt-foot">全部唯讀、研究用途，非買入指令。'
             '缺失顯示 —，唔會當 0。</p></div>')
    return ("交易台 · 今日", "".join(P))
