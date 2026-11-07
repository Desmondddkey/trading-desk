# 網站漏洞審計

頁數 **99**｜總大小 **17.8 MB**

## 問題總表

### NUM_FORMAT（22 頁）
- `breadth_edge.html` — 5 種小數位：.1×37,.2×43,.3×2,.4×2,.16×1
- `dailyscan.html` — 6 種小數位：.1×660,.2×421,.3×30,.14×6,.15×52,.16×21
- `dailyscan_2026-10-19.html` — 5 種小數位：.1×213,.2×244,.14×1,.15×22,.16×13
- `dailyscan_2026-10-20.html` — 6 種小數位：.1×299,.2×292,.3×17,.14×3,.15×40,.16×18
- `dailyscan_2026-10-21.html` — 6 種小數位：.1×459,.2×346,.3×17,.14×1,.15×16,.16×41
- `dailyscan_2026-10-22.html` — 6 種小數位：.1×727,.2×516,.3×24,.14×2,.15×54,.16×34
- `dailyscan_2026-10-23.html` — 7 種小數位：.1×647,.2×422,.3×25,.14×3,.15×44,.16×23,.17×1
- `dailyscan_2026-10-25.html` — 7 種小數位：.1×883,.2×579,.3×33,.14×9,.15×65,.16×27,.17×1
- `dailyscan_2026-10-26.html` — 8 種小數位：.1×906,.2×570,.3×39,.13×1,.14×4,.15×68,.16×28,.17×3
- `dailyscan_2026-10-27.html` — 8 種小數位：.1×857,.2×532,.3×36,.13×1,.14×3,.15×59,.16×27,.17×3
- `dailyscan_2026-10-28.html` — 7 種小數位：.1×874,.2×570,.3×35,.13×2,.14×6,.15×70,.16×28
- `dailyscan_2026-10-29.html` — 7 種小數位：.1×902,.2×581,.3×42,.14×6,.15×74,.16×23,.17×1
- `dailyscan_2026-10-30.html` — 7 種小數位：.1×868,.2×563,.3×41,.14×8,.15×66,.16×23,.17×1
- `dailyscan_2026-11-01.html` — 7 種小數位：.1×747,.2×511,.3×31,.13×1,.14×15,.15×72,.16×12
- `dailyscan_2026-11-02.html` — 7 種小數位：.1×756,.2×502,.3×33,.13×12,.14×7,.15×60,.16×19
- `dailyscan_2026-11-03.html` — 7 種小數位：.1×739,.2×483,.3×34,.13×10,.14×8,.15×59,.16×15
- `dailyscan_2026-11-04.html` — 7 種小數位：.1×631,.2×415,.3×27,.13×9,.14×6,.15×42,.16×18
- `dailyscan_2026-11-05.html` — 7 種小數位：.1×772,.2×500,.3×39,.13×6,.14×8,.15×68,.16×16
- `jobboard.html` — 5 種小數位：.1×292,.2×1244,.3×55,.4×18,.6×1
- `leaders.html` — 9 種小數位：.1×10254,.2×3558,.3×364,.4×30,.5×123,.6×499,.7×274,.8×1,.9×4
- `skills.html` — 5 種小數位：.1×79,.2×78,.3×31,.4×15,.5×11
- `week.html` — 9 種小數位：.1×9350,.2×3439,.3×126,.4×30,.5×123,.6×499,.7×274,.8×1,.9×4

### FAKE_TODAY（6 頁）
- `breadth_edge.html` — 標題寫「今日」但冇日期：['今日讀數']
- `briefing.html` — 標題寫「今日」但冇日期：['📖 The Read 今日一句話']
- `howto.html` — 標題寫「今日」但冇日期：['🧭 一脈相承 由今日開始，點用整套系統']
- `index.html` — 標題寫「今日」但冇日期：['📖 The Read 今日一句話']
- `wave.html` — 標題寫「今日」但冇日期：['今日候選（RS 先、Setup 後）', '預測（今日 RS≥70 候選）']
- `yoyo_ball.html` — 標題寫「今日」但冇日期：['今日訊號']

### DEAD_PAGE（6 頁）
- `desk.html` — body 只有 497 bytes
- `livefeeds.html` — body 只有 509 bytes
- `modelbook_lib.html` — body 只有 513 bytes
- `modelbook_top250.html` — body 只有 513 bytes
- `rocketstock.html` — body 只有 509 bytes
- `themes.html` — body 只有 505 bytes

### NO_DATE_BADGE（5 頁）
- `alerts.html` — 「Setup Alert 所有警報分類」附近冇 ISO 日期
- `briefing.html` — 「圖表隊列 2026-11-06 19:20」附近冇 ISO 日期
- `fatpitch.html` — 「🎯 肥球掃描 J Law：等一個賠率明顯站在我這」附近冇 ISO 日期
- `index.html` — 「圖表隊列 2026-11-06 19:20」附近冇 ISO 日期
- `jobboard.html` — 「Setup Alert 所有警報分類」附近冇 ISO 日期

### DATE_FORMAT（2 頁）
- `jobboard.html` — 混用 ISO×1311/MD×98/US×1
- `lukplaybook.html` — 混用 ISO×9/MD×1/US×12

### 死連結（1 個）
- `method.html` ← 被 3 頁引用

## 逐頁明細

| 頁 | KB | 表 | 空表 | h1 | 日期格式 | 問題 |
|---|---|---|---|---|---|---|
| `jobboard.html` | 257 | 1 | 0 | HI! Desmond | ISO×1311/MD×98/US×1 | ⚠️ 3 |
| `breadth_edge.html` | 134 | 2 | 0 | 升跌比高，突破期望值更高？ | ISO×1 | ⚠️ 2 |
| `briefing.html` | 41 | 4 | 0 | HI! Desmond | ISO×13 | ⚠️ 2 |
| `index.html` | 41 | 4 | 0 | HI! Desmond | ISO×13 | ⚠️ 2 |
| `alerts.html` | 116 | 2 | 0 | HI! Desmond | ISO×1041 | ⚠️ 1 |
| `dailyscan.html` | 672 | 2 | 0 | HI! Desmond | ISO×54 | ⚠️ 1 |
| `dailyscan_2026-10-19.html` | 341 | 1 | 0 | HI! Desmond | ISO×49 | ⚠️ 1 |
| `dailyscan_2026-10-20.html` | 395 | 2 | 0 | HI! Desmond | ISO×43 | ⚠️ 1 |
| `dailyscan_2026-10-21.html` | 457 | 2 | 0 | HI! Desmond | ISO×44 | ⚠️ 1 |
| `dailyscan_2026-10-22.html` | 580 | 2 | 0 | HI! Desmond | ISO×45 | ⚠️ 1 |
| `dailyscan_2026-10-23.html` | 457 | 2 | 0 | HI! Desmond | ISO×48 | ⚠️ 1 |
| `dailyscan_2026-10-25.html` | 551 | 2 | 0 | HI! Desmond | ISO×49 | ⚠️ 1 |
| `dailyscan_2026-10-26.html` | 553 | 2 | 0 | HI! Desmond | ISO×50 | ⚠️ 1 |
| `dailyscan_2026-10-27.html` | 518 | 2 | 0 | HI! Desmond | ISO×51 | ⚠️ 1 |
| `dailyscan_2026-10-28.html` | 551 | 2 | 0 | HI! Desmond | ISO×52 | ⚠️ 1 |
| `dailyscan_2026-10-29.html` | 555 | 2 | 0 | HI! Desmond | ISO×53 | ⚠️ 1 |
| `dailyscan_2026-10-30.html` | 539 | 2 | 0 | HI! Desmond | ISO×53 | ⚠️ 1 |
| `dailyscan_2026-11-01.html` | 487 | 2 | 0 | HI! Desmond | ISO×55 | ⚠️ 1 |
| `dailyscan_2026-11-02.html` | 488 | 2 | 0 | HI! Desmond | ISO×55 | ⚠️ 1 |
| `dailyscan_2026-11-03.html` | 473 | 2 | 0 | HI! Desmond | ISO×55 | ⚠️ 1 |
| `dailyscan_2026-11-04.html` | 446 | 2 | 0 | HI! Desmond | ISO×55 | ⚠️ 1 |
| `dailyscan_2026-11-05.html` | 489 | 2 | 0 | HI! Desmond | ISO×55 | ⚠️ 1 |
| `desk.html` | 0 | 0 | 0 | — | — | ⚠️ 1 |
| `fatpitch.html` | 26 | 3 | 0 | HI! Desmond | ISO×8 | ⚠️ 1 |
| `howto.html` | 20 | 3 | 0 | HI! Desmond | ISO×8 | ⚠️ 1 |
| `leaders.html` | 2213 | 3 | 0 | HI! Desmond | ISO×9 | ⚠️ 1 |
| `livefeeds.html` | 0 | 0 | 0 | — | — | ⚠️ 1 |
| `lukplaybook.html` | 52 | 9 | 0 | HI! Desmond | ISO×9/MD×1/US×12 | ⚠️ 1 |
| `modelbook_lib.html` | 0 | 0 | 0 | — | — | ⚠️ 1 |
| `modelbook_top250.html` | 0 | 0 | 0 | — | — | ⚠️ 1 |
| `rocketstock.html` | 0 | 0 | 0 | — | — | ⚠️ 1 |
| `skills.html` | 700 | 0 | 0 | HI! Desmond | ISO×27/MD×5 | ⚠️ 1 |
| `themes.html` | 0 | 0 | 0 | — | — | ⚠️ 1 |
| `wave.html` | 25 | 4 | 0 | HI! Desmond | ISO×8 | ⚠️ 1 |
| `week.html` | 844 | 1 | 0 | HI! Desmond | ISO×8 | ⚠️ 1 |
| `yoyo_ball.html` | 21 | 1 | 0 | HI! Desmond | ISO×8 | ⚠️ 1 |
| `audit.html` | 28 | 3 | 0 | HI! Desmond | ISO×10 | ✓ |
| `backtest.html` | 29 | 1 | 0 | HI! Desmond | ISO×9/MD×1 | ✓ |
| `beachball.html` | 45 | 1 | 0 | HI! Desmond | ISO×9 | ✓ |
| `bee50.html` | 32 | 0 | 0 | HI! Desmond | ISO×8/MD×1 | ✓ |
| `calculator.html` | 27 | 0 | 0 | HI! Desmond | ISO×8 | ✓ |
| `cm.html` | 32 | 2 | 0 | HI! Desmond | ISO×9 | ✓ |
| `cycle.html` | 41 | 2 | 0 | HI! Desmond | ISO×11 | ✓ |
| `datahealth.html` | 22 | 1 | 0 | HI! Desmond | ISO×10/MD×8 | ✓ |
| `earningscal.html` | 70 | 7 | 0 | HI! Desmond | ISO×23 | ✓ |
| `edgeimprove.html` | 25 | 6 | 0 | HI! Desmond | ISO×10 | ✓ |
| `external.html` | 21 | 0 | 0 | HI! Desmond | ISO×8 | ✓ |
| `feargauge.html` | 20 | 2 | 0 | HI! Desmond | ISO×11 | ✓ |
| `finish.html` | 19 | 2 | 0 | HI! Desmond | ISO×8 | ✓ |
| `gto.html` | 27 | 8 | 0 | HI! Desmond | ISO×8 | ✓ |
| `hermesdir.html` | 21 | 2 | 0 | HI! Desmond | ISO×8 | ✓ |
| `jeffsun.html` | 20 | 1 | 0 | HI! Desmond | ISO×8/MD×1 | ✓ |
| `leadermap.html` | 500 | 12 | 0 | HI! Desmond | ISO×58 | ✓ |
| `levelup.html` | 19 | 0 | 0 | HI! Desmond | ISO×8/MD×1 | ✓ |
| `logbook.html` | 166 | 1 | 0 | HI! Desmond | ISO×248/MD×58 | ✓ |
| `margin.html` | 50 | 3 | 0 | HI! Desmond | ISO×24 | ✓ |
| `market-top.html` | 136 | 3 | 0 | 美股見頂未？用我們自己的數據核對 | ISO×1 | ✓ |
| `martinluk.html` | 19 | 0 | 0 | HI! Desmond | ISO×8 | ✓ |
| `mb_top250.html` | 41 | 5 | 0 | HI! Desmond | ISO×14 | ✓ |
| `mm.html` | 48 | 1 | 0 | HI! Desmond | ISO×8 | ✓ |
| `mmmodel.html` | 125 | 3 | 0 | HI! Desmond | ISO×14/MD×2 | ✓ |
| `modelbook.html` | 72 | 11 | 0 | HI! Desmond | ISO×36/MD×4 | ✓ |
| `ndx.html` | 57 | 1 | 0 | HI! Desmond | ISO×8 | ✓ |
| `ntmflow.html` | 20 | 2 | 0 | HI! Desmond | ISO×19 | ✓ |
| `optledger.html` | 24 | 1 | 0 | HI! Desmond | ISO×19/MD×2 | ✓ |
| `positioning.html` | 24 | 1 | 0 | HI! Desmond | ISO×9 | ✓ |
| `process.html` | 42 | 5 | 0 | HI! Desmond | ISO×16/MD×2 | ✓ |
| `putcall.html` | 203 | 2 | 0 | HI! Desmond | ISO×22 | ✓ |
| `qqqstruct.html` | 221 | 0 | 0 | HI! Desmond | ISO×1020/MD×14 | ✓ |
| `regime.html` | 22 | 2 | 0 | HI! Desmond | ISO×8 | ✓ |
| `regime_mri.html` | 32 | 2 | 0 | HI! Desmond | ISO×11/MD×2 | ✓ |
| `review.html` | 17 | 0 | 0 | HI! Desmond | ISO×8 | ✓ |
| `review2.html` | 21 | 2 | 0 | HI! Desmond | ISO×8 | ✓ |
| `rsbeforeprice.html` | 31 | 1 | 0 | HI! Desmond | ISO×9/MD×1 | ✓ |
| `rsboard.html` | 300 | 4 | 0 | HI! Desmond | ISO×16 | ✓ |
| `rsscan.html` | 110 | 2 | 0 | HI! Desmond | ISO×25 | ✓ |
| `rsscan_2026-10-11.html` | 147 | 2 | 0 | HI! Desmond | ISO×21 | ✓ |
| `rsscan_2026-10-21.html` | 125 | 2 | 0 | HI! Desmond | ISO×22 | ✓ |
| `rsscan_2026-10-22.html` | 148 | 2 | 0 | HI! Desmond | ISO×23 | ✓ |
| `rsscan_2026-10-23.html` | 120 | 2 | 0 | HI! Desmond | ISO×24 | ✓ |
| `rsscan_2026-10-26.html` | 139 | 2 | 0 | HI! Desmond | ISO×25 | ✓ |
| `rsscan_2026-10-27.html` | 132 | 2 | 0 | HI! Desmond | ISO×25 | ✓ |
| `rsscan_2026-10-28.html` | 140 | 2 | 0 | HI! Desmond | ISO×25 | ✓ |
| `rsscan_2026-10-29.html` | 139 | 2 | 0 | HI! Desmond | ISO×25 | ✓ |
| `rsscan_2026-10-30.html` | 136 | 2 | 0 | HI! Desmond | ISO×25 | ✓ |
| `rsscan_2026-11-02.html` | 124 | 2 | 0 | HI! Desmond | ISO×25 | ✓ |
| `rsscan_2026-11-03.html` | 122 | 2 | 0 | HI! Desmond | ISO×25 | ✓ |
| `rsscan_2026-11-04.html` | 121 | 2 | 0 | HI! Desmond | ISO×25 | ✓ |
| `rsscan_2026-11-05.html` | 124 | 2 | 0 | HI! Desmond | ISO×25 | ✓ |
| `rsscan_2026-11-06.html` | 110 | 2 | 0 | HI! Desmond | ISO×25 | ✓ |
| `sectorrot.html` | 51 | 2 | 0 | HI! Desmond | ISO×9 | ✓ |
| `sectors.html` | 77 | 2 | 0 | HI! Desmond | ISO×11 | ✓ |
| `setupfactory.html` | 38 | 2 | 0 | HI! Desmond | ISO×19 | ✓ |
| `setups.html` | 29 | 1 | 0 | HI! Desmond | ISO×8 | ✓ |
| `sysmap.html` | 64 | 8 | 0 | HI! Desmond | ISO×46/MD×9 | ✓ |
| `thinkinr.html` | 124 | 3 | 0 | HI! Desmond | ISO×2683 | ✓ |
| `tightscan.html` | 63 | 1 | 0 | HI! Desmond | ISO×9 | ✓ |
| `topwatch.html` | 21 | 2 | 0 | HI! Desmond | ISO×8 | ✓ |
| `vantharp.html` | 23 | 0 | 0 | HI! Desmond | ISO×10 | ✓ |