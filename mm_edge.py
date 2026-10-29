# -*- coding: utf-8 -*-
"""mm_edge.py — 「升跌比越高，突破期望值越高？」用數據答

方法（同 gto_daily 同一批觀測、同一把尺）
  1. 由 scan_prices.pkl 計每日升跌比：up4 / down4（4% 門檻，Stockbee 式）
  2. 對 gto_daily 每個觀測（日期 + 候選股）配上【當日】升跌比
  3. 按升跌比分 4 組，計每組 EV／勝率／t
  4. 另計「升跌比」同 R 嘅相關係數

限制（一定要講）
  · 升跌比用 277 隻 scan 宇宙計，唔係全美股
  · 觀測有橫截面相關（同一日幾十隻），有效樣本 < n
輸出 output/mm_edge.json
"""
from __future__ import annotations

import glob
import io
import json
import math
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = r"C:/Users/rain0/trading-os"
OUT = os.path.join(LIVE, "output")

sys.path.insert(0, HERE)
import gto_daily as G  # noqa: E402


def breadth_series(px):
    """每日 up4/down4 比（用 scan 宇宙）。"""
    rets = {}
    for t, bars in px.items():
        try:
            s = pd.Series({pd.Timestamp(b[0]): b[4] for b in bars}).sort_index()
            rets[t] = s.pct_change() * 100
        except Exception:                                    # noqa: BLE001
            continue
    df = pd.DataFrame(rets)
    up = (df >= 4).sum(axis=1)
    dn = (df <= -4).sum(axis=1)
    ratio = up / dn.clip(lower=1)
    return pd.DataFrame({"up4": up, "dn4": dn, "ratio": ratio})


def panel():
    """重建 gto 觀測（日期、R）。"""
    px = G.load_px()
    rows = []
    for day_s, path in G.snapshots():
        try:
            with io.open(path, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:                                    # noqa: BLE001
            continue
        day = pd.Timestamp(f"{day_s[:4]}-{day_s[4:6]}-{day_s[6:]}")
        for src, key in (("FOCUS", "focus_list"), ("STALK", "stalk_list")):
            for r in (d.get(key) or []):
                t = r.get("ticker")
                df = G.series(px, t)
                if df is None:
                    continue
                prior = df.index[df.index <= day]
                if len(prior) == 0:
                    continue
                dd = prior[-1]
                if (day - dd).days > 4:
                    continue
                o = G.outcomes(df, dd)
                if not o:
                    continue
                rows.append({"date": dd, "ticker": t, "src": src, "r": o[0]})
    return rows


def agg(vals):
    n = len(vals)
    if n < 2:
        return {"n": n, "ev": None, "wr": None, "t": None}
    m = sum(vals) / n
    var = sum((v - m) ** 2 for v in vals) / (n - 1)
    sd = math.sqrt(var)
    t = m / (sd / math.sqrt(n)) if sd else 0.0
    wr = sum(1 for v in vals if v > 0) / n * 100
    return {"n": n, "ev": round(m, 3), "wr": round(wr, 1), "t": round(t, 2)}


def main() -> int:
    px = G.load_px()
    br = breadth_series(px)
    rows = panel()
    joined = []
    for x in rows:
        try:
            ratio = float(br.loc[x["date"], "ratio"])
        except Exception:                                    # noqa: BLE001
            continue
        joined.append({**x, "ratio": ratio})
    if len(joined) < 100:
        print("樣本不足", len(joined), file=sys.stderr)
        return 0

    rs = sorted(x["ratio"] for x in joined)
    q = [rs[int(len(rs) * f)] for f in (0.25, 0.50, 0.75)]

    def bucket(v):
        if v <= q[0]:
            return f"低 ≤{q[0]:.2f}"
        if v <= q[1]:
            return f"中低 ≤{q[1]:.2f}"
        if v <= q[2]:
            return f"中高 ≤{q[2]:.2f}"
        return f"高 >{q[2]:.2f}"

    groups = {}
    for x in joined:
        groups.setdefault(bucket(x["ratio"]), []).append(x["r"])
    out = {
        "n": len(joined),
        "days": len({x["date"] for x in joined}),
        "quartiles": [round(v, 2) for v in q],
        "by_ratio": {k: agg(v) for k, v in groups.items()},
    }
    # 相關係數（pearson）
    xs = [x["ratio"] for x in joined]
    ys = [x["r"] for x in joined]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    out["corr"] = round(num / den, 3) if den else None

    os.makedirs(OUT, exist_ok=True)
    with io.open(os.path.join(OUT, "mm_edge.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
