# -*- coding: utf-8 -*-
"""howto_page.py — 一脈相承：由今日點用到每月覆盤（單一入口指南）"""
from __future__ import annotations


def _row(step, when, page, what, why):
    return (f'<tr><td class="n">{step}</td>'
            f'<td>{when}</td>'
            f'<td><a href="{page[1]}" target="_self">{page[0]}</a></td>'
            f'<td>{what}</td>'
            f'<td style="opacity:.72">{why}</td></tr>')


def build():
    P = ['<h2>🧭 一脈相承 <small>由今日開始，點用整套系統</small></h2>']
    P.append('<div class="pf-note">'
             '核心：<b>先環境 → 後個股</b>。任何一層斷，後面唔需要睇。'
             '唔係每個 job 都要你睇；你只需要跟住下面 6 步。</div>')

    P.append('<h3 style="margin-top:14px">每日（跟次序，唔可以跳）</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr>'
             '<th class="n">#</th><th>時間</th><th>去邊</th><th>做咩</th>'
             '<th>判斷準則</th></tr></thead><tbody>')
    P.append(_row("1", "開市前 30 分鐘", ("每日流程", "process.html"),
                  "睇七步判決：環境 / 廣度 / 板塊 / 候選 / 計劃 / READY / 錢",
                  "任何一步 NO-GO 就停；唔准用故事推翻算術"))
    P.append(_row("2", "同上", ("肥波總覽", "wave.html"),
                  "睇四層漏斗數字：MRI → 板塊前 5 → RS≥70 → setup 過幾隻",
                  "setup 過 < 3 = 今日觀察，唔開新倉"))
    P.append(_row("3", "開市前", ("Daily Scan", "dailyscan.html"),
                  "FOCUS 表逐隻核：X、EXT、RVOL、TIGHT、評分、SETUP 徽章",
                  "X ≥ 2 或 RVOL ≥ 1.2 或距高 0～−3% → 唔好追（回測最差三類）"))
    P.append(_row("4", "開市後", ("Alert", "alerts.html"),
                  "只理會 ELIGIBLE_FOR_MANUAL_REVIEW；跳空 > 3% 一律等回調",
                  "警報係問題，唔係答案；答唔到「點解呢隻」就唔做"))
    P.append(_row("5", "收市前 30 分鐘", ("覆盤", "review.html"),
                  "記錄今日執行 vs 計劃：有冇跟油門、有冇提早平倉",
                  "睇執行質量，唔係睇賺蝕"))
    P.append('</tbody></table></div>')

    P.append('<h3 style="margin-top:16px">每週</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr>'
             '<th class="n">#</th><th>時間</th><th>去邊</th><th>做咩</th>'
             '<th>判斷準則</th></tr></thead><tbody>')
    P.append(_row("6", "星期六", ("GTO 手牌分析", "gto.html"),
                  "睇每格 EV／勝率／t：邊類手牌值得打、邊類要棄",
                  "n < 30 或 t < 1.96 = 未證實，唔可以改規則"))
    P.append(_row("7", "星期六", ("系統地圖", "sysmap.html"),
                  "掃一次有冇 job 紅燈／停更",
                  "紅燈 = 當日數據唔可信，先修再交易"))
    P.append('</tbody></table></div>')

    P.append('<h3 style="margin-top:16px">每月（覆盤升級）</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr>'
             '<th class="n">#</th><th>去邊</th><th>做咩</th></tr></thead><tbody>')
    P.append('<tr><td class="n">8</td><td><a href="finish.html">收工標準</a></td>'
             '<td>機器逐項檢查：全部 ✅ = 網站同數據可靠；有 ❌ 就係源頭問題</td></tr>')
    P.append('<tr><td class="n">9</td><td><a href="external.html">外部數據源</a></td>'
             '<td>Martin Luk FAQ／NEL console：只補世界觀，唔可以取代本地數據</td></tr>')
    P.append('</tbody></table></div>')

    P.append('<h3 style="margin-top:16px">三條唔可以破嘅線</h3>')
    P.append('<div class="pf-note" style="line-height:2">'
             '<b>① 數字來源唯一</b>：R／EV 只用 gto_daily.py 計；'
             'ATR 只用一個定義；出場只用 SOUL §4.3 階梯。<br>'
             '<b>② 假設同結論分開</b>：t < 1.96 或 n < 30 一律寫「未證實」，'
             '唔准當規則用。<br>'
             '<b>③ 涉錢永遠人手</b>：我只出方案，唔會代你執行；'
             '風控常數改動要你批。'
             '</div>')

    P.append('<h3 style="margin-top:16px">你唔需要睇嘅嘢</h3>')
    P.append('<div class="pf-note">'
             '70+ 個 job 之中，大部分係搬數／同步／巡檢（no_agent、零 token）。'
             '你要睇嘅只有 <b>每日流程、肥波總覽、Daily Scan、Alert、覆盤</b> 五頁；'
             '其餘出問題會由 kitchen-watchdog 主動叫你。'
             '</div>')
    P.append('<div class="pf-note" style="margin-top:14px">'
             '想深一層：<a href="sysmap.html">系統地圖</a> 逐個 job 講做咩；'
             '<a href="gto.html">GTO 手牌分析</a> 講數據點變預測。'
             '</div>')
    return ("一脈相承", "".join(P))


def main():
    t, b = build()
    print(f"{t} — {len(b):,} chars")


if __name__ == "__main__":
    main()
