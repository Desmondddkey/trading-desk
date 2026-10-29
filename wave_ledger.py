# -*- coding: utf-8 -*-
"""wave_ledger.py — 每日記錄「肥波」漏斗（大市 → 板塊 → RS → setup）

第一性原理：一單 trade 嘅期望值 =
    P(大市支持) × P(板塊有資金) × P(個股 RS 領先) × P(設置成立) × 賠率
四層任何一層接近 0，整體就接近 0 —— 所以先記四層，唔係先記 setup。

寫入 output/wave_ledger.jsonl（append-only，同一日重跑只保留最後一份）
"""
from __future__ import annotations

import glob
import io
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = r"C:/Users/rain0/trading-os"
OUT = os.path.join(LIVE, "output")
IND = os.path.join(HERE, "data", "ticker_industry.json")
LEDGER = os.path.join(OUT, "wave_ledger.jsonl")

sys.path.insert(0, HERE)
import gto_daily as G  # noqa: E402


def _load(p):
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return None


def latest(pat):
    fs = sorted(glob.glob(os.path.join(OUT, pat)))
    return fs[-1] if fs else None


def main() -> int:
    snap_p = latest("layer2_*.json")
    if not snap_p:
        print("DATA_UNAVAILABLE layer2", file=sys.stderr)
        return 0
    snap = _load(snap_p) or {}
    day_s = os.path.basename(snap_p)[7:15]
    day = f"{day_s[:4]}-{day_s[4:6]}-{day_s[6:]}"

    reg = _load(os.path.join(HERE, "docs", "regime_live.json")) or {}
    grs = _load(latest("group_rs_*.json")) or {}
    gmap = {r["group"]: r["rs"] for r in (grs.get("rows") or [])}
    grank = {g: i + 1 for i, g in
             enumerate(sorted(gmap, key=lambda k: -gmap[k]))}
    ind = _load(IND) or {}

    def _ind_name(v):
        """ticker_industry.json 有機會係 dict（sector/industry）。"""
        if isinstance(v, dict):
            return (v.get("industry") or v.get("sector") or v.get("group") or "")
        return v or ""

    px = G.load_px()
    rows = []
    for src, key in (("FOCUS", "focus_list"), ("STALK", "stalk_list")):
        for r in (snap.get(key) or []):
            t = r.get("ticker")
            df = G.series(px, t)
            ft = G.features(df, G.pd.Timestamp(day)) if df is not None else None
            if not ft:
                continue
            c = df["c"].dropna()
            rs63 = (float(c.iloc[-1]) / float(c.iloc[-64]) - 1) * 100 if len(c) > 64 else None
            rows.append({"ticker": t, "src": src, "ind": _ind_name(ind.get(t)),
                         "rs63": round(rs63, 2) if rs63 is not None else None,
                         "x": ft["x"], "ext": ft["ext"], "dist": ft["dist"],
                         "rvol": ft["rvol"], "tight": ft["tight"],
                         "score": r.get("score")})

    vals = sorted([x["rs63"] for x in rows if x["rs63"] is not None])
    def pct(v):
        if v is None or not vals:
            return None
        return round(100 * sum(1 for x in vals if x <= v) / len(vals), 0)

    for x in rows:
        x["rs_pct"] = pct(x["rs63"])
        x["grp_rs"] = gmap.get(x["ind"])
        x["grp_rank"] = grank.get(x["ind"])
        try:
            sc = float(x["score"])
        except (TypeError, ValueError):
            sc = 0.0
        conf = (0.40 * (x["rs_pct"] or 0) + 0.30 * (x["grp_rs"] or 0)
                + 0.30 * min(100, sc / 8 * 100))
        x["conf"] = round(conf, 1)

    funnel = {
        "universe": len(rows),
        "rs70": sum(1 for x in rows if (x["rs_pct"] or 0) >= 70),
        "sector_top5": sum(1 for x in rows
                           if (x["rs_pct"] or 0) >= 70 and (x["grp_rank"] or 99) <= 5),
        "setup_ok": sum(1 for x in rows
                        if (x["rs_pct"] or 0) >= 70 and (x["grp_rank"] or 99) <= 5
                        and (str(x["score"]) in ("A+", "A") or (x["score"] or 0) >= 5)),
    }

    rec = {"date": day, "mri": reg.get("mri"), "state": reg.get("state"),
           "pos": reg.get("pos"), "mmtw": reg.get("mmtw"),
           "sectors_top": sorted(gmap.items(), key=lambda kv: -kv[1])[:5],
           "funnel": funnel, "rows": sorted(rows, key=lambda r: -(r["conf"] or 0))}

    # append-only，但同一日只保留一份
    keep = []
    if os.path.exists(LEDGER):
        with io.open(LEDGER, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:                            # noqa: BLE001
                    continue
                if o.get("date") != day:
                    keep.append(o)
    keep.append(rec)
    keep.sort(key=lambda o: o["date"])
    with io.open(LEDGER, "w", encoding="utf-8") as f:
        for o in keep:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")

    print(f"{day}｜MRI {rec['mri']}｜候選 {funnel['universe']} → "
          f"RS≥70 {funnel['rs70']} → 板塊前5 {funnel['sector_top5']} → "
          f"setup {funnel['setup_ok']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
