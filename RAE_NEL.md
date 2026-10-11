# RAE — i-manage-risk/NEL 逆向工程報告

日期：2026-10-11｜做嘅人：HERMES｜目的：Desmond 要求「RAE 逆向工程整個網站所有內容，
再做成繁體版，加我嘅 dashboard 做最頂一個新分頁」

## 一、來源

| 項目 | 值 |
|---|---|
| 網站 | https://i-manage-risk.github.io/NEL/index.html |
| Repo | https://github.com/i-manage-risk/NEL（public，main，110 commits，7 star） |
| 取得方式 | `curl -sL https://codeload.github.com/i-manage-risk/NEL/tar.gz/refs/heads/main` |
| 檔案數 | 251 |
| 授權 | repo 冇 LICENSE 檔 → **只做架構參考 + 自己重寫，唔會複製佢嘅代碼或資料** |

## 二、架構（核心發現）

```
index.html        2 KB    ← 只係殼
assets/workspace.js   36 KB  ← 真正嘅渲染引擎（route: briefing/environment/leadership/positioning/screener/review/method）
assets/workspace.css  15 KB
outputs/workspace.json 2.6 MB ← 全部快照（每日一份）
outputs/market_context.json / positioning.json / breadth_market_monitor.json
themes.html / sectors.html / breadth.html / super-liquid.html / industry_flow_dashboard.html  ← 細節頁
```

**關鍵設計**：細 HTML ＋ 大 JSON ＋ 一支 JS 渲染器。`index.html` 冇內容，
所有嘢由 `workspace.js` 讀 JSON 砌出嚟。呢個 pattern 直接搬到 GitHub Pages。

**導航**：Stocks（index）／Themes／Sectors／Breadth（四頁）
**內部 route**（同一頁換內容）：briefing（Now）／environment（Market pulse）／
leadership（Capital flow）／positioning（Crowding）／screener（Stock radar）／
review（Session replay）／method（Sources & definitions）

## 三、資料管道

| 層 | 做咩 |
|---|---|
| `focus_list.py` | 由 TradingView 匯出嘅 filtered_universe CSV 起 NEL |
| `tight_nel.py` | 用 yfinance 3 個月 OHLC 計 T-NEL coil（9EMA／5 日 ≤2.5 ATR／今日波幅 < 前日 ATR／3+5 日收縮） |
| `etf_strength.py` | 主題／板塊 ETF 排名：`70% × 成員中位百分位 + 30% × 最強成員百分位` |
| `breadth_dashboard.py` | 由 Stockbee Market Monitor 重建歷史 Time Machine |
| `positioning.py` | CFTC COT 報告（大型投機者 156 週極端） |
| `workspace_data.py` | 把每日 CSV 合成 `workspace.json` 快照 |
| `.github/workflows/daily-scan.yml` | 收市後跑、commit、Pages 自動更新 |

## 四、NEL 嘅規則（原文抄落嚟，唔准演繹）

**Liquid Universe 硬閘**
- 30 日平均成交額 > $30M
- 14 期 ADR% > 4%
- 10 日平均成交量 > 350K 股
- 行業唔可以有 "Biotech"

**NEL（Non-Extended Leaders）**
- 1M／3M／6M／1Y 各自取表現前 5% → 四組合併去重
- 剔走 `(Price − SMA50) / (SMA50 × ATR%) > 4` 嘅
- 延伸公式：`ATR Extension from 50d = (Price − SMA50) / (SMA50 × ATR%)`

**T-NEL（Tight）**
- 企喺 9EMA 上
- 5 日高低範圍 ≤ 2.5 ATR
- 今日日內波幅 < 前一日 ATR
- 3 日或 5 日嘅收市／真實波幅符合快速收縮

**ETF 群組評分**
- `70% × 成員中位百分位 + 30% × 最強成員百分位`
- ADR／流動性對 ETF 只係資訊，永遠唔會剔走

## 五、我哋做到幾多（實測）

| 項目 | 狀態 |
|---|---|
| 全市場掃描 | ✅ `tradingview_screener` Python 套件打同一個 API，12,015 隻 US 股票 |
| 硬閘後流動池 | ✅ 383 隻 |
| 動能池（四窗前 5%） | ✅ 55 隻 ← 同 NEL 公佈嘅「Liquid Leaders 55」**數字一樣** |
| NEL | ✅ 39 隻（NEL 公佈 32 隻） |
| 對佢 2026-10-11 名單命中 | **19 / 32** |
| T-NEL coil | ⏳ 未做（要 yfinance 3 個月 OHLC，下一步） |

**差異來源（唔准當同一件事）**
1. NEL 用網頁版匯出嘅 `average_dollar_volume_30d`；套件呢個欄位回 `None`
   → 我哋自己計 `收市 × 10 日平均量`，門檻等效但**唔係同一個欄位**。
2. 套件嘅 `ADRP` 同網頁版 `ADRP` 有出入（例：TEAM 套件出 3.99% < 4% 門檻而被剔，
   但 NEL 名單有佢）→ **同名唔同義，EDGE-036 嗰種陷阱**。
3. 未取得佢嘅 filtered_universe CSV，所以無法逐步對齊。

## 六、我哋做咗嘅嘢

`C:\Users\rain0\trading-os-web\`
- `scan_market.py` — 全市場掃描 → `data/market_scan.json`
- `build_site.py` — 產生 `site/`（純靜態、單檔、無 CDN、file:// 同 Pages 都開得）
- `site/index.html` ＝ 簡報；另有 `leaders / week / rsboard / method / cycle / setups / desk`

**分頁（繁體）**
1. 🖥 交易台 — Desmond 原本嗰個 dashboard（位置圖／輪動／風險／日期回溯）
2. 📋 簡報 — regime ＋ 廣度 ＋ 今日圖表隊列
3. 🚀 領導股 — NEL 等效（全市場）＋ 動能池 ＋ 按行業分組
4. ⚡ 最強 1 週 — 流動池之中本週最強
5. 📊 RS 板 — ETF 群組（**我嘅定義，唔係 Jeff 原文**，圖上有註明）
6. 🧩 方法分類 — Layer1+2 Focus／Stalk 各自清單
7. 🌀 成長週期 — 未接（等 Desmond 確認成長／價值用邊兩條線）
8. 📐 Setups — 未接（等 Desmond 確認虛線／實線／綠方格嘅原文規則）

## 七、未做（唔准當做咗）

- T-NEL coil（要 yfinance OHLC 歷史，~40 隻，可行）
- Growth Cycle（定義已蒸餾，缺一個參數）
- Setups 圖（缺原文規則）
- GitHub Pages 部署（**未有任何 GitHub 憑證**；gh CLI 未裝，無 token，
  無 ~/.git-credentials → 需要 Desmond 用 device flow 授權）
- Themes／Sectors／Breadth 三個細節頁（NEL 有，我哋未有）
