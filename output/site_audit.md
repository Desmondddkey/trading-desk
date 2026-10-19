# 網站漏洞審計

頁數 **32**｜總大小 **3.7 MB**

## 問題總表

### NO_DATE_BADGE（3 頁）
- `alerts.html` — 「ALERT 所有警報分類」附近冇 ISO 日期
- `jobboard.html` — 「ALERT 所有警報分類」附近冇 ISO 日期
- `sectors.html` — 「🏭 Sectors · 行業輪動 同 機會 頁第」附近冇 ISO 日期

### NUM_FORMAT（3 頁）
- `jobboard.html` — 5 種小數位：.1×178,.2×749,.3×56,.4×17,.6×2
- `leaders.html` — 8 種小數位：.1×6713,.2×2325,.3×192,.4×4,.5×20,.6×89,.7×76,.8×8
- `week.html` — 7 種小數位：.1×6056,.2×2255,.4×4,.5×20,.6×89,.7×76,.8×8

### DATE_FORMAT（1 頁）
- `jobboard.html` — 混用 ISO×772/MD×64/US×1

## 逐頁明細

| 頁 | KB | 表 | 空表 | h1 | 日期格式 | 問題 |
|---|---|---|---|---|---|---|
| `jobboard.html` | 193 | 1 | 0 | HI! Desmond | ISO×772/MD×64/US×1 | ⚠️ 3 |
| `alerts.html` | 84 | 1 | 0 | HI! Desmond | ISO×535 | ⚠️ 1 |
| `leaders.html` | 930 | 3 | 0 | HI! Desmond | ISO×13 | ⚠️ 1 |
| `sectors.html` | 39 | 1 | 0 | HI! Desmond | ISO×12 | ⚠️ 1 |
| `week.html` | 242 | 1 | 0 | HI! Desmond | ISO×12 | ⚠️ 1 |
| `bee50.html` | 50 | 0 | 0 | HI! Desmond | ISO×12/MD×1 | ✓ |
| `breadth.html` | 37 | 1 | 0 | HI! Desmond | ISO×13 | ✓ |
| `briefing.html` | 62 | 4 | 0 | HI! Desmond | ISO×17 | ✓ |
| `calculator.html` | 46 | 0 | 0 | HI! Desmond | ISO×12 | ✓ |
| `cm.html` | 95 | 2 | 0 | HI! Desmond | ISO×13 | ✓ |
| `cycle.html` | 41 | 0 | 0 | HI! Desmond | ISO×13 | ✓ |
| `dailyscan.html` | 67 | 1 | 0 | HI! Desmond | ISO×14 | ✓ |
| `datahealth.html` | 40 | 1 | 0 | HI! Desmond | ISO×15/MD×7 | ✓ |
| `desk.html` | 633 | 14 | 0 | 📊 機會 · OPPORTUNITY D | ISO×96 | ✓ |
| `earnings.html` | 190 | 0 | 0 | HI! Desmond | ISO×23 | ✓ |
| `external.html` | 39 | 0 | 0 | HI! Desmond | ISO×12 | ✓ |
| `index.html` | 62 | 4 | 0 | HI! Desmond | ISO×17 | ✓ |
| `jeffsun.html` | 43 | 1 | 0 | HI! Desmond | ISO×12/MD×1 | ✓ |
| `leadermap.html` | 40 | 2 | 0 | HI! Desmond | ISO×25 | ✓ |
| `livefeeds.html` | 41 | 0 | 0 | HI! Desmond | ISO×15 | ✓ |
| `logbook.html` | 145 | 1 | 0 | HI! Desmond | ISO×187/MD×42 | ✓ |
| `method.html` | 61 | 1 | 0 | HI! Desmond | ISO×12 | ✓ |
| `mm.html` | 65 | 1 | 0 | HI! Desmond | ISO×12 | ✓ |
| `ndx.html` | 76 | 1 | 0 | HI! Desmond | ISO×12 | ✓ |
| `positioning.html` | 42 | 1 | 0 | HI! Desmond | ISO×13 | ✓ |
| `regime.html` | 40 | 2 | 0 | HI! Desmond | ISO×12 | ✓ |
| `regime_mri.html` | 43 | 1 | 0 | HI! Desmond | ISO×13 | ✓ |
| `review.html` | 36 | 0 | 0 | HI! Desmond | ISO×12 | ✓ |
| `rocketstock.html` | 50 | 3 | 0 | HI! Desmond | ISO×14 | ✓ |
| `rsboard.html` | 105 | 3 | 0 | HI! Desmond | ISO×13 | ✓ |
| `setups.html` | 53 | 1 | 0 | HI! Desmond | ISO×12 | ✓ |
| `themes.html` | 36 | 1 | 0 | HI! Desmond | ISO×12 | ✓ |