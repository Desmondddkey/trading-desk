#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nel_pages.py — Item 1：蒸餾 NEL 五個新頁（Themes／Sectors／Breadth／Review／Positioning）

Desmond 2026-10-11 Item 1：「完整蒸餾 NEL（review 逐日回顧／positioning COT／
Themes／Sectors／Breadth）」

★ 來源：`RAE_NEL.md`（i-manage-risk/NEL 逆向工程，251 檔、只做架構參考唔抄碼）
★ 五頁各有唯一數據源，**唔准自己發明數字**：

  | 頁 | 數據源 | 唯一實作 |
  |---|---|---|
  | Themes | 主題 ETF 成員表現 | `score_theme()`（70% 中位 + 30% 最強，跟 NEL 原文）|
  | Sectors | 行業 ETF | `rotation_map.compute()`（34 行業）|
  | Breadth | Stockbee 式市場監察 | `trading-os/output/breadth_*.json`（唔重算）|
  | Review | 逐日訊號→之後表現 | `dashboard.py` 嘅 `review_table()` 同源（`add_forward`）|
  | Positioning | CFTC COT 大型投機者 | `cftc_cot()`（Socrata API，公開免 key）|

★ 兩條紀律：
  ① Missing ≠ Zero：缺數出 DATA_UNAVAILABLE，唔准填 0（EDGE-016）
  ② 唔准有第二套實作：能用現成 module 就用，唔可以喺呢個檔重寫公式
"""
import datetime
import io
import json
import math
import os
import sys

HOME = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HOME, "output")

for _p in (HOME, os.path.join(os.path.dirname(HOME), "trading-os-lab"),
           os.path.join(os.path.dirname(HOME), "trading-os")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ══════════════════════════ ① Themes ══════════════════════════
# 主題 ETF（同 NEL 原文一樣嘅做法，但 ETF 清單係我哋自己揀嘅 —— 公開資訊）
THEMES = {
    "AI ／ 半導體": ["SMH", "SOXX", "NVDA", "AMD", "AVGO", "MU", "TSM", "ARM"],
    "雲端 ／ 軟件": ["IGV", "SKYY", "WCLD", "CRM", "NOW", "MSFT", "ORCL"],
    "網絡安全": ["CIBR", "HACK", "PANW", "CRWD", "ZS", "FTNT"],
    "量子 ／ 新運算": ["QTUM", "IONQ", "RGTI", "QBTS", "IBM"],
    "國防 ／ 航天": ["ITA", "PPA", "LMT", "RTX", "GD", "NOC"],
    "能源 ／ 核電": ["XLE", "XOP", "URA", "NLR", "CCJ", "OKLO", "SMR"],
    "電力 ／ 電網": ["XLU", "GRID", "POWL", "ETN", "VRT", "CEG"],
    "醫療 ／ 生技": ["XLV", "IHI", "XBI", "IBB", "LLY", "NVO"],
    "加密 ／ 金融科技": ["BLOK", "FINX", "COIN", "HOOD", "MSTR", "SQ"],
    "黃金 ／ 貴金屬": ["GDX", "GDXJ", "GLD", "SLV", "NEM", "AEM"],
    "銅 ／ 工業金屬": ["COPX", "XME", "FCX", "SCCO", "TECK"],
    "消費 ／ 零售": ["XLY", "XRT", "AMZN", "COST", "WMT"],
}


def score_theme(tk_list, df, bench="SPY"):
    """NEL 原文公式：`70% × 成員中位百分位 + 30% × 最強成員百分位`。

    ★ 唔准自己寫第二套 —— 呢個 function 就係唯一實作，兩處要用就 import 佢。
    回傳 None 代表數據不足（Missing ≠ Zero）。
    """
    import numpy as np
    import pandas as pd
    have = set(df.columns.get_level_values(0))
    if bench not in have:
        return None
    try:
        b = df[bench].dropna(subset=["Close"])["Close"]
    except Exception:                                        # noqa: BLE001
        return None
    if len(b) < 70:
        return None
    r3_bench = float(b.iloc[-1] / b.iloc[-64] - 1) * 100

    rows = []
    for tk in tk_list:
        if tk not in have:
            continue
        try:
            c = df[tk].dropna(subset=["Close"])["Close"]
        except Exception:                                    # noqa: BLE001
            continue
        if len(c) < 70:
            continue
        r1 = float(c.iloc[-1] / c.iloc[-22] - 1) * 100
        r3 = float(c.iloc[-1] / c.iloc[-64] - 1) * 100
        rows.append({"ticker": tk, "r1m": round(r1, 2), "r3m": round(r3, 2),
                     "ex3": round(r3 - r3_bench, 2)})
    if len(rows) < 3:
        return None
    ex3 = np.array([r["ex3"] for r in rows], dtype=float)
    # 百分位（0–100），同 NEL 一致
    pct = pd.Series(ex3).rank(pct=True).values * 100
    for r, p in zip(rows, pct):
        r["pctile"] = round(float(p), 1)
    med = float(np.median(pct))
    top = float(np.max(pct))
    return {
        "n": len(rows), "median_pct": round(med, 1), "top_pct": round(top, 1),
        "score": round(0.70 * med + 0.30 * top, 1),
        "members": sorted(rows, key=lambda z: -z["pctile"]),
    }


def themes_page(ohlc):
    """要 OHLC（同一個池就夠）。ohlc=None → DATA_UNAVAILABLE。"""
    if ohlc is None:
        return _unavail("Themes", "冇 OHLC 快取")
    res = {}
    for name, mem in THEMES.items():
        s = score_theme(mem, ohlc)
        if s:
            res[name] = s
    if not res:
        return _unavail("Themes", "冇一個主題夠數據（每組要 ≥3 隻 × 70 日）")
    ranked = sorted(res.items(), key=lambda kv: -kv[1]["score"])
    rows = []
    for name, s in ranked:
        mem = "、".join(f"{m['ticker']}({m['pctile']:.0f})"
                        for m in s["members"][:6])
        rows.append(
            f'<tr><td class="l"><b>{_e(name)}</b></td>'
            f'<td><b>{s["score"]:.1f}</b></td>'
            f'<td>{s["median_pct"]:.1f}</td><td>{s["top_pct"]:.1f}</td>'
            f'<td>{s["n"]}</td><td class="l dim">{_e(mem)}</td></tr>')
    top3 = ranked[:3]
    head = ('<tr><th class="l">主題</th><th>主題分</th><th>成員中位百分位</th>'
            '<th>最強成員百分位</th><th>成員數</th><th class="l">成員（百分位）</th></tr>')
    return (f'<div class="card"><h2>🧩 Themes · 主題強度 '
            f'<small>NEL 原文公式：70%×中位 + 30%×最強</small></h2>'
            f'<div class="body"><div class="note">'
            f'「百分位」＝ 成員 3 個月超額回報（相對 SPY）嘅組內排名 0–100。'
            f'<b>主題分 = 0.7 × 成員中位 + 0.3 × 最強成員</b>——'
            f'即係「整體有幾強」佔七成、「有冇一隻爆」佔三成。'
            f'呢條係 NEL 原文公式，唔係我哋自己調嘅。</div>'
            f'<div class="scroll"><table><thead>{head}</thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            f'<div class="note">最強三個主題：{"、".join(n for n, _ in top3)}</div>'
            f'</div></div>')


# ══════════════════════════ ② Sectors ══════════════════════════
def sectors_page(ohlc=None):
    """直接用 rotation_map 嘅實作 —— 唔准重寫。

    ★ 2026-10-12 修：唔可以拿股票池 OHLC 塞入去。
      `rotation_map` 要嘅係**34 個行業 ETF**，佢自己 `fetch()` 抓；
      股票池（84 隻個股）入去會出 0 行（第一次就係咁）。
      所以呢度**唔傳 ohlc**，叫 rotation_map 自己攞 —— 保證同 desk.html 同源。
    """
    try:
        import rotation_map as rm
        d = rm.fetch()
        df, spy = rm.compute(d)
        if df is None or df.empty:
            return _unavail("Sectors", "rotation_map 計唔到（ETF 數據不足）")
    except Exception as e:                                   # noqa: BLE001
        return _unavail("Sectors", f"rotation_map 失敗：{type(e).__name__}")
    rows = []
    for _, r in df.head(20).iterrows():
        rows.append(
            f'<tr><td>{int(r["rank"])}</td>'
            f'<td class="l"><b>{_e(str(r["name"]))}</b></td>'
            f'<td>{_e(str(r["stage"]))}</td>'
            f'<td><b>{int(r["score"])}</b></td>'
            f'<td class="{_tone(r["x1m"])}">{r["x1m"]:+.1f}%</td>'
            f'<td class="{_tone(r["x3m"])}">{r["x3m"]:+.1f}%</td>'
            f'<td>{r.get("etf", "")}</td></tr>')
    head = ('<tr><th>#</th><th class="l">SECTOR</th><th>STAGE</th><th>分</th>'
            '<th>1M 超額</th><th>3M 超額</th><th>ETF</th></tr>')
    return (f'<div class="card"><h2>🏭 Sectors · 行業輪動 '
            f'<small>同 <a href="desk.html">機會</a>頁第③面板同一個實作</small></h2>'
            f'<div class="body"><div class="note">'
            f'數字出自 <code>rotation_map.compute()</code>——'
            f'<b>同機會頁完全同一組數</b>，唔係另外計一次。'
            f'階段＝加速／成熟／轉弱／新興／再現／落後。</div>'
            f'<div class="scroll"><table><thead>{head}</thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></div></div>')


# ══════════════════════════ ③ Breadth ══════════════════════════
def _latest_breadth():
    import glob
    fs = sorted(glob.glob(os.path.join(os.path.dirname(HOME), "trading-os",
                                       "output", "breadth_*.json")))
    if not fs:
        return None
    try:
        return json.load(io.open(fs[-1], encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return None


def breadth_page():
    """Stockbee 式市場監察。★ 直接讀 trading-os 產物，唔重算。"""
    d = _latest_breadth()
    if not d:
        return _unavail("Breadth", "冇 breadth_*.json（跑 trading-os/layer4_breadth.py）")
    adl = (d.get("adl") or {})
    nn = (d.get("nnnl") or {})
    pct40 = d.get("pct40ma")
    rows = [
        ("ADL（上升下跌線）", adl.get("value"),
         _adl_read(adl), "bull 線 +100｜中性 0｜mild bear −100｜投降 −200"),
        ("NNNL（新高減新低）", nn.get("value"),
         _nn_read(nn), nn.get("method") or "10 日均（20 日新高% − 新低%）"),
        ("% above 40MA", pct40, _pct40_read(pct40), "市場參與度"),
        ("L/S 比率（代理）", d.get("ls_ratio_proxy"), "—", "long/short 代理指標"),
    ]
    trs = []
    for k, v, read, note in rows:
        vv = "DATA_UNAVAILABLE" if v is None else (
            f"{v:+.1f}" if isinstance(v, (int, float)) else _e(str(v)))
        cls = "dim" if v is None else _tone(v)
        trs.append(f'<tr><td class="l"><b>{_e(k)}</b></td>'
                   f'<td class="{cls}">{vv}</td>'
                   f'<td class="l">{_e(read)}</td>'
                   f'<td class="l dim">{_e(note)}</td></tr>')
    ser = d.get("series") or []
    spark = _spark(ser) if ser else '<span class="dim">冇序列</span>'
    # ★ posture 有機會係 list（多條指示）；唔准原樣 dump JSON 落頁面
    post = d.get("posture")
    if isinstance(post, (list, tuple)):
        post_txt = "；".join(str(x) for x in post[:3])
    elif isinstance(post, dict):
        post_txt = str(post.get("text") or post.get("read") or "—")
    else:
        post_txt = str(post or "—")
    return (f'<div class="card"><h2>🌊 Breadth · 市場廣度 '
            f'<small>Stockbee Market Monitor 式｜至 {_e(str(d.get("as_of","?"))[:10])}</small></h2>'
            f'<div class="body">'
            f'<div class="kpis"><div class="kpi"><div class="k">制度</div>'
            f'<div class="v" style="color:#9fd4ff">{_e(str(d.get("regime","?")))}</div></div>'
            f'<div class="kpi" style="flex:1 1 auto"><div class="k">姿態</div>'
            f'<div class="v" style="font-size:12px;line-height:1.5;text-align:left">'
            f'{_e(post_txt)}</div></div></div>'
            f'<div class="scroll"><table><thead><tr><th class="l">指標</th>'
            f'<th>值</th><th class="l">讀法</th><th class="l">來源／定義</th>'
            f'</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
            f'<div class="note">序列走勢：{spark}</div>'
            f'<div class="note">池：{_e(str(d.get("universe","?")))}｜'
            f'規則版本：<code>{_e(str(d.get("rule_version","?")))}</code><br>'
            f'⚠ 呢頁<b>直接讀</b> <code>trading-os/output/breadth_*.json</code>，'
            f'唔會自己重算 —— 保證同 Plan 卡同一組數（EDGE-036 教訓）。'
            f'指標定義參考 <a href="https://stockbee.blogspot.com/p/mm.html" '
            f'target="_blank" rel="noopener">Stockbee Market Monitor</a>。</div>'
            f'</div></div>')


def _spark(ser, w=560, h=44):
    vals = []
    for x in ser:
        v = x.get("value") if isinstance(x, dict) else x
        if isinstance(v, (int, float)) and math.isfinite(v):
            vals.append(float(v))
    if len(vals) < 3:
        return '<span class="dim">序列太短</span>'
    vals = vals[-60:]
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    pts = " ".join(f"{12 + i*(w-24)/max(1,len(vals)-1):.1f},"
                   f"{h-8 - (v-lo)/rng*(h-16):.1f}" for i, v in enumerate(vals))
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}">'
            f'<polyline points="{pts}" fill="none" stroke="#7fd4a8" '
            f'stroke-width="1.8"/></svg>'
            f'<span class="dim">（{len(vals)} 點，最低 {lo:.1f}／最高 {hi:.1f}）</span>')


def _adl_read(a):
    v = a.get("value")
    if v is None:
        return "—"
    th = a.get("thresholds") or {}
    if th and v >= th.get("bull_line", 100):
        return "🟢 牛區（> +100）"
    if v <= th.get("capitulation_line", -200):
        return "🔴 投降（< −200）"
    if v <= th.get("mild_bear_line", -100):
        return "🟠 溫和熊（< −100）"
    return "⚪ 中性"


def _nn_read(n):
    v = n.get("value")
    if v is None:
        return "—"
    if v <= n.get("deep_oversold", -100):
        return "🔴 深度超賣（< −100）"
    return "🟢 偏強" if v > 0 else "⚪ 偏弱"


def _pct40_read(v):
    if v is None:
        return "—"
    if v >= 60:
        return "🟢 參與度高"
    if v <= 30:
        return "🔴 參與度低"
    return "⚪ 中等"


# ══════════════════════════ ④ Review ══════════════════════════
def review_page():
    """逐日回顧：讀 dashboard 回溯產物。★ 唔重算，只讀。"""
    import glob
    fs = sorted(glob.glob(os.path.join(HERE_CACHE, "review_*.json"))) \
        if os.path.isdir(HERE_CACHE) else []
    if not fs:
        # 退而求其次：由 desk.html 抽唔到就報 unavailable（唔准作假表）
        return _unavail(
            "Review",
            "未有 review 快照。Review 頁嘅數字由 <code>dashboard.py</code> 嘅 "
            "回溯重算（<code>add_forward</code>）產生 —— 跑一次 "
            "<code>dashboard.py</code> 就出到，唔需要另寫一套。")
    d = json.load(io.open(fs[-1], encoding="utf-8"))
    return _unavail("Review", f"讀到 {os.path.basename(fs[-1])}（{len(d)} 項）")


# ══════════════════════════ ⑤ Positioning ══════════════════════════
COT_MARKETS = [
    ("13874A", "E-mini S&P 500", "股指"),
    ("133741", "E-mini Nasdaq-100", "股指"),
    ("209747", "VIX 期貨", "波動率"),
    ("088691", "黃金", "貴金屬"),
    ("084691", "白銀", "貴金屬"),
    ("067651", "原油（WTI）", "能源"),
    ("098662", "10 年美債", "利率"),
    ("096742", "美元指數", "外匯"),
]


def cftc_cot(weeks=160):
    """CFTC COT：大型投機者（non-commercial）淨持倉 156 週極端。

    ★ 公開 Socrata API，免 key。唯一實作 —— 只喺呢度寫一次。
    回傳 {code: {"name":…, "net":…, "net_pct":…, "weeks":…, "series":[…]}}；冇數據 → {}
    """
    import urllib.parse
    import urllib.request
    out = {}
    for code, name, grp in COT_MARKETS:
        q = urllib.parse.urlencode({
            "$limit": weeks, "$order": "report_date_as_yyyy_mm_dd DESC",
            "cftc_contract_market_code": code,
            "futonly_or_combined": "FutOnly",
        })
        url = ("https://publicreporting.cftc.gov/resource/6dca-aqww.json?" + q)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                js = json.loads(r.read().decode("utf-8"))
        except Exception as e:                               # noqa: BLE001
            log(f"  ⚠ COT {name}：{type(e).__name__}")
            continue
        ser = []
        for x in js:
            try:
                L = float(x["noncomm_positions_long_all"])
                S = float(x["noncomm_positions_short_all"])
                oi = float(x["open_interest_all"])
            except (KeyError, TypeError, ValueError):
                continue
            ser.append({"date": str(x["report_date_as_yyyy_mm_dd"])[:10],
                        "long": L, "short": S, "net": L - S,
                        "oi": oi, "net_pct": (L - S) / oi * 100 if oi else None})
        if not ser:
            continue
        ser = list(reversed(ser))          # 舊 → 新
        nets = [s["net"] for s in ser]
        cur = nets[-1]
        lo, hi = min(nets), max(nets)
        rng = (hi - lo) or 1.0
        pct = (cur - lo) / rng * 100       # 0 = 最淡，100 = 最牛
        out[code] = {
            "name": name, "group": grp, "net": cur,
            "net_pct": ser[-1].get("net_pct"), "weeks": len(ser),
            "lo": lo, "hi": hi, "extreme": round(pct, 1),
            "date": ser[-1]["date"],
            "chg4": (cur - nets[-5]) if len(nets) >= 5 else None,
            "series": [s["net"] for s in ser[-52:]],
        }
    return out


def positioning_page():
    d = cftc_cot()
    if not d:
        return _unavail("Positioning",
                        "CFTC COT 抓唔到（網絡？）—— 唔會用假數字填")
    rows = []
    for code, m in sorted(d.items(), key=lambda kv: -kv[1]["extreme"]):
        ex = m["extreme"]
        tag = ("🔴 極度擁擠（>90）" if ex >= 90
               else "🟠 偏擁擠（>75）" if ex >= 75
               else "🟢 偏淡（<25）" if ex <= 25
               else "⚪ 中性")
        nps = "—" if m["net_pct"] is None else f'{m["net_pct"]:+.1f}%'
        chg = ("—" if m["chg4"] is None
               else f'<span class="{_tone(m["chg4"])}">{m["chg4"]:+,.0f}</span>')
        rows.append(
            f'<tr><td class="l"><b>{_e(m["name"])}</b></td>'
            f'<td class="dim">{_e(m["group"])}</td>'
            f'<td>{m["net"]:+,.0f}</td>'
            f'<td>{nps}</td>'
            f'<td><b>{ex:.0f}</b></td><td>{_e(tag)}</td><td>{chg}</td>'
            f'<td>{_sparkline(m["series"])}</td></tr>')
    newest = max(m["date"] for m in d.values())
    head = ('<tr><th class="l">市場</th><th>類別</th><th>淨持倉</th>'
            '<th>佔 OI</th><th>52 週位置</th><th>讀法</th><th>4 週變化</th>'
            '<th>走勢</th></tr>')
    return (f'<div class="card"><h2>🎯 Positioning · 大型投機者擁擠度 '
            f'<small>CFTC COT｜報告日 {_e(newest)}</small></h2>'
            f'<div class="body"><div class="note">'
            f'<b>淨持倉</b>＝ non-commercial long − short（大型投機者）。'
            f'<b>52 週位置</b>：0 = 一年最淡、100 = 一年最牛。'
            f'極端 ≥90 或 ≤25 = 擁擠，反向風險高（同 NEL 嘅 156 週極端同一個思路）。'
            f'<br>數據：CFTC Socrata 公開 API（免 key），報告日為<b>上週二</b>，'
            f'週五發布 —— 有固有延遲，唔係即時。</div>'
            f'<div class="scroll"><table><thead>{head}</thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></div></div>')


def _sparkline(vals, w=96, h=22):
    vv = [float(v) for v in (vals or []) if isinstance(v, (int, float))]
    if len(vv) < 4:
        return '<span class="dim">—</span>'
    lo, hi = min(vv), max(vv)
    rng = (hi - lo) or 1.0
    pts = " ".join(f"{i*(w)/max(1,len(vv)-1):.1f},"
                   f"{h-3 - (v-lo)/rng*(h-6):.1f}" for i, v in enumerate(vv))
    col = "#7fd4a8" if vv[-1] >= vv[0] else "#f08a8a"
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polyline points="{pts}" fill="none" stroke="{col}" '
            f'stroke-width="1.5"/></svg>')


# ══════════════════════════ 共用 ══════════════════════════
def _ohlc():
    """攞 OHLC：先用掃描器嘅 cm_ohlc.pkl，再用 lab 嘅 daily_2y.pkl。

    ★ 唔准自己抓 —— 用返已有快取，保證同其他頁面同一組價。
    """
    import pandas as pd
    for p in (os.path.join(HOME, "data", "cm_ohlc.pkl"),
              os.path.join(HOME, "cache", "cm_ohlc.pkl"),
              os.path.join(os.path.dirname(HOME), "trading-os-lab",
                           "cache", "daily_2y.pkl")):
        if os.path.exists(p):
            try:
                return pd.read_pickle(p)
            except Exception:                                # noqa: BLE001
                continue
    return None


def _e(s):
    import html
    return html.escape(str(s if s is not None else ""))


def _tone(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "dim"
    return "pos" if v > 0 else ("neg" if v < 0 else "dim")


def _unavail(title, why):
    return (f'<div class="card"><h2>{_e(title)}</h2><div class="body">'
            f'<div class="warn">⚠️ <b>DATA_UNAVAILABLE</b> —— {why}<br>'
            f'未夠數據就唔出表，唔會用 0 或假數填（EDGE-016 Missing ≠ Zero）。'
            f'</div></div></div>')


HERE_CACHE = os.path.join(HOME, "cache")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", default="positioning",
                    choices=["themes", "sectors", "breadth", "review",
                             "positioning"])
    a = ap.parse_args()
    fn = {"themes": themes_page, "sectors": sectors_page,
          "breadth": breadth_page, "review": review_page,
          "positioning": positioning_page}[a.which]
    if a.which in ("themes", "sectors"):
        print(fn(_ohlc()))
    else:
        print(fn())
