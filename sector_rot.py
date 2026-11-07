# -*- coding: utf-8 -*-
"""sector_rotation.py — 行業／主題輪動（RAE 自 Desmond 2026-11-07 提供嘅圖）

原圖四塊
  Daily Rank Up / Down     今日最強／最弱 3 隻（連 RS 評分同百分比）
  Weekly Rank Up / Down    一週最強／最弱 3 隻
  Sector Leaders           11 個行業：Now / 1D / 1W / 1M RS 評分 + Day/Wk/Mth% + 52W High
  Industry RS Rank         行業 ETF 表，同一組欄，可排序

定義（寫死）
  回報   1D = 1 日｜1W = 5 日｜1M = 21 日｜3M = 63 日（收市對收市）
  52W High = 收市 ÷ 近 252 日最高收市 − 1
  RS 評分  = 同一組之內，該回報嘅百分位（0-100）；「Now」用 3M

更新：cron 平日 17:10 HKT（18:00 前 build 好）
本模組只寫 cache + output。
"""
from __future__ import annotations

import html as _h
import io
import json
import os
import pickle
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "sector_rot.pkl")
OUT = os.path.join(HERE, "output")
CACHE_H = 6.0

SECTORS = [
    ("XLK", "Technology"), ("XLF", "Financials"), ("XLV", "Health Care"),
    ("XLY", "Cons Disc"), ("XLP", "Cons Stpl"), ("XLE", "Energy"),
    ("XLI", "Industrials"), ("XLB", "Materials"), ("XLU", "Utilities"),
    ("XLRE", "Real Estate"), ("XLC", "Comm Svcs"),
]

INDUSTRIES = [
    ("GDX", "Gold Miners"), ("KWEB", "China Internet"), ("REMX", "Rare Earth"),
    ("XBI", "Biotech"), ("COPX", "Copper Miners"), ("GNOM", "Genomics"),
    ("BOAT", "Marine Shipping"), ("UFO", "Space"), ("XOP", "Oil & Gas Exp."),
    ("TAN", "Solar"), ("WOOD", "Timber"), ("KIE", "Insurance"),
    ("MOO", "Agribusiness"), ("ITB", "Home Constr."), ("IHI", "Med. Devices"),
    ("IPAY", "Mobile Payme…"), ("KRE", "Regional Bank"), ("XRT", "Retail"),
    ("FINX", "FinTech"), ("IYT", "Transportation"), ("JETS", "Global Jets"),
    ("IAI", "Securities Dealers"), ("PEJ", "Leisure"), ("ITA", "Aerospace"),
    ("ICLN", "Clean Energy"), ("KARS", "Electric Cars"), ("SIL", "Silver Miners"),
    ("POWR", "Power-Grid"), ("LIT", "Lithium"), ("SLX", "Steel"),
    ("IGV", "Tech-Software"), ("URA", "Uranium"), ("CIBR", "Cybersecurity"),
    ("BLOK", "Blockchain"), ("IPO", "IPO"), ("QTUM", "Quantum-Tech"),
    ("WQTM", "Pure-Quantum"), ("SMH", "Semiconductor"), ("WGMI", "Bitcoin Miners"),
]


def _esc(x):
    return _h.escape(str(x if x is not None else ""))


def log(*a):
    print(*a, flush=True)


def _all():
    seen, out = set(), []
    for t, n in SECTORS + INDUSTRIES:
        if t in seen:
            continue
        seen.add(t)
        out.append((t, n))
    return out


def fetch(refresh=False):
    if not refresh and os.path.exists(CACHE):
        if (time.time() - os.path.getmtime(CACHE)) / 3600.0 < CACHE_H:
            try:
                with io.open(CACHE, "rb") as f:
                    d = pickle.load(f)
                if d and len(d) > 20:
                    return d
            except Exception:                                # noqa: BLE001
                pass
    import yfinance as yf
    tks = [t for t, _ in _all()] + ["SPY"]
    try:
        raw = yf.download(tks, period="1y", interval="1d", auto_adjust=True,
                          progress=False, threads=True)
        close = raw["Close"] if hasattr(raw.columns, "nlevels") and raw.columns.nlevels > 1 else raw
        d = {}
        for t in tks:
            if t in close.columns:
                s = close[t].dropna()
                if len(s) > 60:
                    d[t] = s
        if len(d) > 20:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            with io.open(CACHE, "wb") as f:
                pickle.dump(d, f)
        return d
    except Exception as e:                                   # noqa: BLE001
        log(f"⚠ sector fetch：{type(e).__name__}: {e}")
        try:
            with io.open(CACHE, "rb") as f:
                return pickle.load(f)
        except Exception:                                    # noqa: BLE001
            return {}


def _ret(s, n):
    if s is None or len(s) <= n:
        return None
    try:
        return float(s.iloc[-1] / s.iloc[-1 - n] - 1.0) * 100
    except Exception:                                        # noqa: BLE001
        return None


def _pct_rank(values, v):
    if v is None:
        return None
    xs = [x for x in values if x is not None]
    if not xs:
        return None
    return round(100.0 * sum(1 for x in xs if x <= v) / len(xs), 0)


def compute(d):
    rows = []
    for t, name in _all():
        s = d.get(t)
        if s is None:
            continue
        hi = float(s.tail(252).max())
        rows.append({
            "t": t, "n": name,
            "r1d": _ret(s, 1), "r1w": _ret(s, 5), "r1m": _ret(s, 21),
            "r3m": _ret(s, 63), "px": round(float(s.iloc[-1]), 2),
            "d52": round((float(s.iloc[-1]) / hi - 1) * 100, 2) if hi else None,
            "date": s.index[-1].strftime("%Y-%m-%d"),
        })
    if not rows:
        return None
    for key, rk in (("r1d", "rs_1d"), ("r1w", "rs_1w"),
                    ("r1m", "rs_1m"), ("r3m", "rs_now")):
        vals = [r[key] for r in rows]
        for r in rows:
            r[rk] = _pct_rank(vals, r[key])
    spy = d.get("SPY")
    return {
        "date": rows[0]["date"], "rows": rows, "n": len(rows),
        "spy": {"r1d": _ret(spy, 1), "r1w": _ret(spy, 5), "r1m": _ret(spy, 21)},
    }


def build_snapshot(refresh=False):
    d = fetch(refresh=refresh)
    if not d:
        return None
    return compute(d)


CSS = """
.sr-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media(max-width:1000px){.sr-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:560px){.sr-grid{grid-template-columns:1fr}}
.sr-box{border:1px solid rgba(148,163,184,.22);border-radius:8px;padding:8px 10px 10px}
.sr-h{font-size:10.5px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;opacity:.6;margin-bottom:6px}
.sr-h.up{color:#1f7f52}.sr-h.dn{color:#a04a44}
.sr-row{display:flex;align-items:center;gap:8px;padding:5px 0;border-top:1px solid rgba(148,163,184,.12)}
.sr-row:first-of-type{border-top:0}
.sr-tk{font-size:12px;font-weight:800;letter-spacing:.02em;min-width:52px}
.sr-nm{font-size:10px;opacity:.55;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sr-px{font-size:11px;font-variant-numeric:tabular-nums;text-align:right}
.sr-ch{font-size:10px;font-variant-numeric:tabular-nums;opacity:.7;min-width:48px;text-align:right}
.sr-tbl{width:100%;border-collapse:collapse;font-size:12px}
.sr-tbl th{text-align:left;font-size:10px;letter-spacing:.05em;opacity:.55;font-weight:800;
  padding:5px 7px;border-bottom:1px solid rgba(148,163,184,.25);white-space:nowrap}
.sr-tbl td{padding:4px 7px;border-bottom:1px solid rgba(148,163,184,.1);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.sr-tbl td.n,.sr-tbl th.n{text-align:right}
.sr-chip{display:inline-block;min-width:26px;text-align:center;border-radius:3px;
  font-size:10.5px;font-weight:800;padding:1px 3px}
.sr-note{font-size:10.5px;opacity:.55;line-height:1.7;margin-top:8px}
.pos{color:#1f7f52}.neg{color:#a04a44}
"""


def _chip(v):
    if v is None:
        return '<span style="opacity:.3">—</span>'
    c = "#9fd6b6" if v >= 80 else "#c9d8ae" if v >= 60 else "#d9d5c4" if v >= 40 else "#e3c3c0"
    return f'<span class="sr-chip" style="background:{c}">{int(v)}</span>'


def _pct(v, dec=2):
    if v is None:
        return "—"
    cls = "pos" if v > 0 else "neg" if v < 0 else ""
    return f'<span class="{cls}">{v:+.{dec}f}%</span>'


def _rank_box(rows, key, title, up=True, k=3):
    sel = sorted([r for r in rows if r.get(key) is not None],
                 key=lambda r: r[key], reverse=up)[:k]
    out = [f'<div class="sr-box"><div class="sr-h {"up" if up else "dn"}">{title}</div>']
    for r in sel:
        out.append('<div class="sr-row">'
                   f'{_chip(r.get("rs_1m"))}'
                   f'<span class="sr-tk">{_esc(r["t"])}</span>'
                   f'<span class="sr-nm">{_esc(r["n"])}</span>'
                   f'<span class="sr-px">{r["px"]:.2f}</span>'
                   f'<span class="sr-ch">{_pct(r[key])}</span></div>')
    out.append('</div>')
    return "".join(out)


def _table(rows):
    out = ['<div class="tscroll"><table class="sr-tbl"><thead><tr>'
           '<th data-no-sort>Now</th><th data-no-sort>1D</th><th data-no-sort>1W</th>'
           '<th data-no-sort>1M</th><th>Ticker</th><th>Name</th>'
           '<th class="n">Day%</th><th class="n">Wk%</th>'
           '<th class="n">Mth%</th><th class="n">3M%</th>'
           '<th class="n">52W High</th></tr></thead><tbody>']
    for r in rows:
        out.append('<tr>'
                   f'<td>{_chip(r["rs_now"])}</td><td>{_chip(r["rs_1d"])}</td>'
                   f'<td>{_chip(r["rs_1w"])}</td><td>{_chip(r["rs_1m"])}</td>'
                   f'<td><b>{_esc(r["t"])}</b></td>'
                   f'<td style="opacity:.7">{_esc(r["n"])}</td>'
                   f'<td class="n">{_pct(r["r1d"])}</td>'
                   f'<td class="n">{_pct(r["r1w"])}</td>'
                   f'<td class="n">{_pct(r["r1m"])}</td>'
                   f'<td class="n">{_pct(r["r3m"])}</td>'
                   f'<td class="n">{_pct(r["d52"])}</td></tr>')
    out.append('</tbody></table></div>')
    return "".join(out)


def _load_json():
    try:
        with io.open(os.path.join(OUT, "sector_rot.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return None


def build():
    snap = _load_json()
    if not snap:
        return ("行業輪動", '<div class="card"><div class="body">'
                           'DATA_UNAVAILABLE — 未跑 sector_rotation.py'
                           '（output/sector_rot.json）。</div></div>')
    rows = snap["rows"]
    stk = dict(SECTORS)
    itk = dict(INDUSTRIES)
    sect = sorted([r for r in rows if r["t"] in stk],
                  key=lambda r: (r["rs_1m"] or 0), reverse=True)
    ind = sorted([r for r in rows if r["t"] in itk],
                 key=lambda r: (r["rs_1m"] or 0), reverse=True)

    L = [f"<style>{CSS}</style>"]
    L.append('<div class="card"><h2>行業輪動 <small>' + _esc(snap["date"]) +
             '｜RS 評分 = 本組 ' + str(snap["n"]) + ' 隻之內嘅百分位</small></h2>'
             '<div class="body">')
    L.append('<div class="sr-grid">')
    L.append(_rank_box(rows, "r1d", "Daily Rank Up", True))
    L.append(_rank_box(rows, "r1w", "Weekly Rank Up", True))
    L.append(_rank_box(rows, "r1d", "Daily Rank Down", False))
    L.append(_rank_box(rows, "r1w", "Weekly Rank Down", False))
    L.append('</div></div></div>')

    L.append('<div class="card"><h2>行業領導（Sector Leaders）'
             '<small>11 個行業 SPDR，按 1M RS 排序</small></h2><div class="body">')
    L.append(_table(sect))
    L.append('<div class="sr-note">Now = 3M 相對排名；1D／1W／1M = 該回報嘅組內排名；'
             'Day/Wk/Mth% = 絕對回報（唔係相對）。</div></div></div>')

    L.append('<div class="card"><h2>Industry RS Rank'
             f'<small>{len(ind)} 隻行業／主題 ETF，按 1M RS 排序；撳欄頭可排序</small></h2>'
             '<div class="body">')
    L.append(_table(ind))
    L.append('</div></div>')
    return ("行業輪動", "".join(L))


def main(argv=None):
    import sys
    argv = sys.argv[1:] if argv is None else argv
    snap = build_snapshot(refresh="--refresh" in argv)
    if not snap:
        log("DATA_UNAVAILABLE")
        return 1
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "sector_rot.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False)
    top = max(snap["rows"], key=lambda r: r["r1d"] if r["r1d"] is not None else -99)
    log(f"{snap['date']}  {len(snap['rows'])} 隻  今日最強 {top['t']} "
        f"{top['r1d']:+.2f}%  → {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
