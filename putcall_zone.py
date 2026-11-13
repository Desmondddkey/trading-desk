# -*- coding: utf-8 -*-
"""putcall_zone.py — 「散戶買 put」逆向區間：用自己 20 年數據驗證，唔係照抄門檻。

假設（@i3_invest 2026-11-12 帖文意譯）：細價股投資者大量買入認沽期權（P/C 高）
→ 通常係短期看漲嘅逆向信號。

驗證方法
  · 用 CBOE Equity P/C 全歷史（2006→）計第 90 百分位做門檻（唔用絕對值）
  · 事件 = P/C 由下向上穿越門檻（10 個交易日冷卻，避免同一段重覆計）
  · 量事件後 20 / 40 個交易日 SPX 回報 + 贏率，同「全期基率」對照

輸出 output/putcall_zone.json
"""
from __future__ import annotations

import io
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "output", "putcall.json")
DST = os.path.join(HERE, "output", "putcall_zone.json")

PCT = 90          # 逆向區間 = P/C 第 90 百分位以上
COOLDOWN = 10     # 事件之間最少交易日
FWD = (20, 40)


def main():
    try:
        d = json.load(io.open(SRC, encoding="utf-8"))
    except (OSError, ValueError):
        print("⚠ putcall_zone：讀唔到 output/putcall.json")
        return 1
    ser = [s for s in (d.get("series") or []) if s.get("pc")]
    if len(ser) < 500:
        print(f"⚠ putcall_zone：樣本不足（{len(ser)} 日）")
        return 1

    pcs = sorted(s["pc"] for s in ser)
    thr = pcs[int(len(pcs) * PCT / 100)]

    events, last_i = [], -999
    for i, s in enumerate(ser):
        prev = ser[i - 1]["pc"] if i else None
        if prev is None or s["pc"] < thr or prev >= thr:
            continue
        if i - last_i < COOLDOWN:
            continue
        last_i = i
        ev = {"d": s["d"], "pc": s["pc"], "spx": s.get("spx")}
        for k in FWD:
            if i + k < len(ser) and ser[i + k].get("spx") and s.get("spx"):
                ev[f"fwd{k}"] = round((ser[i + k]["spx"] / s["spx"] - 1) * 100, 2)
        events.append(ev)

    def stat(key):
        v = [e[key] for e in events if e.get(key) is not None]
        if not v:
            return {"n": 0}
        return {"n": len(v), "avg": round(statistics.mean(v), 2),
                "win": round(100 * sum(1 for x in v if x > 0) / len(v), 0),
                "min": round(min(v), 2), "max": round(max(v), 2)}

    # 基率：全期任何一日之後 20/40 日 SPX 回報
    base = {}
    for k in FWD:
        v = []
        for i, s in enumerate(ser):
            if i + k < len(ser) and s.get("spx") and ser[i + k].get("spx"):
                v.append((ser[i + k]["spx"] / s["spx"] - 1) * 100)
        base[k] = {"n": len(v), "avg": round(statistics.mean(v), 2),
                   "win": round(100 * sum(1 for x in v if x > 0) / len(v), 0)}

    cur = d.get("latest") or {}
    pc_now = cur.get("pc")
    above = pc_now is not None and pc_now >= thr

    out = {
        "as_of": d.get("as_of"),
        "pctile": PCT,
        "threshold": round(thr, 3),
        "current_pc": pc_now,
        "in_zone": bool(above),
        "events": events[-40:],
        "n_events": len(events),
        "stats": {f"fwd{k}": stat(f"fwd{k}") for k in FWD},
        "baseline": base,
        "cooldown": COOLDOWN,
        "note": ("門檻用全歷史第 90 百分位；事件 = 由下向上穿越；"
                 "回報以事件日 SPX 收市起計，唔計交易成本。"),
    }
    with io.open(DST, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    st20 = out["stats"]["fwd20"]
    print(f"📉 散戶買 put 逆向區間：門檻 P/C ≥ {thr:.3f}（第 {PCT} 百分位）")
    print(f"   今日 P/C {pc_now}｜{'在區間內' if above else '未到門檻'}")
    if st20.get("n"):
        print(f"   歷史上 {len(events)} 次穿越；之後 20 日平均 {st20['avg']:+.2f}%"
              f"（贏率 {st20['win']:.0f}%，n={st20['n']}）；"
              f"全期基率 {base[20]['avg']:+.2f}%")
        st40 = out["stats"]["fwd40"]
        if st40.get("n"):
            print(f"   之後 40 日平均 {st40['avg']:+.2f}%（贏率 {st40['win']:.0f}%）"
                  f"；基率 {base[40]['avg']:+.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
