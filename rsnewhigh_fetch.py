# -*- coding: utf-8 -*-
"""rsnewhigh_fetch.py — 抓 Chinar Amrutkar 嘅 RS 新高名單（10 個交易日內）。

來源：https://chinar-amrutkar.github.io/market-leaders/outputs/rs_new_high_details.csv
輸出：data/rs_new_high.json  {as_of, source, n, rows:[...]}
只保留顯示用欄位，數值原樣（唔自己再計 RS，避免同來源唔一致）。
"""
from __future__ import annotations

import csv
import io
import json
import os
import urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(HERE, "data", "rs_new_high.json")
URL = ("https://chinar-amrutkar.github.io/market-leaders/"
       "outputs/rs_new_high_details.csv")
UA = {"User-Agent": "Mozilla/5.0"}

KEEP = ["symbol", "description", "sector", "breakout_date", "sessions_ago",
        "close", "adr_pct", "average_dollar_volume_30d", "breakout_pct",
        "signal_3m", "signal_6m", "signal_12m",
        "weekly_signal", "weekly_signal_age_weeks", "weekly_price_vs_high_pct"]


def num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def main():
    req = urllib.request.Request(URL, headers=UA)
    raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    rows = []
    for r in csv.DictReader(io.StringIO(raw)):
        o = {"t": (r.get("symbol") or "").strip().upper()}
        if not o["t"]:
            continue
        o["name"] = (r.get("description") or "").strip()
        o["sector"] = (r.get("sector") or "").strip()
        o["date"] = (r.get("breakout_date") or "").strip()
        o["ago"] = int(num(r.get("sessions_ago")) or 0)
        o["close"] = num(r.get("close"))
        o["adr"] = round(num(r.get("adr_pct")) or 0, 2)
        o["dvol_m"] = round((num(r.get("average_dollar_volume_30d")) or 0) / 1e6, 1)
        o["bp"] = round(num(r.get("breakout_pct")) or 0, 2)
        o["s3"] = (r.get("signal_3m") or "").lower() == "true"
        o["s6"] = (r.get("signal_6m") or "").lower() == "true"
        o["s12"] = (r.get("signal_12m") or "").lower() == "true"
        o["wk"] = (r.get("weekly_signal") or "").lower() == "true"
        o["wk_age"] = num(r.get("weekly_signal_age_weeks"))
        o["wk_px"] = num(r.get("weekly_price_vs_high_pct"))
        rows.append(o)
    rows.sort(key=lambda x: (x["ago"], -(x["bp"] or 0)))
    # ★ 來源嘅 sessions_ago 同 breakout_date 有矛盾（有啲 ago=0 但日期係 7 月）。
    #   信日期：用最大日期做基準，計工作日差，並以佢排序，避免「舊突破排最前」。
    from datetime import date as _date
    def _d(s):
        try:
            y, m, dd = s.split("-")
            return _date(int(y), int(m), int(dd))
        except (ValueError, AttributeError):
            return None
    dates = [d for d in (_d(r.get("date", "")) for r in rows) if d]
    ref = max(dates) if dates else None
    if ref:
        for r in rows:
            d = _d(r.get("date", ""))
            if not d:
                r["dago"] = None
                continue
            n, cur = 0, d
            while cur < ref:
                cur = cur.fromordinal(cur.toordinal() + 1)
                if cur.weekday() < 5:
                    n += 1
            r["dago"] = n
        rows.sort(key=lambda x: (x["dago"] is None, x["dago"] if x["dago"] is not None else 9e9,
                                 -(x["bp"] or 0)))
    out = {"as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "source": URL, "n": len(rows), "rows": rows}
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with io.open(DST, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"✓ rs_new_high.json｜{len(rows)} 隻")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
