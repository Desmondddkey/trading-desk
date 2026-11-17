# -*- coding: utf-8 -*-
"""screener_q.py — 把 700KB screener.json 壓成 10 行答案（慳 context 用）。

概念（Anthropic code-execution pattern）：
  唔係叫 AI 讀完成個 data 檔再推理，而係跑一個細 script，
  由 script 做過濾／排序，只把「答案」印出嚟。

用法：
  python -X utf8 screener_q.py                       # 今日關鍵球（預設）
  python -X utf8 screener_q.py --preset avwap        # 52W AVWAP 重疊
  python -X utf8 screener_q.py --min-rs 90 --max-atrx 4 --top 10
  python -X utf8 screener_q.py --ticker NVDA         # 單隻查詢
"""
from __future__ import annotations

import argparse
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SCREENER = os.path.join(HERE, "data", "screener.json")
AVWAP = os.path.join(HERE, "data", "avwap52.json")


def _j(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="key", choices=["key", "avwap", "all"])
    ap.add_argument("--min-rs", type=float, default=None)
    ap.add_argument("--max-atrx", type=float, default=None)
    ap.add_argument("--min-tight", type=float, default=None)
    ap.add_argument("--min-d52", type=float, default=None)
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--ticker", default=None)
    a = ap.parse_args()

    scr = _j(SCREENER)
    rows = scr.get("rows") or []
    avw = (_j(AVWAP).get("rows") or {})
    if not rows:
        print("DATA_UNAVAILABLE — data/screener.json")
        return 1

    if a.ticker:
        r = next((x for x in rows if x["t"] == a.ticker.upper()), None)
        if not r:
            print(f"{a.ticker.upper()} 唔喺 744 隻池入面")
            return 1
        v = avw.get(r["t"]) or {}
        print(f"{r['t']}｜{r.get('name','')[:28]}")
        print(f"  價 {r.get('close')}｜RS {r.get('rs')}｜ATRX {r.get('atrx')}｜"
              f"TIGHT {r.get('tight')}｜距52高 {r.get('d52w', r.get('off52_tv'))}%")
        print(f"  止蝕 {r.get('stop')}（{r.get('stop_kind')}）｜距pivot {r.get('dist_pivot')}%")
        print(f"  AVWAP52 {v.get('avwap','—')}｜{v.get('state','—')} {v.get('d_atr','—')} ATR")
        return 0

    def keep(r):
        rs, ax, tg = r.get("rs"), r.get("atrx"), r.get("tight")
        d52 = r.get("d52w", r.get("off52_tv"))
        if a.preset == "key":
            if rs is None or ax is None or tg is None or d52 is None:
                return False
            if not (rs >= 90 and 0 <= ax <= 4 and d52 >= -10 and tg >= 45):
                return False
        if a.preset == "avwap":
            v = avw.get(r["t"]) or {}
            if v.get("state") != "重疊":
                return False
        if a.min_rs is not None and (rs is None or rs < a.min_rs):
            return False
        if a.max_atrx is not None and (ax is None or ax > a.max_atrx):
            return False
        if a.min_tight is not None and (tg is None or tg < a.min_tight):
            return False
        if a.min_d52 is not None and (d52 is None or d52 < a.min_d52):
            return False
        return True

    sel = [r for r in rows if keep(r)]
    sel.sort(key=lambda r: -(r.get("rs") or 0))
    print(f"{a.preset}｜{len(sel)} 隻（池 {len(rows)}）｜as_of {scr.get('as_of')}")
    print("代號    價      RS  ATRX TIGHT 距52高  AVWAP")
    for r in sel[:a.top]:
        v = avw.get(r["t"]) or {}
        print(f"{r['t']:<7}{str(r.get('close')):<7}{int(r['rs']):<4}"
              f"{str(r.get('atrx')):<5}{str(r.get('tight')):<6}"
              f"{str(r.get('d52w', r.get('off52_tv'))):<7}{v.get('state','—')}")
    if len(sel) > a.top:
        print(f"… 另有 {len(sel)-a.top} 隻（用 --top 加大）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
