# -*- coding: utf-8 -*-
"""fear_gauge.py — 投降／過熱儀表（每日收市後）

5 個已回測組件（3 年 753 個交易日，2023-10-24 → 2026-10-23）
  A  VIX ≥ 30                 → 20 日 SPY +10.79%／勝 100%（n=15）
  B  VIX / VIX3M > 1          → +5.69%／71%（n=48）
  C  廣度（>200MA 比例）< 25%  → +3.31%／85%（n=213）
  D  CNN F&G < 25             → +2.88%／89%（n=44）
  P  Put/Call ≥ 0.80          → +3.31%／66%（n=61）

分數 → 20 日 SPY 中位數／勝率（實際回測）
  0 分  +1.40% / 67.7%   （n=446）
  1 分  +2.97% / 77.4%   （n=257）
  2 分  +5.65% / 78.6%   （n=28）
  3 分  +9.04% / 95.0%   （n=20）★ 呢個才是「投降」

過熱（逃頂）方向：回測 **冇 edge**（VIX<14／廣度>85% 樣本不足；
top1 組 SPY +2.89% 反而高過基準）→ 誠實標示「未證實」，唔發警報。

輸出：output/fear_gauge.json（網站讀）、output/fear_gauge_hist.jsonl（append-only）
沉默合約：分數 < 3 = stdout 完全空白；≥3 才出警報。
"""
from __future__ import annotations

import io
import json
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fear_backtest as fb                                  # noqa: E402

OUT = os.path.join(HERE, "output")
ALERT_AT = 3


def log(m):
    print(m, file=sys.stderr)


def main():
    uni = []
    try:
        ms = json.load(io.open(os.path.join(HERE, "data", "market_scan.json"),
                               encoding="utf-8"))
        uni = sorted({(r.get("symbol") or "").upper()
                      for r in (ms.get("universe") or []) if r.get("symbol")})
    except Exception as e:                                    # noqa: BLE001
        log(f"⚠ 冇 market_scan：{e}")

    px = fb.prices(list(dict.fromkeys(uni + ["SPY", "QQQ", "IWM",
                                              "^VIX", "^VIX3M", "^VXN"])))
    need = ["SPY", "^VIX", "^VIX3M"]
    if any(px.get(t) is None or not len(px[t]) for t in need):
        log("✗ 核心數據不足")
        return 1

    spy = px["SPY"]
    vix = px["^VIX"].reindex(spy.index).ffill()
    vix3m = px["^VIX3M"].reindex(spy.index).ffill()
    _vxn = px.get("^VXN")
    vxn = (_vxn if _vxn is not None else pd.Series(dtype=float)).reindex(spy.index).ffill()

    # 廣度
    cols = {t: px[t] for t in uni if px.get(t) is not None and len(px[t]) > 220}
    breadth = np.nan
    if cols:
        cdf = pd.DataFrame(cols).reindex(spy.index)
        ab = (cdf > cdf.rolling(200).mean()).sum(axis=1) / cdf.notna().sum(axis=1).replace(0, np.nan)
        breadth = float((ab * 100).iloc[-1])

    fg_s = fb.cnn_series("fear_and_greed_historical")
    pc_s = fb.cnn_series("put_call_options")
    fg = float(fg_s.iloc[-1]) if fg_s is not None and len(fg_s) else None
    pc = float(pc_s.iloc[-1]) if pc_s is not None and len(pc_s) else None

    v = float(vix.iloc[-1])
    r = float((vix / vix3m).iloc[-1])
    vxnv = float(vxn.iloc[-1]) if len(vxn.dropna()) else None

    checks = [
        ("VIX ≥ 30", v >= 30, f"{v:.2f}", "20日 SPY +10.79%／勝 100%"),
        ("VIX/VIX3M > 1", r > 1.0, f"{r:.2f}", "期限倒掛：+5.69%／71%"),
        ("廣度 < 25%", breadth == breadth and breadth < 25,
         f"{breadth:.0f}%" if breadth == breadth else "—", "+3.31%／85%"),
        ("F&G < 25", fg is not None and fg < 25,
         f"{fg:.0f}" if fg is not None else "—", "+2.88%／89%"),
        ("Put/Call ≥ 0.80", pc is not None and pc >= 0.80,
         f"{pc:.2f}" if pc is not None else "—", "+3.31%／66%"),
    ]
    score = sum(1 for _, hit, _, _ in checks if hit)

    verdict = {0: "平靜", 1: "留意", 2: "超跌累積", 3: "接近投降",
               4: "投降區", 5: "投降區"}[score]
    hist = {0: "20日 SPY +1.40%／勝 67.7%", 1: "+2.97%／77.4%",
            2: "+5.65%／78.6%", 3: "+9.04%／95.0% ★",
            4: "+9.04%／95.0% ★", 5: "+9.04%／95.0% ★"}[score]

    payload = {
        "date": str(spy.index[-1].date()), "generated": date.today().isoformat(),
        "score": score, "verdict": verdict, "expectancy": hist,
        "vix": round(v, 2), "vix3m": round(float(vix3m.iloc[-1]), 2),
        "vix_ratio": round(r, 3),
        "vxn": round(vxnv, 2) if vxnv is not None else None,
        "breadth": round(breadth, 1) if breadth == breadth else None,
        "fg": round(fg, 1) if fg is not None else None,
        "pc": round(pc, 3) if pc is not None else None,
        "checks": [{"name": n, "hit": bool(h), "value": val, "edge": edge}
                   for n, h, val, edge in checks],
        "backtest": {"window": "2023-10-24 → 2026-10-23", "days": 753,
                     "buckets": [[0, 446, 1.40, 67.7], [1, 257, 2.97, 77.4],
                                 [2, 28, 5.65, 78.6], [3, 20, 9.04, 95.0]],
                     "top_side": "未證實（回測冇 edge）"},
    }
    os.makedirs(OUT, exist_ok=True)
    json.dump(payload, io.open(os.path.join(OUT, "fear_gauge.json"), "w",
                               encoding="utf-8"), ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUT, "fear_gauge_hist.jsonl"), "a",
                 encoding="utf-8") as f:
        f.write(json.dumps({k: payload[k] for k in
                            ("date", "score", "verdict", "vix", "vix_ratio",
                             "breadth", "fg", "pc")},
                           ensure_ascii=False) + "\n")

    if score >= ALERT_AT:
        hits = "、".join(c["name"] for c in payload["checks"] if c["hit"])
        print(f"🩸 投降儀表 {score}/5 — {verdict}")
        print(f"數據日 {payload['date']}")
        print(f"命中：{hits}")
        print(f"VIX {payload['vix']}（VIX/VIX3M {payload['vix_ratio']}）"
              f"｜廣度 {payload['breadth']}%｜F&G {payload['fg']}｜P/C {payload['pc']}")
        print(f"歷史同分：{hist}")
        print("→ 分批建倉，唔好一次打光；止蝕照跟 3 段。")
    log(f"score {score}/5 — {verdict}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
