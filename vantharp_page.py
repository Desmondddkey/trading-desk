# -*- coding: utf-8 -*-
"""vantharp_page.py — Van K. Tharp 五法（網站頁）

Desmond 2026-10-22 貼文：「5 種改善你市場表現嘅方法 — 由已故 Van K. Tharp, Ph.D. 撰寫」
                                    →「將以上既方法加入我的網站」

━━━ 設計原則 ━━━
唔係原文照抄。每一條都要接到 Desmond 現有系統：
  ① 原文講咩（翻譯）
  ② 我哋系統點做（對應嘅 module / 常數 / 頁面）
  ③ 現時狀態（有做 / 未做 / 做得唔夠）

因為一條規則若果冇連到實際動作 = 教條（SOUL §8.15）。
"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TO = r"C:\Users\rain0\trading-os"


def _read(p, n=4000):
    try:
        if os.path.exists(p):
            return io.open(p, encoding="utf-8", errors="replace").read()[:n]
    except Exception:                                        # noqa: BLE001
        pass
    return ""


METHODS = [
    dict(
        n=1,
        icon="📈",
        title="跟住市場嘅當前趨勢投資",
        quote="喺入市之前，先知市場而家做緊乜。係升定跌？"
              "睇下 $SPY 同佢嘅 200 日移動平均線比較下價位。"
              "當市場喺 200 日移動平均線以上嘅時候，歷史上表現會比喺以下嘅時候好。"
              "如果價位跌穿咗佢，考慮減低你嘅曝險。",
        system=(
            "Weinstein 四階段（30 週 MA）＋ SPY vs 200MA ＋ MMFI 廣度",
            "market_regime.py｜weinstein_stage.py",
            "site/regime_mri.html",
        ),
        now="✅ 已做 —— 但 Tharp 用 200 日，我哋用 30 週（150 日）＋4 週斜率，"
            "更早察覺趨勢轉向。廣度（MMFI）補足「指數升但個股跌」嘅假象。",
        check="每日開市前睇 MARKET REGIME：SPY 喺 200MA 上定下？"
              "Weinstein Stage 幾？MMFI 幾 %（>50 健康、<30 弱）？",
    ),
    dict(
        n=2,
        icon="🚪",
        title="唔知點出場，千祈唔好入倉",
        quote="喺入任何倉之前，定好你嘅出場點。投資界經常推廣「買入並持有」，"
              "但冇出場計劃就持有，會令你暴露喺重大損失之下。"
              "如果你唔知點出場，你就唔知你嘅風險。"
              "Tharp 建議長期倉位最少用 25% 嘅跟蹤止蝕。",
        system=(
            "Jeff Sun 3-Stop 階梯（LoD → 2R 減 33% → Day3 breakeven → 10EMA）",
            "jeffsun_stop.py｜ahead_tree.py",
            "site/setups.html",
        ),
        now="✅ 已做 —— 每張卡都預先寫死止蝕（LoD）＋分批止賺＋時間停。"
            "★ 2026-10-22 修：trim2r 由公式計（入場 + 2×風險），唔再信卡片解析。",
        check="入場前問：止蝕喺邊？幾多 R 減倉？幾時全清？"
              "答唔到 = 唔准入（EDGE：冇出場計劃 = 冇風險控制）。",
    ),
    dict(
        n=3,
        icon="⚖️",
        title="任何倉位都唔好冒超過投資組合 1% 嘅險",
        quote="倉位大小應該由你嘅風險決定，而唔係你想買幾多決定。"
              "如果你有 $25,000 嘅投資組合，冒 1% 險就意味住將你潛在損失限喺 $250 內。"
              "如果你嘅止蝕位離 $2，你可以買 125 股。如果你嘅止蝕位離 $20，你只可以買 12 股。"
              "倉位大小會變，但投資組合風險保持一樣。",
        system=(
            "每單風險 0.5%（比 Tharp 1% 更保守）＋ 單一倉位上限 33% ＋ 總風險 ≤1.5%",
            "daily_plan.py（stop_plan）｜discipline_gate.py",
            "site/calculator.html",
        ),
        now="✅ 已做，而且比 Tharp 更嚴 —— 0.5% 而非 1%。"
            "倉位由風險反推：size% = min(0.5% ÷ 止蝕%, 33%)。",
        check="落場前計：止蝕距離幾 %？→ 倉位 = 0.5% ÷ 止蝕%。"
              "唔准先諗買幾多股。",
    ),
    dict(
        n=4,
        icon="🪞",
        title="持續觀察你嘅模式、習慣同情緒",
        quote="自我意識對改善嚟講係必需嘅。留意你喺入場、管理同出場交易時諗緊乜同感覺點。"
              "保持一份交易日誌，搵出重複出現嘅情緒、諗頭同行為，可能會傷害你嘅表現。"
              "目標唔係消除情緒，而係察覺佢哋，而唔畀佢哋控制你嘅決定。",
        system=(
            "交易日誌 + Edge Improving 六維度分解 + Think in R 分佈",
            "logbook.py｜edge_page.py｜thinkinr_page.py",
            "site/edgeimprove.html｜site/thinkinr.html",
        ),
        now="✅ 已做 —— 1,316 round-trip 全部分析：勝率 31.8%、贏輸比 1.68:1、"
            "每單 −$11。持倉 <30 分鐘 631 單 −$19,317；≥1 日 190 單 +$14,617。",
        check="每週答三條：① 我呢個星期重複犯咩錯？"
              "② 邊個情緒令我提早平倉？③ 我有冇因為一單輸而報復交易？",
    ),
    dict(
        n=5,
        icon="🎯",
        title="為你嘅結果負責任",
        quote="當事情出錯嘅時候，好容易怪市場、你嘅經紀、分析師、基金經理或者外部事件。"
              "但迴避個人責任會阻止你從錯誤中學習。"
              "如果你完全為你嘅結果負責，你就可以識別乜嘢出錯，修正佢，"
              "同避免重複同樣錯誤。無論市場發生乜，負責任你嘅結果。",
        system=(
            "did_nothing.py（實際 PnL vs 完全唔做 PnL）＋ 每單記錄執行質量",
            "did_nothing.py｜edge_book/",
            "site/logbook.html",
        ),
        now="✅ 已做 —— 每日記「實際 vs 完全唔做」差距；"
            "覆盤基準係【有冇跟足規則】，唔係賺定輸。",
        check="每單覆盤問：如果依家爆倉，我會唔會後悔冇跟返規則？"
              "答「會」= 呢單係執行問題，唔係市場問題。",
    ),
]


CARD_CSS = """
<style>
/* ★ 2026-10-22 修：原本用死深色主題色（#e2e8f0 / #94a3b8），
   但網站有淺色主題（body{background:#f6f8fb;color:#1a2433}）
   → 淺灰字喺白底幾乎睇唔到。改為全部用 inherit + opacity，
     等文字永遠跟住當前主題嘅前景色。 */
.vt-hero{border:1px solid rgba(128,140,170,.28);
  border-radius:14px;padding:18px 18px 14px;margin-bottom:14px;
  background:rgba(128,140,170,.07)}
.vt-hero h2{margin:0 0 6px;font-size:17px;color:inherit}
.vt-hero p{margin:0;font-size:12.5px;line-height:1.85;
  color:inherit;opacity:.78}
.vt-card{border:1px solid rgba(128,140,170,.22);
  border-radius:10px;padding:14px 15px;margin-bottom:12px;
  background:rgba(128,140,170,.05)}
.vt-card h3{margin:0 0 10px;font-size:14px;color:inherit;
  display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.vt-n{background:#2563eb;color:#fff;border-radius:6px;padding:1px 7px;
  font-size:11.5px;font-weight:700}
.vt-q{background:rgba(37,99,235,.13);border-left:3px solid #2563eb;
  padding:9px 12px;border-radius:6px;font-size:12.5px;line-height:1.9;
  color:inherit;opacity:.92;margin-bottom:10px}
.vt-row{display:flex;gap:8px;font-size:12.5px;line-height:1.8;
  padding:6px 0;border-top:1px dashed rgba(128,140,170,.28);
  flex-wrap:wrap;color:inherit}
.vt-k{min-width:74px;flex:0 0 74px;font-weight:700;opacity:.62}
.vt-v{flex:1;min-width:180px;color:inherit}
.vt-check{background:rgba(34,197,94,.14);border:1px solid rgba(34,197,94,.42);
  border-radius:8px;padding:9px 12px;margin-top:9px;font-size:12.5px;
  line-height:1.85;color:inherit}
.vt-code{font-family:ui-monospace,Consolas,monospace;font-size:11.5px;
  background:rgba(128,140,170,.20);padding:1px 6px;border-radius:4px;
  color:inherit}
@media(max-width:700px){
  .vt-k{flex:0 0 100%;min-width:0}
  .vt-v{flex:0 0 100%;min-width:0}
  .vt-hero{padding:14px 13px 11px}
  .vt-card{padding:12px 12px}
}
</style>
"""


def build():
    """→ (title, html)"""
    cards = []
    for m in METHODS:
        cards.append(
            f'<div class="vt-card">'
            f'<h3><span class="vt-n">方法 {m["n"]}</span>'
            f'{m["icon"]} {m["title"]}</h3>'
            f'<div class="vt-q">「{m["quote"]}」</div>'
            f'<div class="vt-row"><span class="vt-k">我哋點做</span>'
            f'<span class="vt-v">{m["system"][0]}</span></div>'
            f'<div class="vt-row"><span class="vt-k">模組</span>'
            f'<span class="vt-v"><span class="vt-code">{m["system"][1]}</span>'
            f'</span></div>'
            f'<div class="vt-row"><span class="vt-k">頁面</span>'
            f'<span class="vt-v">{m["system"][2]}</span></div>'
            f'<div class="vt-row"><span class="vt-k">現況</span>'
            f'<span class="vt-v">{m["now"]}</span></div>'
            f'<div class="vt-check">✅ <b>每次問自己</b>：{m["check"]}</div>'
            f'</div>')

    hero = (
        '<div class="vt-hero">'
        '<h2>🧠 Van K. Tharp 五法</h2>'
        '<p>已故 Van K. Tharp, Ph.D. —— 交易心理學之父。'
        '佢嘅核心主張：<b>你交易嘅唔係市場，係你對市場嘅信念</b>。<br>'
        '呢頁唔係原文照抄 —— 每條都接到我哋現有系統，'
        '寫明「邊個模組做、現時做唔做到、每次要問自己咩」。'
        '一條規則若果冇連到實際動作，就係教條。</p></div>')

    tail = (
        '<div class="vt-hero" style="margin-top:6px">'
        '<h2>📚 原文出處</h2>'
        '<p>PS：啲最偉大嘅免費交易資源可以喺「The Gifts of Dr. Van Tharp」'
        '網站搵到。佢哋係永恆嘅。<br>'
        '<a href="https://vantharp.com/tharps-thoughts-weekly-newsletter-archive/" '
        'target="_blank" rel="noopener" '
        'style="color:#2563eb;font-weight:600">vantharp.com → '
        "Tharp's Thoughts 週刊存檔 ↗</a>"
        '</p></div>')

    return ("Van K. Tharp 五法", CARD_CSS + hero + "".join(cards) + tail)
