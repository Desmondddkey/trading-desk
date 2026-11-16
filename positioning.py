# -*- coding: utf-8 -*-
"""positioning.py — CFTC COT 大戶倉位（同 NEL 同源，唔抄佢個檔）。

來源：CFTC 公開 Socrata API
  https://publicreporting.cftc.gov/resource/6dca-aqww.json
  dataset = Futures Only（legacy），非商業＝大戶、商業＝生產商／貿易商、非報告＝散戶

輸出 data/positioning.json：
  markets[{code,name,etf,group,date,oi,participants{large,commercials,small}{long,short,net,netPctOI,idx1y,idx3y}}]
  crowded = 大戶淨倉 5 年百分位 ≤10（Crowded Short）或 ≥90（Crowded Long）

用法： python -X utf8 positioning.py
"""
from __future__ import annotations

import io
import json
import os
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "positioning.json")
BASE = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"

MARKETS = [
    ("13874A", "S&P 500", "SPY", "Equity index"),
    ("209742", "Nasdaq 100", "QQQ", "Equity index"),
    ("239742", "Russell 2000", "IWM", "Equity index"),
    ("088691", "Gold", "GLD", "Metals"),
    ("084691", "Silver", "SLV", "Metals"),
    ("085692", "Copper", "CPER", "Metals"),
    ("067651", "WTI crude oil", "USO", "Energy"),
    ("023651", "Natural gas", "UNG", "Energy"),
    ("133741", "Bitcoin", "IBIT", "Crypto"),
    ("146021", "Ether", "ETHA", "Crypto"),
]

LOOKBACK_WEEKS = 260          # 5 年
COLS = ("comm_positions_long_all,comm_positions_short_all,"
        "noncomm_positions_long_all,noncomm_positions_short_all,"
        "nonrept_positions_long_all,nonrept_positions_short_all,"
        "open_interest_all,report_date_as_yyyy_mm_dd,contract_market_name")


def _get(code, limit=LOOKBACK_WEEKS + 10):
    q = urllib.parse.urlencode({
        "$select": COLS,
        "$where": f"cftc_contract_market_code='{code}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": limit,
    })
    url = f"{BASE}?{q}"
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, timeout=45, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def _i(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _pct_rank(series, v):
    """0-100 percentile of v within series."""
    xs = [x for x in series if x is not None]
    if not xs or v is None:
        return None
    n = sum(1 for x in xs if x <= v)
    return round(100.0 * n / len(xs), 1)


def _block(rows, lk, sk):
    """rows = list of raw dicts oldest→newest; lk/sk = long/short column names."""
    hist = []
    for r in rows:
        lo, sh = _i(r.get(lk)), _i(r.get(sk))
        if lo is None or sh is None:
            continue
        hist.append((lo, sh, lo - sh))
    if not hist:
        return None
    nets = [h[2] for h in hist]
    net = nets[-1]
    oi = _i(rows[-1].get("open_interest_all"))
    return {
        "long": hist[-1][0], "short": hist[-1][1], "net": net,
        "netPctOI": (round(100.0 * net / oi, 2) if oi else None),
        "idx1y": _pct_rank(nets[-52:], net),
        "idx3y": _pct_rank(nets[-156:], net),
        "idx5y": _pct_rank(nets, net),
    }


def build_market(code, name, etf, group):
    rows = _get(code)
    if not rows:
        return None
    rows = list(reversed(rows))                    # oldest → newest
    last = rows[-1]
    large = _block(rows, "noncomm_positions_long_all", "noncomm_positions_short_all")
    comm = _block(rows, "comm_positions_long_all", "comm_positions_short_all")
    small = _block(rows, "nonrept_positions_long_all", "nonrept_positions_short_all")
    if not (large and comm):
        return None
    i5 = large.get("idx5y")
    if i5 is None:
        crowd = "—"
    elif i5 <= 10:
        crowd = "Crowded Short"
    elif i5 >= 90:
        crowd = "Crowded Long"
    else:
        crowd = "中性"
    return {
        "code": code, "name": name, "etf": etf, "group": group,
        "contract": last.get("contract_market_name"),
        "date": (last.get("report_date_as_yyyy_mm_dd") or "")[:10],
        "oi": _i(last.get("open_interest_all")),
        "participants": {"large": large, "commercials": comm, "small": small},
        "crowded": crowd,
        "weeks": len(rows),
    }


def main():
    out, fail = [], []
    for code, name, etf, group in MARKETS:
        try:
            m = build_market(code, name, etf, group)
            (out.append(m) if m else fail.append(name + "(empty)"))
        except Exception as e:                                   # noqa: BLE001
            fail.append(f"{name}:{type(e).__name__}")
    if not out:
        print("DATA_UNAVAILABLE — CFTC 冇回任何市場")
        return 1
    payload = {
        "source": BASE,
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lookbackWeeks": LOOKBACK_WEEKS,
        "markets": out,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"✓ {len(out)} 市場｜{out[0]['date']}｜{OUT}")
    for m in out:
        lg = m["participants"]["large"]
        print(f"   {m['etf']:<5}{m['name']:<15}{m['crowded']:<14}"
              f"large net {lg['net']:>9} idx5y {lg.get('idx5y')}")
    if fail:
        print("⚠ 失敗：" + "、".join(fail))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
