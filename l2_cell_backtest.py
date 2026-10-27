# -*- coding: utf-8 -*-
"""l2_cell_backtest.py — L2 買入區「邊一格最容易升」回測

問題（Desmond 2026-10-28）：
  Daily Scan 位置圖分 4 個 X 區 × 4 個 Y 區，邊一格嘅股最容易升？
  FOCUS 同 STALK 邊個好？

方法（第一性原理，唔用感覺）
  1. 用歷史 layer2_*.json 快照（每日最後一次），每 (date, ticker) 只保留一次
  2. X = (收市 − EMA21) / ATR14；Y = atr_ext_50ma（距 50MA，ATR 單位）
  3. 入場 = 快照日之後第一個交易日開盤（T+1 開盤，唔用快照日收市）
  4. 出場指標：5/10/20 日收市回報、10 日內最大有利幅度（MFE）、20 日勝率
  5. 按 X 格、Y 格、來源（FOCUS/STALK）分組

判讀門檻（事先寫死）
  n ≥ 30 才報；n < 30 = 「樣本不足」

輸出：output/l2_cell_backtest.json + console
用法：python trading-os-web/l2_cell_backtest.py
"""
from __future__ import annotations

import glob
import io
import json
import os
import pickle
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = r"C:/Users/rain0/trading-os"
OUT = os.path.join(HERE, "output")
PICKLE = os.path.join(HERE, "data", "tight_prices.pkl")
MIN_N = 30

XB = ((0, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 99))
YB = ((0, 1), (1, 2), (2, 4), (4, 99))


def log(m):
    print(m, file=sys.stderr)


def load_px():
    try:
        return pickle.load(io.open(PICKLE, "rb"))
    except Exception as e:                                    # noqa: BLE001
        log(f"✗ {PICKLE} 讀唔到：{e}")
        return {}


def snapshots():
    """每日最後一份快照（同一日多份只取最夜）。"""
    best = {}
    for f in sorted(glob.glob(os.path.join(LIVE, "output", "layer2_*.json"))):
        b = os.path.basename(f)[7:15]          # YYYYMMDD
        best[b] = f                            # sorted → 最後覆蓋
    return sorted(best.items())


def series(px, t):
    bars = px.get(t)
    if not bars or len(bars) < 80:
        return None
    df = pd.DataFrame(bars, columns=["date", "o", "h", "l", "c", "v"])
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


def x_val(df, day):
    """快照日嘅 X = (收市 − EMA21) / ATR14"""
    sub = df.loc[:day]
    if len(sub) < 30:
        return None
    c = sub["c"]
    k = 2 / 22.0
    ema = c.iloc[0]
    for v in c.iloc[1:]:
        ema = v * k + ema * (1 - k)
    tr = (sub["h"] - sub["l"]).tail(14).mean()
    if not tr:
        return None
    return (float(c.iloc[-1]) - ema) / tr


def fwd(df, day, horizon):
    """T+1 開盤入場；回傳 (ret_close, mfe, ok)"""
    after = df.loc[day:]
    if len(after) < horizon + 2:
        return None
    entry = float(after["o"].iloc[1])
    if not entry:
        return None
    end = after["c"].iloc[min(horizon, len(after) - 1)]
    mfe = float(after["h"].iloc[1:horizon + 1].max()) / entry - 1
    return ((float(end) / entry - 1) * 100, mfe * 100)


def bucket(v, edges):
    if v is None:
        return None
    for lo, hi in edges:
        if lo <= v < hi:
            return f"{lo:g}–{hi:g}" if hi < 90 else f"≥{lo:g}"
    return None


def main():
    px = load_px()
    if not px:
        return 1
    snaps = snapshots()
    log(f"快照 {len(snaps)} 日：{snaps[0][0]} → {snaps[-1][0]}")

    recs = []
    seen = set()
    for day_s, path in snaps:
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
                df = series(px, t)
                if df is None:
                    continue
                day = pd.Timestamp(f"{day_s[:4]}-{day_s[4:6]}-{day_s[6:]}")
                if day not in df.index:
                    idx = df.index[df.index <= day]
                    if len(idx) == 0:
                        continue
                    day = idx[-1]
                xv = x_val(df, day)
                yv = r.get("atr_ext_50ma")
                f20 = fwd(df, day, 20)
                if f20 is None:
                    continue
                f5 = fwd(df, day, 5)
                f10 = fwd(df, day, 10)
                recs.append(dict(day=day_s, ticker=t, src=src,
                                 x=xv, y=float(yv) if isinstance(yv, (int, float)) else None,
                                 score=r.get("score"),
                                 r20=f20[0], mfe20=f20[1],
                                 r10=f10[0] if f10 else None,
                                 r5=f5[0] if f5 else None))
    log(f"有效樣本 {len(recs)} 筆")

    def agg(rows):
        if not rows:
            return None
        r20 = [r["r20"] for r in rows]
        return dict(n=len(rows),
                    win=round(100.0 * sum(1 for v in r20 if v > 0) / len(r20), 1),
                    avg20=round(float(np.mean(r20)), 2),
                    med20=round(float(np.median(r20)), 2),
                    avg_mfe=round(float(np.mean([r["mfe20"] for r in rows])), 2))

    # ① X × Y 格
    cells = defaultdict(list)
    for r in recs:
        bx, by = bucket(r["x"], XB), bucket(r["y"], YB)
        if bx and by:
            cells[(bx, by)].append(r)
    print("\n=== 買入區格（X 距21EMA × Y 距50MA）｜20 日 ===")
    print(f"{'X':>10} {'Y':>6} {'n':>5} {'勝率':>6} {'平均':>7} {'中位':>7} {'MFE':>7}")
    out_cells = []
    for (bx, by), rows in sorted(cells.items(), key=lambda kv: -len(kv[1])):
        a = agg(rows)
        if a["n"] < MIN_N:
            continue
        print(f"{bx:>10} {by:>6} {a['n']:>5} {a['win']:>5.1f}% "
              f"{a['avg20']:>+6.2f}% {a['med20']:>+6.2f}% {a['avg_mfe']:>+6.2f}%")
        out_cells.append(dict(x=bx, y=by, **a))

    # ② FOCUS vs STALK
    print("\n=== FOCUS vs STALK ===")
    out_src = {}
    for src in ("FOCUS", "STALK"):
        a = agg([r for r in recs if r["src"] == src])
        if a and a["n"] >= MIN_N:
            print(f"{src:6s} n={a['n']:>4} 勝率 {a['win']:>5.1f}% "
                  f"平均 {a['avg20']:>+6.2f}% 中位 {a['med20']:>+6.2f}% "
                  f"MFE {a['avg_mfe']:>+6.2f}%")
            out_src[src] = a
        elif a:
            print(f"{src:6s} n={a['n']} 樣本不足")

    # ③ Y 單獨（買入區內）
    print("\n=== Y（距 50MA）單獨 ===")
    out_y = {}
    for lo, hi in YB:
        lbl = f"{lo:g}–{hi:g}" if hi < 90 else f"≥{lo:g}"
        rows = [r for r in recs if bucket(r["y"], YB) == lbl]
        a = agg(rows)
        if a and a["n"] >= MIN_N:
            print(f"Y {lbl:>6} n={a['n']:>4} 勝率 {a['win']:>5.1f}% "
                  f"平均 {a['avg20']:>+6.2f}% MFE {a['avg_mfe']:>+6.2f}%")
            out_y[lbl] = a

    # ④ 整體基準
    base = agg(recs)
    print(f"\n全部（基準） n={base['n']} 勝率 {base['win']}% "
          f"平均 {base['avg20']:+.2f}% 中位 {base['med20']:+.2f}%")

    os.makedirs(OUT, exist_ok=True)
    json.dump({"days": [snaps[0][0], snaps[-1][0]], "n": len(recs),
               "base": base, "cells": out_cells, "src": out_src, "y": out_y},
              io.open(os.path.join(OUT, "l2_cell_backtest.json"), "w",
                      encoding="utf-8"), ensure_ascii=False, indent=1)
    # 每日累積（append-only），用嚟睇結論會唔會隨時間改變
    with io.open(os.path.join(OUT, "l2_cell_hist.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"run": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                            "days": [snaps[0][0], snaps[-1][0]],
                            "n": len(recs), "base": base,
                            "src": out_src, "y": out_y,
                            "cells": out_cells}, ensure_ascii=False) + "\n")
    log("✓ output/l2_cell_backtest.json + l2_cell_hist.jsonl")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
