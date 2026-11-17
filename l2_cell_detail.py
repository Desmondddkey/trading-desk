# -*- coding: utf-8 -*-
"""l2_cell_detail.py — 逐隻列出回測買咗邊隻、贏幾 R、幾時 trim。

基於 l2_cell_backtest.py 同一批訊號（同一份 layer2 快照、同一 T+1 開盤入場），
再加：3% 止蝕 → 1R；2R 減 33%；ATRX8（50MA + 8×ATR）減 33%；其餘拖 10EMA。

用法：python -X utf8 l2_cell_detail.py [--top 20] [--since 20260915]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from collections import Counter

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_cell_backtest as B                                  # noqa: E402

STOP_PCT = 0.03          # SOUL §4.3：3% 係上限
TRIM_R = 2.0
ATRX_HI = 8.0


def ema(vals, n=10):
    k = 2.0 / (n + 1)
    e = vals[0]
    for v in vals[1:]:
        e = v * k + e * (1 - k)
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=3)      # Desmond：只限 3 隻
    ap.add_argument("--since", default=None)
    ap.add_argument("--mode", default="today", choices=["today", "latest", "backtest"])
    a = ap.parse_args()

    px = B.load_px()
    if not px:
        return 1
    snaps = B.snapshots()
    recs, seen = [], set()

    for day_s, path in snaps:
        if a.since and day_s < a.since:
            continue
        try:
            d = json.load(io.open(path, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for src, key in (("FOCUS", "focus_list"), ("STALK", "stalk_list")):
            for r in (d.get(key) or []):
                t = (r.get("ticker") or "").upper()
                if not t or (day_s, t) in seen:
                    continue
                seen.add((day_s, t))
                df = B.series(px, t)
                if df is None:
                    continue
                day = pd.Timestamp(f"{day_s[:4]}-{day_s[4:6]}-{day_s[6:]}")
                if day not in df.index:
                    idx = df.index[df.index <= day]
                    if len(idx) == 0:
                        continue
                    day = idx[-1]
                after = df.loc[day:]
                if len(after) < 4:
                    continue
                entry = float(after["o"].iloc[1])
                if not entry:
                    continue
                stop = entry * (1 - STOP_PCT)
                risk = entry - stop
                win = after.iloc[1:21]                    # 最長 20 日
                if len(win) < 2:
                    continue
                # 先觸邊一樣？
                hit2r_at = None
                stop_at = None
                for i in range(len(win)):
                    hi, lo = float(win["h"].iloc[i]), float(win["l"].iloc[i])
                    if lo <= stop and stop_at is None:
                        stop_at = i
                    if hi >= entry + TRIM_R * risk and hit2r_at is None:
                        hit2r_at = i
                    if stop_at is not None or hit2r_at is not None:
                        break
                # MFE 只計到「先觸發事件」為止（停蝕後嘅反彈唔算）
                if stop_at is not None and (hit2r_at is None or stop_at < hit2r_at):
                    _w = win.iloc[:stop_at + 1]
                    mfe_r = (float(_w["h"].max()) / entry - 1) / STOP_PCT
                    last_r = -1.0
                else:
                    mfe_r = (float(win["h"].max()) / entry - 1) / STOP_PCT
                    last_r = (float(win["c"].iloc[-1]) / entry - 1) / STOP_PCT
                ma50 = float(df["c"].loc[:day].tail(50).mean())
                tr = (df["h"] - df["l"]).loc[:day].tail(14).mean()
                atrx8 = ma50 + ATRX_HI * float(tr)
                e10 = ema(list(df["c"].loc[:day].tail(40)))
                recs.append(dict(
                    day=day_s, ticker=t, src=src, entry=round(entry, 2),
                    stop=round(stop, 2), r1=round(risk, 2),
                    mfe_r=round(mfe_r, 2), last_r=round(last_r, 2),
                    first="2R" if (hit2r_at is not None and
                                   (stop_at is None or hit2r_at < stop_at))
                          else ("STOP" if stop_at is not None else "—"),
                    trim2r=round(entry + TRIM_R * risk, 2),
                    atrx8=round(atrx8, 2), e10=round(e10, 2)))

    if not recs:
        print("冇樣本")
        return 1

    # 去重：同一隻股連續幾日入選，只計第一次（避免同一段升幅重複計算）
    _first = {}
    for r in sorted(recs, key=lambda x: x["day"]):
        _first.setdefault(r["ticker"], r)
    _dups = len(recs) - len(_first)
    recs = list(_first.values())
    _days = {}
    for r in recs:
        _days.setdefault(r["ticker"], []).append(r["day"])
    for r in recs:
        r["repeat"] = len(_days[r["ticker"]]) - 1
        r["new"] = (r["day"] == snaps[-1][0])

    if a.mode == "today":
        day_s, path = snaps[-1]
        d0 = json.load(io.open(path, encoding="utf-8"))
        cand = []
        for src, key in (("FOCUS", "focus_list"), ("STALK", "stalk_list")):
            for r in (d0.get(key) or []):
                cand.append((r.get("score") or 0, src, r))
        cand.sort(key=lambda x: -x[0])
        prev_snaps = [p2 for d2, p2 in snaps[:-1]][-5:]
        seen_before = set()
        for p2 in prev_snaps:
            try:
                dd = json.load(io.open(p2, encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for k in ("focus_list", "stalk_list"):
                for r in (dd.get(k) or []):
                    seen_before.add((r.get("ticker") or "").upper())
        _pxlast = max(str(b[-1][0]) for b in px.values())
        print(f"今日快照 {day_s}｜候選 {len(cand)} 隻｜只列 {a.top} 隻（配額上限）"
              f"｜🆕 價格 {_pxlast}")
        print("標記       代號    來源   參考價   止蝕    1R     2R減33%  ATRX8   10EMA")
        out = []
        for score, src, r in cand[:a.top]:
            t = (r.get("ticker") or "").upper()
            df = B.series(px, t)
            if df is None:
                continue
            px_ = float(df["c"].iloc[-1])
            stop = px_ * (1 - STOP_PCT)
            r1 = px_ - stop
            ma50 = float(df["c"].tail(50).mean())
            tr = (df["h"] - df["l"]).tail(14).mean()
            e10 = ema(list(df["c"].tail(40)))
            tag = "↻ 重複" if t in seen_before else "🆕 新"
            print(f"{tag:<9}{t:<7}{src:<6}{px_:<9.2f}{stop:<8.2f}{r1:<7.2f}"
                  f"{px_ + 2 * r1:<9.2f}{ma50 + ATRX_HI * float(tr):<8.2f}{e10:.2f}")
            out.append({"ticker": t, "src": src, "ref": round(px_, 2),
                        "stop": round(stop, 2), "trim2r": round(px_ + 2 * r1, 2),
                        "atrx8": round(ma50 + ATRX_HI * float(tr), 2),
                        "e10": round(e10, 2), "new": t not in seen_before,
                        "score": score})
        json.dump({"as_of": day_s, "limit": a.top, "rows": out},
                  io.open(os.path.join(B.OUT, "l2_cell_today.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("OK output/l2_cell_today.json（3 隻上限，待評分）")
        return 0

    if a.mode == "latest":
        last = max(r["day"] for r in recs)      # 最新一日「有訊號」嘅快照
        cur = [r for r in recs if r["day"] == last]
        cur.sort(key=lambda r: -(r.get("mfe_r") or 0))
        cur = cur[:a.top]
        print(f"最新快照 {last}｜訊號 {len([r for r in recs if r['day']==last])} 隻"
              f"｜只列 {len(cur)} 隻（配額上限）")
        print("標記       代號    來源   入場    止蝕    1R    2R減33%  ATRX8   10EMA")
        for r in cur:
            tag = "🆕 新" if r["repeat"] == 0 else f"↻ 重複{r['repeat']}日"
            print(f"{tag:<9}{r['ticker']:<7}{r['src']:<6}{r['entry']:<8}{r['stop']:<7}"
                  f"{r['r1']:<6}{r['trim2r']:<9}{r['atrx8']:<7}{r['e10']}")
        json.dump({"as_of": last, "limit": a.top, "rows": cur},
                  io.open(os.path.join(B.OUT, "l2_cell_latest.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("OK output/l2_cell_latest.json（3 隻上限）")
        return 0

    recs.sort(key=lambda r: -r["mfe_r"])
    n = len(recs)
    hit2 = sum(1 for r in recs if r["first"] == "2R")
    stop = sum(1 for r in recs if r["first"] == "STOP")
    print(f"（原始 {n + _dups} 筆 → 去重後 {n} 隻，重複訊號 {_dups} 筆）")
    print(f"樣本 {n}｜先到 2R {hit2}（{100*hit2/n:.1f}%）｜先止蝕 {stop} "
          f"（{100*stop/n:.1f}%）｜平均 MFE {sum(r['mfe_r'] for r in recs)/n:+.2f}R")
    print()
    print("日期      代號    來源   入場    止蝕   1R    MFE(R) 先到  2R減33%  ATRX8  10EMA")
    for r in recs[:a.top]:
        print(f"{r['day']} {r['ticker']:<7}{r['src']:<6}{r['entry']:<8}{r['stop']:<7}"
              f"{r['r1']:<5}{r['mfe_r']:>+6.2f} {r['first']:<6}"
              f"{r['trim2r']:<9}{r['atrx8']:<7}{r['e10']}")

    print("\n最好 5 隻（MFE）：")
    for r in recs[:5]:
        print(f"  {r['ticker']}: {r['mfe_r']:+.2f}R｜2R {r['trim2r']}｜ATRX8 {r['atrx8']}")
    print("最差 5 隻：")
    for r in recs[-5:]:
        print(f"  {r['ticker']} {r['day']}: {r['mfe_r']:+.2f}R｜先到 {r['first']}")

    json.dump({"n": n, "hit2r": hit2, "stopped": stop, "rows": recs},
              io.open(os.path.join(B.OUT, "l2_cell_detail.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n✓ output/l2_cell_detail.json（{n} 筆）")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
