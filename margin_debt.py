# -*- coding: utf-8 -*-
"""margin_debt.py — 保證金債務 × QQQ（RAE 重建）

來源（官方，非二手）
  FINRA Margin Statistics 公開 xlsx：
  https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx
  欄位：Year-Month / Debit Balances in Customers' Securities Margin Accounts（百萬美元）
  QQQ：yfinance 日線
輸出 output/margin_debt.json

圖表規則（照原圖）
  · 左軸：保證金債務（萬億美元）｜右軸：QQQ 收市
  · 柱：月度增減（負 = 去槓桿）
  · 陰影：QQQ 主要回調 ≥ 7%（peak → trough）
  · 標註：歷史高位、收縮事件（跌幅 ≥ 4%）
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r"C:/Users/rain0/trading-os/output/margin_debt.json"
CACHE = os.path.join(HERE, "data", "finra_margin.xlsx")
URL = "https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx"
DD_THRESHOLD = 7.0          # 原圖：QQQ 主要回調 ≥7%
SHRINK_MIN = 4.0            # 原圖標註 4.5% / 9.2% / 10.5% / 33.3%


def _finra():
    import urllib.request
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    fresh = (os.path.exists(CACHE) and
             (time.time() - os.path.getmtime(CACHE)) < 7 * 86400)
    if not fresh:
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r, io.open(CACHE, "wb") as f:
                f.write(r.read())
        except Exception as e:                               # noqa: BLE001
            if not os.path.exists(CACHE):
                raise RuntimeError(f"FINRA 下載失敗：{e}") from None
    d = pd.read_excel(CACHE, header=0)
    d.columns = ["ym", "debit", "cash_free", "sec_free"][:len(d.columns)]
    d["ym"] = pd.to_datetime(d["ym"].astype(str), format="%Y-%m", errors="coerce")
    d = d.dropna(subset=["ym"]).sort_values("ym")
    d["debit"] = pd.to_numeric(d["debit"], errors="coerce") / 1e6   # → 萬億美元
    return d.dropna(subset=["debit"]).set_index("ym")["debit"]


def _qqq():
    import yfinance as yf
    d = yf.download("QQQ", period="10y", interval="1d", progress=False,
                    auto_adjust=False)
    if hasattr(d.columns, "levels"):
        d.columns = [c[0] for c in d.columns]
    return d["Close"].dropna()


def _drawdowns(q: pd.Series, thresh=DD_THRESHOLD):
    """回傳 list[(start, trough, end, dd%)]，end = 收復前高當日。"""
    out = []
    peak = q.iloc[0]
    peak_d = q.index[0]
    start = trough_d = None
    trough = peak
    for d, v in q.items():
        if v >= peak:
            if start is not None and (trough / peak - 1) * 100 <= -thresh:
                out.append((str(start.date()), str(trough_d.date()),
                            str(d.date()), round((trough / peak - 1) * 100, 2)))
            peak, peak_d, start, trough, trough_d = v, d, None, v, None
        else:
            if start is None:
                start = peak_d
            if v < trough:
                trough, trough_d = v, d
    if start is not None and (trough / peak - 1) * 100 <= -thresh:
        out.append((str(start.date()), str(trough_d.date()), None,
                    round((trough / peak - 1) * 100, 2)))
    return out


def main() -> int:
    m = _finra()
    q = _qqq()
    mom = m.diff()
    peak = m.max()
    peak_d = m.idxmax()
    cur = m.iloc[-1]
    prev = m.iloc[-2]
    last12 = m.tail(13)

    # 收縮事件（月度跌幅 ≥ SHRINK_MIN）
    shrinks = []
    for d, v in m.pct_change().items():
        if pd.notna(v) and v * 100 <= -SHRINK_MIN:
            shrinks.append({"ym": d.strftime("%Y-%m"),
                            "pct": round(float(v) * 100, 2),
                            "level": round(float(m.loc[d]), 4)})

    # 最近一次回撤 + 回補比例
    recovery = None
    dd_from_peak = (cur / peak - 1) * 100
    try:
        trough_i = m.loc[peak_d:].idxmin()
        trough_v = m.loc[trough_i]
        after = m.loc[trough_i:]
        gain = cur - trough_v
        drop = peak - trough_v
        recovery = {"peak_ym": peak_d.strftime("%Y-%m"), "peak": round(float(peak), 4),
                    "trough_ym": trough_i.strftime("%Y-%m"), "trough": round(float(trough_v), 4),
                    "now": round(float(cur), 4),
                    "drop_pct": round(float((trough_v / peak - 1) * 100), 2),
                    "recovered_pct": round(float(gain / drop * 100), 1) if drop else None}
    except Exception:                                        # noqa: BLE001
        pass

    payload = {
        "as_of": m.index[-1].strftime("%Y-%m"),
        "level_tn": round(float(cur), 4),
        "prev_tn": round(float(prev), 4),
        "mom_tn": round(float(mom.iloc[-1]), 4),
        "mom_pct": round(float((cur / prev - 1) * 100), 2),
        "peak_tn": round(float(peak), 4),
        "peak_ym": peak_d.strftime("%Y-%m"),
        "from_peak_pct": round(float(dd_from_peak), 2),
        "recovery": recovery,
        "shrinks": shrinks[-8:],
        "series": [{"ym": d.strftime("%Y-%m"), "debit_tn": round(float(v), 4),
                    "mom_tn": (round(float(mom.loc[d]), 4) if pd.notna(mom.loc[d]) else None)}
                   for d, v in m.loc["2022-01":].items()],
        "qqq_last": round(float(q.iloc[-1]), 2),
        "qqq_date": str(q.index[-1].date()),
        "drawdowns": _drawdowns(q),
        "qqq_daily": [{"d": str(d.date()), "c": round(float(v), 2)}
                      for d, v in q.loc["2022-01-01":].items()],
        "source": "FINRA Margin Statistics（官方 xlsx，每月中更新）；QQQ = yfinance",
        "rule": "陰影 = QQQ 回撤 ≥7%；收縮事件 = 月度債務跌幅 ≥4%",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"{payload['as_of']} 債務 {cur:.3f} 萬億（{payload['mom_pct']:+.1f}%）｜"
          f"距峰 {dd_from_peak:+.1f}%｜QQQ {payload['qqq_last']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
