# SPEC — NEL Console 合併（v1）

## 目標
將 https://i-manage-risk.github.io/NEL/ 嘅單頁 console 設計 RAE 落嚟，
用我哋**自己嘅數據層**餵，並把現有 website 內容塞返入去做 v1。
v0 已備份：`git tag v0-20261116` ＋ `v0_backup_20261116.tgz`（7.8MB）。

## NEL 係咩（RAE 結果）
一個**單頁 Market console**，靠 `workspace.js` 喺 runtime fetch `outputs/*.json` 渲染。
章節（#anchor）：
1. **Environment**（參與度）：升／跌家數、net、±4% 日、±25% 季、34日 ±13%、月 ±25/50%、5D/10D pressure、站上 40MA%
2. **Leadership / Market tape**：SPY/QQQ/IWM/DIA/RSP/QQQE/SPMO/TLT 即市% + 1M/RSP + ATR index；SPX 收市
3. **Leadership / Sector**：Top4 + Bottom2 行業（session% / 1M/RSP / EW/RSP）
4. **Industries**：行業 ETF（PAWZ/PHO/JETS/ITB/PPH…）session% / 1M/RSP / thrust%；session 最強／最弱
5. **Positioning（COT）**：天然氣 UNG / Nasdaq QQQ / WTI USO / Bitcoin IBIT —— Large specs／Commercials／Small specs 倉位，Crowded Short/Long
6. **Screener**（#screener）

NEL 嘅數據層（outputs/*.json，全部公開可 fetch）：
- workspace.json（10MB）= liquid universe 每 snapshot（symbol/industry/price/adr/extension/dollarVolume）
- market_context.json = benchmark 表現
- positioning.json（3.5MB）= COT，source 係 CFTC Socrata `publicreporting.cftc.gov/resource/6dca-aqww.json`
- breadth_market_monitor.json、liquid_leadership.json、etf/sectors_snapshots.json、etf/themes_snapshots.json

## 我哋嘅數據對應（用自己嘅，唔抄人）
| NEL 章節 | 我哋已有數據 |
|---|---|
| Environment | `output/breadth_YYYYMMDD.json`（adl/nnnl/pct40ma/ls_ratio）|
| Leadership tape | `output/market_insight_YYYYMMDD.json`（indices SPY/QQQ/IWM）|
| Sector | `output/market_insight` lead + `data/screener.json` sector/industry |
| Industries | `data/screener.json` industry 欄 + tv_meta |
| Screener | `data/screener.json`（744 隻，已計 RS/ATRX/TIGHT/止蝕/股數）|
| **Positioning（COT）** | **冇 —— 要新加**：直接 fetch CFTC Socrata（同 NEL 同源）|

## v1 架構
- `nel.html` = 單頁 console（NEL 排版：卡片 + #anchor + pill header）
- 章節導航 = 固定 sidebar / 頂 bar
- 每個數字讀現有 json，缺失顯示 —（唔當 0）
- 現有 66 頁 = 保留做「內頁」，console 提供入口連結（唔刪，避免 bookmark 404）

## 未決（要 Desmond 揀）
1. 視覺：**完整複製 NEL CSS**（164KB，連埋佢個 JS）vs **自建 console**（用我哋設計 token，跟 NEL 排版）
2. Positioning 數據：直接 fetch CFTC（同 NEL 同源、但要建 fetcher）vs 跳過 Positioning 章節
3. 入口：nel.html 取代 index 做首頁？定獨立頁？

## 步驟
1. 建 CFTC positioning fetcher（如揀做）
2. 建 `nel.py` console 頁（environment/leadership/sector/industries/screener）
3. 接 positioning
4. 現有內容做「內頁」連結層
5. 部署 v1；v0 tag 留低可回滾
