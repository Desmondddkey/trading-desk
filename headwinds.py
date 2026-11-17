# -*- coding: utf-8 -*-
"""headwinds.py — 四大宏觀逆風（Ted Zhang, Revere Asset Management 2026-11）。

四個條件（歷史上同時出現 → 2000／2022 式回撤）：
  1. 防禦跑贏        XLP ÷ SPY 20 日變化 > 0（必需消費跑贏大市）
  2. 美元近高位      DXY ≥ 52 週高嘅 98%
  3. 10 年債息急升   ^TNX 6 個月 ≥ +0.40pp，或 20 日 ≥ +0.25pp
  4. 加息已計價      2 年債息（FRED DGS2）− 聯邦基金（DFF）≥ +0.50pp

輸出 data/headwinds.json：每項 flag／數值／一句風險描述，加總体風險等級。
"""
from __future__ import annotations

import csv
import io
import json
import os
import urllib.request
from datetime import datetime, timezone

import yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "headwinds.json")
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s"


def _series(t, period="1y"):
    d = yf.download(t, period=period, progress=False, auto_adjust=False)
    s = d["Close"]
    if hasattr(s, "columns"):
        s = s.iloc[:, 0]
    return s.dropna()


def _fred(series_id):
    try:
        with urllib.request.urlopen(FRED % series_id, timeout=30) as r:
            rows = list(csv.reader(io.StringIO(r.read().decode("utf-8"))))
    except Exception:                                            # noqa: BLE001
        return None
    vals = []
    for row in rows[1:]:
        if len(row) < 2 or not row[1] or row[1] == ".":
            continue
        try:
            vals.append((row[0], float(row[1])))
        except ValueError:
            continue
    return vals[-1][1] if vals else None


def main():
    out = {"asOf": None, "flags": [], "count": 0, "risk": "", "advice": "", "notes": []}
    flags = []

    try:
        xlp, spy = _series("XLP"), _series("SPY")
        n = min(len(xlp), len(spy))
        ratio = xlp.iloc[-n:] / spy.iloc[-n:]
        ch20 = float(ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100 if n > 21 else None
        flags.append({
            "key": "defensive",
            "name": "防禦跑贏大市",
            "on": (ch20 is not None and ch20 > 0),
            "value": f"XLP/SPY 20日 {ch20:+.2f}%" if ch20 is not None else "—",
            "desc": "必需消費跑贏＝資金由增長股流向避險；歷史上係回撤前段特徵。",
        })
        out["asOf"] = str(xlp.index[-1])[:10]
    except Exception as e:                                       # noqa: BLE001
        out["notes"].append(f"XLP/SPY：{type(e).__name__}")

    try:
        dxy = _series("DX-Y.NYB")
        last, hi = float(dxy.iloc[-1]), float(dxy.tail(252).max())
        pct = 100 * last / hi
        flags.append({
            "key": "dollar",
            "name": "美元接近 52 週高",
            "on": pct >= 98.0,
            "value": f"DXY {last:.2f}（高位 {hi:.2f} 嘅 {pct:.1f}%）",
            "desc": "強美元收緊全球流動性、壓縮企業海外盈利，係風險資產逆風。",
        })
    except Exception as e:                                       # noqa: BLE001
        out["notes"].append(f"DXY：{type(e).__name__}")

    try:
        tnx = _series("^TNX")
        last = float(tnx.iloc[-1])
        ch6m = last - float(tnx.iloc[-126]) if len(tnx) > 126 else None
        ch20 = last - float(tnx.iloc[-21]) if len(tnx) > 21 else None
        on = bool((ch6m is not None and ch6m >= 0.40) or (ch20 is not None and ch20 >= 0.25))
        flags.append({
            "key": "yield10",
            "name": "10 年債息急升",
            "on": on,
            "value": f"10Y {last:.2f}%｜6個月 {ch6m:+.2f}pp｜20日 {ch20:+.2f}pp"
                     if ch6m is not None and ch20 is not None else f"10Y {last:.2f}%",
            "desc": "長息急升壓縮估值（特別高 PE 增長股），同时推高借貸成本。",
        })
    except Exception as e:                                       # noqa: BLE001
        out["notes"].append(f"TNX：{type(e).__name__}")

    try:
        dgs2, dff = _fred("DGS2"), _fred("DFF")
        spread = (dgs2 - dff) if (dgs2 is not None and dff is not None) else None
        flags.append({
            "key": "hikes",
            "name": "加息已計價",
            "on": bool(spread is not None and spread >= 0.50),
            "value": f"2Y {dgs2:.2f}% − 聯邦基金 {dff:.2f}% = {spread:+.2f}pp"
                     if spread is not None else "—",
            "desc": "2 年息高於聯邦基金＝市場已 price in 進一步加息；歷史上出現喺 2000／2022。",
        })
    except Exception as e:                                       # noqa: BLE001
        out["notes"].append(f"DGS2/DFF：{type(e).__name__}")

    cnt = sum(1 for f in flags if f["on"])
    if cnt <= 1:
        risk, adv = "低", "逆風未形成；照常按配額執行，維持 0.5% 風險上限。"
    elif cnt == 2:
        risk, adv = "中", "兩項同時出現：減慢加倉節奏，只做 A+ 關鍵球，唔追高。"
    elif cnt == 3:
        risk, adv = "高", "三項同時出現：新倉減半（0.25% 探路）、優先收緊止蝕、留現金。"
    else:
        risk, adv = "極高", "四項全中＝2000／2022 式組合：唔開新倉，只管理現有持倉並提高現金比重。"

    out.update({"flags": flags, "count": cnt, "risk": risk, "advice": adv,
                "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"✓ 宏觀逆風 {cnt}/4｜風險 {risk}｜{out['asOf']}")
    for f in flags:
        print(f"   {'⚠' if f['on'] else '·'} {f['name']:<12}{f['value']}")
    if out["notes"]:
        print("⚠ " + "、".join(out["notes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
