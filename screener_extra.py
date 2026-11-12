# -*- coding: utf-8 -*-
"""screener_extra.py — 喺 screener_cache.py 之後跑，補齊 Stock Screener 需要嘅欄位。

做四件事，全部只讀既有產物、唔改 screener_cache.py：
  ① 公司名（TradingView description，一次 query）
  ② 風控欄位：止蝕價／止蝕類別／風險%（3% 上限，10 日低點只在更緊且 <0.60 ATR 才用）
  ③ tag：HTF、沙灘球（讀 trading-os/output/*.json）
  ④ 輸出 Stock Wall 圖表包（45 根日線，delta 編碼）＋ 最近 6 個交易日快照

輸出
  data/screener.json            原地補充欄位（唔刪任何舊欄位）
  data/wall_series.json         Stock Wall 用
  data/screener_hist/<date>.json 日期切換用

⚠ 缺失唔等於 0：冇數就唔寫該欄（前端顯示 —）。
"""
from __future__ import annotations

import bisect
import io
import json
import os
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SCREENER = os.path.join(DATA, "screener.json")
OHLC = os.path.join(DATA, "screener_ohlc.pkl")
WALL = os.path.join(DATA, "wall_series.json")
HIST = os.path.join(DATA, "screener_hist")
TO = r"C:\Users\rain0\trading-os"
HTF = os.path.join(TO, "output", "htf_flag.json")
BB = os.path.join(TO, "output", "beachball.json")

WALL_BARS = 45
HIST_DAYS = 6
MIN_BARS = 60
STOP_PCT = 0.03          # 同 daily_plan.STOP_PCT
LOD_MAX_ATR = 0.60       # 同 daily_plan.LOD_MAX_ATR


def log(*a):
    print(*a, flush=True)


def _jload(p, d):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return d


def _names(tickers):
    try:
        from tradingview_screener import Query, col
        _, df = (Query().set_markets("america")
                 .select("name", "description")
                 .where(col("type") == "stock",
                        col("exchange").isin(["NASDAQ", "NYSE", "AMEX"]),
                        col("close") > 3)
                 .limit(20000)).get_scanner_data()
        m = {str(r["name"]).upper(): (r.get("description") or "")
             for r in df.to_dict("records")}
        hit = sum(1 for t in tickers if m.get(t))
        return {t: m.get(t, "") for t in tickers}, f"公司名 {hit}/{len(tickers)}"
    except Exception as e:                                     # noqa: BLE001
        return {}, f"⚠ 公司名拿唔到：{type(e).__name__}"


def _tag_src():
    h, b = {}, {}
    for r in (_jload(HTF, {}) or {}).get("rows") or []:
        t = str(r.get("ticker") or "").upper()
        if t:
            h[t] = str(r.get("rule") or r.get("tag") or "")
    for r in (_jload(BB, {}) or {}).get("rows") or []:
        t = str(r.get("ticker") or "").upper()
        if t:
            b[t] = r.get("ball")
    return h, b


def _ohlc(df):
    c = df["Close"].astype(float)
    h = df["High"].astype(float)
    l = df["Low"].astype(float)
    v = df["Volume"].astype(float) if "Volume" in df else None
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr14 = float(tr.rolling(14).mean().iloc[-1])
    atr50 = float(tr.tail(50).mean())
    if not (atr14 > 0 and atr50 > 0):
        return None
    px = float(c.iloc[-1])
    sma50 = float(c.tail(50).mean())
    e21 = float(c.ewm(span=21, adjust=False).mean().iloc[-1])
    sma200 = float(c.tail(200).mean()) if len(c) >= 200 else None
    s50_prev = float(c.iloc[-70:-20].tail(50).mean()) if len(c) >= 70 else None
    box = float(h.tail(10).max() - l.tail(10).min())
    o = {
        "close": round(px, 2),
        "atr_usd": round(atr14, 3),
        "atr_pct": round(atr14 / px * 100, 2),
        "adr": round(atr50 / px * 100, 2),
        "atrx": round((px - sma50) / atr14, 2),
        "d21": round((px - e21) / atr14, 2),
        "box_atr": round(box / atr50, 2),
        "tight": round(max(0.0, min(100.0, 100.0 * (1 - (box / atr50) / 6.0))), 1),
        "pivot": round(float(h.tail(20).max()), 2),
        "low10": round(float(l.tail(10).min()), 2),
        "hi52": round(float(c.tail(252).max()), 2),
        "above50": 1 if px > sma50 else 0,
        "ma50_up": 1 if s50_prev and sma50 > s50_prev else 0,
        "chg1d": round(px / float(c.iloc[-2]) * 100 - 100, 2) if len(c) >= 2 else None,
    }
    o["dist_pivot"] = round((px / o["pivot"] - 1) * 100, 2)
    o["d52w"] = round((px / o["hi52"] - 1) * 100, 2)
    o["newhi"] = 1 if o["d52w"] >= -0.5 else 0
    o["stage"] = ("?" if sma200 is None else
                  "UP" if (px > sma50 > sma200 and o["ma50_up"]) else
                  "DOWN" if (px < sma50 and sma200 and px < sma200) else "MIXED")
    # 止蝕：3% 係上限；10 日低點只在（低於入場 + 緊過 3% + 距入場 < 0.60 ATR）才替代
    pct_stop = px * (1 - STOP_PCT)
    stop, kind = pct_stop, "3%"
    if pct_stop < o["low10"] < px and (px - o["low10"]) / atr14 < LOD_MAX_ATR:
        stop, kind = o["low10"], "LOD"
    o["stop"] = round(stop, 2)
    o["stop_pct"] = round((px - stop) / px * 100, 2)
    o["stop_kind"] = kind
    pf = {}
    for n, dd in ((5, "1w"), (21, "1m"), (63, "3m"), (126, "6m"), (252, "1y")):
        if len(c) > n:
            pf[dd] = round(float(c.iloc[-1] / c.iloc[-1 - n] - 1) * 100, 1)
    o["perf"] = pf
    if v is not None and len(v) >= 10:
        o["dvol_m"] = round(float(px * v.tail(10).mean()) / 1e6, 1)
    return o


def _rsw(df, spy_c):
    if spy_c is None or df is None:
        return None
    c = df["Close"].astype(float)
    ex = {}
    for k, dd in ((63, "3m"), (126, "6m"), (189, "9m"), (252, "12m")):
        if len(c) > k and len(spy_c) > k:
            ex[dd] = ((float(c.iloc[-1] / c.iloc[-1 - k] - 1))
                      - float(spy_c.iloc[-1] / spy_c.iloc[-1 - k] - 1)) * 100
    if len(ex) < 4:
        return None
    return 0.4 * ex["3m"] + 0.2 * ex["6m"] + 0.2 * ex["9m"] + 0.2 * ex["12m"]


def _rs_pct(rows):
    vals = sorted(r["_rsw"] for r in rows if r.get("_rsw") is not None)
    nv = len(vals)
    for r in rows:
        w = r.pop("_rsw", None)
        if w is not None and nv:
            r["rs"] = int(round(100 * bisect.bisect_left(vals, w) / max(1, nv - 1)))


def _tags(r, htf, bb):
    t = []
    rs, d52, tg, rv = r.get("rs"), r.get("d52w"), r.get("tight"), r.get("rvol")
    dp, d21 = r.get("dist_pivot"), r.get("d21")
    if rs is not None and rs >= 90 and d52 is not None and d52 >= -10:
        t.append("領導")
    if r.get("newhi"):
        t.append("新高")
    if dp is not None and dp >= -0.3 and (rv or 0) >= 1.5:
        t.append("突破")
    if d21 is not None and -0.5 <= d21 <= 0.5 and (rs or 0) >= 75 and r.get("above50") == 1:
        t.append("回調")
    if tg is not None and tg >= 45 and d52 is not None and d52 >= -15:
        t.append("收縮")
    if r.get("rsline_newhi"):
        t.append("RS新高")
    if r["t"] in htf:
        t.append("HTF")
    if r["t"] in bb:
        t.append("沙灘球")
    return t


def _enc(df, n=WALL_BARS):
    d = df.tail(n)
    prev, out = None, []
    for o, h, l, c in zip(d["Open"], d["High"], d["Low"], d["Close"]):
        base = prev if prev is not None else c
        q = [round(float(x) * 100) for x in (o, h, l, c)]
        b = round(float(base) * 100)
        out.append("%d,%d,%d,%d" % (q[0] - b, q[1] - b, q[2] - b, q[3] - b))
        prev = c
    return ";".join(out)


def main():
    t0 = time.time()
    d = _jload(SCREENER, {})
    rows = d.get("rows") or []
    if not rows:
        log("✗ 冇 data/screener.json（先跑 screener_cache.py）")
        return 1
    if not os.path.exists(OHLC):
        log("✗ 冇 data/screener_ohlc.pkl")
        return 1
    db = pd.read_pickle(OHLC) or {}
    spy = db.get("_SPY")
    spy_c = spy["Close"] if spy is not None and "Close" in spy else None
    tickers = [r["t"] for r in rows if r.get("t")]

    names, msg = _names(tickers)
    log(f"  {msg}")
    htf, bb = _tag_src()
    log(f"  HTF {len(htf)} 隻｜沙灘球 {len(bb)} 隻")

    # ① ② ③：補充現有行
    for r in rows:
        t = r["t"]
        r["name"] = names.get(t, r.get("name") or "")
        df = db.get(t)
        if df is not None and len(df) >= MIN_BARS:
            o = _ohlc(df)
            if o:
                for k, v in o.items():
                    if k != "perf":
                        r[k] = v
                    else:
                        r["perf_ohlc"] = v
        r["tags"] = _tags(r, htf, bb)

    d["risk"] = {"stop_pct": STOP_PCT, "lod_max_atr": LOD_MAX_ATR}
    with io.open(SCREENER, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    log(f"✓ screener.json 補齊（{len(rows)} 隻）")

    # ④ Stock Wall 圖表包
    wall = {"as_of": d.get("as_of"), "bars": WALL_BARS, "tickers": {}}
    for r in rows:
        df = db.get(r["t"])
        if df is None or len(df) < 20:
            continue
        wall["tickers"][r["t"]] = {
            "n": r.get("name") or "", "s": r.get("sector") or "",
            "i": r.get("industry") or "", "c": r.get("close"),
            "chg": r.get("chg1d"), "atr": r.get("atr_pct"), "adr": r.get("adr"),
            "rs": r.get("rs"), "ax": r.get("atrx"), "tg": r.get("tight"),
            "d52": r.get("d52w"), "p": r.get("pivot"), "st": r.get("stop"),
            "k": _enc(df),
        }
    with io.open(WALL, "w", encoding="utf-8") as f:
        json.dump(wall, f, ensure_ascii=False, separators=(",", ":"))
    log(f"✓ wall_series.json｜{len(wall['tickers'])} 隻｜{os.path.getsize(WALL)//1024} KB")

    # ⑤ 最近 6 個交易日快照（用 OHLC 重算同一條尺）
    os.makedirs(HIST, exist_ok=True)
    dates = list(spy.index[-HIST_DAYS:]) if spy is not None else []
    made = 0
    for dd_ in dates:
        day = str(dd_)[:10]
        sc = spy["Close"].loc[:dd_] if spy is not None else None
        hrows = []
        for r in rows:
            df = db.get(r["t"])
            if df is None or len(df) < MIN_BARS:
                continue
            sub = df.loc[:dd_]
            if len(sub) < MIN_BARS or sub.index[-1] != dd_:
                continue
            o = _ohlc(sub)
            if not o:
                continue
            row = {"t": r["t"], "name": r.get("name") or "",
                   "sector": r.get("sector") or "", "industry": r.get("industry") or ""}
            row.update(o)
            row["_rsw"] = _rsw(sub, sc)
            hrows.append(row)
        if not hrows:
            continue
        _rs_pct(hrows)
        for row in hrows:
            row.pop("perf_ohlc", None)
            row["tags"] = _tags(row, htf, bb)
        with io.open(os.path.join(HIST, f"{day}.json"), "w", encoding="utf-8") as f:
            json.dump({"as_of": day, "n": len(hrows), "rows": hrows},
                      f, ensure_ascii=False, separators=(",", ":"))
        made += 1
    log(f"✓ 歷史快照 {made} 日")
    log(f"  完成 {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
