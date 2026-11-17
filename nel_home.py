# -*- coding: utf-8 -*-
"""nel_home.py — 交易台首頁（Desmond 2026-11-16 手機設計稿 × 我哋數據層）。

4 個 panel＋底部固定 tab：今日 / 大市 / 名單 / 工具
數據邏輯全部 import 自 nel.py（單一實作），呢個模組只負責呈現。
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from nel import (_load, _key_shots, _sector_agg, _zh_sector,      # noqa: E402
                 _f, _cls, _j)

HW = os.path.join(HERE, "data", "headwinds.json")
CR = os.path.join(HERE, "data", "correction_risk.json")
SP13 = os.path.join(HERE, "data", "spark13.json")

CSS = """
.nxt{width:100%;max-width:760px;margin:0 auto;padding:0 0 84px;box-sizing:border-box;
  overflow-x:clip}
.nxt *{min-width:0}
.nxt-top{position:sticky;top:0;z-index:30;display:flex;align-items:baseline;
  justify-content:space-between;gap:10px;padding:12px 16px 10px;
  background:rgba(7,11,22,.94);backdrop-filter:blur(10px);
  border-bottom:1px solid rgba(148,163,184,.25)}
html[data-theme="light"] .nxt-top{background:rgba(246,248,251,.95)}
.nxt-brand{font-size:13px;font-weight:700;letter-spacing:.08em;opacity:.72}
.nxt-asof{font-size:11.5px;opacity:.55;font-variant-numeric:tabular-nums}
.nxt-panel{display:none;padding:16px 16px 24px}
.nxt-panel.on{display:block}
.nxt-hero{border:1px solid rgba(245,197,66,.4);background:rgba(245,197,66,.12);
  border-radius:16px;padding:18px 18px 16px;margin:0 0 12px}
.nxt-k{font-size:11.5px;letter-spacing:.14em;font-weight:800;opacity:.75;margin:0 0 3px}
.nxt-lamp{font-size:44px;line-height:1;font-weight:800;margin:0 0 2px;color:#f5c542}
.nxt-dir{font-size:18px;font-weight:700;opacity:.85;margin:0 0 14px}
.nxt-vd{font-size:28px;font-weight:800;margin:0 0 8px;letter-spacing:-.02em}
.nxt-sig{font-size:14px;line-height:1.5;margin:0;opacity:.9}
.nxt-meta{font-size:12.5px;opacity:.6;margin:12px 0 0;line-height:1.6;
  font-variant-numeric:tabular-nums}
.nxt-block{border:1px solid rgba(148,163,184,.22);border-radius:13px;padding:13px 15px;
  margin:0 0 10px;background:rgba(148,163,184,.05)}
.nxt-block h3{margin:0 0 9px;font-size:11.5px;letter-spacing:.08em;opacity:.62;font-weight:800}
.nxt-kv{display:flex;justify-content:space-between;gap:10px;padding:6px 0;font-size:14px;
  border-bottom:1px solid rgba(148,163,184,.12)}
.nxt-kv:last-child{border-bottom:0}
.nxt-kv .k{opacity:.66}
.nxt-kv .v{font-weight:700;font-variant-numeric:tabular-nums;text-align:right}
.nxt-pills{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px}
.nxt-pill{background:rgba(148,163,184,.12);border:1px solid rgba(148,163,184,.28);
  border-radius:999px;padding:4px 10px;font-size:13px;font-weight:700;text-decoration:none;
  color:inherit}
.nxt-pill.hot{border-color:rgba(245,197,66,.55);color:#f5c542}
.nxt-pill.bad{color:#ff8b8b;border-color:rgba(255,107,107,.4)}
.nxt-note{font-size:11.5px;opacity:.55;line-height:1.6;margin:8px 0 0}
.nxt-next{font-size:15px;line-height:1.5;margin:0}
.nxt-tbl{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums}
.nxt-tbl th{text-align:left;font-size:10px;letter-spacing:.04em;opacity:.6;font-weight:700;
  padding:5px 5px;border-bottom:1px solid rgba(148,163,184,.3);white-space:nowrap}
.nxt-tbl td{padding:4px 5px;border-bottom:1px solid rgba(148,163,184,.1);white-space:nowrap}
.nxt-tbl a{color:inherit;text-decoration:none;font-weight:800}
.nxt-tbl a:hover{color:#f97316}
.nxt-pos{color:#3ddc97}.nxt-neg{color:#ff8b8b}
.nxt-hscroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -15px;padding:0 15px}
.nxt-tabs{position:fixed;left:0;right:0;bottom:0;margin:0 auto;max-width:760px;
  box-sizing:border-box;z-index:60;display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  background:rgba(8,13,26,.97);backdrop-filter:blur(12px);
  border-top:1px solid rgba(148,163,184,.25)}
@media(max-width:420px){.nxt-vd{font-size:24px}.nxt-lamp{font-size:38px}
  .nxt-tabs a,.nxt-tabs button{font-size:12px}}
html[data-theme="light"] .nxt-tabs{background:rgba(246,248,251,.97)}
.nxt-tabs a,.nxt-tabs button{appearance:none;background:transparent!important;border:0!important;
  border-radius:0!important;color:inherit;text-decoration:none;opacity:.5;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;
  padding:8px 0 7px;font-size:12.5px;font-weight:700;letter-spacing:.04em;min-height:52px}
.nxt-tabs .nxt-dot{margin:0}
.nxt-tabs a.on,.nxt-tabs button.on{opacity:1}
.nxt-dot{display:block;width:4px;height:4px;border-radius:50%;background:transparent}
.nxt-tabs a.on .nxt-dot,.nxt-tabs button.on .nxt-dot{background:#f5c542}
"""

JS = """
(function(){
  var ok={today:1,market:1,list:1,tools:1};
  function show(id){
    if(!ok[id]) id='today';
    document.querySelectorAll('.nxt-panel').forEach(function(p){
      p.classList.toggle('on', p.id==='panel-'+id);});
    document.querySelectorAll('.nxt-tabs a,.nxt-tabs button').forEach(function(b){
      b.classList.toggle('on', b.getAttribute('data-tab')===id);});
    if(history.replaceState) history.replaceState(null,'','#'+id);
  }
  document.querySelectorAll('.nxt-tabs a,.nxt-tabs button').forEach(function(b){
    b.addEventListener('click',function(){show(b.getAttribute('data-tab'));window.scrollTo(0,0);});});
  show((location.hash||'#today').replace('#',''));
  window.addEventListener('hashchange',function(){
    show((location.hash||'#today').replace('#',''));});
})();
"""


def _spark(vals, pos4=""):
    """Jeff Sun 風格 13 週 mini bars：最後一根藍色。"""
    if not vals:
        return "—"
    mx = max(abs(v) for v in vals) or 1.0
    bw, gap, hmax = 4.4, 1.6, 16
    w = len(vals) * (bw + gap)
    bars = []
    for i, v in enumerate(vals):
        h = max(1.5, hmax * abs(v) / mx)
        col = "#2563eb" if i == len(vals) - 1 else ("#94a3b8" if v >= 0 else "#e2e8f0")
        x = i * (bw + gap)
        bars.append(f'<rect x="{x:.1f}" y="{hmax - h:.1f}" width="{bw}" height="{h:.1f}" '
                    f'rx="1" fill="{col}"/>')
    return (f'<span style="display:inline-flex;align-items:center;gap:6px">'
            f'<svg width="{w:.0f}" height="{hmax}" style="overflow:visible">'
            f'{"".join(bars)}</svg>'
            f'<b style="font-size:11px">{pos4}</b></span>')


def _hint(t):
    return f'<p class="nxt-note" style="margin:0 0 8px;opacity:.62">{t}</p>'


def _cr_block(cr):
    """修正風險模型（自建）——大市 tab 最頂。"""
    if not cr.get("components"):
        return ""
    lv = int(cr.get("level") or 0)
    col = {0: "#3ddc97", 1: "#3ddc97", 2: "#f5c542", 3: "#f97316", 4: "#ff6b6b"}.get(lv, "#94a3b8")
    P = [f'<div class="nxt-block" style="border-color:{col}55">'
         f'<h3>修正風險模型 · 自建</h3>'
         + _hint("4 級制：3 級新倉減半、4 級唔開新倉。黏性＝降級要連續 5 日確認。") +
         f'<p class="nxt-next" style="color:{col};font-weight:800;font-size:24px;margin:0">'
         f'LEVEL {lv} / 4</p>'
         f'<p class="nxt-note" style="margin:2px 0 8px">'
         f'{cr.get("rawScore")}/5 構件成立｜黏性 {cr.get("stickyDays",0)} 日</p>']
    for c in cr["components"]:
        mark = "⚠" if c.get("on") else "·"
        P.append(f'<div class="nxt-kv"><span class="k">{mark} {c.get("name","")}</span>'
                 f'<span class="v" style="font-size:12px;font-weight:600">{c.get("value","—")}</span></div>')
    P.append(f'<p class="nxt-next" style="margin-top:8px">{cr.get("advice","")}</p>')
    P.append('<div class="nxt-note">')
    for c in cr["components"]:
        if c.get("on"):
            P.append(f'· {c.get("desc","")}<br>')
    P.append(f'資料 {cr.get("asOf","—")}｜非價格主導：廣度背離／信貸／利率美元／波動結構／新高動能。'
             '原作者未公開公式，呢個係同思路自建，唔可以當成 TSF 官方評分。</div></div>')
    return "".join(P)


def _hw_block(hw):
    """四大宏觀逆風——放喺大市 tab 最頂。"""
    if not hw.get("flags"):
        return ""
    cnt, risk = hw.get("count"), hw.get("risk") or "—"
    col = "#ff6b6b" if cnt >= 3 else ("#f5c542" if cnt == 2 else "#3ddc97")
    P = [f'<div class="nxt-block"><h3>四大宏觀逆風 · {cnt}/4</h3>'
         + _hint("2 項＝放慢；3 項＝新倉減半；4 項＝2000／2022 式，唔開新倉。") +
         f'<p class="nxt-next" style="color:{col};font-weight:800;font-size:17px;margin:0 0 6px">'
         f'{risk}風險</p>']
    for f in hw["flags"]:
        mark = "⚠" if f.get("on") else "·"
        P.append(f'<div class="nxt-kv"><span class="k">{mark} {f.get("name","")}</span>'
                 f'<span class="v" style="font-size:12px;font-weight:600">{f.get("value","—")}</span></div>')
    P.append(f'<p class="nxt-next" style="margin-top:8px">{hw.get("advice","")}</p>')
    P.append('<div class="nxt-note">')
    for f in hw["flags"]:
        if f.get("on"):
            P.append(f'· {f.get("desc","")}<br>')
    P.append(f'資料 {hw.get("asOf","—")}｜來源 Ted Zhang（Revere）四項條件，'
             '已用 DXY／XLP÷SPY／10Y／2Y−聯邦基金 每日重算。</div></div>')
    return "".join(P)


def build():
    br, ins, dash, bud, scr, pos = _load()
    rows = scr.get("rows") or []
    ks = _key_shots(rows)
    hw = _j(HW, {}) or {}
    cr = _j(CR, {}) or {}
    sp13 = (_j(SP13, {}) or {}).get("rows") or {}
    day = (br.get("as_of") or "")[:10] or scr.get("as_of") or "—"
    regime = dash.get("regime") or br.get("regime") or "—"
    cap = dash.get("trade_cap")
    lamp = "綠燈" if regime == "BULL" else ("黃燈" if regime == "CHOP" else "紅燈")
    verdict = ("唔做新多" if cap == 0 else
               f"可以做 {cap} 單（只做 A+）" if isinstance(cap, int) else "—")
    status = br.get("status") or "—"

    P = [f"<style>{CSS}</style>", '<div class="nxt">']
    P.append(f'<div class="nxt-top"><span class="nxt-brand">交易台</span>'
             f'<span class="nxt-asof">{day}｜{br.get("_file", "—")}</span></div>')

    # ── 今日 ──
    P.append('<section class="nxt-panel on" id="panel-today">')
    P.append(f'<div class="nxt-hero"><p class="nxt-k">今日燈</p>'
             f'<p class="nxt-lamp">{lamp}</p><p class="nxt-dir">{regime}</p>'
             f'<p class="nxt-k">做定唔做</p><p class="nxt-vd">{verdict}</p>'
             f'<p class="nxt-sig">{status}｜關鍵球 {len(ks)} 隻｜配額 剩 {bud.get("left", "—")}</p>'
             f'<p class="nxt-meta">SPY {_f(dash.get("spy_close") or br.get("spy_close"), 2)}'
             f'｜ADL {_f((br.get("adl") or {}).get("value"), 1)}'
             f'｜站上40MA {_f(br.get("pct40ma"), 1)}%</p>')
    if hw.get("flags") and (hw.get("count") or 0) >= 2:
        _hc = "#ff6b6b" if hw.get("count") >= 3 else "#f5c542"
        P.append(f'<p class="nxt-sig" style="color:{_hc};font-weight:800;margin-top:10px">'
                 f'⚠️ 宏觀逆風 {hw.get("count")}/4（{hw.get("risk")}）'
                 f'｜{hw.get("advice","")}</p>')
    P.append('</div>')

    P.append('<div class="nxt-block"><h3>關鍵球（四條全中）</h3>')
    if ks:
        P.append('<div class="nxt-pills">' + "".join(
            f'<a class="nxt-pill hot" href="https://www.tradingview.com/chart/?symbol={r["t"]}"'
            f' target="_blank" rel="noopener">{r["t"]} RS{int(r["rs"])}</a>' for r in ks) + '</div>')
    else:
        P.append('<p class="nxt-note" style="margin:0">今日冇 A+ 候選 —— 等於今日可以唔做。</p>')
    P.append('<p class="nxt-note">RS≥90、ATRX 0–4、距52高≥−10、TIGHT≥45。'
             '候選數本身就係信息：得 2 隻就唔應該做 6 單。</p></div>')

    P.append('<div class="nxt-block"><h3>下一步</h3>'
             f'<p class="nxt-next">配額 {bud.get("quota", "—")}（{bud.get("regime", "—")}）'
             f'｜已用 {bud.get("used", "—")}｜剩 {bud.get("left", "—")}'
             f'｜{"收工" if bud.get("closed") else "可以做（只做 A+）"}</p>'
             '<p class="nxt-note">連蝕 2 單 → 當日停手；10:30 ET 後一律收工。'
             '關鍵球 0.5%（≤0.6%）、非關鍵球 0.2% 探路。</p></div>')
    P.append('</section>')

    # ── 大市 ──
    P.append('<section class="nxt-panel" id="panel-market">')
    P.append(_cr_block(cr))
    P.append(_hw_block(hw))
    P.append('<div class="nxt-block"><h3>主尺 · 廣度</h3>'
             + _hint("ADL 同新高新低淨值同時 > 0 = 健康；一正一負 = 背離，減注。"))
    for k, v in [("Regime／Posture",
                  f'{br.get("regime","—")}／{(br.get("posture") or {}).get("posture","—")}'),
                 ("多空比", _f(br.get("ls_ratio_proxy"), 2)),
                 ("ADL", _f((br.get("adl") or {}).get("value"), 1)),
                 ("新高新低淨值", _f((br.get("nnnl") or {}).get("value"), 1)),
                 ("站上 40MA", _f(br.get("pct40ma"), 1) + "%"),
                 ("SPY 收市", _f(br.get("spy_close"), 2))]:
        P.append(f'<div class="nxt-kv"><span class="k">{k}</span><span class="v">{v}</span></div>')
    P.append(f'<p class="nxt-note">{br.get("universe","—")}｜狀態 {status}。'
             '呢把係主尺；Stockbee 4% 尺係另一把，唔可以加減。</p></div>')

    ix = ins.get("indices") or {}
    if ix:
        P.append('<div class="nxt-block"><h3>Tape · 指數 vs 均線</h3>'
                 + _hint("全部企 20MA 上 = 順風；龍頭跌穿 20MA 先算轉弱。")
                 + '<div class="nxt-hscroll">'
                 '<table class="nxt-tbl"><thead><tr><th>指數</th><th>收市</th>'
                 '<th>vs 20MA</th><th>vs 50MA</th><th>vs 200MA</th></tr></thead><tbody>')
        for sym in ("SPY", "QQQ", "IWM", "DIA"):
            d = ix.get(sym) or {}
            if d.get("last") is None:
                continue
            cells = []
            for ma in ("ma20", "ma50", "ma200"):
                m = d.get(ma)
                cells.append(f'{_f(100 * (d["last"] / m - 1), 1, True)}%' if m else "—")
            P.append(f'<tr><td><b>{sym}</b></td><td>{_f(d["last"], 2)}</td>'
                     + "".join(f'<td>{c}</td>' for c in cells) + '</tr>')
        P.append('</tbody></table></div></div>')

    b = ins.get("breadth") or {}
    if b:
        P.append('<div class="nxt-block"><h3>Breadth · 站上均線</h3>'
                 + _hint("50MA 比例 < 40% ＝ 內部弱，突破容易失敗。"))
        for k, v in [("20MA", b.get("above20")), ("50MA", b.get("above50")),
                     ("200MA", b.get("above200")), ("20日新高", b.get("new_highs")),
                     ("20日新低", b.get("new_lows"))]:
            P.append(f'<div class="nxt-kv"><span class="k">{k}</span>'
                     f'<span class="v">{_f(v,1) if isinstance(v,float) else (v if v is not None else "—")}</span></div>')
        P.append('</div>')

    secs = _sector_agg(rows)
    if secs:
        _vx = (ins.get("vix") or {}).get("last")
        _sp = (ins.get("indices") or {}).get("SPY", {}).get("last") or br.get("spy_close")
        if _vx and _sp:
            _mv = _vx / 16.0
            P.append('<div class="nxt-block"><h3>VIX 16 規則</h3>'
                     + _hint("預期日波幅 ≈ VIX ÷ 16。波幅大 → 止蝕要闊、倉要細。")
                     + f'<div class="nxt-kv"><span class="k">VIX</span>'
                       f'<span class="v">{_vx:.2f}</span></div>'
                     f'<div class="nxt-kv"><span class="k">預期日波幅</span>'
                       f'<span class="v">±{_mv:.2f}%</span></div>'
                     f'<div class="nxt-kv"><span class="k">SPY 點數</span>'
                       f'<span class="v">±{_sp * _mv / 100:.2f}</span></div>'
                     '<p class="nxt-note">參考：12 → ±0.75%｜16 → ±1.0%｜20 → ±1.25%｜'
                     '24 → ±1.5%｜32 → ±2.0%｜40 → ±2.5%</p></div>')
        P.append('<div class="nxt-block"><h3>Sector · Top4 / Bottom2</h3>'
                 + _hint("Top4 揀方向，Bottom2 用嚟避開；唔好買 Bottom2 嘅反彈。")
                 + '<div class="nxt-hscroll">'
                 '<table class="nxt-tbl"><thead><tr><th>板塊</th><th>隻數</th>'
                 '<th>中位 RS</th><th>平均 1M</th></tr></thead><tbody>')
        for s in secs[:4] + secs[-2:]:
            P.append(f'<tr><td>{_zh_sector(s["sector"])}</td><td>{s["n"]}</td>'
                     f'<td>{_f(s["rs"], 0)}</td>'
                     f'<td class="{_cls(s["m1"])}">{_f(s["m1"], 1, True)}%</td></tr>')
        P.append('</tbody></table></div><p class="nxt-note">'
                 '聚合自本地有 OHLC 嘅股票，唔係官方 sector ETF。</p></div>')

    ms = pos.get("markets") or []
    if ms:
        P.append('<div class="nxt-block"><h3>Positioning · COT 大戶倉位</h3>'
                 + _hint("≤10 = 擁擠空（反彈燃料）；≥90 = 擁擠多（回落風險）。")
                 + '<div class="nxt-pills">')
        for m in ms:
            c = m.get("crowded") or "—"
            cls = "bad" if "Short" in c else ("hot" if "Long" in c else "")
            P.append(f'<span class="nxt-pill {cls}">{m.get("etf","—")} {c}</span>')
        P.append('</div><div class="nxt-hscroll"><table class="nxt-tbl"><thead><tr>'
                 '<th>市場</th><th>大戶淨倉</th><th>5年%</th><th>狀態</th></tr></thead><tbody>')
        for m in ms:
            lg = (m.get("participants") or {}).get("large") or {}
            P.append(f'<tr><td>{m.get("name","—")}</td>'
                     f'<td class="{_cls(lg.get("net"))}">{lg.get("net","—")}</td>'
                     f'<td>{_f(lg.get("idx5y"),0)}</td><td>{m.get("crowded","—")}</td></tr>')
        P.append(f'</tbody></table></div><p class="nxt-note">CFTC｜報告日 {ms[0].get("date","—")}。'
                 '≤10 擁擠空、≥90 擁擠多。</p></div>')
    else:
        P.append('<div class="nxt-block"><h3>Positioning</h3>'
                 '<p class="nxt-note" style="margin:0">DATA_UNAVAILABLE — 未跑 positioning.py</p></div>')

    P.append('</section>')

    # ── 名單 ──
    P.append('<section class="nxt-panel" id="panel-list">')
    P.append(f'<div class="nxt-block"><h3>關鍵球 A+｜{len(ks)} 隻</h3>')
    if ks:
        P.append('<div class="nxt-hscroll"><table class="nxt-tbl"><thead><tr>'
                 '<th>代號</th><th>RS</th><th>EXT</th><th>TIGHT</th><th>推移（13週）</th>'
                 '<th>4週</th><th>距52高</th><th>距pivot</th></tr></thead><tbody>')
        for r in ks:
            d52 = r.get("d52w", r.get("off52_tv"))
            P.append(f'<tr><td><a href="https://www.tradingview.com/chart/?symbol={r["t"]}"'
                     f' target="_blank" rel="noopener">{r["t"]}</a></td>'
                     f'<td>{int(r["rs"])}</td>'
                     f'<td>{_f(r.get("atrx"),1)}</td><td>{_f(r.get("tight"),0)}</td>'
                     f'<td>{_spark((sp13.get(r["t"]) or {}).get("v"), (sp13.get(r["t"]) or {}).get("pos4",""))}</td>'
                     f'<td>{(sp13.get(r["t"]) or {}).get("pos4","—")}</td>'
                     f'<td>{_f(d52,1)}%</td>'
                     f'<td>{_f(r.get("dist_pivot"),1)}%</td></tr>')
        P.append('</tbody></table></div>')
    else:
        P.append('<p class="nxt-note" style="margin:0">今日冇 A+ 候選。</p>')
    P.append('<p class="nxt-note"><a href="screener.html">Stock Screener（744 隻）</a>｜'
             '<a href="peg.html">PEG 清單</a>｜<a href="alerts.html">Setup Alert</a>｜'
             '<a href="screenwall.html">Stock Wall</a></p></div>')
    P.append('</section>')

    # ── 工具 ──
    P.append('<section class="nxt-panel" id="panel-tools">')
    for g, items in [
            ("選股", [("Stock Screener", "screener.html"), ("Stock Wall", "screenwall.html"),
                      ("PEG 清單", "peg.html"), ("Setup Alert", "alerts.html"),
                      ("Daily Scan", "dailyscan.html"), ("RS 新高", "rsnewhigh.html"),
                      ("財報日曆", "earningscal.html")]),
            ("大市", [("環境熱力圖", "regimeheat.html"), ("市場簡報", "briefing.html"),
                      ("Market Monitor", "mm.html"), ("成長週期", "cycle.html"),
                      ("Put/Call", "putcall.html"), ("投降儀表", "feargauge.html")]),
            ("成績", [("Review", "review.html"), ("覆盤（R／期望值）", "review2.html"),
                      ("Think in R", "thinkinr.html"), ("Backtest", "backtest.html"),
                      ("系統審計", "audit.html"), ("Edge Improving", "edgeimprove.html")]),
            ("流程", [("每日流程", "process.html"), ("使用手冊", "howto.html"),
                      ("倉位計算機", "calculator.html"), ("交易日誌", "logbook.html")]),
            ("方法", [("Luk 手冊", "lukplaybook.html"), ("Qullamaggie 手冊", "qmb.html"),
                      ("MODEL BOOK", "modelbook.html"), ("外部數據源", "external.html")])]:
        P.append(f'<div class="nxt-block"><h3>{g}</h3><div class="nxt-pills">')
        P.append("".join(f'<a class="nxt-pill" href="{h}">{n}</a>' for n, h in items))
        P.append('</div></div>')
    P.append('<p class="nxt-note">全部唯讀、研究用途，非買入指令。'
             '缺失顯示 —，唔會當 0。</p>')
    P.append('</section>')

    P.append('<nav class="nxt-tabs">')
    for _id, _n in [("today", "今日"), ("market", "大市"), ("list", "名單"), ("tools", "工具")]:
        _on = ' class="on"' if _id == "today" else ""
        P.append(f'<a href="#{_id}" data-tab="{_id}"{_on}>'
                 f'<span>{_n}</span><span class="nxt-dot"></span></a>')
    P.append('</nav>')
    P.append(f"<script>{JS}</script>")
    P.append('</div>')
    return ("交易台 · 今日", "".join(P))
