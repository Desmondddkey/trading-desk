# -*- coding: utf-8 -*-
"""freshness_audit.py — 網站數據新鮮度審計（Desmond 2026-10-19）

★ 目的：Desmond 講「我見有d有更又無更新咁 所以都唔肯定今日可唔可以用呢個網頁黎check野」
   → 建一個確定性工具，逐個數據源報「最後更新幾時、差幾日、邊個 job 負責」。

★ 第一性原理：
    網站頁面嘅 mtime 冇意義（build_site.py 每次都重寫全部檔）。
    有意義嘅係【數據源本身】幾時更新過。
    所以要審數據源，唔係審 HTML。

判準（事先寫死，唔准見到數才改）：
    STALE_DAYS = 3   —— 超過 3 個日曆日 = 🟡 警告
    DEAD_DAYS  = 7   —— 超過 7 日 = ❌ 失效
    （交易日 < 日曆日，所以 3 日 ≈ 2 個交易日，合理緩衝）

用法：
    python freshness_audit.py            # 表格
    python freshness_audit.py --json     # 機讀
"""
import datetime
import io
import json
import os
import sys

STALE_DAYS = 3
DEAD_DAYS = 7

HOME = os.path.expanduser("~")
TO = os.path.join(HOME, "trading-os")
LAB = os.path.join(HOME, "trading-os-lab")
WEB = os.path.join(HOME, "trading-os-web")

# ── 數據源 → 負責 job（job 名要同 jobs.json 對得上）──
SOURCES = [
    # (路徑, 標籤, 用喺邊個頁, 更新 job, 類別)
    (f"{TO}/output/layer4_breadth.json", "市場廣度",
     "breadth / briefing", "layer4-breadth-daily", "core"),
    (f"{TO}/output/layer2_focus.json", "Focus/Stalk 掃描",
     "briefing / desk", "jeffsun-daily-scan-layer1+2", "core"),
    (f"{TO}/output/layer2a_rs_leader.json", "RS Leader 排名",
     "rsboard", "jeffsun-daily-scan-layer1+2", "core"),
    (f"{LAB}/cache/daily_2y.pkl", "日線價格快取（lab）",
     "desk ①RS Leader 位置圖 / leaders", "（冇 job 負責）", "critical"),
    (f"{LAB}/cache/rs_select_prices.pkl", "RS 選股價格快取",
     "desk ①RS Leader 位置圖", "（冇 job 負責）", "critical"),
    (f"{TO}/output/edge_audit.json", "Edge Audit",
     "review / setup-check", "usic-edge-audit-notion", "core"),
    (f"{TO}/output/theme_watch_*.json", "主題監察",
     "themes", "theme-watch-daily", "core"),
    (f"{TO}/output/weekly_watchlist_*.json", "週度觀察名單",
     "week", "weekly-watchlist-sunday-0900", "weekly"),
    (f"{TO}/edge_book/competition.json", "比賽帳戶",
     "index / desk", "competition-daily", "core"),
    (f"{TO}/output/setup_alerts_history.csv", "6-setup 警報",
     "setups / cm", "setup-alerts", "intraday"),
    (f"{TO}/output/orh_alert_history.csv", "ORH 警報",
     "cm", "jeffsun-intraday-ORH-RVOL-alert", "intraday"),
    (f"{TO}/sim_ledger/fleet", "fleet 模擬帳本",
     "fleet 曲線", "fleet-sim-daily", "core"),
    (f"{TO}/output/rotation_map*.json", "輪動圖",
     "sectors", "rotation-map-weekly", "weekly"),
    (f"{TO}/output/market_watch_latest.json", "市場觀察",
     "regime", "market-watch", "core"),
]


def _newest(pattern_or_path):
    """支援 * glob：回傳最新 match 嘅 (path, mtime)。"""
    import glob
    if "*" in pattern_or_path:
        fs = glob.glob(pattern_or_path)
        if not fs:
            return None, None
        fs.sort(key=os.path.getmtime, reverse=True)
        p = fs[0]
    else:
        p = pattern_or_path
        if not os.path.exists(p):
            return None, None
    return p, datetime.datetime.fromtimestamp(os.path.getmtime(p))


def audit():
    today = datetime.date.today()
    rows = []
    for path, label, page, job, kind in SOURCES:
        p, mt = _newest(path)
        if mt is None:
            rows.append(dict(label=label, page=page, job=job, kind=kind,
                             path=path, mtime=None, days=None, state="missing"))
            continue
        days = (today - mt.date()).days
        if days > DEAD_DAYS:
            state = "dead"
        elif days > STALE_DAYS:
            state = "stale"
        else:
            state = "ok"
        rows.append(dict(label=label, page=page, job=job, kind=kind,
                         path=p, mtime=mt.strftime("%Y-%m-%d %H:%M"),
                         days=days, state=state))
    return rows


ICON = {"ok": "✅", "stale": "🟡", "dead": "❌", "missing": "⛔"}
NAME = {"ok": "新鮮", "stale": "過期", "dead": "失效", "missing": "缺檔"}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = audit()
    if "--json" in sys.argv:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0

    bad = [r for r in rows if r["state"] in ("stale", "dead", "missing")]
    print(f"══ 數據新鮮度審計（今日 {datetime.date.today()}）══")
    print(f"   判準：>{STALE_DAYS}日=🟡過期｜>{DEAD_DAYS}日=❌失效\n")
    print(f"  {len(rows)} 個數據源｜✅ {len(rows)-len(bad)}｜問題 {len(bad)}\n")

    for r in sorted(rows, key=lambda x: (x["days"] if x["days"] is not None else 999),
                    reverse=True):
        ic = ICON[r["state"]]
        d = f"{r['days']} 日" if r["days"] is not None else "—"
        print(f"  {ic} {r['label']:<22}{d:<8}{r['state']:<8}"
              f"job={r['job']}")
        if r["state"] != "ok":
            print(f"      頁面：{r['page']}")
            print(f"      檔案：{os.path.basename(str(r['path']))}"
                  f"（{r['mtime'] or '不存在'}）")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
