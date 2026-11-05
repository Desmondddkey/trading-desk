# -*- coding: utf-8 -*-
"""putcall_fetch.py — CBOE Equity Put/Call Ratio 抓取（可中斷續跑）

歷史：CBOE 官方存檔 equitypc.csv（2006-11 → 2019-10）
之後：CBOE 每日統計頁 ?dt=YYYY-MM-DD 逐日抓（頁面內嵌 JSON：EQUITY PUT/CALL RATIO）
輸出：output/putcall_raw.csv（date,ratio），每次續跑只補缺日
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "output", "putcall_raw.csv")
ARCHIVE = os.path.join(HERE, "data", "equitypc_archive.csv")
ARCH_URL = "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/equitypc.csv"
DAY_URL = "https://www.cboe.com/us/options/market_statistics/daily/?dt={d}"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SLEEP = 0.25
WORKERS = 5


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _load_archive():
    """回傳 {YYYY-MM-DD: ratio}，缺檔就抓一次。"""
    os.makedirs(os.path.dirname(ARCHIVE), exist_ok=True)
    if not os.path.exists(ARCHIVE):
        with io.open(ARCHIVE, "w", encoding="utf-8", newline="\n") as f:
            f.write(_get(ARCH_URL))
    out = {}
    for line in io.open(ARCHIVE, encoding="utf-8", errors="replace"):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5 or not re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", parts[0]):
            continue
        try:
            d = dt.datetime.strptime(parts[0], "%m/%d/%Y").date().isoformat()
            out[d] = float(parts[4])
        except ValueError:
            continue
    return out


def _load_raw():
    if not os.path.exists(RAW):
        return {}
    out = {}
    for line in io.open(RAW, encoding="utf-8"):
        p = line.strip().split(",")
        if len(p) == 2:
            try:
                out[p[0]] = float(p[1])
            except ValueError:
                pass
    return out


def _parse_day(html):
    m = re.search(r'EQUITY PUT/CALL RATIO\\?"\s*,\s*\\?"value\\?"\s*:\s*\\?"([0-9.]+)', html)
    if not m:
        m = re.search(r"EQUITY PUT/CALL RATIO.{0,120}?([01]\.[0-9]{2})", html, flags=re.S)
    return float(m.group(1)) if m else None


def main():
    start = dt.date(2019, 10, 7)
    today = dt.date.today()
    raw = _load_raw()
    if not raw:
        raw = dict(_load_archive())
        print(f"archive {len(raw)} rows", file=sys.stderr)

    todo = []
    d = start
    while d <= today:
        if d.weekday() < 5 and d.isoformat() not in raw:
            todo.append(d)
        d += dt.timedelta(days=1)

    print(f"missing {len(todo)} days", file=sys.stderr)
    new = 0
    done = 0
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _one(day):
        for _ in range(3):
            try:
                return day, _parse_day(_get(DAY_URL.format(d=day.isoformat())))
            except Exception:                                 # noqa: BLE001
                time.sleep(1.0)
        return day, None

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(_one, d0) for d0 in todo]
        for fu in as_completed(futs):
            day, val = fu.result()
            done += 1
            if val is not None:
                raw[day.isoformat()] = val
                new += 1
            if done % 100 == 0 or done == len(todo):
                with io.open(RAW, "w", encoding="utf-8", newline="\n") as fh:
                    for k in sorted(raw):
                        fh.write(f"{k},{raw[k]}\n")
                print(f"{done}/{len(todo)} new={new} total={len(raw)}", file=sys.stderr)
            time.sleep(SLEEP / WORKERS)

    with io.open(RAW, "w", encoding="utf-8", newline="\n") as f:
        for k in sorted(raw):
            f.write(f"{k},{raw[k]}\n")
    print(json.dumps({"rows": len(raw), "added": new}), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
