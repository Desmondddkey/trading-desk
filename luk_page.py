# -*- coding: utf-8 -*-
"""luk_page.py — Martin Luk 手冊（RAE 蒸餾自 James Muninn 2026-11-03 文章）

來源：https://x.com/muninn/status/2117629160348668285
作者記錄 112 場直播、211 小時，重建其多日 swing 交易，並與其 Discord 日誌盲檢。
本頁只放文章有數據支持嘅內容；推論會標明。
"""
from __future__ import annotations

import html as _h
import os


def _esc(x):
    return _h.escape(str(x))


def _table(head, rows, cls="pf-mini2"):
    P = [f'<div class="{cls}"><table><thead><tr>']
    P += [f'<th>{h}</th>' for h in head]
    P.append('</tr></thead><tbody>')
    for r in rows:
        P.append('<tr>' + "".join(
            f'<td class="n">{c}</td>' if isinstance(c, (int, float)) else f'<td>{c}</td>'
            for c in r) + '</tr>')
    P.append('</tbody></table></div>')
    return "".join(P)



ARTICLE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "content", "luk_article.md")


def _full_article():
    """原文全文（英文），Markdown → HTML。讀本地副本，唔靠網。"""
    import io as _io
    import os as _os
    try:
        import markdown as _md
    except ImportError:
        return '<div class="dim">UNVERIFIED：markdown 模組未安裝</div>'
    if not _os.path.exists(ARTICLE):
        return '<div class="dim">UNVERIFIED：找不到 data/luk_article.md</div>'
    with _io.open(ARTICLE, encoding="utf-8") as f:
        txt = f.read()
    html = _md.markdown(txt, extensions=["tables", "fenced_code", "sane_lists"])
    return html


ARTICLE_ZH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "content", "luk_article_zh.md")


def _full_article_zh():
    """原文全文（中文翻譯，逐段對應）。"""
    import io as _io
    import os as _os
    try:
        import markdown as _md
    except ImportError:
        return '<div class="dim">UNVERIFIED：markdown 模組未安裝</div>'
    if not _os.path.exists(ARTICLE_ZH):
        return '<div class="dim">UNVERIFIED：找不到 content/luk_article_zh.md</div>'
    with _io.open(ARTICLE_ZH, encoding="utf-8") as f:
        txt = f.read()
    return _md.markdown(txt, extensions=["tables", "fenced_code", "sane_lists"])


def build():
    P = ['<h2>🏆 Martin Luk 手冊 <small>USIC #1 · 969.8% 嘅可複製部分</small></h2>']
    P.append('<p class="crumb">來源：James Muninn（記錄 112 場直播、211 小時，重建多日 swing）'
             '｜2026 年 1–10 月 +844.5%（文章）｜Kinfo 驗證帳戶 > $4M</p>')

    P.append('<h3>一、核心算式（唯一可照抄嘅部分）</h3>')
    P.append('<pre>倉位 % = 帳戶風險 % ÷ 止蝕距離 %</pre>')
    P.append(_table(["交易者", "止蝕", "風險", "倉位", "同一隻股 +50% 嘅結果"], [
        ["一般日線交易者", "3.0%", "0.50%", "16.7%", "+16.7R（帳戶 +8.35%）"],
        ["Martin Luk", "1.5%（1 分鐘）", "0.50%", "33.3%", "+33.3R（帳戶 +16.65%）"],
    ]))
    P.append('<div class="pf-note">兩者輸嘅時候一樣蝕 0.50%。差別純粹係「同一筆風險買到幾多曝險」。</div>')

    P.append('<h3>二、風險階梯（2026，帳戶過百萬後）</h3>')
    P.append(_table(["情況", "每單風險"], [
        ["標準", "0.30%"],
        ["連蝕期", "0.15% – 0.25%"],
        ["一年一兩次高信心", "1.0% – 1.5%"],
        ["單一股票上限", "35%（硬上限）"],
    ]))

    P.append('<h3>三、出場：15% + 85%（2025 年後改動）</h3>')
    P.append('<pre>+3R ~ +5R  → 減 10–15%（用嚟「養住個止蝕」）\n'
             '其餘 85–90% → 日線收市跌穿 9EMA（快股）或 21EMA（慢股）才走</pre>')
    P.append('<div class="pf-note">文章原話：MRVL 2026-03-31 → 05-07，+25R；'
             'SMCI 提早賣走核心，之後再升 200%+，他自己評為 40R+ 錯誤。</div>')

    P.append('<h3>四、持倉時間（2026 數據）</h3>')
    P.append(_table(["類別", "平均交易日"], [
        ["多頭贏單（拖 9EMA）", "9.0"],
        ["多頭贏單（實際直播出場）", "7.4"],
        ["空頭贏單", "6.9 – 8.6"],
        ["所有輸單", "0.54"],
    ]))
    P.append('<div class="pf-note">45.8% 嘅交易、53.7% 嘅輸單，喺第 1 日就止蝕（多數入場後 15–90 分鐘）。</div>')

    P.append('<h3>五、入場方式（2026，多頭）</h3>')
    P.append(_table(["訊號", "佔比"], [
        ["AVWAP / VWAP 收復或拒絕", "29.6%"],
        ["日內楔形／微趨勢線突破", "19.2%"],
        ["1m / 5m / 15m 開盤區間突破", "17.1%"],
        ["開盤洗盤後收復", "10.4%"],
    ]))
    P.append('<div class="pf-note">水平箱體突破幾乎消失（2.3%）。原因：2024 年後乾淨箱體變少、'
             '突破後被洗走太多次；改成等 3–7 日回調入 9/21EMA 與 AVWAP，止蝕可以收緊 50%。</div>')

    P.append('<h3>六、空頭（42% 交易，貢獻 > 一半淨 R）</h3>')
    P.append(_table(["設置", "做法"], [
        ["弱反彈（Weak Bounce）", "前領頭股跌穿 21EMA → 2–4 日縮量反彈入下跌 9/21EMA → 日內失敗做空"],
        ["拋物線做空", "連續 5–10 日垂直、跳空入高潮 → 1m/5m 開盤區間跌破，止蝕放在日內高位之上"],
    ]))
    P.append('<div class="pf-note">空頭勝率 23.5% > 多頭 16.9%。轉向靠兩個即時訊號：'
             '① 自己連續止蝕；② 100 隻動能股掃描有 90 隻變差。</div>')

    P.append('<h3>七、心理現實（最容易被忽略）</h3>')
    P.append(_table(["事實", "數字"], [
        ["全年 R 總和", "+300R"],
        ["其中 10 單貢獻", "+220R（73%）"],
        ["全 -1R 止蝕收場", "461 單中 305 單"],
        ["最長連蝕（2026 數據）", "33 單"],
        ["2025-12 單月回撤", "−26.6%（74 單，勝率 12.2%）"],
    ]))
    P.append('<div class="pf-note">2025-12 有 46% 交易被他自己歸類為「隨機交易」。'
             '教訓：因為每單只 0.3–0.5%，連蝕 20 單只蝕 6–10%，一單贏家已足够補回。</div>')

    P.append('<h3>八、對我們系統嘅四個差異（未改，等批准）</h3>')
    P.append(_table(["項目", "我們現時", "Martin Luk", "影響"], [
        ["止蝕距離", "3%（上限）", "1.5% 日內", "同樣 0.5% 風險，倉位由 16.7% → 33%"],
        ["第一次減倉", "2R 減 33%", "+3R~+5R 減 10–15%", "我們切斷大贏家嘅腿"],
        ["拖線", "10EMA（日線收市）", "9EMA（快）/ 21EMA（慢）", "我們慢一日"],
        ["持有贏單", "未統計", "7.4–9.0 日", "要開始量度"],
    ]))
    P.append('<div class="pf-note">⚠ 以上屬 SOUL §4 風控／出場規則，係單向門：'
             '我只出方案，改要你批。同時提醒：Luk 用 Portfolio Margin，'
             '200–350% gross 曝險；我們冇槓桿，唔可以照搬倉位。</div>')

    P.append('<h3>九、可即刻做（不需批准）</h3>')
    P.append('<ul>'
             '<li>每日計劃卡加一欄「拖線天數」，開始量度贏單持有日數</li>'
             '<li>R 分佈圖：頭 10 單佔全年幾成 R（檢驗我們是否同一模式）</li>'
             '<li>止蝕距離 vs 倉位對照表：同一 0.5% 風險下，1.5% / 2% / 3% 嘅倉位與 R 差異</li>'
             '</ul>')
    P.append('<h3>十、原文全文（中文，逐段對照）</h3>')
    P.append('<div class="pf-note">Muninn 文章全文中文翻譯；數字、專有名詞保留原文。'
             '英文原文喺下面第二個摺位。</div>')
    P.append('<details class="art" open><summary>展開全文（中文）</summary>'
             f'<div class="artbody">{_full_article_zh()}</div></details>')
    P.append('<details class="art"><summary>English original（未刪節）</summary>'
             f'<div class="artbody">{_full_article()}</div></details>')
    P.append("""<style>
.art{border:1px solid #cfc7bb;border-radius:8px;background:#fff;margin:0 0 12px;color:#1f1e1d}
.art>summary{cursor:pointer;padding:10px 14px;font-weight:700;font-size:13px}
.artbody{padding:4px 16px 16px;border-top:1px solid #e6e0d6;font-size:13px;line-height:1.6}
.artbody h2{font-size:15px;margin:16px 0 6px}
.artbody h3{font-size:13.5px;margin:12px 0 4px}
.artbody table{border-collapse:collapse;width:100%;margin:8px 0;font-size:12.5px}
.artbody th,.artbody td{border:1px solid #e0d9cc;padding:5px 7px;text-align:left}
.artbody blockquote{border-left:2px solid #c2410c;margin:8px 0;padding:2px 10px;color:#5b564c}
.artbody code{background:#f2eee5;padding:1px 4px;border-radius:3px}
.artbody pre{background:#f6f3ec;padding:8px 10px;border-radius:5px;overflow-x:auto}
</style>""")

    P.append('<div class="pf-note">限制：文章為第三方重建，非 Luk 本人完整交易日誌；'
             '2026 數據截至 10 月；Kinfo 驗證期為過去 12 個月，與文章 2026 數據不同期。</div>')
    return ("Martin Luk 手冊", "".join(P))


def main():
    t, b = build()
    print(f"{t} — {len(b):,} chars｜{b.count('<table')} 表")


if __name__ == "__main__":
    main()
