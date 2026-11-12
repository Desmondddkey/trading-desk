# -*- coding: utf-8 -*-
"""screener_cache.py — 一個檔案養晒 Stock Screener 嘅全部數字。

輸入
  data/market_scan.json     744 隻（TV 掃描：價、行業、ATR%、RVOL、成交額、1W/1M/3M/6M/1Y、距52高）
  data/screener_ohlc.pkl    自建 OHLC 快取（由 kell_ohlc/cm_ohlc/charts_ohlc 起，之後每日增量補）
  data/tv_meta.json         行業後備

輸出
  data/screener.json        {"generated","as_of","bench","n","rows":[...]}
  data/screener_ohlc.pkl    OHLC 快取（{"_SPY": df, "NVDA": df, ...}）

定義（全部有出處，唔准自己改）
  atr14   = TR.rolling(14).mean()                       ← rs_scan.py（X/Y 同一條尺）
  atrx/ y = (close - sma50) / atr14                     ← rs_scan.py（ATRX = 距 50MA 幾多個 ATR）
  d21/ x  = (close - ema21) / atr14                     ← rs_scan.py（距 21EMA）
  atr50   = TR 50 日平均                                ← tight_scan.py
  tight   = 100 × (1 − (10日高低箱 ÷ atr50) / 6)          ← tight_scan.py
  adr     = atr50 / close × 100                         ← 波幅（同 TV ADRP 唔可混用）
  rs      = 0.4×3M + 0.2×6M + 0.2×9M + 0.2×12M 相對 SPY 超額，再取本池百分位（0–99）
            ← layer2a_rs_leader.py 權重；百分位用真百分位（唔用飽和公式）
  pivot   = max(high[-20:])；dist_pivot = (close/pivot − 1) × 100
  rsline  = close / SPY close；rsline_newhi = RS line 距自己 52 週高 ≤0.5%
  d52w    = (close/52週高 − 1) × 100（OHLC 有就用 OHLC，冇就用 TV 嘅 off52w）
  stage   = UP（close>sma50>sma200 且 sma50 20 日上升）／DOWN（兩線之下）／MIXED

⚠ 缺失唔等於 0：OHLC 拿唔到嘅股票，該欄位寫 None（前端顯示 —），唔准填 0。
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SCAN = os.path.join(DATA, "market_scan.json")
META = os.path.join(DATA, "tv_meta.json")
OHLC = os.path.join(DATA, "screener_ohlc.pkl")
OUT = os.path.join(DATA, "screener.json")

OHLC_COLS = ["Open", "High", "Low", "Close", "Volume"]
MIN_BARS = 60
CHUNK = 120


def log(*a):
    print(*a, flush=True)


def _jload(p, d):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return d


def _norm(df: pd.DataFrame) -> pd.DataFrame | None:
    """統一成單層欄位 OHLCV，按日期排序、去重、去 NaN close。"""
    if df is None or not len(df):
        return None
    if isinstance(df.columns, pd.MultiIndex):
        lv = df.columns.get_level_values(0)
        # ('NVDA','Close') 或者 ('Close','NVDA') 兩種都見過
        want = [c for c in OHLC_COLS if c in set(lv)]
        if want:
            df = df.loc[:, lv.isin(want)]
            df.columns = df.columns.get_level_values(0)
        else:
            df = df.droplevel(0, axis=1)
    keep = [c for c in OHLC_COLS if c in df.columns]
    if "Close" not in keep:
        return None
    df = df[keep].copy()
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()]
    try:
        df.index = df.index.tz_localize(None)
    except (TypeError, AttributeError):
        pass
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df[df["Close"].notna()]
    return df if len(df) else None


def _seed_cache() -> dict:
    """由現有快取起底（只讀，唔改佢哋）。"""
    out: dict[str, pd.DataFrame] = {}
    for fn in ("kell_ohlc.pkl", "cm_ohlc.pkl", "charts_ohlc.pkl"):
        p = os.path.join(DATA, fn)
        if not os.path.exists(p):
            continue
        try:
            raw = pd.read_pickle(p)
        except Exception as e:                                  # noqa: BLE001
            log(f"  ⚠ {fn} 讀唔到：{type(e).__name__}: {e}")
            continue
        if not isinstance(raw, pd.DataFrame):
            continue
        if isinstance(raw.columns, pd.MultiIndex):
            tks = sorted(set(raw.columns.get_level_values(0)))
            for t in tks:
                try:
                    sub = _norm(raw[t])
                except Exception:                              # noqa: BLE001
                    sub = None
                if sub is not None and t not in out:
                    out[t] = sub
        else:
            for c in raw.columns:
                t = str(c).split("_")[0]
                sub = _norm(raw[[c]].rename(columns={c: "Close"}))
                if sub is not None and t not in out:
                    out[t] = sub
        log(f"  起底 {fn}: {len(out)} 隻")
    return out


def _dl(tickers, period):
    """一次抓一批；回 {ticker: df}。"""
    import yfinance as yf
    got = {}
    if not tickers:
        return got
    d = yf.download(list(tickers), period=period, interval="1d",
                    group_by="ticker", auto_adjust=True,
                    progress=False, threads=True)
    if d is None or not len(d):
        return got
    if len(tickers) == 1:
        s = _norm(d)
        if s is not None:
            got[tickers[0]] = s
        return got
    for t in tickers:
        try:
            sub = _norm(d[t])
        except Exception:                                      # noqa: BLE001
            sub = None
        if sub is not None:
            got[t] = sub
    return got


def _last_bar(df) -> pd.Timestamp | None:
    return None if df is None or not len(df) else df.index[-1]


def build(force=False):
    t0 = time.time()
    scan = _jload(SCAN, {})
    rows_in = scan.get("universe") or []
    if not rows_in:
        log("✗ market_scan.json 冇 universe")
        return 1
    meta = _jload(META, {})

    cache = {}
    if os.path.exists(OHLC):
        try:
            cache = pd.read_pickle(OHLC) or {}
        except Exception as e:                                 # noqa: BLE001
            log(f"⚠ screener_ohlc.pkl 壞咗（重建）：{type(e).__name__}: {e}")
            cache = {}
    if not cache or force:
        cache = _seed_cache()

    uni = [str(r.get("symbol") or "").upper() for r in rows_in]
    uni = [t for t in uni if t and t.replace(".", "").replace("-", "").isalnum()]
    need = [t for t in uni if t not in cache]
    log(f"  universe {len(uni)}｜快取有 {len(uni) - len(need)}｜要補 {len(need)}")

    # SPY：先確保有
    if "_SPY" not in cache or force:
        got = _dl(["_SPY".replace("_", ""),], "2y")
        if "SPY" in got:
            cache["_SPY"] = got["SPY"]
    spy = cache.get("_SPY")

    # 補全新嘅（2y 一次)，分塊
    for i in range(0, len(need), CHUNK):
        part = need[i:i + CHUNK]
        got = _dl(part, "2y")
        cache.update(got)
        log(f"    補 {i + len(got)}/{len(need)}（今批返 {len(got)}）")

    # 增量：落後嘅用 10d 補
    exp_last = _last_bar(spy)
    if exp_last is not None:
        stale = [t for t in uni if t in cache and (_last_bar(cache[t]) or exp_last) < exp_last]
        for i in range(0, len(stale), CHUNK):
            part = stale[i:i + CHUNK]
            got = _dl(part, "10d")
            for t, sub in got.items():
                old = cache.get(t)
                if old is None:
                    cache[t] = sub
                    continue
                try:
                    new = pd.concat([old, sub])
                    new = new[~new.index.duplicated(keep="last")].sort_index()
                    cache[t] = new.tail(420)
                except Exception:                              # noqa: BLE001
                    pass
        if stale:
            log(f"  增量補 {len(stale)} 隻")

    # 只留 universe + SPY，控制檔案大細
    keep = {t: cache[t] for t in uni if t in cache}
    if spy is not None:
        keep["_SPY"] = spy
    try:
        pd.to_pickle(keep, OHLC)
        log(f"  快取已存：{len(keep)} 隻")
    except Exception as e:                                     # noqa: BLE001
        log(f"⚠ 快取寫唔到：{type(e).__name__}: {e}")

    # ── 計數 ──────────────────────────────────────────────
    spy_c = spy["Close"] if spy is not None and "Close" in spy else None
    spy_ret = {}
    if spy_c is not None:
        for k, d in ((63, "3m"), (126, "6m"), (189, "9m"), (252, "12m")):
            spy_ret[d] = (float(spy_c.iloc[-1] / spy_c.iloc[-1 - k] - 1)
                          if len(spy_c) > k else None)

    recs = []
    for r in rows_in:
        t = str(r.get("symbol") or "").upper()
        df = keep.get(t)
        m = meta.get(t) or {}
        rec = {
            "t": t,
            "sector": r.get("sector") or m.get("sector") or "",
            "industry": r.get("industry") or m.get("industry") or "",
            "close": r.get("close"),
            "atrp_tv": r.get("atrp"),
            "rvol": r.get("rvol"),
            "dvol_m": round((r.get("dvol") or 0) / 1e6, 1) if r.get("dvol") else None,
            "mcap_b": round((r.get("mcap") or 0) / 1e9, 1) if r.get("mcap") else None,
            "off52_tv": r.get("off52w"),
            "ext_tv": r.get("extension"),
            "perf": r.get("perf") or {},
            "_ohlc": df is not None,
        }
        if df is not None and len(df) >= MIN_BARS:
            c = df["Close"].astype(float)
            h = df["High"].astype(float)
            l = df["Low"].astype(float)
            v = df["Volume"].astype(float) if "Volume" in df else None
            tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
            atr14 = float(tr.rolling(14).mean().iloc[-1])
            atr50 = float(tr.tail(50).mean())
            sma50 = float(c.tail(50).mean())
            e21 = float(c.ewm(span=21, adjust=False).mean().iloc[-1])
            sma200 = float(c.tail(200).mean()) if len(c) >= 200 else None
            s50_prev = float(c.iloc[-70:-20].tail(50).mean()) if len(c) >= 70 else None
            px = float(c.iloc[-1])
            if atr14 > 0 and atr50 > 0:
                rec["close"] = round(px, 2)
                rec["atr_pct"] = round(atr14 / px * 100, 2)
                rec["adr"] = round(atr50 / px * 100, 2)
                rec["atrx"] = round((px - sma50) / atr14, 2)
                rec["d21"] = round((px - e21) / atr14, 2)
                box = float(h.tail(10).max() - l.tail(10).min())
                rec["box_atr"] = round(box / atr50, 2)
                rec["tight"] = round(max(0.0, min(100.0, 100.0 * (1 - (box / atr50) / 6.0))), 1)
                rec["pivot"] = round(float(h.tail(20).max()), 2)
                rec["dist_pivot"] = round((px / rec["pivot"] - 1) * 100, 2)
                hi252 = c.tail(252)
                rec["hi52"] = round(float(hi252.max()), 2)
                rec["d52w"] = round((px / float(hi252.max()) - 1) * 100, 2)
                rec["newhi"] = 1 if rec["d52w"] >= -0.5 else 0
                rec["above50"] = 1 if px > sma50 else 0
                rec["above200"] = (1 if sma200 and px > sma200 else 0) if sma200 else None
                rec["ma50_up"] = 1 if s50_prev and sma50 > s50_prev else 0
                if sma200 is None:
                    rec["stage"] = "?"
                elif px > sma50 > sma200 and rec["ma50_up"]:
                    rec["stage"] = "UP"
                elif px < sma50 and (sma200 and px < sma200):
                    rec["stage"] = "DOWN"
                else:
                    rec["stage"] = "MIXED"
                # 相對 SPY 超額（3/6/9/12 個月）
                if spy_c is not None:
                    ex = {}
                    for k, dd in ((63, "3m"), (126, "6m"), (189, "9m"), (252, "12m")):
                        if len(c) > k and spy_ret.get(dd) is not None:
                            ex[dd] = (float(c.iloc[-1] / c.iloc[-1 - k] - 1) - spy_ret[dd]) * 100
                    if len(ex) == 4:
                        rec["_rsw"] = (0.4 * ex["3m"] + 0.2 * ex["6m"]
                                       + 0.2 * ex["9m"] + 0.2 * ex["12m"])
                    # RS line 新高
                    try:
                        rs = (c / spy_c.reindex(c.index).ffill()).dropna()
                        if len(rs) >= 60:
                            rec["rsline_newhi"] = 1 if rs.iloc[-1] >= rs.tail(252).max() * 0.995 else 0
                    except Exception:                          # noqa: BLE001
                        pass
            # 成交額／波幅後備
            if v is not None and len(v) >= 10:
                rec["dvol_m"] = round(float(px * v.tail(10).mean()) / 1e6, 1)
            # 績效後備（TV 冇就用 OHLC 計）
            pf = dict(rec.get("perf") or {})
            for n, dd, _unused in ((5, "1w", 5), (21, "1m", 21), (63, "3m", 63),
                                   (126, "6m", 126), (252, "1y", 252)):
                if pf.get(dd) is None and len(c) > n:
                    pf[dd] = round(float(c.iloc[-1] / c.iloc[-1 - n] - 1) * 100, 1)
            rec["perf"] = pf
            rec["chg1d"] = round(float(c.iloc[-1] / c.iloc[-2] - 1) * 100, 2) if len(c) >= 2 else None
        recs.append(rec)

    # RS 百分位（只用有 _rsw 嘅）
    vals = sorted(r["_rsw"] for r in recs if r.get("_rsw") is not None)
    nv = len(vals)
    if nv:
        import bisect
        for r in recs:
            w = r.pop("_rsw", None)
            if w is not None:
                r["rs"] = int(round(100 * bisect.bisect_left(vals, w) / max(1, nv - 1)))
    else:
        for r in recs:
            r.pop("_rsw", None)

    # 訊號標籤（每個都有明文條件）
    for r in recs:
        tags = []
        rs = r.get("rs"); atrx = r.get("atrx"); dp = r.get("dist_pivot")
        d52 = r.get("d52w"); tg = r.get("tight"); rv = r.get("rvol"); d21 = r.get("d21")
        if rs is not None and rs >= 90 and (d52 is not None and d52 >= -10):
            tags.append("領導")
        if r.get("newhi"):
            tags.append("新高")
        if dp is not None and dp >= -0.3 and (rv or 0) >= 1.5:
            tags.append("突破")
        if d21 is not None and -0.5 <= d21 <= 0.5 and (rs or 0) >= 75 and (r.get("above50") == 1):
            tags.append("回調")
        if tg is not None and tg >= 70 and (d52 is not None and d52 >= -12):
            tags.append("收縮")
        if r.get("rsline_newhi"):
            tags.append("RS新高")
        r["tags"] = tags

    cov = sum(1 for r in recs if r.get("_ohlc"))
    _bars = [_last_bar(keep[t]) for t in keep if keep[t] is not None]
    _bars = [b for b in _bars if b is not None]
    as_of = (max(_bars) if _bars else "") 
    as_of = str(as_of)[:10]
    payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "as_of": as_of,
        "bench": "SPY",
        "n": len(recs),
        "n_ohlc": cov,
        "scan_generated": scan.get("generated"),
        "rows": recs,
    }
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    log(f"✓ {OUT}｜{len(recs)} 隻（OHLC {cov}）｜as_of {as_of}｜{time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(build(force="--force" in sys.argv[1:]))
