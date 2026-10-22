# -*- coding: utf-8 -*-
"""market_regime.py — MARKET REGIME（MRI 0-100）
★ 2026-10-19 重寫：完全照 Desmond 提供嘅 Pine 原碼
  「Smart Money Sector Flow — Fused Engine v1.9 + MRI」裡面嘅計分邏輯。

━━━ 原始 Pine 公式（逐條照抄）━━━
mriTrendScore       = trendUp ? 25 : trendDown ? 0 : 12
  trendUp   = close > sma50 and sma50 > sma150 and not (sma200 < sma200[1])
  trendDown = (close < sma50 and sma50 < sma150) or (sma200 < sma200[1])
mriBreadthRaw       = clamp((mmtw - 20) / 60 * 20, 0, 20)
mriBreadthScore     = (oversold and mmtwRising) ? max(raw, 7) : raw
mriStructureScore   = structLowerHigh ? 0
                    : (higherHigh and higherLow) ? 15
                    : higherLow ? 10
                    : consecUp >= 3 ? 11
                    : consecDn >= 2 ? 3 : 7
mriFTDScore         = (ftd found and not broken) ? 12
                    : rallyDay >= 4 ? 8 : rallyDay > 0 ? 4
                    : trendUp ? 6 : 1
mriVixScore         = vix < 15 ? 10 : vix < 25 ? 7 : vix < 35 ? 4 : 0
mriEqualWeightScore = rspVsSpy > 1.0 ? 10 : > 0 ? 8 : > -1.0 ? 4 : 0
mriSeasonScore      = seasonBull ? 8 : seasonBear ? 0 : 4
mri = clamp(sum, 0, 100)

seasonAvg = [1.1, 0.3, 0.8, 1.4, -0.1, -0.2, 1.3, -0.1, -0.7, 0.8, 1.3, 1.0]

mriRiskOff          = mri < 35 or trendDown or (mriWorsening and mri < 50)
mriInternalWeakness = trendUp and (mriBreadthScore < 8 or widthNarrow
                                   or mriWorsening or vixStress)

━━━ 與原 Pine 唯一差異（必須講明）━━━
Pine 用 `INDEX:MMTW`（TradingView 嘅 % Above 20MA）。
我哋冇 TradingView 嘅 MMTW，改用【自己計嘅 % 站上 40MA】代替，
頁面標示「寬度（40MA）」。兩把尺唔可直接比較。
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

# Pine 原碼常數（唔准改）
SEASON_AVG = [1.1, 0.3, 0.8, 1.4, -0.1, -0.2, 1.3, -0.1, -0.7, 0.8, 1.3, 1.0]
SCORE1, SCORE2, SCORE3, SCORE4 = 35, 50, 65, 80
EARLY_DELTA, RISK_DELTA, PILOT_PCT = 5.0, -6.0, 25
FTD_MIN_DAY = 4
VIX_HOLD, VIX_SCALE, VIX_BUY = 15.0, 25.0, 35.0


def _yf(tickers, days=420):
    os.makedirs(CACHE, exist_ok=True)
    key = "_".join(sorted(t.replace("^", "") for t in tickers))
    p = os.path.join(CACHE, f"{key}.pkl")
    today = dt.date.today()
    if os.path.exists(p):
        try:
            d, asof = pickle.load(open(p, "rb"))
            if (today - asof).days <= 0:
                return d, asof
        except Exception:                                    # noqa: BLE001
            pass
    import yfinance as yf
    df = yf.download(list(tickers), period=f"{days}d", interval="1d",
                     progress=False, auto_adjust=False, group_by="ticker")
    out = {}
    for t in tickers:
        try:
            sub = (df[t] if len(tickers) > 1 else df).dropna(subset=["Close"])
        except (KeyError, TypeError):
            continue
        rows = []
        for idx, r in sub.iterrows():
            try:
                rows.append((str(idx.date()), float(r["Close"]),
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
    raise RuntimeError("冇抓到數據")


def _sma(vals, n):
    return sum(vals[-n:]) / n if len(vals) >= n else None


def _breadth():
    import glob
    fs = sorted(glob.glob(os.path.join(OUT, "breadth_*.json")))
    if not fs:
        return None
    try:
        return json.load(io.open(fs[-1], encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _tv_mmtw(ttl_min=10):
    """用 TradingView screener 算真正 % above 20MA（＝MMTW 定義）。

    全美股有 SMA20 嘅股票，計 close > SMA20 嘅比例。
    快取 10 分鐘，避免每 5 分鐘 cron 都打 TV。
    → (pct, n_total, asof_str) 或 (None, 0, None)
    """
    import time
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "mmtw.json")
    if os.path.exists(p):
        try:
            d = json.load(io.open(p, encoding="utf-8"))
            ts = d.get("ts", 0)
            if time.time() - ts < ttl_min * 60:
                return d.get("pct"), d.get("n", 0), d.get("asof")
        except (OSError, ValueError):
            pass
    try:
        from tradingview_screener import Query
        q = (Query().set_markets("america")
             .select("name", "close", "SMA20")
             .limit(6500))
        _c, df = q.get_scanner_data()
        d = df.dropna(subset=["close", "SMA20"])
        n = len(d)
        if not n:
            raise ValueError("no rows")
        pct = float((d["close"] > d["SMA20"]).sum()) / n * 100.0
        rec = dict(pct=round(pct, 2), n=n, ts=time.time(),
                   asof=dt.date.today().isoformat())
        io.open(p, "w", encoding="utf-8").write(
            json.dumps(rec, ensure_ascii=False))
        return rec["pct"], n, rec["asof"]
    except Exception:                                        # noqa: BLE001
        # 退回舊快取
        try:
            d = json.load(io.open(p, encoding="utf-8"))
            return d.get("pct"), d.get("n", 0), d.get("asof")
        except (OSError, ValueError):
            return None, 0, None


def _tv_mmfi(ttl_min=15):
    """自算 MMFI ≈ % of NYSE+NASDAQ+AMEX 普通股 above 50MA。

    Desmond 2026-10-20：MARKET REGIME 頁 MMTW 下面加 MMFI。

    ★ 為何要自算：MMFI 係 TradingView 自家 index（INDEX:MMFI），
      冇公開 API 讀數值，只有 widget 顯示 →
      所以用 screener 自己數，同時用 widget 顯示官方圖。

    ★ 校準（2026-10-20 實測，官方 28.64%）：
        NYSE only           36.57%  （差 +7.9pp ✗）
        NYSE+NASDAQ+AMEX    29.76%  （差 +1.1pp ✓）
        全美股（含 OTC）      30.01%  （差 +1.4pp）
      → 用 NYSE+NASDAQ+AMEX，剔走 OTC 仙股。

    → (pct, n_total, asof_str) 或 (None, 0, None)
    """
    import time
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "mmfi.json")
    if os.path.exists(p):
        try:
            d = json.load(io.open(p, encoding="utf-8"))
            if time.time() - d.get("ts", 0) < ttl_min * 60:
                return d.get("pct"), d.get("n", 0), d.get("asof")
        except (OSError, ValueError):
            pass
    try:
        from tradingview_screener import Query
        q = (Query().set_markets("america")
             .select("name", "exchange", "close", "SMA50")
             .limit(8000))
        _c, df = q.get_scanner_data()
        d = df.dropna(subset=["close", "SMA50"])
        d = d[d["exchange"].isin(["NYSE", "NASDAQ", "AMEX"])]
        n = len(d)
        if not n:
            raise ValueError("no rows")
        pct = float((d["close"] > d["SMA50"]).sum()) / n * 100.0
        rec = dict(pct=round(pct, 2), n=n, ts=time.time(),
                   asof=dt.date.today().isoformat())
        io.open(p, "w", encoding="utf-8").write(
            json.dumps(rec, ensure_ascii=False))
        return rec["pct"], n, rec["asof"]
    except Exception:                                        # noqa: BLE001
        try:
            d = json.load(io.open(p, encoding="utf-8"))
            return d.get("pct"), d.get("n", 0), d.get("asof")
        except (OSError, ValueError):
            return None, 0, None


def _mmfi_label(v):
    """MMFI 分區（來源：@ohiain 2026-10-20 帖）。

    ≥70 Broad strength — 橡皮筋拉緊，easy money 通常已賺
    ~50 Neutral + mixed — 睇領導股
    20-30 Weak + oversold — 壓力釋放但唔代表即刻升
    """
    if v is None:
        return ("N/A", "#64748b", "")
    if v >= 70:
        return ("Broad strength", "#16a34a",
                "大部分股票喺 50MA 上｜健康，但橡皮筋拉緊 —— easy money 通常已賺")
    if v >= 55:
        return ("Healthy", "#22c55e", "多數股票參與中期趨勢")
    if v >= 45:
        return ("Neutral + mixed", "#f59e0b",
                "約一半市場參與｜睇領導股同相對強度")
    if v >= 30:
        return ("Weakening", "#ea580c", "參與度下降｜提高選股門檻")
    if v >= 20:
        return ("Weak + oversold", "#dc2626",
                "大部分股票喺 50MA 下｜壓力已釋放，但唔代表即刻升")
    return ("Extreme oversold", "#991b1b",
            "極度超賣｜歷史洗盤區，但可以更超賣")


def compute():
    try:
        d, asof = _yf(["SPY", "RSP", "^VIX"])
    except Exception as e:                                   # noqa: BLE001
        return dict(err=f"{type(e).__name__}: {e}")

    spy = d.get("SPY") or []
    if len(spy) < 210:
        return dict(err="SPY 數據不足 210 根")

    cl = [b[1] for b in spy]
    hi = [b[2] for b in spy]
    lo = [b[3] for b in spy]
    px = cl[-1]
    s50, s150, s200 = _sma(cl, 50), _sma(cl, 150), _sma(cl, 200)
    s200p = _sma(cl[:-1], 200)

    # ① SPY 趨勢 25
    ma200Decl = (s200 is not None and s200p is not None and s200 < s200p)
    upTrend = bool(s50 and s150 and px > s50 and s50 > s150)
    downTrend = bool(s50 and s150 and px < s50 and s50 < s150)
    trendUp = bool(upTrend and not ma200Decl)
    trendDown = bool(downTrend or ma200Decl)
    trendScore = 25.0 if trendUp else (0.0 if trendDown else 12.0)
    trendLabel = ("下行趨勢 (200MA↓)" if ma200Decl else
                  "上行趨勢 (+1)" if upTrend else
                  "下行趨勢 (-1)" if downTrend else "波動上落 (0)")

    # ② 寬度 20（真正 % above 20MA = MMTW 定義，TV screener）
    br = _breadth() or {}
    tv_pct, tv_n, tv_asof = _tv_mmtw()
    mmfi_pct, mmfi_n, mmfi_asof = _tv_mmfi()
    _mmfi_pct, _mmfi_n, _mmfi_asof = mmfi_pct, mmfi_n, mmfi_asof
    mmtw = tv_pct if tv_pct is not None else br.get("pct40ma")
    breadthRaw = (10.0 if mmtw is None
                  else max(0.0, min(20.0, (mmtw - 20.0) / 60.0 * 20.0)))
    OS_LEVEL, OS_EXIT = 25.0, 30.0   # Pine 原值（20MA 尺）
    prev42 = br.get("pct40ma")
    # 用 breadth json 的 40MA 變化做方向代理（兩者高度相關）
    prev = br.get("prev_pct40ma")
    mmtwRising = bool(mmtw is not None and prev is not None
                      and prev42 is not None and prev42 > prev)
    oversold = bool(mmtw is not None and mmtw <= OS_LEVEL)
    breadthScore = (max(breadthRaw, 7.0) if (oversold and mmtwRising)
                    else breadthRaw)

    # ③ 市場結構 15
    rH = max(hi[-10:]) if len(hi) >= 20 else None
    pH = max(hi[-20:-10]) if len(hi) >= 20 else None
    rL = min(lo[-10:]) if len(lo) >= 20 else None
    pL = min(lo[-20:-10]) if len(lo) >= 20 else None
    lowerHigh = (rH is not None and pH is not None and rH < pH)
    higherHigh = (rH is not None and pH is not None and rH >= pH)
    higherLow = (rL is not None and pL is not None and rL > pL)
    consecUp = 0
    for i in range(len(cl) - 1, max(0, len(cl) - 6), -1):
        if cl[i] > cl[i - 1]:
            consecUp += 1
        else:
            break
    consecDn = 0
    for i in range(len(cl) - 1, max(0, len(cl) - 6), -1):
        if cl[i] < cl[i - 1]:
            consecDn += 1
        else:
            break
    if lowerHigh:
        structScore = 0.0
    elif higherHigh and higherLow:
        structScore = 15.0
    elif higherLow:
        structScore = 10.0
    elif consecUp >= 3:
        structScore = 11.0
    elif consecDn >= 2:
        structScore = 3.0
    else:
        structScore = 7.0
    structText = ("低高結構⚠️" if lowerHigh else
                  "高高低低·健康" if (higherHigh and higherLow) else "結構轉換中")
    if consecUp >= 1:
        structText += f" · 連升{consecUp}日"
    elif consecDn >= 1:
        structText += f" · 連跌{consecDn}日"

    # ④ FTD 12
    hi63 = max(hi[-63:])
    lo40 = min(lo[-40:])
    ddPct = (lo40 / hi63 - 1) * 100 if hi63 else None
    inCorr = bool(ddPct is not None and ddPct <= -5.0)
    rallyDay, ftdFound, ftdBroken, ftdDay = 0, False, False, 0
    if inCorr:
        lowIdx = lo.index(lo40, len(lo) - 40)
        for j in range(max(lowIdx + 1, 1), len(cl)):
            if cl[j] > cl[j - 1]:
                rallyDay = j - lowIdx + 1
                if rallyDay >= FTD_MIN_DAY:
                    g = (cl[j] / cl[j - 1] - 1) * 100 if cl[j - 1] else 0
                    if g >= 1.25:
                        ftdFound, ftdDay = True, rallyDay
                        break
        if ftdFound:
            ftdLow = lo[lowIdx + ftdDay - 1]
            ftdBroken = any(c < ftdLow for c in cl[lowIdx + ftdDay:])
    if ftdFound and not ftdBroken:
        ftdScore = 12.0
    elif rallyDay >= FTD_MIN_DAY:
        ftdScore = 8.0
    elif rallyDay > 0:
        ftdScore = 4.0
    elif trendUp:
        ftdScore = 6.0
    else:
        ftdScore = 1.0
    ftdText = ("✅ FTD 確認" if (ftdFound and not ftdBroken) else
               f"嘗試反彈 第{rallyDay}日" if rallyDay > 0 else
               f"未處於調整（低位距63日高 {ddPct:+.1f}%）"
               if (ddPct is not None and not inCorr) else "未有反彈嘗試")

    # ⑤ VIX 10
    vix = (d.get("^VIX") or [[None, None]])[-1][1]
    if vix is None:
        vixScore = 5.0
    elif vix < VIX_HOLD:
        vixScore = 10.0
    elif vix < VIX_SCALE:
        vixScore = 7.0
    elif vix < VIX_BUY:
        vixScore = 4.0
    else:
        vixScore = 0.0
    vixStress = bool(vix is not None and vix >= VIX_SCALE)
    vixLabel = ("N/A" if vix is None else
                "BUY 激進進攻" if vix >= VIX_BUY else
                "SCALE IN 分段加倉" if vix >= VIX_SCALE else
                "HOLD 持倉觀察" if vix >= VIX_HOLD else "SELL 減倉防守")

    # ⑥ RSP vs SPY 10
    rsp = d.get("RSP") or []
    rspVsSpy = None
    if len(rsp) >= 22 and len(cl) >= 22:
        rspVsSpy = ((rsp[-1][1] / rsp[-22][1] - 1)
                    - (cl[-1] / cl[-22] - 1)) * 100
    if rspVsSpy is None:
        eqScore = 5.0
    elif rspVsSpy > 1.0:
        eqScore = 10.0
    elif rspVsSpy > 0:
        eqScore = 8.0
    elif rspVsSpy > -1.0:
        eqScore = 4.0
    else:
        eqScore = 0.0
    widthNarrow = bool(rspVsSpy is not None and rspVsSpy < 0)

    # ⑦ 季節性 8
    mIdx = dt.date.today().month - 1
    mAvg = SEASON_AVG[mIdx]
    seasonBull, seasonBear = mAvg >= 1.0, mAvg < 0
    seasonScore = 8.0 if seasonBull else (0.0 if seasonBear else 4.0)

    mri = max(0.0, min(100.0, trendScore + breadthScore + structScore
                       + ftdScore + vixScore + eqScore + seasonScore))
    mriR = round(mri)

    yp = os.path.join(CACHE, "mri_prev.json")
    today = dt.date.today().isoformat()
    prev_mri = None
    try:
        st = json.load(io.open(yp, encoding="utf-8"))
        if st.get("date") != today:
            prev_mri = st.get("mri")
    except (OSError, ValueError):
        pass
    io.open(yp, "w", encoding="utf-8").write(
        json.dumps({"date": today, "mri": mriR}))
    delta = (mriR - prev_mri) if prev_mri is not None else None
    improving = delta is not None and delta >= EARLY_DELTA
    worsening = delta is not None and delta <= RISK_DELTA

    riskOff = bool(mri < SCORE1 or trendDown or (worsening and mri < SCORE2))
    internalWeak = bool(trendUp and (breadthScore < 8 or widthNarrow
                                     or worsening or vixStress))
    earlyRepair = bool(SCORE1 <= mri < SCORE2
                       and (improving or (mmtwRising and structScore >= 10))
                       and not vixStress and not lowerHigh)

    if riskOff:
        state, scol, posPct = "防守／風險關閉", "dn", 0
    elif internalWeak:
        state, scol, posPct = "內部轉弱／停止加倉", "dn", 25
    elif mri >= SCORE4:
        state, scol, posPct = "強勢上行", "up", 100
    elif mri >= SCORE3:
        state, scol, posPct = "上行確認", "up", 75
    elif mri >= SCORE2:
        state, scol, posPct = "修復轉強", "", 50
    elif earlyRepair:
        state, scol, posPct = "早期轉強／試倉", "", PILOT_PCT
    else:
        state, scol, posPct = "觀察／低風險", "", 10

    posText = ("0%｜停止 Long／現金優先" if posPct == 0 else
               "10%｜只觀察或極小倉" if posPct <= 10 else
               f"{posPct}%｜A+ Setup 試倉" if posPct <= 25 else
               "50%｜分批建立持倉" if posPct <= 50 else
               "75%｜正常風險配置" if posPct <= 75 else
               "100%｜可進攻，但遵守單筆風險")

    diff = ("Easy Dollar"
            if (trendUp and mmtw is not None and mmtw >= 55
                and not widthNarrow and not vixStress and not lowerHigh)
            else "Hard Penny"
            if (trendDown and (breadthScore < 8 or widthNarrow
                               or vixStress or lowerHigh)) else "CHOP")

    opp = ("潛在機會：轉強試倉，只做領先股" if earlyRepair else
           "潛在機會：可找突破／續升 setup"
           if (mri >= SCORE3 and not internalWeak) else
           "風險：價升但內部轉弱，停止加倉" if internalWeak else
           "風險：假突破機率高，避免新 Long" if riskOff else
           "觀察：等待 breadth 或結構確認")

    return dict(
        mri=mriR, asof=str(asof), state=state, state_col=scol,
        pos=posText, pos_pct=posPct, diff=diff, opp=opp, delta=delta,
        mmtw=mmtw, mmtw_rising=mmtwRising, oversold=oversold,
        mmfi=_mmfi_pct, mmfi_n=_mmfi_n, mmfi_asof=_mmfi_asof,
        delta_txt=("昨日資料建立中" if delta is None else
                   f"較昨日 +{delta:.0f}" if delta > 0 else
                   f"較昨日 {delta:.0f}" if delta < 0 else "較昨日持平"),
        rows=[
            dict(n=1, name="SPY 趨勢", w=25, s=trendScore, d=trendLabel),
            dict(n=2, name="MMTW 寬度", w=20,
                 s=round(breadthScore, 1),
                 d=(f"{mmtw:.1f}%" if mmtw is not None else "N/A")
                   + (" ↑改善" if mmtwRising else "")
                   + ("｜超賣區" if oversold else "")),
            dict(n=3, name="市場結構", w=15, s=structScore, d=structText),
            dict(n=4, name="FTD 狀態", w=12, s=ftdScore, d=ftdText),
            dict(n=5, name="VIX 風險", w=10, s=vixScore,
                 d=f"{vix:.1f}｜{vixLabel}" if vix is not None else "N/A"),
            dict(n=6, name="RSP vs SPY", w=10, s=eqScore,
                 d=(f"21D {rspVsSpy:+.2f}%｜"
                    + ("窄·大票獨舞" if widthNarrow else "闊·普漲"))
                 if rspVsSpy is not None else "N/A"),
            dict(n=7, name="季節性", w=8, s=seasonScore,
                 d=f"{mIdx+1} 月 {mAvg:+.1f}%｜"
                   + ("季節順風" if seasonBull else
                      "季節逆風" if seasonBear else "中性")),
        ],
    )


CSS = """
.mr-big{display:flex;align-items:center;gap:16px;flex-wrap:wrap;
  padding:15px 17px;border-radius:13px;margin:0 0 13px;
  border:1px solid rgba(128,128,128,.32);background:rgba(128,128,128,.06)}
.mr-big .lab{font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;
  opacity:.62;font-weight:700}
.mr-big .val{font-size:36px;font-weight:800;line-height:1.05}
.mr-bar10{font-family:ui-monospace,monospace;font-size:16px;
  letter-spacing:-1.5px}
.mr-hero{display:flex;align-items:center;gap:18px;flex-wrap:wrap;
  padding:15px 17px;border-radius:13px;margin:0 0 14px;
  border:1px solid rgba(128,128,128,.3);background:rgba(128,128,128,.045)}
.mr-num{font-size:40px;font-weight:800;line-height:1}
.mr-num small{font-size:14px;opacity:.55;font-weight:600}
.mr-tag{font-size:12px;font-weight:800;padding:5px 12px;border-radius:999px;
  border:1px solid currentColor}
.mr-bar{height:9px;border-radius:999px;background:rgba(128,128,128,.2);
  overflow:hidden;margin:7px 0 0;width:100%;max-width:400px}
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

JS = """
(function(){
  var el=document.getElementById('mr-live');
  if(!el) return;
  function pull(){
    fetch('regime_live.json?t='+Date.now(), {cache:'no-store'})
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(d){
        if(!d || d.err) return;
        el.textContent = '🟢 實時 ' + (d.asof||'') + ' ' + (d.updated||'');
        el.style.opacity = '1';
        var m=document.getElementById('mr-score');
        if(m && d.mri!=null){ m.textContent = d.mri; }
        var b=document.getElementById('mr-breadth');
        if(b && d.mmtw!=null){ b.textContent = d.mmtw.toFixed(1)+'%'; }
        var s=document.getElementById('mr-state');
        if(s && d.state){ s.textContent = d.state; }
        var p=document.getElementById('mr-pos');
        if(p && d.pos){ p.textContent = d.pos; }
      })
      .catch(function(){});
  }
  pull();
  setInterval(pull, 60000);
})();
"""


def _esc(v):
    return _h.escape(str(v)) if v is not None else ""


def build():
    r = compute()
    parts = [f"<style>{CSS}</style><script>{JS}</script>"]
    parts.append('<h2>MARKET REGIME <small>MRI 0–100</small></h2>')
    parts.append(
        '<p class="crumb">計分公式照 Desmond 嘅 Pine 原碼'
        '（Smart Money Sector Flow v1.9 + MRI）｜'
        'MMTW 由 TradingView screener 實時計算（全美股 % above 20MA）｜'
        '<span id="mr-live" style="opacity:.6">⏳ 等實時資料…</span></p>')

    if r.get("err"):
        parts.append('<div class="card"><div class="body" style="color:#e5484d">'
                     f'⛔ DATA_UNAVAILABLE：{_esc(r["err"])}</div></div>')
        return ("MARKET REGIME", "".join(parts))

    mri = r["mri"]
    col = ("#16a34a" if mri >= 65 else "#f59e0b" if mri >= 50 else
           "#ea580c" if mri >= 35 else "#dc2626")

    # ① 寬度（預設最顯眼）
    bv = r.get("mmtw")
    filled = max(0, min(10, round(bv / 10))) if bv is not None else 0
    bar = "█" * filled + "░" * (10 - filled)
    bcol = ("#16a34a" if bv and bv >= 55 else
            "#f59e0b" if bv and bv >= 40 else "#dc2626")
    parts.append(
        '<div class="mr-big">'
        '<div><div class="lab">MMTW 寬度（% above 20MA）</div>'
        f'<div class="val" id="mr-breadth" style="color:{bcol}">'
        f'{f"{bv:.1f}%" if bv is not None else "N/A"}</div></div>'
        f'<div class="mr-bar10" style="color:{bcol}">{bar}</div>'
        f'<div style="font-size:12px;opacity:.72">'
        + ("↑ 改善" if r.get("mmtw_rising") else "↓ 惡化" if bv else "")
        + ("｜超賣區" if r.get("oversold") else "")
        + '</div></div>')

    # ★ MMFI（Desmond 2026-10-20：MMTW 下面加 MMFI）
    # 來源：@ohiain —— % of NYSE stocks above their 50-day MA
    mv = r.get("mmfi")
    mv = float(mv) if mv is not None else None
    mlab, mcol, mdesc = _mmfi_label(mv)
    mfill = max(0, min(10, round(mv / 10))) if mv is not None else 0
    mbar = "█" * mfill + "░" * (10 - mfill)
    parts.append(
        '<div class="mr-big" style="margin-top:10px">'
        '<div><div class="lab">MMFI（% above 50MA）'
        '<span style="opacity:.5;font-weight:400"> · 中期趨勢參與度</span>'
        '</div>'
        f'<div class="val" id="mr-mmfi" style="color:{mcol}">'
        f'{f"{mv:.1f}%" if mv is not None else "N/A"}</div></div>'
        f'<div class="mr-bar10" style="color:{mcol}">{mbar}</div>'
        f'<div style="font-size:12px;opacity:.78;margin-top:2px">'
        f'<b style="color:{mcol}">{mlab}</b>'
        + (f'　·　{mdesc}' if mdesc else '')
        + '</div></div>')

    # ★ 2026-10-21 Desmond：「我想佢可以自動表示到我宜家當日身處既階段」
    #   Stan Weinstein 四階段（Basing / Advancing / Topping / Declining）
    #   ★ 用 30 週 MA（150 日）+ 4 週斜率，機械判定，唔靠感覺。
    try:
        import sys as _sys2
        _TO = r"C:\Users\rain0\trading-os"
        if _TO not in _sys2.path:
            _sys2.path.insert(0, _TO)
        import weinstein_stage as _ws
        parts.append(_ws.card_html())
    except Exception as _ew:                                 # noqa: BLE001
        parts.append(
            '<div class="card"><h2>📊 Weinstein 四階段</h2>'
            f'<div class="body"><div class="warn">讀唔到：'
            f'{type(_ew).__name__}: {_ew}</div></div></div>')

    # ★ MMFI TradingView 圖（官方 INDEX:MMFI）
    parts.append(
        '<div class="card" style="padding:0;overflow:hidden;margin-top:10px">'
        '<div style="padding:9px 14px;background:rgba(128,128,128,.08);'
        'display:flex;align-items:center;gap:9px;flex-wrap:wrap">'
        '<b style="font-size:13px">MMFI 圖</b>'
        '<span style="font-size:11.5px;opacity:.6">'
        '% NYSE stocks above 50MA</span>'
        '<span style="margin-left:auto;font-size:11px;opacity:.55">'
        '紅線 70 ｜ 中線 50 ｜ 綠線 30</span></div>'
        '<iframe src="https://s.tradingview.com/widgetembed/?'
        'symbol=INDEX%3AMMFI&interval=D&hidesidetoolbar=1&symboledit=0&'
        'saveimage=0&toolbarbg=rgba(0,0,0,0)&studies=[]&theme=dark&style=1&'
        'timezone=America%2FNew_York&withdateranges=1&hide_side_toolbar=1&'
        'allow_symbol_change=0&details=0&hotlist=0&calendar=0" '
        'style="width:100%;height:320px;border:0;display:block" '
        'allowfullscreen loading="lazy" '
        'referrerpolicy="no-referrer-when-downgrade"></iframe></div>')

    # MMFI 點用（原文分區）
    parts.append(
        '<div class="card" style="margin-top:10px"><div style="padding:11px 14px">'
        '<div style="font-size:12.5px;font-weight:800;margin-bottom:7px">'
        'MMFI 點用（@ohiain 原文分區）</div>'
        '<div style="font-size:12px;line-height:1.95">'
        '<b style="color:#16a34a">70–80%+ 　Broad strength</b><br>'
        '　大部分股票喺 50MA 上。健康，但橡皮筋拉緊 —— '
        '動能可以持續，但大市嘅 easy money 通常已賺。<br>'
        '<b style="color:#f59e0b">約 50% 　Neutral + mixed</b><br>'
        '　大約一半市場參與。單獨唔太有用 —— '
        '要睇領導股同相對強度。<br>'
        '<b style="color:#dc2626">20–30% 以下 　Weak + oversold</b><br>'
        '　大部分股票喺 50MA 下。市場受壓。'
        '呢啲讀數通常出現喺洗盤或中期趨勢轉向下時。'
        '唔保證見底，但話你知參與度薄、做多條件差。<br>'
        '<b>電梯比喻</b>：70-80% = 好多人已經上咗電梯，越嚟越滿；'
        '跌到 20-30% = 大部分人落咗，電梯空。'
        '空唔代表即刻會上，但壓力已釋放。</div>'
        f'<div style="font-size:11px;opacity:.55;margin-top:9px">'
        f'自算讀數 {f"{mv:.2f}%" if mv is not None else "N/A"}'
        f'（NYSE+NASDAQ+AMEX 普通股，n={r.get("mmfi_n") or 0}）'
        f'　｜　官方 INDEX:MMFI 見上面圖'
        f'　｜　as of {r.get("mmfi_asof") or "—"}</div>'
        '</div></div>')

    # ★ TradingView 圖表（Desmond 要求保留）
    parts.append(
        '<div class="card" style="padding:0;overflow:hidden">'
        '<div style="padding:10px 14px;background:rgba(128,128,128,.08);'
        'display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
        '<b style="font-size:13px">TradingView</b>'
        '<span style="font-size:11.5px;opacity:.6">SPY 日線</span>'
        '<span style="margin-left:auto;font-size:11.5px">'
        '<a href="https://www.tradingview.com/chart/h6bQ6ADj/" '
        'target="_blank" rel="noopener noreferrer">↗ 你嘅私有 chart</a>'
        '</span></div>'
        '<iframe src="https://s.tradingview.com/widgetembed/?'
        'symbol=AMEX%3ASPY&interval=D&hidesidetoolbar=1&symboledit=0&'
        'saveimage=0&toolbarbg=rgba(0,0,0,0)&studies=[]&theme=dark&style=1&'
        'timezone=America%2FNew_York&withdateranges=1&hide_side_toolbar=1&'
        'allow_symbol_change=0&details=0&hotlist=0&calendar=0" '
        'style="width:100%;height:460px;border:0;display:block" '
        'allowfullscreen loading="lazy" '
        'referrerpolicy="no-referrer-when-downgrade"></iframe></div>')

    # ② MRI
    parts.append(
        '<div class="mr-hero">'
        f'<div><div class="mr-num" style="color:{col}">'
        f'<span id="mr-score">{mri}</span><small> / 100</small></div>'
        f'<div class="mr-bar"><span style="width:{mri}%;'
        f'background:{col}"></span></div></div>'
        '<div style="flex:1;min-width:180px">'
        f'<div><span class="mr-tag" id="mr-state" style="color:{col}">'
        f'{_esc(r["state"])}</span></div>'
        f'<div style="font-size:12.5px;opacity:.8;margin-top:8px">'
        f'建議總持倉 <b id="mr-pos">{_esc(r["pos"])}</b>｜'
        f'難度 <b>{_esc(r["diff"])}</b></div>'
        f'<div style="font-size:12px;opacity:.65;margin-top:5px">'
        f'{_esc(r["delta_txt"])}｜{_esc(r["opp"])}</div>'
        f'<div style="font-size:11px;opacity:.42;margin-top:4px">'
        f'資料 {_esc(r["asof"])}</div>'
        '</div></div>')

    # ③ 七個分項
    parts.append('<div class="card"><h2>七個分項 '
                 '<small>滿分 = 權重｜照 Pine 原碼</small></h2>'
                 '<div style="padding:10px 14px">'
                 '<table class="mr-tbl"><thead><tr>'
                 '<th>分項</th><th class="r">得分</th><th class="r">權重</th>'
                 '<th style="width:90px"></th><th>判讀</th>'
                 '</tr></thead><tbody>')
    for c in r["rows"]:
        pctv = c["s"] / c["w"] * 100 if c["w"] else 0
        cc = ("#16a34a" if pctv >= 70 else "#f59e0b" if pctv >= 40
              else "#dc2626")
        parts.append(
            f'<tr><td><b>{c["n"]}. {_esc(c["name"])}</b></td>'
            f'<td class="r" style="font-weight:800;color:{cc}">{c["s"]}</td>'
            f'<td class="r mr-wt">{c["w"]}</td>'
            f'<td><span class="mr-mini"><span style="width:{pctv:.0f}%;'
            f'background:{cc}"></span></span></td>'
            f'<td style="font-size:12px;white-space:normal;'
            f'word-break:break-word">{_esc(c["d"])}</td></tr>')
    parts.append('</tbody></table></div></div>')
    return ("MARKET REGIME", "".join(parts))


def write_live():
    """寫 docs/regime_live.json 俾前端每 60 秒 poll（cron 每 5 分鐘刷新）。"""
    r = compute()
    r["updated"] = dt.datetime.now().strftime("%H:%M")
    p = os.path.join(HERE, "docs", "regime_live.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(
        json.dumps(r, ensure_ascii=False, indent=1))
    return p


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if "--live" in sys.argv:
        p = write_live()
        print(f"✓ {p}")
        return 0
    r = compute()
    print(json.dumps({k: v for k, v in r.items() if k != "rows"},
                     ensure_ascii=False, indent=1))
    for c in r.get("rows") or []:
        print(f"  {c['n']}. {c['name']:<22}{c['s']:>5}/{c['w']:<3} {c['d']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
