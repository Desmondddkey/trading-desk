# -*- coding: utf-8 -*-
"""market_regime.py — MARKET REGIME 指標（MRI 0-100）Desmond 2026-10-19

★ 需求：「幫我網頁加入 MARKET REGIME，可以令我睇到呢個 TradingView 指標」
   https://www.tradingview.com/chart/h6bQ6ADj/

★★★ 誠實聲明：該指標係私有 Pine 腳本，**原始碼讀唔到**。
   本檔係從畫面反推嘅【重建版】，權重同分項名稱跟足畫面，
   但每個分項嘅具體計分公式係我自己定義（寫死喺下面 SCORING 註解）。
   → 數字會同原指標接近但唔會完全一樣。呢點必須講明，唔准扮一樣。

★ 畫面顯示嘅 7 個分項同權重（總 100）：
     1. SPY 趨勢    | 25
     2. MMTW 寬度   | 20
     3. 市場結構    | 15
     4. FTD 狀態    | 12
     5. VIX 風險    | 10
     6. RSP vs SPY  | 10
     7. 季節性      |  8

★ 資料來源：
   - SPY / RSP / ^VIX 日線 → yfinance（快取 cache/regime/）
   - 寬度 %above40MA → output/breadth_*.json（我哋自己 breadth 模組）
   - FTD → 由 SPY 高低點自行判定

★ 唯讀研究用途，非買入指令。
"""
import datetime as dt
import html as _h
import io
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TO = r"C:\Users\rain0\trading-os"
OUT = os.path.join(TO, "output")
CACHE = os.path.join(HERE, "cache", "regime")

# ══════════════════════════════════════════════════════════════
# ★ 分項權重（跟畫面寫死，唔准隨意改）
WEIGHTS = [
    ("spy_trend", "SPY 趨勢", 25),
    ("mmtw", "MMTW 寬度", 20),
    ("structure", "市場結構", 15),
    ("ftd", "FTD 狀態", 12),
    ("vix", "VIX 風險", 10),
    ("rsp", "RSP vs SPY", 10),
    ("season", "季節性", 8),
]
MAX_MRI = sum(w for _, _, w in WEIGHTS)          # = 100


# ══════════════════════════════════════════════════════════════
# 資料層
def _yf_daily(tickers, days=400):
    """抓日線 → dict[ticker] = list[(date, close, high, low)]。有快取。"""
    os.makedirs(CACHE, exist_ok=True)
    key = "_".join(sorted(tickers))
    p = os.path.join(CACHE, f"{key}.pkl")
    today = dt.date.today()
    if os.path.exists(p):
        try:
            d, asof = pickle.load(open(p, "rb"))
            if (today - asof).days <= 1:
                return d, asof
        except Exception:                                    # noqa: BLE001
            pass
    try:
        import yfinance as yf
        df = yf.download(list(tickers), period=f"{days}d",
                         interval="1d", progress=False,
                         auto_adjust=False, group_by="ticker")
    except Exception as e:                                   # noqa: BLE001
        # 退回舊快取
        if os.path.exists(p):
            try:
                d, asof = pickle.load(open(p, "rb"))
                return d, asof
            except Exception:                                # noqa: BLE001
                pass
        raise RuntimeError(f"yfinance 失敗: {e}") from e

    out = {}
    for t in tickers:
        try:
            sub = df[t] if len(tickers) > 1 else df
            sub = sub.dropna(subset=["Close"])
        except (KeyError, TypeError):
            continue
        rows = []
        for idx, r in sub.iterrows():
            try:
                rows.append((str(idx.date()),
                             float(r["Close"]),
                             float(r.get("High", r["Close"])),
                             float(r.get("Low", r["Close"]))))
            except (TypeError, ValueError):
                continue
        if rows:
            out[t] = rows
    if out:
        asof = dt.date.fromisoformat(max(v[-1][0] for v in out.values()))
        pickle.dump((out, asof), open(p, "wb"))
        return out, asof
    raise RuntimeError("冇抓到任何數據")


def _load_breadth():
    """讀最新 breadth json → dict | None。"""
    import glob
    fs = sorted(glob.glob(os.path.join(OUT, "breadth_*.json")))
    if not fs:
        return None
    try:
        return json.load(io.open(fs[-1], encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _ma(vals, n):
    return (sum(vals[-n:]) / n) if len(vals) >= n else None


# ══════════════════════════════════════════════════════════════
# 七個分項（每項回 dict: score, detail, tone）
# ★ 每項滿分 = 該項權重；0 = 最差
def s_spy(d, wt):
    """SPY 趨勢（25）：收市 vs 20/50/200MA + 20MA 斜率。

    計分：站上 20MA +8 / 50MA +8 / 200MA +6 / 20MA 上升 +3
    """
    bars = d.get("SPY") or []
    if len(bars) < 210:
        return None
    cl = [b[1] for b in bars]
    px = cl[-1]
    ma20, ma50, ma200 = _ma(cl, 20), _ma(cl, 50), _ma(cl, 200)
    slope20 = (_ma(cl, 20) - _ma(cl[:-5], 20)) if len(cl) > 25 else 0
    s = 0
    got = []
    if ma20 and px > ma20:
        s += 8; got.append(">20MA")
    if ma50 and px > ma50:
        s += 8; got.append(">50MA")
    if ma200 and px > ma200:
        s += 6; got.append(">200MA")
    if slope20 and slope20 > 0:
        s += 3; got.append("20MA↑")
    s = min(s, wt)
    state = ("上行趨勢" if s >= 20 else "轉弱" if s >= 12 else
             "下行趨勢" if s < 8 else "混合")
    return dict(name="SPY 趨勢", wt=wt, score=s, tone="up" if s >= 20 else
                "dn" if s < 12 else "",
                detail=f"{state}（{'·'.join(got) if got else '全部跌穿'}）｜"
                       f"收 {px:,.2f}｜20MA {ma20:,.2f}")


def s_mmtw(d, wt, br):
    """MMTW 寬度（20）：% 股票站上 40MA + 相對 5 日前改善。

    計分：>=60% → 20｜>=50 → 16｜>=40 → 12｜>=30 → 8｜<30 → 4
          改善 ≥2pp 額外 +0（已計入 grade）
    """
    if not br:
        return None
    pct = br.get("pct40ma")
    if pct is None:
        return None
    if pct >= 60:
        s = 20
    elif pct >= 50:
        s = 16
    elif pct >= 40:
        s = 12
    elif pct >= 30:
        s = 8
    else:
        s = 4
    s = min(s, wt)
    tone = "up" if pct >= 50 else "dn" if pct < 35 else ""
    band = ("強" if pct >= 60 else "中性偏強" if pct >= 50 else
            "中性" if pct >= 40 else "弱" if pct >= 30 else "極弱")
    return dict(name="MMTW 寬度", wt=wt, score=s, tone=tone,
                detail=f"{pct:.1f}%｜{band}")


def s_structure(d, wt):
    """市場結構（15）：最近 10 日 SPY 高高低低。

    計分：數「higher high + higher low」嘅日數（0-10）
          → 10 日全健康 = 15；每少一日 -1.5
    """
    bars = d.get("SPY") or []
    if len(bars) < 15:
        return None
    seg = bars[-11:]
    hh = hl = 0
    for i in range(1, len(seg)):
        if seg[i][2] > seg[i - 1][2]:
            hh += 1
        if seg[i][3] > seg[i - 1][3]:
            hl += 1
    health = (hh + hl) / 2.0                 # 0-10
    s = min(wt, round(health / 10 * wt))
    state = ("健康" if health >= 7 else "轉差" if health >= 4 else "破壞")
    return dict(name="市場結構", wt=wt, score=s,
                tone="up" if health >= 7 else "dn" if health < 4 else "",
                detail=f"高 {hh}/10 · 低 {hl}/10｜{state}")


def s_ftd(d, wt):
    """FTD 狀態（12）：距離 63 日高位 + 是否處於調整。

    計分：距高位 >=-2% → 12｜>=-5% → 9｜>=-8% → 6｜>=-12% → 3｜更差 → 0
    """
    bars = d.get("SPY") or []
    if len(bars) < 70:
        return None
    cl = [b[1] for b in bars]
    hi63 = max(cl[-63:])
    px = cl[-1]
    dist = (px / hi63 - 1) * 100
    if dist >= -2:
        s = 12
    elif dist >= -5:
        s = 9
    elif dist >= -8:
        s = 6
    elif dist >= -12:
        s = 3
    else:
        s = 0
    s = min(s, wt)
    state = "新高區" if dist >= -2 else "未處於調整" if dist >= -5 else "調整中"
    return dict(name="FTD 狀態", wt=wt, score=s,
                tone="up" if s >= 9 else "dn" if s <= 3 else "",
                detail=f"{state}（距 63 日高 {dist:+.1f}%）")


def s_vix(d, wt):
    """VIX 風險（10）：VIX 絕對水平 + 5 日變化。

    計分：<15 → 10｜15-20 → 8｜20-25 → 5｜25-30 → 2｜>30 → 0
    """
    bars = d.get("^VIX") or []
    if len(bars) < 6:
        return None
    v = bars[-1][1]
    v5 = bars[-6][1]
    chg = (v / v5 - 1) * 100 if v5 else 0
    if v < 15:
        s = 10
    elif v < 20:
        s = 8
    elif v < 25:
        s = 5
    elif v < 30:
        s = 2
    else:
        s = 0
    s = min(s, wt)
    state = ("LOW 順風" if v < 15 else "HOLD 持倉觀察" if v < 20 else
             "CAUTION 減倉" if v < 25 else "RISK-OFF 防守" if v < 30 else "PANIC")
    return dict(name="VIX 風險", wt=wt, score=s,
                tone="up" if v < 15 else "dn" if v >= 25 else "",
                detail=f"{v:.1f}｜{state}｜5日 {chg:+.1f}%")


def s_rsp(d, wt):
    """RSP vs SPY（10）：21 日相對表現，衡量市場闊度。

    計分：RSP 跑贏 >=+2% → 10｜>=0 → 8｜>=-2% → 5｜>=-4% → 2｜更差 → 0
    """
    a = d.get("SPY") or []
    b = d.get("RSP") or []
    if len(a) < 22 or len(b) < 22:
        return None
    ra = a[-1][1] / a[-22][1] - 1
    rb = b[-1][1] / b[-22][1] - 1
    rel = (rb - ra) * 100
    if rel >= 2:
        s = 10
    elif rel >= 0:
        s = 8
    elif rel >= -2:
        s = 5
    elif rel >= -4:
        s = 2
    else:
        s = 0
    s = min(s, wt)
    state = ("全面參與" if rel >= 0 else "窄·大票獨舞" if rel >= -2 else "極窄")
    return dict(name="RSP vs SPY", wt=wt, score=s,
                tone="up" if rel >= 0 else "dn",
                detail=f"21D {rel:+.2f}%｜{state}")


_SEASON = {
    1: (0.9, "一月效應"), 2: (0.0, "二月弱"), 3: (1.1, "季末強"),
    4: (1.2, "四月強"), 5: (-0.3, "Sell in May"), 6: (-0.2, "六月弱"),
    7: (0.9, "七月強"), 8: (-0.4, "八月弱"), 9: (-1.0, "九月最弱"),
    10: (1.0, "十月反彈"), 11: (1.4, "十一月最強"), 12: (0.7, "聖誕行情"),
}


def s_season(wt, today=None):
    """季節性（8）：按月歷史平均回報（長期美股統計，粗略）。

    計分：avg >=+1.0% → 8｜>=+0.3 → 6｜>=-0.3 → 4｜>=-1.0 → 2｜更差 → 0
    """
    m = (today or dt.date.today()).month
    avg, label = _SEASON.get(m, (0.0, ""))
    if avg >= 1.0:
        s = 8
    elif avg >= 0.3:
        s = 6
    elif avg >= -0.3:
        s = 4
    elif avg >= -1.0:
        s = 2
    else:
        s = 0
    s = min(s, wt)
    return dict(name="季節性", wt=wt, score=s,
                tone="up" if avg >= 0.3 else "dn" if avg < -0.3 else "",
                detail=f"{m} 月 {avg:+.1f}%｜{label}")


# ══════════════════════════════════════════════════════════════
def compute():
    """→ dict(mri, comps, verdict, posture_txt, asof, err)。"""
    today = dt.date.today()
    try:
        d, asof = _yf_daily(["SPY", "RSP", "^VIX"])
    except Exception as e:                                   # noqa: BLE001
        return dict(err=f"{type(e).__name__}: {e}")
    br = _load_breadth()
    W = {k: w for k, _, w in WEIGHTS}

    comps = [
        s_spy(d, W["spy_trend"]),
        s_mmtw(d, W["mmtw"], br),
        s_structure(d, W["structure"]),
        s_ftd(d, W["ftd"]),
        s_vix(d, W["vix"]),
        s_rsp(d, W["rsp"]),
        s_season(W["season"], today),
    ]
    comps = [c for c in comps if c]
    if not comps:
        return dict(err="全部分項計算失敗")
    mri = sum(c["score"] for c in comps)
    mx = sum(c["wt"] for c in comps)
    mri100 = round(mri / mx * MAX_MRI) if mx else 0

    # 建議總持倉（跟畫面嘅 25% / A+ Setup 試倉 邏輯，分段寫死）
    if mri100 >= 80:
        pos, pos_lbl = "75-100%", "全速"
    elif mri100 >= 65:
        pos, pos_lbl = "50-75%", "正常"
    elif mri100 >= 50:
        pos, pos_lbl = "25-50%", "減速"
    elif mri100 >= 35:
        pos, pos_lbl = "10-25%", "A+ Setup 試倉"
    else:
        pos, pos_lbl = "0-10%", "現金為主"

    # 交易難度
    if mri100 >= 70:
        diff = "TREND"
    elif mri100 >= 45:
        diff = "CHOP"
    else:
        diff = "HOSTILE"

    # 結論（最弱兩項主導）
    weak = sorted(comps, key=lambda c: c["score"] / c["wt"])[:2]
    verdict = ("內部轉弱 / 停止加倉" if mri100 < 50 else
               "偏強但需揀股" if mri100 < 70 else "趨勢健康 / 可加倉")
    return dict(mri=mri100, comps=comps, asof=str(asof),
                pos=pos, pos_lbl=pos_lbl, diff=diff,
                verdict=verdict,
                weak=[w["name"] for w in weak],
                breadth_txt=(f"{br.get('pct40ma'):.1f}% 站上 40MA"
                             if br and br.get("pct40ma") else "—"))


CSS = """
.mr-hero{display:flex;align-items:center;gap:18px;flex-wrap:wrap;
  padding:16px 18px;border-radius:14px;margin:0 0 16px;
  border:1px solid rgba(128,128,128,.3);background:rgba(128,128,128,.05)}
.mr-num{font-size:44px;font-weight:800;line-height:1}
.mr-num small{font-size:15px;opacity:.55;font-weight:600}
.mr-tag{font-size:12px;font-weight:800;padding:5px 12px;border-radius:999px;
  border:1px solid currentColor}
.mr-bar{height:10px;border-radius:999px;background:rgba(128,128,128,.2);
  overflow:hidden;margin:8px 0 0;width:100%;max-width:420px}
.mr-bar>span{display:block;height:100%;border-radius:999px}
.mr-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
.mr-tbl th{text-align:left;font-size:10.5px;letter-spacing:.05em;
  text-transform:uppercase;opacity:.6;padding:6px 8px;
  border-bottom:1px solid rgba(128,128,128,.25)}
.mr-tbl th.r,.mr-tbl td.r{text-align:right}
.mr-tbl td{padding:7px 8px;border-bottom:1px solid rgba(128,128,128,.1)}
.mr-tbl tr:hover{background:rgba(128,128,128,.07)}
.mr-wt{font-size:10.5px;opacity:.55;font-weight:600}
.mr-mini{display:inline-block;height:7px;border-radius:3px;
  background:rgba(128,128,128,.25);width:60px;vertical-align:middle;
  overflow:hidden;margin-right:6px}
.mr-mini>span{display:block;height:100%}

/* ★ 手機：判讀欄換行到下一行，唔會被切 */
@media(max-width:700px){
  .mr-tbl thead{display:none}
  .mr-tbl,.mr-tbl tbody,.mr-tbl tr,.mr-tbl td{display:block;width:100%}
  .mr-tbl tr{padding:9px 0;border-bottom:1px solid rgba(128,128,128,.18)}
  .mr-tbl td{border:0;padding:1px 0;text-align:left!important}
  .mr-tbl td:nth-child(1){font-size:13px}
  .mr-tbl td:nth-child(2){display:inline;font-size:15px}
  .mr-tbl td:nth-child(3){display:inline;font-size:11px;opacity:.55;
    margin-left:4px}
  .mr-tbl td:nth-child(4){display:inline;margin-left:8px}
  .mr-tbl td:nth-child(5){font-size:11.5px;opacity:.8;margin-top:3px;
    line-height:1.6;white-space:normal}
  .mr-mini{width:70px}
}
"""


def _esc(v):
    return _h.escape(str(v)) if v is not None else ""


def build():
    r = compute()
    parts = [f"<style>{CSS}</style>"]
    parts.append('<h2>MARKET REGIME <small>MRI 0–100</small></h2>')
    parts.append(
        '<p class="crumb">★ 重建版（原 TradingView 指標為私有腳本，'
        '讀唔到原始碼）｜權重同分項跟足畫面，'
        '每項計分公式由本系統定義｜唯讀研究用途</p>')


    # ★ 2026-10-19 Desmond：「你要將呢個網頁嵌入直接顯示係入面」
    #   實測：www.tradingview.com/chart/h6bQ6ADj/ → 403 + frame-ancestors 'none'
    #        → 私有 chart 物理上唔可能嵌入。
    #   改用官方 s.tradingview.com/widgetembed/（200，無 X-Frame-Options）。
    parts.append(
        '<div class="card" style="padding:0;overflow:hidden">'
        '<div style="padding:11px 15px;background:rgba(128,128,128,.08);'
        'display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
        '<b style="font-size:13.5px">TradingView 圖表</b>'
        '<span style="font-size:11.5px;opacity:.6">SPY 日線 · 官方 widget</span>'
        '<span style="margin-left:auto;font-size:11.5px">'
        '<a href="https://www.tradingview.com/chart/h6bQ6ADj/" '
        'target="_blank" rel="noopener noreferrer">↗ 你嘅私有 chart（要登入）</a>'
        '</span></div>'
        '<iframe src="https://s.tradingview.com/widgetembed/?'
        'symbol=AMEX%3ASPY&interval=D&hidesidetoolbar=0&symboledit=1&'
        'saveimage=1&toolbarbg=rgba(0,0,0,0)&studies=[]&theme=dark&style=1&'
        'timezone=America%2FNew_York&withdateranges=1&hide_side_toolbar=1&'
        'allow_symbol_change=1&details=0&hotlist=0&calendar=0" '
        'style="width:100%;height:520px;border:0;display:block" '
        'allowfullscreen loading="lazy" '
        'referrerpolicy="no-referrer-when-downgrade"></iframe>'
        '<div style="padding:10px 15px;font-size:12px;line-height:1.75;'
        'opacity:.75">'
        '★ <b>你嗰個 MARKET REGIME 指標嵌唔到</b>：'
        'TradingView 對 <code>/chart/h6bQ6ADj/</code> 回 <b>403</b>'
        ' 同 <code>frame-ancestors &quot;none&quot;</code>，'
        '而且私有 Pine 腳本只有你自己登入後才見到。'
        '呢個 iframe 用官方 widget，所以係真嘅即時 TradingView 圖；'
        '指標數值就用下面我哋自己計嘅七個分項。'
        '</div></div>')

    if r.get("err"):
        parts.append('<div class="card"><div class="body" style="color:#e5484d">'
                     f'⛔ DATA_UNAVAILABLE：{_esc(r["err"])}'
                     '<br>★ Missing ≠ Zero，唔會扮有數。</div></div>')
        return ("MARKET REGIME", "".join(parts))

    mri = r["mri"]
    col = ("#16a34a" if mri >= 70 else "#f59e0b" if mri >= 50 else
           "#ea580c" if mri >= 35 else "#dc2626")

    parts.append(
        '<div class="mr-hero">'
        f'<div><div class="mr-num" style="color:{col}">{mri}'
        f'<small> / {MAX_MRI}</small></div>'
        f'<div class="mr-bar"><span style="width:{mri}%;'
        f'background:{col}"></span></div></div>'
        f'<div style="flex:1;min-width:180px">'
        f'<div><span class="mr-tag" style="color:{col}">'
        f'{_esc(r["verdict"])}</span></div>'
        f'<div style="font-size:12.5px;opacity:.75;margin-top:8px">'
        f'建議總持倉 <b>{_esc(r["pos"])}</b>（{_esc(r["pos_lbl"])}）'
        f'｜交易難度 <b>{_esc(r["diff"])}</b></div>'
        f'<div style="font-size:11.5px;opacity:.55;margin-top:4px">'
        f'最弱兩項：{_esc("、".join(r["weak"]))}'
        f'｜資料 {_esc(r["asof"])}</div>'
        '</div></div>')

    parts.append('<div class="card"><h2>七個分項 '
                 '<small>滿分 = 權重</small></h2>'
                 '<div style="padding:10px 14px">'
                 '<table class="mr-tbl"><thead><tr>'
                 '<th>分項</th><th class="r">得分</th>'
                 '<th class="r">權重</th><th style="width:90px"></th>'
                 '<th>判讀</th></tr></thead><tbody>')
    for i, c in enumerate(r["comps"], 1):
        pctv = c["score"] / c["wt"] * 100 if c["wt"] else 0
        cc = ("#16a34a" if pctv >= 70 else "#f59e0b" if pctv >= 40
              else "#dc2626")
        parts.append(
            f'<tr><td><b>{i}. {_esc(c["name"])}</b></td>'
            f'<td class="r" style="font-weight:800;color:{cc}">'
            f'{c["score"]}</td>'
            f'<td class="r mr-wt">{c["wt"]}</td>'
            f'<td><span class="mr-mini"><span style="width:{pctv:.0f}%;'
            f'background:{cc}"></span></span></td>'
            f'<td class="{c["tone"]}" style="font-size:12px;white-space:normal;'
            f'word-break:break-word">'
            f'{_esc(c["detail"])}</td></tr>')
    parts.append('</tbody></table></div></div>')

    parts.append(
        '<div class="card"><h2>★ 計分規則（寫死）</h2>'
        '<div class="body" style="font-size:12.5px;line-height:1.95">'
        '<b>1. SPY 趨勢（25）</b>：站上 20MA +8／50MA +8／200MA +6／'
        '20MA 上升 +3<br>'
        '<b>2. MMTW 寬度（20）</b>：站上 40MA 比例 '
        '≥60%→20｜≥50→16｜≥40→12｜≥30→8｜&lt;30→4<br>'
        '<b>3. 市場結構（15）</b>：最近 10 日 SPY 高高低低健康度 ×15<br>'
        '<b>4. FTD 狀態（12）</b>：距 63 日高 ≥−2%→12｜≥−5→9｜'
        '≥−8→6｜≥−12→3｜更差→0<br>'
        '<b>5. VIX 風險（10）</b>：&lt;15→10｜15–20→8｜20–25→5｜'
        '25–30→2｜&gt;30→0<br>'
        '<b>6. RSP vs SPY（10）</b>：21 日相對 ≥+2%→10｜≥0→8｜'
        '≥−2→5｜≥−4→2｜更差→0<br>'
        '<b>7. 季節性（8）</b>：按月長期平均 ≥+1.0%→8｜≥+0.3→6｜'
        '≥−0.3→4｜≥−1.0→2｜更差→0<br><br>'
        '<b>持倉分段</b>：MRI ≥80 → 75–100%｜65–79 → 50–75%｜'
        '50–64 → 25–50%｜35–49 → 10–25%（A+ 試倉）｜&lt;35 → 0–10%<br>'
        '<b>交易難度</b>：MRI ≥70 TREND｜45–69 CHOP｜&lt;45 HOSTILE'
        '</div></div>')
    return ("MARKET REGIME", "".join(parts))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    r = compute()
    print(json.dumps({k: v for k, v in r.items() if k != "comps"},
                     ensure_ascii=False, indent=1))
    if r.get("comps"):
        print("\n分項：")
        for i, c in enumerate(r["comps"], 1):
            print(f"  {i}. {c['name']:<14}{c['score']:>3}/{c['wt']:<3}"
                  f"  {c['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
