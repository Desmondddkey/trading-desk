# -*- coding: utf-8 -*-
"""job_purpose.py — 每個 cron job「對 Desmond 有咩用」一句白話（2026-10-19）

★ 原因：Desmond 講「廚房看板有好多JOB 但我完全唔知佢地既工作係做」「係有咩作用」
   → 現有 job_descriptions.json 係技術描述（跑邊個 .py、產出邊個檔），
     對「我要唔要理佢」冇幫助。

★ 原則（第一性原理）：
    一句話講【你會得到咩】，唔講【程式點做】。
    如果一句話講唔出，代表呢個 job 可能唔需要存在。

分類標籤（方便你決定要唔要睇）：
    📌 一定要睇   —— 直接影響你今日買咩 / 幾時出
    👀 有時間睇   —— 幫你判斷環境，唔急
    🔧 系統自動   —— 你唔需要理，壞咗會出聲
"""

PURPOSE = {
    # ── 📌 一定要睇：直接影響今日決定 ──
    "Daily-Pre-market-Plan":
        "今日一張紙：regime、買咩候選、組合熱度、集中度警告。開市前睇呢張就夠。",
    "setup-alerts":
        "6 種 setup 嘅即時入場警報（每分鐘掃）。冇訊息＝冇 setup 成立，唔係壞。",
    "jeffsun-intraday-ORH-RVOL-alert":
        "開盤區間突破（ORH）+ 成交量爆發警報。呢啲係 Jeff Sun 體系最核心嘅入場點。",
    "osib-setup-alert":
        "OSIB（開盤狹窄區間突破）setup 警報。同 ORH 唔同：呢個要求區間更窄。",
    "yoyo-gap-alert":
        "YOYO 跳空 setup 警報（1chartmaster 方法）。跳空後回補嘅機會。",
    "ftd-pre-alert-daily":
        "FTD（跟進日）前嘅領先股。市場跌完、可能見底時，話你知邊幾隻已經偷步走強。",
    "leader-map-daily":
        "RS Leader 位置圖：邊隻領導股而家喺「買入區」內（唔追高、唔接刀）。",
    "desk-refresh-daily":
        "更新價格數據 + 重算位置圖。你唔需要睇，但冇佢位置圖就停更。",
    "risk-gate-daily":
        "今日風險閘：帳戶回撤到邊、仲可唔可以開新倉、單筆風險上限幾多。",
    "discipline-gate":
        "13 條紀律閘即時檢查（每 30 分鐘）。你買之前問佢：呢單准唔准做。",
    "macro-tail-guard":
        "宏觀尾部風險警報：VIX 急升、指數跳空、廣度崩潰 → 叫你減倉或全清。",
    "close-watch-exit":
        "美股收市前 20 分鐘檢查持倉：跌穿 10EMA 叫你全清、到 2R 叫你減 33%。",

    # ── 👀 有時間睇：幫你判斷環境 ──
    "market-insight-layer3b":
        "市場階段判斷（BULL／CHOP／BEAR）+ 今日應該用邊種武器。",
    "layer4-breadth-daily":
        "市場廣度：幾多 % 股票站上 40MA、ADL、新高新低。判斷「係唔係健康升市」。",
    "market-watch":
        "大市觀察：指數位置、領頭板塊、有冇 distribution 跡象。",
    "sector-rotation-daily":
        "板塊輪動：錢由邊個板塊流向邊個板塊。早一步知道下一波領頭。",
    "rotation-map-weekly":
        "輪動圖（RRG）：板塊由「改善」→「領先」→「轉弱」→「落後」嘅位置。",
    "theme-watch-daily":
        "主題監察：邊個主題（AI、核能、國防…）正在聚集動能。",
    "momentum-theme-daily":
        "動能主題排序：今日最強嘅主題係邊個。",
    "jeffsun-daily-scan-layer1+2":
        "每日選股掃描：由全市場篩到 FOCUS（幾十隻）+ STALK（十幾隻）。揀股第一步。",
    "weekly-watchlist-sunday-0900":
        "週度觀察名單：今個星期值得跟嘅股。星期日睇一次就夠。",
    "morales-prone":
        "Gil Morales「Eat My Short」setup：適合做空／避開嘅形態。",

    # ── 📚 記錄 / 歸檔 ──
    "usic-edge-audit-notion":
        "Edge Audit：逐個 setup 回溯計勝率／期望值／最佳出場。話你知邊個 setup 真係賺錢。",
    "usic-setup-daily-review":
        "每日 setup 覆盤：尋日邊個 setup 出過訊號、結果點。",
    "usic-monthly-log-excel":
        "月度交易日誌 Excel + 推上 Notion。你自己事後查成績用。",
    "track-record-daily":
        "成績追蹤：累計回報、勝率、贏輸比。用嚟對比目標（每月 ≥5%）。",
    "money-daily-benchmark":
        "資金曲線 vs 基準（SPY／QQQ）。睇你係唔係真係跑贏大市。",
    "competition-daily":
        "USIC 月度比賽進度：今個月賺咗幾多 %、距離 5% 目標幾遠。",
    "notion-trade-journal-sync":
        "把券商成交紀錄同步去 Notion「實盤交易日誌」。你自己覆盤用。",
    "premarket-notion-record":
        "把盤前分析（洞察＋掃描＋計劃）寫入 Notion，保留歷史。",
    "notion-records-daily":
        "Notion 記錄同步（日誌／筆記）。",
    "journal-open-check":
        "開市前檢查交易日誌有冇寫漏。",
    "journal-daily-reminder":
        "提醒你寫交易日誌。",
    "digest-morning":
        "早上摘要：尋晚美股發生咩事、今日要留意咩。",
    "digest-premarket":
        "開市前摘要：今日盤前重點。",
    "digest-evening":
        "收市後摘要：今日成績、邊單贏輸、明日重點。",

    # ── 🔧 系統自動：你唔需要理 ──
    "site-auto-rebuild":
        "自動重建網站並上線（08:50 + 23:50）。你唔需要睇。",
    "kitchen-watchdog":
        "每小時巡查：邊個 job 失敗咗就叫你。健康時完全靜音。",
    "kitchen-status-daily":
        "更新 Notion「廚房狀態」頁。",
    "trading-os-tests":
        "跑全套測試（600+ 個）。防止改壞嘢。",
    "edge-candidate-daily":
        "每日最多提 1 條新 edge 候選。冇新候選＝靜音。",
    "edge-question-weekly":
        "每週用數據質疑自己嘅規則（可唔可否證）。",
    "quality-watch-weekly":
        "每週驗證 6-setup 嘅 quality 分有冇用。",
    "shadow-exit-weekly":
        "每週比較出場規則（拖10EMA vs T+1 vs T+3…）。累積到 n≥200 才判。",
    "michelin-audit-weekly":
        "每週評星：邊個 job 係三星級（可靠＋有測試＋確定性合約）。",
    "model-book-weekly":
        "每週更新選股模型手冊。",
    "notion-kb-sync":
        "同步 Notion 知識庫（Jeff Sun 全書等）做本地快取。",
    "changelog-notion-sync":
        "把今日嘅改動寫入 Notion 更新日誌。",
    "edgebook-notion-sync":
        "把 EDGE BOOK 同步去 Notion。",
    "trading-desk-daily":
        "生成交易台總表（desk.html）。",
    "site-db-daily":
        "網站資料庫同步。",
    "fleet-sim-daily":
        "每個選股 job 自己模擬交易，比較邊個策略賺得多。",
    "sim-trade-daily":
        "模擬交易每日結算。",
    "jeffsun-intraday-rvol-record":
        "記錄今日 RVOL 數據（供日後回溯）。",
    "yoyo-gap-postclose":
        "YOYO 跳空收市後記錄。",
    "tree-trace-weekly":
        "樹命中率週報：預先寫嘅分支有冇命中。樣本不足會靜音。",
    "edge-036-recheck":
        "一次性檢查 EDGE-036（已完成，已停用）。",
    "premarket-list-daily":
        "開市前清單：三個原則 + 唔應該做 + 3 條自問。",
    "hermes-daily-digest":
        "Hermes 自己嘅每日摘要。",
    "cashdesk-daily":
        "現金台：可用資金、倉位佔比。",
}

# ★ 分類：一句話之外，仲要知「要唔要睇」
MUST_READ = {
    "Daily-Pre-market-Plan", "setup-alerts", "jeffsun-intraday-ORH-RVOL-alert",
    "osib-setup-alert", "yoyo-gap-alert", "ftd-pre-alert-daily",
    "leader-map-daily", "risk-gate-daily", "discipline-gate",
    "macro-tail-guard", "close-watch-exit",
}

WORTH_READ = {
    "market-insight-layer3b", "layer4-breadth-daily", "market-watch",
    "sector-rotation-daily", "rotation-map-weekly", "theme-watch-daily",
    "momentum-theme-daily", "jeffsun-daily-scan-layer1+2",
    "weekly-watchlist-sunday-0900", "morales-prone",
    "usic-edge-audit-notion", "usic-setup-daily-review", "track-record-daily",
    "money-daily-benchmark", "competition-daily", "digest-morning",
    "digest-premarket", "digest-evening", "premarket-list-daily",
}


def purpose(name):
    """→ (白話一句, 級別 emoji)。搵唔到 = ('', '')。"""
    p = PURPOSE.get(name)
    if p is None:
        for k, v in PURPOSE.items():
            if k.endswith("*") and name.startswith(k[:-1]):
                p = v
                break
    if p is None:
        return "", ""
    if name in MUST_READ:
        return p, "📌"
    if name in WORTH_READ:
        return p, "👀"
    return p, "🔧"
