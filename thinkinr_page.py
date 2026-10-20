# -*- coding: utf-8 -*-
"""thinkinr_page.py — Think in R（4R 格仔牆）

Desmond 2026-10-20：「係網頁到打做一頁 Think in R
想將每個 4R 既 trade 用格仔記底」

靈感來源（AMD 交易檢討）：
  「我最近大部分交易，總係上到 4-5R 就即刻平倉」
  → 唔係用「賺幾多錢」衡量，係用「賺幾多 R」

━━━ 點計 R ━━━
實盤只有 PnL（美元），冇逐單止蝕價。
用標準做法：R = 該單 PnL ÷ 平均輸單絕對值。
即係「1R ≈ 你平均一單止蝕嘅金額」。
呢個係近似值 —— 頁面會寫明。

━━━ 格仔 ━━━
  每個格 = 一單
  4R+  = 金色（目標格）
  2-4R = 綠色
  0-2R = 淺綠
  -1R  = 紅色（正常止蝕）
  <-1R = 深紅（超額虧損）
"""
import io
import json
import os
import sys

BASE = r"C:\Users\rain0\trading-os-lab\output\fills_clean.csv"
TO = r"C:\Users\rain0\trading-os-web"

CSS = """
.r-wrap{display:flex;flex-wrap:wrap;gap:5px;margin:0 0 14px}
.r-c{width:34px;height:34px;border-radius:6px;display:flex;
  align-items:center;justify-content:center;font-size:9.5px;
  font-weight:800;font-family:ui-monospace;cursor:default;
  border:1px solid rgba(0,0,0,.12);transition:transform .1s}
.r-c:hover{transform:scale(1.18);z-index:5}
.r-4{background:#f59e0b;color:#422006}
.r-3{background:#22c55e;color:#052e16}
.r-2{background:#86efac;color:#14532d}
.r-1{background:#d1fae5;color:#065f46}
.r-0{background:#e2e8f0;color:#475569}
.r-m1{background:#fca5a5;color:#7f1d1d}
.r-m2{background:#dc2626;color:#fff}
.r-k{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 14px}
.r-k>div{flex:1 1 100px;padding:11px 13px;border-radius:11px;
  border:1px solid rgba(128,128,128,.26);background:rgba(128,128,128,.05)}
.r-k .n{font-size:21px;font-weight:800;line-height:1.15}
.r-k .l{font-size:10.5px;opacity:.6;margin-top:2px}
.r-lg{display:flex;gap:12px;flex-wrap:wrap;font-size:11.5px;
  margin:0 0 14px;opacity:.75}
.r-lg span{display:flex;align-items:center;gap:5px}
.r-sq{width:14px;height:14px;border-radius:4px;display:inline-block}
@media(max-width:700px){
  .r-c{width:30px;height:30px;font-size:8.5px}
}
"""


def fsig():
    """直接引用 edge_page 嘅 FIFO 邏輯，唔重複實作。"""
    sys.path.insert(0, TO)
    import edge_page as E
    fills = E.load_fills()
    return E, E.fifo_pairs(fills), fills


def rclass(r):
    if r >= 4:
        return "r-4"
    if r >= 3:
        return "r-3"
    if r >= 2:
        return "r-2"
    if r > 0:
        return "r-1"
    if r > -1.5:
        return "r-m1"
    return "r-m2"


def build():
    try:
        E, trips, fills = fsig()
    except Exception as e:                                   # noqa: BLE001
        return ("Think in R", f'<div class="warn">⛔ 讀唔到成交：'
                f'{type(e).__name__}: {e}</div>')
    if not trips:
        return ("Think in R", '<div class="warn">⛔ 冇配對到 round-trip</div>')

    # 1R = 平均輸單絕對值
    losses = [abs(t["pnl"]) for t in trips if t["pnl"] < 0]
    one_r = (sum(losses) / len(losses)) if losses else 1.0
    for t in trips:
        t["R"] = t["pnl"] / one_r

    n4 = [t for t in trips if t["R"] >= 4]
    n2 = [t for t in trips if 2 <= t["R"] < 4]
    nloss = [t for t in trips if t["R"] <= 0]
    total_r = sum(t["R"] for t in trips)

    L = [f"<style>{CSS}</style>",
         "<h2>Think in R <small>以 R 為單位，唔係以錢為單位</small></h2>",
         '<p class="crumb">1R = 你平均一單止蝕嘅金額'
         f'（${one_r:,.0f}）｜{len(trips)} 單</p>']

    # KPI
    L.append('<div class="r-k">')
    for v, lab, col in (
            (f"{total_r:+.0f}R", "總 R",
             "#16a34a" if total_r > 0 else "#dc2626"),
            (str(len(n4)), "4R+ 格仔", "#f59e0b"),
            (str(len(n2)), "2–4R", "#22c55e"),
            (str(len(nloss)), "止蝕單", "#dc2626"),
            (f"${one_r:,.0f}", "1R 金額", "")):
        c = f' style="color:{col}"' if col else ""
        L.append(f'<div><div class="n"{c}>{v}</div>'
                 f'<div class="l">{lab}</div></div>')
    L.append("</div>")

    # 圖例
    L.append('<div class="r-lg">'
             '<span><i class="r-sq r-4"></i>4R+（目標）</span>'
             '<span><i class="r-sq r-3"></i>3–4R</span>'
             '<span><i class="r-sq r-2"></i>2–3R</span>'
             '<span><i class="r-sq r-1"></i>0–2R</span>'
             '<span><i class="r-sq r-m1"></i>−1R（正常止蝕）</span>'
             '<span><i class="r-sq r-m2"></i>超額虧損</span>'
             '</div>')

    # ── 4R 牆（核心）──
    L.append('<div class="card"><h2>4R 牆 <small>'
             f'每一格 = 一單 4R 或以上（{len(n4)} 格）</small></h2>'
             '<div class="body">')
    if n4:
        n4.sort(key=lambda t: -t["R"])
        L.append('<div class="r-wrap">')
        for t in n4:
            tip = (f'{t["sym"]}｜{t["entry_date"]}｜'
                   f'{t["R"]:.1f}R｜${t["pnl"]:,.0f}')
            L.append(f'<div class="r-c {rclass(t["R"])}" '
                     f'title="{tip}">{t["R"]:.0f}R</div>')
        L.append('</div>')
        L.append(f'<div style="font-size:12.5px;line-height:1.8">'
                 f'呢 {len(n4)} 格貢獻 <b>'
                 f'{sum(t["R"] for t in n4):+.0f}R</b> = '
                 f'<b>${sum(t["pnl"] for t in n4):,.0f}</b><br>'
                 f'相當於總 R 嘅 <b>'
                 f'{sum(t["R"] for t in n4)/total_r*100 if total_r else 0:.0f}%</b>。'
                 f'<br><b style="color:#b45309">你嘅問題唔係唔識贏，'
                 f'係贏得太少數、蝕得太多數。</b></div>')
    else:
        L.append('<div style="font-size:12.5px;opacity:.7">'
                 '⚪ 冇任何一單達到 4R。<br>'
                 '呢個係最需要改嘅一件事 —— 目標係「贏要贏 4R」。'
                 '</div>')
    L.append('</div></div>')

    # ── 全部格仔 ──
    L.append('<div class="card"><h2>全部交易 <small>'
             '按時間順序，一格一單</small></h2><div class="body">'
             '<div class="r-wrap">')
    for t in trips:
        tip = (f'{t["sym"]}｜{t["entry_date"]}→{t["exit_date"]}｜'
               f'{t["R"]:+.1f}R｜${t["pnl"]:+,.0f}')
        L.append(f'<div class="r-c {rclass(t["R"])}" '
                 f'title="{tip}">{t["R"]:+.0f}</div>')
    L.append('</div></div></div>')

    # ── 分佈 ──
    buckets = [("4R+", 4, 999), ("3–4R", 3, 4), ("2–3R", 2, 3),
               ("0–2R", 0, 2), ("−1R", -1.5, 0), ("<-1.5R", -999, -1.5)]
    L.append('<div class="card"><h2>R 分佈</h2><div class="body">'
             '<table class="eh-t"><thead><tr><th>區間</th><th>單數</th>'
             '<th>佔比</th><th>合計 R</th></tr></thead><tbody>')
    for lab, lo, hi in buckets:
        v = [t for t in trips if lo <= t["R"] < hi]
        if not v:
            continue
        sr = sum(t["R"] for t in v)
        col = "pos" if sr > 0 else "neg"
        L.append(f'<tr><td><b>{lab}</b></td><td>{len(v)}</td>'
                 f'<td>{len(v)/len(trips)*100:.0f}%</td>'
                 f'<td class="{col}">{sr:+.0f}R</td></tr>')
    L.append('</tbody></table></div></div>')

    # ── Think in R 原則 ──
    L.append('<div class="card"><h2>Think in R 原則 '
             '<small>來源：AMD 交易檢討</small></h2><div class="body">'
             '<div style="font-size:12.5px;line-height:2">'
             '<b>① 用 R 思考，唔用錢</b><br>'
             '　「賺 $500」冇意義。「賺 4.5R」才有意義 —— '
             '因為 R 已經包含風險。<br><br>'
             '<b>② 4-5R 就平倉</b><br>'
             '　原話：「我最近大部分交易，總係上到 4-5R 就即刻平倉」<br>'
             '　唔係等 10R、唔係等 20R。4-5R 就夠。<br><br>'
             '<b>③ 分批：4R 賣第一批 → 止蝕移保本</b><br>'
             '　「賣出首批修剪，止蝕移到保本，手上就有一單贏交易」<br><br>'
             '<b>④ 唔在乎離場後仲升</b><br>'
             '　「呢隻股喺我離場後走得更高，我完全唔在乎」<br>'
             '　因為目標唔係食盡，係穩定執行。<br><br>'
             '<b>⑤ 每次檢討都問：呢單幾多 R？</b><br>'
             '　唔係「賺定蝕」，係「幾多 R」。</div>'
             '</div></div>')

    # 誠實聲明
    L.append('<div class="note" style="margin-top:14px;font-size:11.5px;'
             'line-height:1.85">'
             f'<b>R 定義</b>：1R = 你平均輸單絕對值（${one_r:,.0f}）。'
             '實盤記錄冇逐單止蝕價，所以用呢個標準近似值。<br>'
             '<b>限制</b>：如果你某段時間止蝕特別闊／窄，'
             '嗰段嘅 R 會失真。<br>'
             f'<b>數據</b>：{len(fills)} 張成交單 → {len(trips)} 個 round-trip，'
             '同 Edge Improving 頁同一來源。</div>')
    return ("Think in R", "".join(L))


if __name__ == "__main__":
    t, b = build()
    print(t, len(b) // 1024, "KB")
