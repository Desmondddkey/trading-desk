# -*- coding: utf-8 -*-
"""screener_refresh.py — Stock Screener 每日刷新（盤前＋盤後各一次）。

順序（缺一即數字唔一致）：
  1. scan_market.py       TV 掃描 → data/market_scan.json（universe＋價／ADR／RVOL）
  2. screener_cache.py    重算 744 隻所有欄位（OHLC 增量補到 SPY 最後一根）
  3. screener_extra.py    公司名／止蝕／股數／tags／Stock Wall／歷史快照
  4. avwap52.py           52 週高 AVWAP（The Setup Factory）

用法： python -X utf8 screener_refresh.py [--skip-scan]
"""
from __future__ import annotations

import os
import subprocess
import sys
import io

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"C:\Users\rain0\trading-os\.venv\Scripts\python.exe"


def _env():
    e = {k: v for k, v in os.environ.items() if not k.upper().startswith("PY")}
    e["PYTHONNOUSERSITE"] = "1"
    e["PYTHONPATH"] = ""
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def run(name, timeout):
    p = os.path.join(HERE, name)
    r = subprocess.run([PY, "-X", "utf8", "-W", "ignore", p],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, env=_env(), cwd=HERE)
    tail = (r.stdout or "").strip().splitlines()[-2:]
    for line in tail:
        print(f"   {line}")
    if r.returncode != 0:
        print(f"✗ {name} rc={r.returncode}\n{(r.stderr or '')[-800:]}")
        return False
    return True


def drop_spy():
    """刪掉快取嘅 _SPY，逼 screener_cache 重抓最新 SPY，再用佢做「最後交易日」基準。
    否則快取 SPY 自己都停喺舊日期 → 冇任何 ticker 被判定 stale → 永遠唔更新。"""
    import pandas as pd
    pkl = os.path.join(HERE, "data", "screener_ohlc.pkl")
    if not os.path.exists(pkl):
        return
    try:
        c = pd.read_pickle(pkl)
        if isinstance(c, dict) and "_SPY" in c:
            c.pop("_SPY", None)
            pd.to_pickle(c, pkl)
            print("   ↺ 已清 _SPY（下次會重抓最新交易日）")
    except Exception as e:                                       # noqa: BLE001
        print(f"   ⚠ 清 _SPY 失敗：{type(e).__name__}: {e}")


def main(argv=None):
    argv = argv or sys.argv[1:]
    steps = [("scan_market.py", 240), ("screener_cache.py", 1800),
             ("screener_extra.py", 900), ("avwap52.py", 600), ("headwinds.py", 300)]
    if "--skip-scan" in argv:
        steps = steps[1:]
    print(f"🔄 Screener 刷新 {len(steps)} 步")
    drop_spy()
    for name, to in steps:
        print(f"▶ {name}")
        if not run(name, to):
            return 1
    print("✓ Screener 刷新完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
