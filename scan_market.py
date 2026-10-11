#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_market.py — 全市場掃描（NEL 逆向工程之後，用 Desmond 自己嘅來源重做）

NEL 原文（i-manage-risk/NEL README）嘅機械部分：
  * 30 日平均成交額 > $30M
  * 14 期 ADR% > 4%
  * 10 日平均成交量 > 350K 股
  * 行業唔可以有 "Biotech"
  * 取 1M／3M／6M／1Y 表現各自前 5% → 四個組合成一個池，去重
  * 剔走距離 50SMA 超過 4× ATR% 延伸嘅
  → 得出 NEL（Non-Extended Leaders）
  T-NEL（Tight）＝ NEL 再加：企喺 9EMA 上、5 日高低範圍 ≤2.5 ATR、今日波幅 < 前一日 ATR

⚠ 同 NEL 唔同嘅地方（唔准當一樣）：
  1. NEL 用 TradingView 網頁版手動/自動匯出 CSV；我哋用 `tradingview_screener`
     Python 套件直接打同一個 screener API。**來源同一個，但欄位名要自己對**。
  2. `average_dollar_volume_30d` 喺 API 度係空值 → 我哋自己計
     `成交額 = close × 10 日平均成交量`。所以門檻等效但唔係同一個欄位。
  3. `ADRP`／`ATRP` 直接用 API 出嘅值（呢兩個真係有數）。
  4. 延伸倍數公式跟 NEL 原文：`(price − SMA50) / (SMA50 × ATR%)`。
  5. 我哋唔做 T-NEL 嘅 coil（要 OHLC 歷史 + yfinance），第一版只做 NEL。
     → 標住 "未做"，唔准當做咗。

輸出：`data/market_scan.json`
"""
import argparse
import datetime
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, r"C:\Users\rain0\trading-os")

# ── NEL 原文門檻（唔准改，改就唔係 NEL）────────────────────────────
MIN_DOLLAR_VOL = 30_000_000
MIN_ADR = 4.0
MIN_AVG_VOL = 350_000
EXCLUDE_INDUSTRY = ("biotech",)
TOP_FRAC = 0.05
MAX_EXTENSION = 4.0

FIELDS = ["name", "close", "industry", "sector", "market_cap_basic",
          "average_volume_10d_calc", "Perf.W", "Perf.1M", "Perf.3M", "Perf.6M",
          "Perf.Y", "SMA50", "ADRP", "ATRP", "price_52_week_high"]
PERF_KEYS = [("1m", "Perf.1M"), ("3m", "Perf.3M"), ("6m", "Perf.6M"), ("1y", "Perf.Y")]


def log(*a):
    print(*a, flush=True)


def num(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def scan():
    from tradingview_screener import Query, col
    n, df = (Query().set_markets("america")
             .select(*FIELDS)
             .where(col("type") == "stock",
                    col("exchange").isin(["NASDAQ", "NYSE", "AMEX"]),
                    col("close") > 3,
                    col("ADRP") > 1.0,
                    col("average_volume_10d_calc") > 100_000)
             .order_by("market_cap_basic", ascending=False)
             .limit(20000)).get_scanner_data()
    log(f"TradingView 回 {n} 行")
    return df


def build(df):
    rows = []
    for r in df.to_dict("records"):
        tk = str(r.get("name") or "").strip().upper()
        if not tk:
            continue
        close = num(r.get("close"))
        adv = num(r.get("average_volume_10d_calc"))
        adr = num(r.get("ADRP"))
        atrp = num(r.get("ATRP"))
        sma50 = num(r.get("SMA50"))
        ind = str(r.get("industry") or "未分類")
        if not close or not adv or not adr or not atrp or not sma50:
            continue
        dvol = close * adv
        ext = (close - sma50) / (sma50 * atrp / 100.0) if atrp > 0 else None
        perf = {k: num(r.get(f)) for k, f in PERF_KEYS}
        perf["1w"] = num(r.get("Perf.W"))
        rows.append({
            "symbol": tk, "close": round(close, 2), "industry": ind,
            "sector": str(r.get("sector") or ""), "adr": round(adr, 2),
            "atrp": round(atrp, 2), "adv": round(adv, 0), "dvol": round(dvol, 0),
            "mcap": num(r.get("market_cap_basic")),
            "extension": round(ext, 2) if ext is not None else None,
            "perf": {k: (round(v, 1) if v is not None else None) for k, v in perf.items()},
            "off52w": (round((close / float(r["price_52_week_high"]) - 1) * 100, 1)
                       if num(r.get("price_52_week_high")) else None),
        })

    # 硬閘（同 NEL 一樣）
    uni = [r for r in rows
           if r["dvol"] > MIN_DOLLAR_VOL
           and r["adr"] > MIN_ADR
           and r["adv"] > MIN_AVG_VOL
           and not any(x in r["industry"].lower() for x in EXCLUDE_INDUSTRY)]
    log(f"流動性／ADR／成交量閘後：{len(uni)} 隻（原始 {len(rows)}）")

    # 四個窗口各取前 5% → 合併去重
    picked = {}
    for key, _ in PERF_KEYS:
        pool = [r for r in uni if r["perf"].get(key) is not None]
        pool.sort(key=lambda r: -r["perf"][key])
        cut = max(1, int(len(pool) * TOP_FRAC))
        for r in pool[:cut]:
            picked.setdefault(r["symbol"], r)
            picked[r["symbol"]].setdefault("in", []).append(key)
    log(f"四個窗口前 5% 合併：{len(picked)} 隻")

    nel = [r for r in picked.values()
           if r["extension"] is not None and r["extension"] <= MAX_EXTENSION]
    for r in picked.values():
        r.setdefault("in", [])
    return uni, list(picked.values()), nel


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", default=None, help="用已有 JSON，唔上網")
    a = ap.parse_args(argv if argv is not None else sys.argv[1:])
    os.makedirs(DATA, exist_ok=True)
    today = datetime.date.today().isoformat()

    if a.offline:
        with io.open(a.offline, encoding="utf-8") as f:
            payload = json.load(f)
    else:
        df = scan()
        uni, momentum, nel = build(df)
        # 1 週最強（只限已過流動性閘）
        wk = sorted([r for r in uni if r["perf"].get("1w") is not None],
                    key=lambda r: -r["perf"]["1w"])
        payload = {
            "generated": datetime.datetime.now().isoformat(timespec="seconds"),
            "source": "tradingview_screener (america / NASDAQ-NYSE-AMEX / type=stock)",
            "thresholds": {"min_dollar_vol": MIN_DOLLAR_VOL, "min_adr": MIN_ADR,
                           "min_avg_vol": MIN_AVG_VOL, "top_frac": TOP_FRAC,
                           "max_extension": MAX_EXTENSION,
                           "exclude_industry": list(EXCLUDE_INDUSTRY)},
            "counts": {"raw": len(uni), "momentum": len(momentum), "nel": len(nel)},
            "universe": uni,
            "momentum": momentum,
            "nel": nel,
            "week": wk[:60],
        }

    p = os.path.join(DATA, f"market_scan_{today}.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    latest = os.path.join(DATA, "market_scan.json")
    with io.open(latest, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    log(f"✓ {p}")
    log(f"  流動池 {payload['counts']['raw']}｜動能池 {payload['counts']['momentum']}"
        f"｜NEL {payload['counts']['nel']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
