# -*- coding: utf-8 -*-
"""optledger_page.py — 優化帳本（錢 ↔ 優化 掛勾）

Desmond 2026-10-22：
  「我想係 website buildup 個 page 入面見到你優化左d 咩
    我見你有時會彈個 improvement 出黎」
  「我想用錢同你既優化做掛勾」

━━━ 設計原則（第一性原理）━━━
一條「優化」若果量唔到錢，就唔係優化，係改動。
所以呢頁只列【有金額影響】嘅項目，並且寫明：
  ① 改咩（before → after）
  ② 用咩量（樣本 n、EV、Kelly、PnL）
  ③ 影響幾多錢（HK$ 或 R）
  ④ 證據強度（n ≥ 30 + 顯著 = 強；n < 30 = 弱，唔准當結論）

未量化嘅改動放最後一節，明寫「未量化」——
唔准把「做咗嘢」當成「賺咗錢」。
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TO = r"C:\Users\rain0\trading-os"
CHANGELOG = os.path.join(TO, "CHANGELOG.jsonl")
AUDIT_HIST = os.path.join(TO, "output", "audit_history.jsonl")
SA_JSON = os.path.join(TO, "output", "system_audit.json")
PNL = os.path.join(TO, "edge_book", "pnl_daily.jsonl")

MEASURED = [
    dict(
        date="2026-10-21",
        title="Jeff Sun 3-stop 持倉上限 30 日 → 3 日",
        what="訊號 edge 只活 3 日（第 3 日勝率 74%），第 4 日起全部回吐",
        metric="同一 35 個訊號：EV −0.22R → +0.24R｜Kelly −0.33 → +0.24",
        amt=None,
        basis="Kelly 改善 +0.57，但倉位規則未套用，未折算成 HK$",
        strength="強", n=35, tag="出場",
    ),
    dict(
        date="2026-10-21",
        title="修 3 個回測測量 bug（0R 假樣本 / 冇 mark-to-market / 索引錯位）",
        what="224 個未到期訊號被當成打和，拉低 EV；剩餘倉位憑空消失",
        metric="系統 Kelly −0.327 → −0.077",
        amt=None,
        basis="令之後所有判斷可信；唔修 = 每次優化都建基於錯數",
        strength="強", n=175, tag="量度",
    ),
    dict(
        date="2026-10-22",
        title="trim2r 改由公式計（入場 + 2×風險）",
        what="PENG 卡片 trim2r 記 60.41（低過入場 67.33）→ 2R 減倉從未觸發",
        metric="PENG 應 −1.55R，實際 −4.43R",
        amt=-244.02,
        basis="單筆多蝕 HK$244（2.88R）。影響全部已平倉單，未逐單重算",
        strength="中", n=1, tag="出場",
    ),
    dict(
        date="2026-10-22",
        title="組合層出場煞停（連蝕 3 日停手 / 累積賺 5 萬鎖半倉）",
        what="原本冇任何組合層規則；峰值 +61,489 → 吐返 73%",
        metric="同一 19 日：+22,281 → +50,041｜最大回撤 −44,597 → −13,500",
        amt=27759.0,
        basis="用 Desmond 自己 09-28→10-22 真實每日盈虧回測（19 日）",
        strength="中", n=19, tag="組合",
    ),
    dict(
        date="2026-10-22",
        title="pkl 壞 bar 修復（low > open）",
        what="11 根壞 bar，涉及 7 隻股；我哋自己回測一直靜靜用住",
        metric="壞 bar 11 → 0；非空 Close 33,063 格不變（冇少數據）",
        amt=None,
        basis="未直接量到錢，但 NautilusTrader 一撞就 raise —— 證明係真壞",
        strength="中", n=11, tag="量度",
    ),
    dict(
        date="2026-10-22",
        title="rs_select 建立 cron（原本完全冇）",
        what="網站「今日圖表隊列」連續 10 日顯示同一份舊名單",
        metric="產物由 0 個/日 → 1 個/日（json + txt + png）",
        amt=None,
        basis="未量化（唔知你有冇跟過呢個名單做嘢）",
        strength="弱", n=0, tag="假更新",
    ),
]


def _load_jsonl(p):
    rows = []
    if not os.path.exists(p):
        return rows
    for line in io.open(p, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:                                    # noqa: BLE001
            pass
    return rows


CSS = """
<style>
.ol-hero{border:1px solid rgba(128,140,170,.28);border-radius:14px;
  padding:16px 18px;margin-bottom:14px;background:rgba(128,140,170,.07)}
.ol-hero h2{margin:0 0 8px;font-size:17px;color:inherit}
.ol-hero p{margin:0;font-size:12.5px;line-height:1.85;
  color:inherit;opacity:.8}
.ol-big{font-size:26px;font-weight:800;color:#16a34a;margin:6px 0}
.ol-card{border:1px solid rgba(128,140,170,.22);border-radius:10px;
  padding:12px 14px;margin-bottom:10px;background:rgba(128,140,170,.04)}
.ol-h{display:flex;gap:8px;align-items:center;flex-wrap:wrap;
  margin-bottom:8px;font-size:14px;color:inherit}
.ol-tag{background:rgba(37,99,235,.18);border:1px solid rgba(37,99,235,.4);
  border-radius:5px;padding:0 6px;font-size:10.5px;font-weight:700}
.ol-d{margin-left:auto;font-size:10.5px;opacity:.55}
.ol-r{display:flex;gap:8px;font-size:11.5px;line-height:1.75;
  padding:4px 0;border-top:1px dashed rgba(128,140,170,.22);
  flex-wrap:wrap;color:inherit}
.ol-k{flex:0 0 62px;min-width:62px;font-weight:700;opacity:.6}
.ol-v{flex:1;min-width:180px}
.ol-s{border-radius:4px;padding:0 5px;font-size:10.5px;font-weight:700}
.ol-s.ok{background:rgba(34,197,94,.22);border:1px solid rgba(34,197,94,.5)}
.ol-s.mid{background:rgba(245,158,11,.22);border:1px solid rgba(245,158,11,.5)}
.ol-s.weak{background:rgba(148,163,184,.22);border:1px solid rgba(148,163,184,.5)}
.up{color:#16a34a}.down{color:#dc2626}
.dim{opacity:.55;font-weight:400}
.ol-warn{border:1px solid rgba(245,158,11,.45);background:rgba(245,158,11,.10);
  border-radius:10px;padding:12px 14px;margin-bottom:14px;font-size:12.5px;
  line-height:1.85;color:inherit}
@media(max-width:700px){
  .ol-k{flex:0 0 100%;min-width:0}
  .ol-v{flex:0 0 100%;min-width:0}
}
</style>
"""


def build():
    logs = _load_jsonl(CHANGELOG)
    pnl = _load_jsonl(PNL)
    tot = sum(m["amt"] for m in MEASURED if m["amt"] is not None)
    kinds = {}
    for r in logs:
        k = r.get("kind") or "?"
        kinds[k] = kinds.get(k, 0) + 1

    cards = []
    for m in sorted(MEASURED, key=lambda x: (x["date"], x["title"]),
                    reverse=True):
        s_cls = {"強": "ok", "中": "mid", "弱": "weak"}.get(m["strength"],
                                                           "weak")
        if m["amt"] is not None:
            cls = "up" if m["amt"] >= 0 else "down"
            amt = f'<b class="{cls}">{m["amt"]:+,.0f} HK$</b>'
        else:
            amt = '<span class="dim">未折算</span>'
        cards.append(
            f'<div class="ol-card">'
            f'<div class="ol-h"><b>{m["title"]}</b>'
            f'<span class="ol-tag">{m["tag"]}</span>'
            f'<span class="ol-d">{m["date"]}</span></div>'
            f'<div class="ol-r"><span class="ol-k">改咗咩</span>'
            f'<span class="ol-v">{m["what"]}</span></div>'
            f'<div class="ol-r"><span class="ol-k">量度</span>'
            f'<span class="ol-v">{m["metric"]}</span></div>'
            f'<div class="ol-r"><span class="ol-k">影響</span>'
            f'<span class="ol-v">{amt}　<span class="dim">'
            f'（{m["basis"]}）</span></span></div>'
            f'<div class="ol-r"><span class="ol-k">證據</span>'
            f'<span class="ol-v"><span class="ol-s {s_cls}">'
            f'{m["strength"]}</span>　n = {m["n"]}</span></div>'
            f'</div>')

    unmeasured = [m for m in MEASURED if m["amt"] is None]
    n_meas = len(MEASURED) - len(unmeasured)

    hero = (
        '<div class="ol-hero">'
        '<h2>💰 優化帳本 —— 錢 ↔ 優化 掛勾</h2>'
        f'<div class="ol-big">{tot:+,.0f} HK$</div>'
        f'<p>呢個數 = 已量到金額嘅優化總和。'
        f'共 {len(MEASURED)} 條改動，其中 {n_meas} 條量到錢、'
        f'{len(unmeasured)} 條未折算。<br>'
        f'系統累積 {len(logs)} 條改動記錄（'
        f'fix {kinds.get("fix",0)}｜rule {kinds.get("rule",0)}｜'
        f'tool {kinds.get("tool",0)}｜feature {kinds.get("feature",0)}｜'
        f'research {kinds.get("research",0)}｜'
        f'data {kinds.get("data",0)}）。</p></div>')

    warn = (
        '<div class="ol-warn">'
        '<b>⚠ 呢頁最重要嘅一句</b>：'
        '「有改動」≠「賺到錢」。下面只列【量到金額】嘅項目；'
        '量唔到嘅我標明「未折算」，唔會塞個靚數字落去。'
        '證據強度弱（n &lt; 30）唔可以當結論。</div>')

    body = ('<div class="card"><h2>📒 已量化嘅優化 '
            f'<small>{len(MEASURED)} 條</small></h2>'
            '<div class="body">' + "".join(cards) + '</div></div>')

    un_rows = "".join(
        f'<tr><td class="l"><b>{m["title"]}</b></td>'
        f'<td>{m["date"]}</td><td class="l dim">{m["basis"]}</td></tr>'
        for m in unmeasured)
    unsec = (
        '<div class="card"><h2>❓ 已改但未量化 '
        f'<small>{len(unmeasured)} 條 —— 唔准當成果</small></h2>'
        '<div class="body"><div class="scroll"><table><thead><tr>'
        '<th class="l">改動</th><th>日期</th><th class="l">為何量唔到</th>'
        '</tr></thead><tbody>' + un_rows + '</tbody></table></div>'
        '</div></div>')

    # 你自己嘅每日盈虧（同優化對照）
    if pnl:
        cum = 0.0
        peak = 0.0
        for r in pnl:
            cum += float(r.get("pnl") or 0)
            peak = max(peak, cum)
        dd = cum - peak
        pnlsec = (
            '<div class="card"><h2>📈 你自己嘅實際表現 '
            f'<small>{len(pnl)} 個交易日</small></h2><div class="body">'
            f'<div class="ol-r"><span class="ol-k">累積</span>'
            f'<span class="ol-v"><b>{cum:+,.0f} HK$</b></span></div>'
            f'<div class="ol-r"><span class="ol-k">峰值</span>'
            f'<span class="ol-v">{peak:+,.0f} HK$</span></div>'
            f'<div class="ol-r"><span class="ol-k">現時回撤</span>'
            f'<span class="ol-v down">{dd:+,.0f} HK$'
            f'（{dd/peak*100:.0f}%）</span></div>'
            f'<div class="ol-r"><span class="ol-k">距峰值</span>'
            f'<span class="ol-v">你吐返咗 {abs(dd)/peak*100:.0f}% —— '
            f'呢個就係組合煞停要解決嘅問題</span></div>'
            '</div></div>')
    else:
        pnlsec = ""

    try:
        sa = json.load(io.open(SA_JSON, encoding="utf-8"))
        s = sa.get("system") or {}
        live = (
            '<div class="card"><h2>📊 模擬系統現況 '
            f'<small>{sa.get("date","")}</small></h2><div class="body">'
            f'<div class="ol-r"><span class="ol-k">資金</span>'
            f'<span class="ol-v">US${s.get("nav",0):,.0f}</span></div>'
            f'<div class="ol-r"><span class="ol-k">賺蝕</span>'
            f'<span class="ol-v">{s.get("pnl",0):+,.0f}'
            f'（{s.get("ret_pct",0):+.2f}%）</span></div>'
            f'<div class="ol-r"><span class="ol-k">Kelly</span>'
            f'<span class="ol-v">{s.get("kelly")}</span></div>'
            '</div></div>')
    except Exception:                                        # noqa: BLE001
        live = ""

    return ("優化帳本", CSS + hero + warn + pnlsec + body + unsec + live)
