#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""charts.py — 迷你 K 線牆（一次過睇哂所有領導股嘅圖）

Desmond 2026-10-11 要求：「透過 Layer1+2 每天選股…可以可視化地一次過睇哂所有圖」。

做法：一批過用 yfinance 下載 OHLC（90 日），再純 Python 畫迷你 K 線 SVG（冇 CDN，
file:// 同 Pages 都開得）。一支 56×64px，直接 inline 落 HTML，唔係外鏈圖片。

設計契約
--------
- 唯讀：只寫自己嘅 cache/；唔會改任何實盤常數。
- 快取：`data/charts_ohlc.pkl`，1 日內唔重複下載（跟 rs_select.fetch 同一 freshness）。
- 出錯降級：yfinance 限流 / 冇咗某隻 → 嗰格顯示「—」，唔會拖死成頁。
"""
import datetime
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "charts_ohlc.pkl")

UP = "#4ade80"
DN = "#f87171"
GRID = "#24365a"


def log(*a):
    print(*a, flush=True)


def fetch(tickers, maxage_days=1):
    """一批過下載 OHLC。命中快取（1 日內）就直接用。"""
    import pandas as pd
    import yfinance as yf
    tickers = sorted(set(t for t in tickers if t))
    if os.path.exists(CACHE):
        try:
            d = pd.read_pickle(CACHE)
            have = set(d.columns.get_level_values(0))
            last = d.index[-1].date()
            need = set(tickers) - have
            if not need and (datetime.date.today() - last).days <= maxage_days:
                log(f"  圖表快取命中（{len(have)} 隻，至 {last}）")
                return d
        except Exception:                                    # noqa: BLE001
            pass
    if not tickers:
        return None
    log(f"  yfinance 下載 {len(tickers)} 隻 OHLC…")
    end = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    d = yf.download(tickers, start="2026-07-01", end=end, interval="1d",
                    auto_adjust=False, progress=False, group_by="ticker", threads=True)
    if d is None or d.empty:
        return None
    os.makedirs(DATA, exist_ok=True)
    d.to_pickle(CACHE)
    log(f"  下載完成：{len(set(d.columns.get_level_values(0)))} 隻，最後 {d.index[-1].date()}")
    return d


def adr_pct(ohlc, n=14):
    import pandas as pd
    try:
        h, l, c = ohlc["High"], ohlc["Low"], ohlc["Close"]
        tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()],
                       axis=1).max(axis=1)
        a = tr.rolling(n).mean()
        return float((a.iloc[-1] / c.iloc[-1] * 100)) if c.iloc[-1] else None
    except Exception:                                        # noqa: BLE001
        return None


def render_mini(ohlc, n=40, w=58, h=64):
    """畫一支迷你 K 線 SVG。回傳 (svg, adr)。"""
    import numpy as np
    try:
        f = ohlc.dropna(subset=["Open", "High", "Low", "Close"]).tail(n)
    except Exception:                                        # noqa: BLE001
        return None, None
    if len(f) < 5:
        return None, None
    o, hh, ll, c = f["Open"], f["High"], f["Low"], f["Close"]
    sma = c.rolling(50).mean()
    lo = float(ll.min())
    hi = float(hh.max())
    rg = (hi - lo) or 1
    pad = 2
    pw = w - 2 * pad
    ph = h - 2 * pad
    bw = max(1.0, pw / len(f) * 0.6)
    out = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           f'xmlns="http://www.w3.org/2000/svg">']

    def X(i):
        return pad + (i + 0.5) / len(f) * pw

    def Y(v):
        return pad + (1 - (v - lo) / rg) * ph

    # SMA50 線
    pts = []
    for i, (idx, v) in enumerate(sma.items()):
        if not math.isfinite(v):
            continue
        pts.append(f"{X(i):.0f},{Y(v):.0f}")
    if len(pts) > 1:
        out.append(f'<polyline points="{" ".join(pts)}" fill="none" '
                   f'stroke="#8ea0bf" stroke-width="1" opacity=".55"/>')
    # K 線
    for i in range(len(f)):
        x = X(i)
        col = UP if c.iloc[i] >= o.iloc[i] else DN
        out.append(f'<line x1="{x:.0f}" y1="{Y(hh.iloc[i]):.0f}" '
                   f'x2="{x:.0f}" y2="{Y(ll.iloc[i]):.0f}" stroke="{col}" '
                   f'stroke-width="1"/>')
        yo, yc = Y(o.iloc[i]), Y(c.iloc[i])
        top, bot = min(yo, yc), max(yo, yc)
        hhpx = max(1.0, bot - top)
        out.append(f'<rect x="{x - bw/2:.0f}" y="{top:.0f}" width="{bw:.0f}" '
                   f'height="{hhpx:.0f}" fill="{col}"/>')
    out.append("</svg>")
    return "".join(out), adr_pct(f)


def build_grid(tickers, max_cells=48):
    """回傳 [(ticker, svg, adr)]，逐隻降級唔會炸。"""
    df = fetch(tickers)
    if df is None:
        return []
    grid = []
    for t in tickers:
        if t not in set(df.columns.get_level_values(0)):
            continue
        try:
            svg, adr = render_mini(df[t])
        except Exception:                                    # noqa: BLE001
            svg, adr = None, None
        grid.append((t, svg, adr))
        if len(grid) >= max_cells:
            break
    return grid


def grid_html(grid, cell_w=72):
    """一行 HTML：每格 = 迷你圖 ＋ 代號 ＋ ADR%。"""
    cells = []
    for t, svg, adr in grid:
        if svg:
            cells.append(
                f'<div class="cand"><div class="mini">{svg}</div>'
                f'<div class="tk">{t}</div>'
                f'<div class="dim">{"ADR " + f"{adr:.0f}%" if adr else "—"}</div></div>')
        else:
            cells.append(f'<div class="cand"><div class="mini" '
                         f'style="color:#5f708c;font-size:11px">—</div>'
                         f'<div class="tk">{t}</div></div>')
    return ('<div class="chartwall">' + "".join(cells) + "</div>")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    # 自測：用交易台 web 嘅 market_scan.json 頭 12 隻
    import json
    p = os.path.join(DATA, "market_scan.json")
    if not os.path.exists(p):
        print("冇 market_scan.json")
        sys.exit(1)
    d = json.load(io.open(p, encoding="utf-8"))
    tk = [r["symbol"] for r in d.get("nel", [])][:12]
    g = build_grid(tk)
    print(f"{len(g)} 格 OK")
    for t, svg, adr in g[:4]:
        print(t, "ADR", adr, "svg", len(svg), "chars")
