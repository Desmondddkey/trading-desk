# -*- coding: utf-8 -*-
"""mb_page.py — Model Book 頁（量化案例庫）

來源（Desmond 2026-10-22）：
  YouTube "Become a Market Wizard by Studying Past Traders"（Clement Ang）
  Substack "Building Model Books: What, Why and How"

呢頁唔係貼圖，係【統計庫】：2,377 個真實案例，每種形態都有
勝率 / 賠率 / 平均 R / 2R 減倉率。

輸出：docs/modelbook.html
"""
import io
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = r"C:\Users\rain0\trading-os\output\model_book"
DOCS = os.path.join(HERE, "docs")

NAMES = {
    "vcp": ("VCP 波幅收縮", "Minervini",
            "連續 3 段 10 日波幅逐段收窄，第 3 段 < 第 1 段 60%；"
            "10 日均量 < 20 日均量 85%；價格 > 50DMA > 200DMA"),
    "undercut_rally": ("Undercut & Rally", "O'Neil / Sperandeo 2B",
                       "今日低穿前 20 日低位，收市重返其上，且收陽；"
                       "O'Neil 叫 undercut and rally，Sperandeo 叫 2B"),
    "rs_new_high_first": ("RS 新高先於價格", "Clement Ang（MSTR 2023）",
                          "價格距 52 週高仍 >3%，但 RS line（股/大盤）"
                          "已創 60 日新高；價格仍喺 50DMA 上"),
}

LINEAGE = [
    ("Jesse Livermore", "價格與成交量收斂處 = 方向轉變訊號", "1920s"),
    ("William O'Neil", "CAN SLIM：領導股 + 盈利增長 + 機構持股 + RS",
     "1960s–"),
    ("Stan Weinstein", "四階段理論（Basing / Advancing / Topping / Declining）",
     "1988"),
    ("Gil Morales / Chris Kacher", "Pocket pivot、Volume dry-up、"
     "Buyable gap-up、Undercut & rally、Backside short", "2010s"),
    ("Mark Minervini", "VCP（Volatility Contraction Pattern）、"
     "Tight & orderly、Linear pullback", "2010s"),
    ("Qullamaggie / Oliver Kell", "Episodic pivot、"
     "10/20EMA 騎乘、後周期延續", "2010s–"),
    ("Clement Ang", "共同點蒸餾 + 心理 + 歷史押韻"
     "（1930s 鐵路 → 今日 AI）", "2020s"),
]

CHECK_TECH = [
    "價格喺上升嘅 50DMA 同 200DMA 之上",
    "50DMA > 200DMA",
    "Wedge pop 之後騎住 10 / 20DMA（linearity = 有序回調）",
    "VCP 特徵：tight & orderly（唔可以 wide and loose）",
    "成交量乾涸（dry-up）→ 機構冇派貨",
]

CHECK_TML = [
    "流動性夠大，機構可以持倉",
    "盈利同銷售雙位或三位數增長",
    "當期主題嘅領頭羊（2020 TSLA、2023+ NVDA）",
    "RS line 新高【先於】價格新高",
]


def load():
    """讀最新【日期命名】嘅案例檔

    ★ 2026-10-23 修：原本揀資料夾最後一個 .json，
      但 top250.json 排喺 2026-10-23.json 之後（'t' > '2'）
      → 揀錯檔 → KeyError: 'cases' → 整頁統計消失。
      修法：只接受檔名以數字開頭（日期格式）＋ 真係有 cases key。
    """
    if not os.path.isdir(CASES):
        return None
    fs = sorted(f for f in os.listdir(CASES)
                if f.endswith(".json") and f[0].isdigit())
    for f in reversed(fs):
        p = os.path.join(CASES, f)
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception:                                # noqa: BLE001
            continue
        if isinstance(d, dict) and d.get("cases"):
            return d
    return None


def stats_of(cases, pat):
    v = [c for c in cases if c["pattern"] == pat]
    if not v:
        return None
    rs = [c["r"] for c in v]
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    wr = len(wins) / len(rs) * 100
    payoff = (st.mean(wins) / abs(st.mean(losses))) if losses else 0
    return {
        "n": len(v), "wr": round(wr, 1), "ev": round(st.mean(rs), 3),
        "payoff": round(payoff, 2),
        "trim": round(sum(1 for c in v if c["trimmed"]) / len(v) * 100),
        "med": round(st.median(rs), 2),
        "max": round(max(rs), 1),
        "risk_med": round(st.median([c["risk_pct"] for c in v]), 2),
    }


def top_cases(cases, pat, n=5):
    v = [c for c in cases if c["pattern"] == pat]
    v.sort(key=lambda x: -x["r"])
    return v[:n]


CSS = """
.mbh{font-size:12.5px;line-height:1.85;opacity:.85;max-width:760px}
.mbg{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
  gap:11px;margin:0 0 16px}
.mbc{border:1px solid rgba(128,128,128,.2);border-radius:10px;
  padding:13px 15px;background:rgba(128,128,128,.04)}
.mbc h4{margin:0 0 4px;font-size:14px;font-weight:800}
.mbc .who{font-size:10.5px;opacity:.55;font-family:ui-monospace;
  margin:0 0 8px}
.mbc .big{font-size:26px;font-weight:800;line-height:1.1;
  font-family:ui-monospace}
.mbc .big.ok{color:#15803d}
.mbc .row{display:flex;justify-content:space-between;font-size:11.5px;
  padding:2.5px 0;border-bottom:1px solid rgba(128,128,128,.09)}
.mbc .row:last-child{border:0}
.mbline{list-style:none;padding:0;margin:0 0 16px}
.mbline li{display:flex;gap:10px;padding:7px 0;font-size:12.5px;
  border-bottom:1px solid rgba(128,128,128,.1);align-items:baseline}
.mbline li b{flex:0 0 150px}
.mbline li span{opacity:.8}
.mbline li i{margin-left:auto;font-size:10.5px;opacity:.45;
  font-family:ui-monospace;font-style:normal}
.mbchk{list-style:none;padding:0;margin:0 0 14px}
.mbchk li{padding:5px 0 5px 20px;position:relative;font-size:12.5px}
.mbchk li:before{content:"✓";position:absolute;left:0;color:#15803d;
  font-weight:800}
.mbtb{width:100%;border-collapse:collapse;font-size:11.5px}
.mbtb th{text-align:left;padding:6px 8px;font-size:10.5px;
  text-transform:uppercase;letter-spacing:.04em;opacity:.55;
  border-bottom:1px solid rgba(128,128,128,.25)}
.mbtb td{padding:5px 8px;border-bottom:1px solid rgba(128,128,128,.09);
  font-family:ui-monospace}
.mbwarn{border-left:3px solid #c2410c;background:rgba(194,65,12,.07);
  padding:11px 14px;border-radius:0 10px 10px 0;font-size:12.5px;
  line-height:1.85;margin:0 0 14px}
@media(max-width:700px){
  .mbg{grid-template-columns:1fr}
  .mbtb{font-size:10.5px}
  .mbtb th,.mbtb td{padding:4px 5px}
}
"""


def block():
    d = load()
    if not d:
        return ('<div class="card"><h3>Model Book</h3>'
                '<p>未有案例庫。跑 <code>mb_cases.py --build</code>。</p></div>')

    cs = d["cases"]
    out = [f'<style>{CSS}</style>']
    out.append('<div class="card">')
    out.append('<h3>📚 Model Book — 量化案例庫</h3>')
    out.append(
        f'<p class="mbh">{d["date"]}｜{d["n_tickers"]} 隻股票 × 500 日'
        f'｜<b>{len(cs):,} 個真實案例</b>。每個形態都有勝率、賠率、'
        f'平均 R、2R 減倉率 —— 唔係貼圖，係統計。</p>')

    # 血統
    out.append('<h3 style="margin-top:18px">血統（Clement Ang 蒸餾）</h3>')
    out.append('<ul class="mbline">')
    for who, what, era in LINEAGE:
        out.append(f'<li><b>{who}</b><span>{what}</span><i>{era}</i></li>')
    out.append('</ul>')

    # 三張卡
    out.append('<h3>三種形態實測</h3>')
    out.append('<div class="mbg">')
    for pat, (nm, who, desc) in NAMES.items():
        s = stats_of(cs, pat)
        if not s:
            continue
        cls = "ok" if s["ev"] > 0 else ""
        out.append('<div class="mbc">')
        out.append(f'<h4>{nm}</h4><div class="who">{who}</div>')
        out.append(f'<div class="big {cls}">{s["ev"]:+.2f}R</div>')
        out.append('<div style="font-size:10.5px;opacity:.55;'
                   'margin-bottom:7px">每單期望</div>')
        out.append(f'<div class="row"><span>樣本</span><b>{s["n"]}</b></div>')
        out.append(f'<div class="row"><span>勝率</span><b>{s["wr"]}%</b></div>')
        out.append(f'<div class="row"><span>賠率</span>'
                   f'<b>{s["payoff"]}:1</b></div>')
        out.append(f'<div class="row"><span>中位 R</span>'
                   f'<b>{s["med"]:+.2f}</b></div>')
        out.append(f'<div class="row"><span>2R 減倉率</span>'
                   f'<b>{s["trim"]}%</b></div>')
        out.append(f'<div class="row"><span>風險中位</span>'
                   f'<b>{s["risk_med"]}%</b></div>')
        out.append('</div>')
    out.append('</div>')

    # ★ 最大發現
    out.append('<div class="mbwarn">')
    out.append('<b>★ 最大發現：三種形態結果幾乎一樣</b><br>')
    out.append('VCP（波幅收縮）、Undercut & Rally（破底返上）、'
               'RS 先新高 —— 三個 detector 邏輯完全唔同，'
               '但結果全部 <b>34.5% 勝率、約 3.0 賠率、+0.3～0.45R</b>。')
    out.append('<br><br>→ 你嘅 edge 唔在「揀邊個形態」，'
               '在「3 段 stop 令你蝕 1R 但賺 3R」。')
    out.append('<br>→ 對照實盤：你勝率 32.1%（幾乎一樣），'
               '但賠率只 1.68:1（呢度 3.0）。'
               '<b>你揀股冇問題，出場規則令賠率腰斬。</b>')
    out.append('</div>')

    # 檢查表
    out.append('<h3>入場檢查表（Clement 原文）</h3>')
    out.append('<p style="font-size:11.5px;opacity:.6;margin:0 0 6px">'
               '技術 edge</p><ul class="mbchk">')
    for x in CHECK_TECH:
        out.append(f'<li>{x}</li>')
    out.append('</ul>')
    out.append('<p style="font-size:11.5px;opacity:.6;margin:0 0 6px">'
               '大股 / TML edge</p><ul class="mbchk">')
    for x in CHECK_TML:
        out.append(f'<li>{x}</li>')
    out.append('</ul>')

    # 每種形態 top cases
    out.append('<h3>最佳案例（每種形態 Top 5）</h3>')
    for pat, (nm, _, _) in NAMES.items():
        v = top_cases(cs, pat, 5)
        if not v:
            continue
        out.append(f'<p style="font-size:11.5px;font-weight:700;'
                   f'margin:12px 0 5px">{nm}</p>')
        out.append('<table class="mbtb"><tr><th>股票</th><th>日期</th>'
                   '<th>入場</th><th>止蝕</th><th>風險%</th>'
                   '<th>R</th></tr>')
        for c in v:
            out.append(f'<tr><td>{c["ticker"]}</td><td>{c["date"]}</td>'
                       f'<td>{c["entry"]}</td><td>{c["stop"]}</td>'
                       f'<td>{c["risk_pct"]}%</td>'
                       f'<td style="color:#15803d;font-weight:700">'
                       f'{c["r"]:+.2f}</td></tr>')
        out.append('</table>')

    out.append('<p class="mbh" style="margin-top:16px">'
               '維護：每週一次 <code>mb_cases.py --build</code>。'
               'Clement 原文：「252 個交易日，每日 1 張 = 每年 252 張」'
               '—— 我哋每次掃 379 隻 × 500 日 = 即時幾千張，'
               '而且有統計。但【紀律】仍然要人手：'
               '每週睇一次最新案例，刪走已經認得出係平庸嘅設置。</p>')
    out.append('</div>')

    # ★ 升幅時間集中度（TraderGoku 深入研究，Desmond 2026-10-23）
    try:
        import mb_burst_page as _bb
        _bh = _bb.block()
        if _bh:
            out.append(_bh)
    except Exception as e:                               # noqa: BLE001
        out.append(f'<div class="card"><p>⚠️ 集中度區塊失敗：'
                   f'{type(e).__name__}</p></div>')

    # ★ Top 250 US Gainers（Desmond 2026-10-23 提供 new.xlsx）
    try:
        import mb_top250_page as _t2
        out.append(_t2.block())
    except Exception as e:                               # noqa: BLE001
        out.append(f'<div class="card"><p>⚠️ Top 250 區塊失敗：'
                   f'{type(e).__name__}</p></div>')
    return "".join(out)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    html = block()
    os.makedirs(DOCS, exist_ok=True)
    p = os.path.join(DOCS, "modelbook_lib.html")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ {p}｜{len(html):,} 字")


if __name__ == "__main__":
    main()
