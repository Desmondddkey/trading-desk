# -*- coding: utf-8 -*-
"""fill_industry.py — 補齊每隻股嘅行業／板塊（解決「未分類」）

為咩要做（Desmond 2026-10-25）：
  「Stock 入面仲有未分類，咁我點知邊 D 係 RS 版塊、有冇 group move？」

來源優先次序
  1. data/market_scan.json（TradingView 分類，最細緻：industry）
  2. output/model_book/ticker_meta.json（之前 Top250 已抓，sector）
  3. yfinance .info（補未有名嘅，慢但一次性，結果寫入快取）

輸出：data/ticker_industry.json
  {"AAPL": {"industry": "Computer Manufacturing", "sector": "Technology", "src": "scan"}}

用法：python fill_industry.py [--limit N]
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "ticker_industry.json")
SCAN = os.path.join(HERE, "data", "market_scan.json")
META = r"C:/Users/rain0/trading-os/output/model_book/ticker_meta.json"
L2 = r"C:/Users/rain0/trading-os/output/layer2_*.json"
RS = r"C:/Users/rain0/trading-os/output/rs_select_*.json"


def log(m):
    print(m, file=sys.stderr)


def load(p, default):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)

    m = load(OUT, {})
    added = 0

    # 1) market_scan
    sc = load(SCAN, {})
    for k in ("nel", "momentum", "universe"):
        for r in (sc.get(k) or []):
            t = (r.get("symbol") or r.get("ticker") or "").upper()
            ind = r.get("industry") or r.get("sector")
            if t and ind and not (m.get(t, {}).get("industry")):
                m[t] = {"industry": ind, "sector": r.get("sector") or "",
                        "src": "scan"}
                added += 1

    # 2) Top250 meta
    meta = load(META, {})
    for t, v in meta.items():
        t = str(t).upper()
        if v.get("sector") and not (m.get(t, {}).get("industry")):
            m[t] = {"industry": v.get("sector"), "sector": v.get("sector"),
                    "src": "meta"}
            added += 1

    # 3) 收集所有需要嘅 ticker（L2 + rs_select）
    need = set()
    for pat in (L2, RS):
        fs = sorted(glob.glob(pat))
        if not fs:
            continue
        d = load(fs[-1], {})
        rows = d.get("rows") or (d.get("focus_list") or []) + (d.get("stalk_list") or [])
        for r in rows:
            t = (r.get("ticker") or "").upper()
            if t:
                need.add(t)
    todo = sorted(t for t in need if not m.get(t))
    if a.limit:
        todo = todo[:a.limit]
    log(f"已識 {len(m)}｜需要補 {len(need)}｜今次抓 {len(todo)}")

    if todo:
        try:
            import yfinance as yf
        except ImportError:
            log("⚠ 冇 yfinance，跳過")
        else:
            for i, t in enumerate(todo, 1):
                try:
                    info = yf.Ticker(t).info or {}
                except Exception:                              # noqa: BLE001
                    continue
                sec = info.get("sector") or ""
                ind = info.get("industry") or sec
                if ind:
                    m[t] = {"industry": ind, "sector": sec, "src": "yf"}
                    added += 1
                if i % 25 == 0:
                    log(f"  …{i}/{len(todo)}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(m, io.open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    cov = sum(1 for t in need if m.get(t))
    log(f"✓ 寫入 {OUT}｜新增 {added}｜覆蓋 {cov}/{len(need)}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
