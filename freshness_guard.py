# -*- coding: utf-8 -*-
"""freshness_guard.py — 檢查關鍵 JSON 嘅資料日期係唔係最新（沉默合約）

為咩要：2026-10-26 → 28 連續三日出現同一個 bug ——
  group_rs / beachball / fear_gauge 嘅價格快取「有檔就用」，永遠唔刷新，
  頁面照樣寫「今日」，但數字係幾日前。呢個就係「零假更新」嘅來源。

判準
  最後一個美股交易日（週一至五，粗略不計假期）＝ expected
  檔案內 as_of / date < expected → STALE，出聲
  全部新鮮 → stdout 完全空白

用法：python freshness_guard.py
"""
from __future__ import annotations

import io
import json
import os
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = r"C:/Users/rain0/trading-os/output"

# (顯示名, 路徑, 取日期嘅 key 順序)
TARGETS = (
    ("beachball", os.path.join(LIVE, "beachball.json"), ("as_of", "date")),
    ("group_rs", None, ("as_of", "date")),          # glob group_rs_*.json
    ("fear_gauge", os.path.join(HERE, "output", "fear_gauge.json"), ("date",)),
    ("tight_scan", os.path.join(HERE, "output", "tight_scan.json"), ("data_asof", "date")),
    ("rotation", r"C:/Users/rain0/trading-os-lab/output/rotation_latest.json", ("date",)),
)


def last_us_session(now=None):
    """粗略：今日 ET 16:00 前 → 前一個工作日；否則今日（週末回退）。"""
    now = now or datetime.now()
    et = now - timedelta(hours=12)          # HKT→ET 約 -12/+12，夠用於判斷日期
    d = et.date()
    if (now.hour, now.minute) < (4, 0):     # 美股未收市（HKT 04:00 = ET 16:00）
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _glob_group_rs():
    import glob
    fs = sorted(glob.glob(os.path.join(LIVE, "group_rs_20*.json")))
    return fs[-1] if fs else None


def main():
    exp = last_us_session()
    stale = []
    missing = []
    for name, path, keys in TARGETS:
        p = _glob_group_rs() if path is None else path
        if not p or not os.path.exists(p):
            missing.append(name)
            continue
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except (OSError, ValueError):
            missing.append(name)
            continue
        val = None
        for k in keys:
            if d.get(k):
                val = str(d[k])[:10]
                break
        if not val:
            missing.append(name)
            continue
        if val < exp.isoformat():
            stale.append((name, val, os.path.basename(p)))

    if not stale and not missing:
        return 0
    print(f"⏳ 資料新鮮度｜應為 {exp}")
    for name, val, f in stale:
        print(f"STALE  {name:12s} {val}（{f}）")
    for name in missing:
        print(f"MISSING {name}")
    print("→ 對應腳本要加／收緊快取時效，唔可以用「有檔就用」")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
