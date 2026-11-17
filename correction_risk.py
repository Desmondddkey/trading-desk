# -*- coding: utf-8 -*-
"""correction_risk.py — 修正風險模型（自建，非價格主導）。

⚠️ 誠實聲明：The Setup Factory 嘅原模型**冇公開公式**（作者：based on a discovery
   I made）。呢個係用同一思路（非價格、結構裂縫、0–4 級、黏住唔亂 reset）
   自行設計嘅可重算版本，唔係原作者模型，數字亦唔會同佢一樣。

五個構件（每個 0/1）：
  1. 廣度背離    指數貼近 52 週高，但站上 40MA 嘅比例低過自己 20 日均值 ≥3pp
  2. 信貸轉弱    HYG ÷ SPY 20 日變化 ≤ −1.5%（信用先於股票轉差）
  3. 利率／美元   DXY ≥ 52 週高 98%，或 10Y 20 日 ≥ +0.15pp
  4. 波動結構    VIX > 自己 10 日均，且 VIX ≥ 18
  5. 新高動能衰減 新高新低淨值 10 日均 < 0，且 5 日前 > 0（由正轉負）

輸出 data/correction_risk.json（含 0–4 級、黏性狀態、歷史）。
"""
from __future__ import annotations

import glob
import io
import json
import os
from datetime import datetime, timezone

import yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "correction_risk.json")
STATE = os.path.join(HERE, "data", "correction_risk_state.json")
TS = r"C:\Users\rain0\trading-os"


def _j(p, d=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return d


def _px(ticker, period="1y"):
    d = yf.download(ticker, period=period, progress=False, auto_adjust=False)
    s = d["Close"]
    if hasattr(s, "columns"):
        s = s.iloc[:, 0]
    return s.dropna()


def _latest(pat):
    fs = sorted(glob.glob(pat))
    return fs[-1] if fs else None


def main():
    comps = []
    breadth = _j(_latest(os.path.join(TS, "output", "breadth_*.json")) or "", {}) or {}
    as_of = (breadth.get("as_of") or "")[:10] or None

    # 1) 廣度背離
    try:
        spy = _px("SPY")
        hi = float(spy.tail(252).max())
        near_hi = float(spy.iloc[-1]) >= hi * 0.97
        p40 = (breadth.get("series") or {}).get("pct40ma") or []
        p40 = [x for x in p40 if x is not None]
        cur = p40[-1] if p40 else None
        avg20 = sum(p40[-20:]) / len(p40[-20:]) if len(p40) >= 20 else None
        gap = (cur - avg20) if (cur is not None and avg20 is not None) else None
        on = bool(near_hi and gap is not None and gap <= -3.0)
        comps.append({"key": "breadth", "name": "廣度背離", "on": on,
                      "value": f"指數距52高 {(spy.iloc[-1]/hi-1)*100:+.1f}%｜"
                               f"40MA 比例 {cur:.1f}%（20日均 {avg20:.1f}）"
                      if gap is not None else "—",
                      "desc": "指數仲喺高位，但參與度已回落＝升勢由少數股票撐住。"})
    except Exception as e:                                       # noqa: BLE001
        comps.append({"key": "breadth", "name": "廣度背離", "on": False,
                      "value": "—", "desc": f"計算失敗 {type(e).__name__}"})

    # 2) 信貸轉弱
    try:
        hyg, spy2 = _px("HYG"), _px("SPY")
        n = min(len(hyg), len(spy2))
        r = (hyg.iloc[-n:] / spy2.iloc[-n:]).dropna()
        ch = float(r.iloc[-1] / r.iloc[-21] - 1) * 100
        comps.append({"key": "credit", "name": "信貸轉弱", "on": ch <= -1.5,
                      "value": f"HYG÷SPY 20日 {ch:+.2f}%",
                      "desc": "高收益債跑輸＝資金先撤風險資產，通常早過股票見頂。"})
    except Exception as e:                                       # noqa: BLE001
        comps.append({"key": "credit", "name": "信貸轉弱", "on": False,
                      "value": "—", "desc": f"計算失敗 {type(e).__name__}"})

    # 3) 利率／美元
    try:
        dxy, tnx = _px("DX-Y.NYB"), _px("^TNX")
        pct = 100 * float(dxy.iloc[-1]) / float(dxy.tail(252).max())
        ch20 = float(tnx.iloc[-1]) - float(tnx.iloc[-21]) if len(tnx) > 21 else 0.0
        on = bool(pct >= 98.0 or ch20 >= 0.15)
        comps.append({"key": "rates", "name": "利率／美元", "on": on,
                      "value": f"DXY 高位 {pct:.1f}%｜10Y 20日 {ch20:+.2f}pp",
                      "desc": "美元強或長息急升＝估值同流動性同時受壓。"})
    except Exception as e:                                       # noqa: BLE001
        comps.append({"key": "rates", "name": "利率／美元", "on": False,
                      "value": "—", "desc": f"計算失敗 {type(e).__name__}"})

    # 4) 波動結構
    try:
        vix = _px("^VIX", "6mo")
        last = float(vix.iloc[-1])
        ma10 = float(vix.tail(10).mean())
        on = bool(last > ma10 and last >= 18)
        comps.append({"key": "vol", "name": "波動結構", "on": on,
                      "value": f"VIX {last:.2f}（10日均 {ma10:.2f}）",
                      "desc": "波動由低位回升＝對沖需求增加，回撤風險升。"})
    except Exception as e:                                       # noqa: BLE001
        comps.append({"key": "vol", "name": "波動結構", "on": False,
                      "value": "—", "desc": f"計算失敗 {type(e).__name__}"})

    # 5) 新高動能衰減
    try:
        nnnl = (breadth.get("series") or {}).get("nnnl") or []
        nnnl = [x for x in nnnl if x is not None]
        cur = nnnl[-1] if nnnl else None
        prev5 = nnnl[-6] if len(nnnl) >= 6 else None
        on = bool(cur is not None and cur < 0 and prev5 is not None and prev5 > 0)
        comps.append({"key": "highs", "name": "新高動能衰減", "on": on,
                      "value": f"新高新低淨值 {cur:+.1f}（5日前 {prev5:+.1f}）"
                      if cur is not None and prev5 is not None else "—",
                      "desc": "由淨新高轉淨新低＝內部結構開始破裂。"})
    except Exception as e:                                       # noqa: BLE001
        comps.append({"key": "highs", "name": "新高動能衰減", "on": False,
                      "value": "—", "desc": f"計算失敗 {type(e).__name__}"})

    raw = sum(1 for c in comps if c["on"])
    level_raw = min(4, raw)

    # 黏性：升級即刻；降級要連續 5 個交易日確認
    stt = _j(STATE, {}) or {}
    prev_level = int(stt.get("level") or 0)
    prev_date = stt.get("date")
    quiet = int(stt.get("quiet_days") or 0)
    if raw >= prev_level:
        level, quiet = raw, 0
    else:
        quiet += 1
        level = prev_level if quiet < 5 else raw
        if quiet >= 5:
            quiet = 0

    today = as_of or datetime.now(timezone.utc).date().isoformat()
    hist = stt.get("history") or []
    if not hist or hist[-1].get("date") != today:
        hist.append({"date": today, "raw": raw, "level": level})

    state = {"date": today, "level": level, "raw": raw, "quiet_days": quiet,
             "history": hist[-120:]}
    io.open(STATE, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False))

    advice = {
        0: "冇結構裂縫；照常執行配額。",
        1: "早期訊號：維持風險上限，唔需要減倉。",
        2: "裂縫增加：新倉只做 A+ 關鍵球，避免追高。",
        3: "高風險：新倉減半（0.25% 探路）、收緊止蝕、留現金。",
        4: "最高級別：唔開新倉，只管理現有持倉，提高現金比重。",
    }[level]

    payload = {"asOf": today, "level": level, "rawScore": raw,
               "components": comps, "advice": advice,
               "stickyDays": quiet, "history": hist[-30:],
               "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "note": "自建版本（原作者未公開公式），唔可以當成 TSF 官方評分。"}
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(payload, ensure_ascii=False, indent=1))

    print(f"✓ 修正風險 level {level}（raw {raw}/5）｜{today}｜黏性 {quiet} 日")
    for c in comps:
        print(f"   {'⚠' if c['on'] else '·'} {c['name']:<8}{c['value']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
