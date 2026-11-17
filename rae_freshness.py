# -*- coding: utf-8 -*-
"""rae_freshness.py — 守護規則：所有 RAE 出嚟嘅模型，必須自動更新。

規則（Desmond 2026-11-17）：「RAE 既野要自動更新，以後所有功能都要咁做。」

做法：
  1. 掃 data/*.json（跳過歷史快照／dated 副本）
  2. 搵出邊個 .py 寫佢（模組內出現檔名 + json.dump/open(...,"w")）
  3. 檢查該 .py 有冇列喺 screener_refresh.py 嘅 STEPS
  4. 檢查檔案年齡（交易日計）≤ MAX_AGE
輸出：每個 data 檔 → 生產者｜已排程？｜年齡
任何一項 fail → rc=1（cron 會出聲）。
"""
from __future__ import annotations

import glob
import io
import os
import re
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CHAIN = os.path.join(HERE, "screener_refresh.py")
MAX_AGE_DAYS = 3          # 跨週末：星期五數據星期一仍然 OK

ON_DEMAND = {
    "data/peg_quarter.json": "每季建立一次（設計如此）",
    "data/correction_risk_state.json": "狀態檔（由 correction_risk.py 寫）",
    "data/universe_wide.json": "lab 產物，非網站資料",
}

SKIP = re.compile(r"(_\d{4}-\d{2}-\d{2}\.json$|/hist/|screener_hist|market_scan_\d)")


def chain_steps():
    try:
        src = io.open(CHAIN, encoding="utf-8").read()
    except OSError:
        return set()
    return set(re.findall(r"[\(\[]\s*[\"']([a-z0-9_]+\.py)[\"']\s*,\s*\d+", src))


def producers(fname):
    out = []
    for py in glob.glob(os.path.join(HERE, "*.py")):
        if os.path.basename(py) in ("rae_freshness.py",):
            continue
        try:
            src = io.open(py, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        if fname in src and re.search(r"json\.dump|open\([^)]*\"w\"", src):
            out.append(os.path.basename(py))
    return out


def main():
    steps = chain_steps()
    today = date.today()
    rows, bad = [], []
    for f in sorted(glob.glob(os.path.join(DATA, "*.json"))):
        rel = f.replace(HERE + os.sep, "").replace("\\", "/")
        if SKIP.search(rel):
            continue
        if rel in ON_DEMAND:
            rows.append((rel, "on-demand", "—", 0, True))
            continue
        age = (today - datetime.fromtimestamp(os.path.getmtime(f)).date()).days
        prods = producers(os.path.relpath(f, HERE).replace("\\", "/"))
        sched = any(p in steps for p in prods)
        ok = bool(prods) and sched and age <= MAX_AGE_DAYS
        rows.append((rel, ",".join(prods) or "—", "✓" if sched else "✗", age, ok))
        if not ok:
            bad.append((rel, prods, sched, age))

    print(f"{'檔案':<34}{'生產者':<26}{'排程':<5}{'年齡(日)':<8}")
    for rel, p, s, age, ok in rows:
        print(f"{rel:<34}{p:<26}{s:<5}{age:<8}{'' if ok else '⚠'}")
    if bad:
        print(f"\n⚠ {len(bad)} 個 data 檔未達標（規則：所有 RAE 模型必須自動更新）")
        for rel, prods, sched, age in bad:
            why = []
            if not prods:
                why.append("搵唔到生產者")
            elif not sched:
                why.append("生產者未加入 screener_refresh.py")
            if age > MAX_AGE_DAYS:
                why.append(f"已 {age} 日未更新")
            print(f"   · {rel}：{'、'.join(why)}")
        return 1
    print(f"\n✓ 全部 {len(rows)} 個 data 檔已排程且新鮮（≤{MAX_AGE_DAYS} 日）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
