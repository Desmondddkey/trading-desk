# -*- coding: utf-8 -*-
"""gto_daily.py — 用撲克 GTO／EV 框架分析 Daily Scan 選股

第一性原理
─────────
「邊隻股勝率最高」唔係問隻股，係問【手牌類別】：
    同一類設置（同 grade、同 EXT 區間、同距 52 週高區間）反覆出現，
    佢嘅歷史勝率同期望值就係呢一類手牌嘅 EV。

所以流程同撲克一樣：
  1. 定 hand class（特徵分桶）
  2. 量每類 EV = P(win)×平均贏 − P(loss)×平均輸（用 R，唔用 %）
  3. Range = 只打 EV > 0 且 n ≥ MIN_N 嘅類別；其餘 fold
  4. Sizing = Kelly 折半（上限 25% Kelly），對應 0.2% / 0.5% 油門
  5. Timing = 同一個 range 再按 星期幾 / 大市狀態 分層

資料
  快照：trading-os/output/layer2_*.json（96 個交易日）
  價格：trading-os-web/data/tight_prices.pkl
  入場：快照日之後第一個交易日開盤（T+1 open，無前視）
  止蝕：入場 − 1.0 × ATR14（R 分母下限 0.5% 價格 → 防止分母近零）
  出場：第 10 個交易日收市（固定持有期，避免出場規則污染選股結論）

判準（事先寫死）
  MIN_N = 30          樣本 < 30 只顯示、唔准入 range
  MIN_EV = +0.05R     低於此 = 唔值得打
  T_CRIT = 1.96       雙尾 95%

輸出 output/gto_daily.json
"""
from __future__ import annotations

import glob
import io
import json
import math
import os
import pickle
import statistics as st

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = r"C:/Users/rain0/trading-os"
PICKLE = os.path.join(HERE, "data", "tight_prices.pkl")
OUT = os.path.join(LIVE, "output")

MIN_N = 30
MIN_EV = 0.05
T_CRIT = 1.96
HOLD = 10
STOP_ATR = 1.0
RISK_FLOOR = 0.005


def log(m):
    print(m)


def load_px():
    try:
        with io.open(PICKLE, "rb") as f:
            return pickle.load(f)
    except Exception as e:                                   # noqa: BLE001
        log(f"✗ 價格 cache 讀唔到：{e}")
        return {}


def snapshots():
    best = {}
    for f in sorted(glob.glob(os.path.join(LIVE, "output", "layer2_*.json"))):
        b = os.path.basename(f)[7:15]
        best[b] = f
    return sorted(best.items())


def series(px, t):
    bars = px.get(t)
    if not bars or len(bars) < 80:
        return None
    df = pd.DataFrame(bars, columns=["date", "o", "h", "l", "c", "v"])
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


def features(df, day):
    """由價格自己計特徵（唔信快照欄位）—— Focus 同 Stalk 用同一把尺。"""
    pre = df.loc[:day]
    if len(pre) < 60:
        return None
    c = pre["c"]
    tr = (pre["h"] - pre["l"]).tail(14).mean()
    if not tr or tr <= 0:
        return None
    close = float(c.iloc[-1])
    atr = float(tr)
    ema21 = float(c.ewm(span=21, adjust=False).mean().iloc[-1])
    sma50 = float(c.tail(50).mean())
    hi252 = float(c.tail(252).max()) if len(c) >= 252 else float(c.max())
    v = pre["v"]
    rvol = float(v.iloc[-1] / v.tail(50).mean()) if v.tail(50).mean() else None
    box10 = float(pre["h"].tail(10).max() - pre["l"].tail(10).min())
    return {
        "x": round((close - ema21) / atr, 2),
        "ext": round((close - sma50) / atr, 2),
        "dist": round((close / hi252 - 1) * 100, 2),
        "rvol": round(rvol, 2) if rvol else None,
        "tight": round(max(0.0, min(100.0, 100 * (1 - (box10 / atr) / 6))), 0),
    }


def outcomes(df, day):
    """T+1 開盤入場，1 ATR 止蝕，第 HOLD 日收市出。回傳 (r, ret_pct, mfe_pct)。"""
    after = df.loc[day:]
    if len(after) < HOLD + 2:
        return None
    entry = float(after["o"].iloc[1])
    if not entry or entry <= 0:
        return None
    atr = float((after["h"] - after["l"]).rolling(14).mean().iloc[0]) if len(after) > 14 else None
    # ATR 用快照日之前 14 日
    pre = df.loc[:day]
    atr = float((pre["h"] - pre["l"]).tail(14).mean()) if len(pre) >= 14 else None
    if not atr or atr <= 0:
        return None
    stop = entry - STOP_ATR * atr
    risk = max(entry - stop, RISK_FLOOR * entry)
    path = after.iloc[1:HOLD + 1]
    exit_px = float(path["c"].iloc[-1])
    for _, row in path.iterrows():
        if float(row["l"]) <= stop:
            exit_px = stop
            break
    r = (exit_px - entry) / risk
    return round(r, 3), round((exit_px / entry - 1) * 100, 2)


def bucket_ext(v):
    if v is None:
        return "n/a"
    if v < 0:
        return "<0"
    if v < 1:
        return "0–1"
    if v < 2:
        return "1–2"
    if v < 3:
        return "2–3"
    if v < 4:
        return "3–4"
    return "≥4"


def bucket_dist(v):
    if v is None:
        return "n/a"
    if v > -3:
        return "0～−3%"
    if v > -8:
        return "−3～−8%"
    if v > -15:
        return "−8～−15%"
    return "≤−15%"


def bucket_score(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "n/a"
    if v >= 7:
        return "A+ (≥7)"
    if v >= 5:
        return "A (5-6)"
    if v >= 3:
        return "B (3-4)"
    return "C/D (<3)"


def agg(rows):
    if not rows:
        return None
    rs = [x["r"] for x in rows]
    n = len(rs)
    m = sum(rs) / n
    sd = st.stdev(rs) if n > 1 else 0.0
    t = m / (sd / math.sqrt(n)) if sd and n > 1 else 0.0
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    wr = len(wins) / n
    aw = st.mean(wins) if wins else 0.0
    al = abs(st.mean(losses)) if losses else 0.0
    rr = (aw / al) if al else 0.0
    # Kelly（用真 RR；1 以下就當冇 edge）
    kelly = (wr - (1 - wr) / rr) if rr > 0 else -1.0
    return {
        "n": n, "ev_r": round(m, 3), "t": round(t, 2),
        "wr": round(wr * 100, 1), "avg_win": round(aw, 2),
        "avg_loss": round(al, 2), "rr": round(rr, 2),
        "kelly": round(kelly, 3),
        "size_pct": round(min(max(kelly, 0) * 0.25 * 100, 25.0), 1),
        "play": ("打" if (n >= MIN_N and m >= MIN_EV and t >= T_CRIT)
                 else "觀察" if n < MIN_N else "棄"),
    }


def main():
    px = load_px()
    snaps = snapshots()
    panel = []
    for day_s, path in snaps:
        try:
            with io.open(path, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:                                    # noqa: BLE001
            continue
        day = pd.Timestamp(f"{day_s[:4]}-{day_s[4:6]}-{day_s[6:]}")
        for src, key in (("FOCUS", "focus_list"), ("STALK", "stalk_list")):
            for row in (d.get(key) or []):
                t = row.get("ticker")
                df = series(px, t)
                if df is None or day not in df.index:
                    continue
                o = outcomes(df, day)
                if not o:
                    continue
                ft = features(df, day)
                if not ft:
                    continue
                panel.append({
                    "day": day_s, "dow": day.day_name()[:3],
                    "ticker": t, "src": src,
                    "ext": ft["ext"], "dist": ft["dist"],
                    "x": ft["x"], "rvol": ft["rvol"], "tight": ft["tight"],
                    "score": row.get("score"),
                    "earn": row.get("days_to_earnings"),
                    "r": o[0], "ret": o[1],
                })
    if not panel:
        log("DATA_UNAVAILABLE")
        return 1

    def group(fn):
        g = {}
        for x in panel:
            g.setdefault(fn(x), []).append(x)
        return {k: agg(v) for k, v in sorted(g.items(), key=lambda kv: -len(kv[1]))}

    out = {
        "n_obs": len(panel),
        "n_days": len({x["day"] for x in panel}),
        "base": agg(panel),
        "by_score": group(lambda x: bucket_score(x["score"])),
        "by_ext": group(lambda x: bucket_ext(x["ext"])),
        "by_dist": group(lambda x: bucket_dist(x["dist"])),
        "by_src": group(lambda x: x["src"]),
        "by_x": group(lambda x: ("<0" if x["x"] < 0 else "0–0.5" if x["x"] < 0.5
                                  else "0.5–1" if x["x"] < 1 else "1–2" if x["x"] < 2
                                  else "≥2")),
        "by_rvol": group(lambda x: ("<0.8" if (x["rvol"] or 1) < 0.8 else
                                     "0.8–1.2" if (x["rvol"] or 1) < 1.2 else
                                     "1.2–2" if (x["rvol"] or 1) < 2 else "≥2")),
        "by_tight": group(lambda x: ("<40" if x["tight"] < 40 else
                                      "40–70" if x["tight"] < 70 else "≥70")),
        "by_dow": group(lambda x: x["dow"]),
        "by_combo": group(lambda x: f'{bucket_score(x["score"])}｜{bucket_ext(x["ext"])}'),
        "criteria": {"min_n": MIN_N, "min_ev": MIN_EV, "t_crit": T_CRIT,
                     "hold_days": HOLD, "stop_atr": STOP_ATR,
                     "entry": "T+1 開盤", "risk_floor": RISK_FLOOR},
    }
    os.makedirs(OUT, exist_ok=True)
    with io.open(os.path.join(OUT, "gto_daily.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    b = out["base"]
    log(f"樣本 {out['n_obs']} 筆 / {out['n_days']} 日｜基準 EV {b['ev_r']:+.2f}R"
        f"｜勝率 {b['wr']}%｜RR {b['rr']}")
    for name in ("by_ext", "by_x", "by_dist", "by_rvol", "by_tight", "by_dow", "by_src"):
        log(f"\n▍{name}")
        for k, v in out[name].items():
            if not v:
                continue
            log(f"  {k:<12} n={v['n']:<4} EV {v['ev_r']:+.2f}R  WR {v['wr']:>5}%  "
                f"RR {v['rr']:>4}  t {v['t']:+.2f}  {v['play']}  倉 {v['size_pct']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
