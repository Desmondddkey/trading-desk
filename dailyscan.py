# -*- coding: utf-8 -*-
"""dailyscan.py — Daily Scan 頁（Desmond 2026-10-19）

★ 需求：「jeff sun daily scan layer 1+2 呢個JOB內容要加埋落選股到 開一個叫 Daily scan」
   L1 = 12 個 scan 嘅 ticker 清單（來自 My_Scans_*.xlsx）
   L2 = 圖表隊列表格（來自 layer2_*.json）+ 新增 EXT / ATR% / RVOL(50D) / DAY ON

★ 資料源（全部本機，唔上網，唔用 pickle）：
   L1: output/My_Scans_YYYYMMDD.xlsx  （jeffsun_scan.py 產出，12 個 sheet + All_Scans）
   L2: output/layer2_YYYYMMDD_HHMM.json（focus_list / stalk_list）
   OHLC: output/ohlc_latest.json       （含 volume，用嚟算 ATR% / RVOL）
   DAY ON: edge_book/dailyscan_history.json（我哋自己累積，記錄每隻股連續在名單幾日）

★ 欄位定義（寫死）：
   EXT      = atr_ext_50ma（＝ATRX＝(close−SMA50)/ATR14）
   ATR%     = ATR14 / close × 100
   RVOL(50D)= 當日成交量 / 過去 50 日平均成交量
   DAY ON   = 連續在 L1/L2 名單嘅日數（新上榜 = 1）

★ 沉默合約：冇資料 = DATA_UNAVAILABLE，唔准扮有。
"""
import datetime as dt
import glob
import html as _h
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TO = r"C:\Users\rain0\trading-os"
OUT = os.path.join(TO, "output")
BOOK = os.path.join(TO, "edge_book")

SCAN_ORDER = [
    "Mom_1W_Small", "Mom_1W_Large", "Mom_1M_Small", "Mom_1M_Large",
    "Mom_3M_Small", "Mom_3M_Large", "Mom_6M_Small", "Mom_6M_Large",
    "1_Fundamental_Growth", "3_Post_Earnings_Cont_Base",
    "4_Strongest_Stock_JK", "5_Strongest_Stock_10B_Rev_30_JK",
    "Daily_Tightness_Swing",
]

# ★ 2026-10-20 Desmond：滑鼠移過去顯示方格（同 ALERT 卡一樣）
SCAN_DESC = {
    "Mom_1W_Small": dict(full="Momentum 1-Week · Small Cap",
                         zh="1 週動能（小市值）",
                         how="過去 5 個交易日升幅最大嘅小型股。用嚟捉短線起步。"),
    "Mom_1W_Large": dict(full="Momentum 1-Week · Large Cap",
                         zh="1 週動能（大市值）",
                         how="過去 5 個交易日升幅最大嘅大型股。大票郁得慢但穩。"),
    "Mom_1M_Small": dict(full="Momentum 1-Month · Small Cap",
                         zh="1 月動能（小市值）",
                         how="過去 21 個交易日升幅最大嘅小型股。捉月度趨勢。"),
    "Mom_1M_Large": dict(full="Momentum 1-Month · Large Cap",
                         zh="1 月動能（大市值）",
                         how="過去 21 個交易日升幅最大嘅大型股。"),
    "Mom_3M_Small": dict(full="Momentum 3-Month · Small Cap",
                         zh="3 月動能（小市值）",
                         how="過去 63 個交易日升幅最大。較長線嘅趨勢確認。"),
    "Mom_3M_Large": dict(full="Momentum 3-Month · Large Cap",
                         zh="3 月動能（大市值）",
                         how="過去 63 個交易日升幅最大嘅大型股。"),
    "Mom_6M_Small": dict(full="Momentum 6-Month · Small Cap",
                         zh="6 月動能（小市值）",
                         how="過去 126 個交易日。捉中期領先股，噪音最少。"),
    "Mom_6M_Large": dict(full="Momentum 6-Month · Large Cap",
                         zh="6 月動能（大市值）",
                         how="過去 126 個交易日升幅最大嘅大型股。"),
    "1_Fundamental_Growth": dict(
        full="Fundamental Growth Screen",
        zh="基本面成長",
        how="盈利／營收成長達標嘅股票。Jeff Sun：基本面係「為什麼要升」嘅理由。"),
    "3_Post_Earnings_Cont_Base": dict(
        full="Post-Earnings Continuation Base",
        zh="財報後延續整理",
        how="財報大漲之後橫行整理（唔跌返去），等佢再突破。"
            "典型 O'Neil / Minervini 形態。"),
    "4_Strongest_Stock_JK": dict(
        full="Strongest Stock (JK)",
        zh="最強股票（JK 版）",
        how="JK 篩選條件下最強嘅股票清單。"),
    "5_Strongest_Stock_10B_Rev_30_JK": dict(
        full="Strongest + Revenue >$10B / Growth 30% (JK)",
        zh="最強 ＋ 營收 100 億以上、成長 30%",
        how="市值夠大、營收成長 ≥30% 嘅最強股票。過濾走細價股。"),
    "Daily_Tightness_Swing": dict(
        full="Daily Tightness Swing",
        zh="日線收窄（波段）",
        how="日線波幅持續收窄（ATR 壓縮）—— 收窄之後通常爆邊。"
            "配合 ATRX ≤4 入場。"),
}


def _sinfo(k):
    return SCAN_DESC.get(k) or dict(full=k, zh=k, how="—")


def _esc(v):
    return _h.escape(str(v)) if v is not None else ""


def _f(v, d=2):
    try:
        return f"{float(v):,.{d}f}"
    except (TypeError, ValueError):
        return "—"


def _pct(v, d=1):
    try:
        return f"{float(v):+.{d}f}%"
    except (TypeError, ValueError):
        return "—"


def _gcol(g):
    return {"A+": "#a855f7", "A": "#22c55e", "B": "#f59e0b",
            "C": "#94a3b8", "D": "#ef4444"}.get(g, "#94a3b8")


def _grade(ext, rvol, dist, atrp):
    """SETUP 品質 A+ → D（只用呢頁已有數字）。"""
    if ext is None:
        return "—", 0
    if ext > 4:
        return "D", 0
    pts = 3 if 0 <= ext <= 2 else 2
    pts += 2 if (rvol or 0) >= 2 else (1 if (rvol or 0) >= 1.2 else 0)
    if dist is not None:
        pts += 2 if dist >= -5 else (1 if dist >= -12 else 0)
    if atrp and 2 <= atrp <= 8:
        pts += 1
    return ("A+" if pts >= 7 else "A" if pts >= 5
            else "B" if pts >= 3 else "C"), pts


def _atr_band(ext_f):
    """ATR 帶 mini SVG：顯示 EXT 喺 [0,4] 範圍嘅位置"""
    if ext_f is None:
        return '<svg width="40" height="10" viewBox="0 0 40 10"><rect x="0" y="3" width="40" height="4" fill="rgba(128,128,128,.2)" rx="2"/></svg>'
    pct = max(0, min(1, ext_f / 4.0))
    x = int(pct * 36) + 2
    c = "#f97316" if ext_f > 4 else "#7c3aed"
    return f'<svg width="40" height="10" viewBox="0 0 40 10"><rect x="0" y="3" width="40" height="4" fill="rgba(128,128,128,.2)" rx="2"/><rect x="{x}" y="1" width="6" height="8" fill="{c}" rx="3"/></svg>'


# ══════════════════════════════════════════════════════════════
def load_l1():
    """My_Scans xlsx → (dict[scan] = [ticker], asof)。"""
    fs = sorted(glob.glob(os.path.join(OUT, "My_Scans_*.xlsx")))
    if not fs:
        return None, None
    f = fs[-1]
    asof = os.path.basename(f).replace("My_Scans_", "").replace(".xlsx", "")
    try:
        import openpyxl
        wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
    except Exception:                                        # noqa: BLE001
        return None, asof
    scans = {}

    def _read_sheet(ws, i_scan, i_tk):
        first = True
        for r in ws.iter_rows(values_only=True):
            if not r or len(r) <= max(i_scan, i_tk):
                continue
            if first:            # ★ 跳過表頭，唔可以當數據
                first = False
                continue
            sc, tk = r[i_scan], r[i_tk]
            if not sc or not tk:
                continue
            sc = str(sc).strip()
            if sc in ("Source_Scan", "", "None"):
                continue
            tk = str(tk).split(":")[-1].strip().upper()
            if not tk or tk in ("TICKER", "None"):
                continue
            scans.setdefault(sc, []).append(tk)

    # ★ 2026-10-19：Momentum scan（Mom_1W/1M/3M/6M × Small/Large）唔喺
    #   All_Scans sheet，佢哋喺獨立 `Momentum` sheet。要兩個都讀。
    if "All_Scans" in wb.sheetnames:
        ws = wb["All_Scans"]
        rows = ws.iter_rows(values_only=True)
        hdr = list(next(rows, None) or ())
        try:
            i_scan = hdr.index("Source_Scan")
            i_tk = hdr.index("ticker")
        except ValueError:
            i_scan = i_tk = -1
        if i_scan >= 0:
            _read_sheet(ws, i_scan, i_tk)

    if "Momentum" in wb.sheetnames:
        ws = wb["Momentum"]
        rows = ws.iter_rows(values_only=True)
        hdr = list(next(rows, None) or ())
        try:
            i_scan = hdr.index("Source_Scan")
            i_tk = hdr.index("ticker")
        except ValueError:
            i_scan = i_tk = -1
        if i_scan >= 0:
            _read_sheet(ws, i_scan, i_tk)

    wb.close()
    for k in scans:
        scans[k] = sorted(set(scans[k]))
    return scans, asof


def available_days():
    """由 layer2_* 檔名抽出可用日期（新→舊）。"""
    import re
    days = set()
    for p in glob.glob(os.path.join(OUT, "layer2_*.json")):
        m = re.search(r"layer2_(\d{8})_", os.path.basename(p))
        if m:
            s = m.group(1)
            days.add(f"{s[:4]}-{s[4:6]}-{s[6:]}")
    return sorted(days, reverse=True)


def load_l2(day=None):
    """day=YYYY-MM-DD → 揀嗰日最新一份；唔指定 → 最新。"""
    if day:
        pat = os.path.join(OUT, "layer2_%s_*.json" % day.replace("-", ""))
        fs = sorted(glob.glob(pat))
    else:
        fs = sorted(glob.glob(os.path.join(OUT, "layer2_*.json")))
    if not fs:
        return None, None
    f = fs[-1]
    try:
        d = json.load(io.open(f, encoding="utf-8"))
    except (OSError, ValueError):
        return None, os.path.basename(f)
    rows = []
    for src in ("focus_list", "stalk_list"):
        for r in d.get(src) or []:
            x = dict(r)
            x["_src"] = src.replace("_list", "").upper()
            rows.append(x)
    return rows, os.path.basename(f)


def load_ohlc():
    p = os.path.join(OUT, "ohlc_latest.json")
    try:
        d = json.load(io.open(p, encoding="utf-8"))
        return d.get("data") or {}, d.get("asof")
    except (OSError, ValueError):
        return {}, None


def compute_metrics(ohlc):
    """→ dict[ticker] = {atr, atr_pct, rvol50, close}。"""
    out = {}
    for t, rec in ohlc.items():
        bars = rec.get("bars") or []
        if len(bars) < 55:
            continue
        closes = [b[3] for b in bars]
        highs = [b[1] for b in bars]
        lows = [b[2] for b in bars]
        vols = [b[4] if len(b) > 4 else 0 for b in bars]
        trs = [highs[i] - lows[i] for i in range(len(bars))]
        atr = sum(trs[-14:]) / 14
        close = closes[-1]
        v50 = (sum(vols[-50:]) / 50) if len(vols) >= 50 else 0
        rvol = (vols[-1] / v50) if v50 else None
        # EMA21（同 RS Daily Scan 同一條線：X = (收市 − EMA21)/ATR）
        k = 2 / 22.0
        ema21 = closes[0]
        for c_ in closes[1:]:
            ema21 = c_ * k + ema21 * (1 - k)
        out[t.upper()] = dict(atr=atr,
                              atr_pct=(atr / close * 100) if close else 0,
                              rvol50=rvol, close=close,
                              x=((close - ema21) / atr) if atr else None)
    return out


def update_day_on(tickers, read_only=False):
    """記錄每隻股連續在名單幾日。→ dict[ticker] = n。

    ★ read_only=True：只讀唔寫（歷史日期頁面用，唔准改 state）。
    """
    p = os.path.join(BOOK, "dailyscan_history.json")
    today = dt.date.today().isoformat()
    hist = {}
    try:
        hist = json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        hist = {}
    rec = hist.get("tickers") or {}
    newrec = {}
    for t in tickers:
        old = rec.get(t) or {}
        last = old.get("last")
        n = int(old.get("n") or 0)
        if last == today:
            newrec[t] = {"n": n, "last": last}
        else:
            newrec[t] = {"n": n + 1, "last": today}
    if not read_only:
        io.open(p, "w", encoding="utf-8").write(json.dumps(
            {"updated": today, "tickers": newrec}, ensure_ascii=False, indent=1))
    return {t: v["n"] for t, v in newrec.items()}


# ══════════════════════════════════════════════════════════════
CSS = """
.ds-dbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0 10px}
.ds-dbtn{font-size:12px;padding:5px 10px;border-radius:8px;font-weight:700;
  border:1px solid rgba(128,128,128,.35);text-decoration:none;color:inherit}
.ds-dbtn:hover{border-color:#f97316;color:#f97316}
.ds-dbtn.off{opacity:.32;pointer-events:none}
.ds-dsel{font:inherit;font-size:12.5px;padding:5px 8px;border-radius:8px;
  border:1px solid rgba(128,128,128,.35);background:transparent;color:inherit}
.ds-dn{font-size:11.5px;opacity:.62;font-weight:800}
.ds-histwarn{font-size:11.5px;line-height:1.6;padding:7px 10px;border-radius:8px;
  background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.35);
  margin:0 0 10px}
.ds-h{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:0 0 4px}
.ds-l1{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
  gap:10px;margin:0 0 16px}
.ds-sc{border:1px solid rgba(128,128,128,.26);border-radius:11px;
  padding:10px 12px;background:rgba(128,128,128,.035)}
.ds-sc .nm{font-weight:700;font-size:12.5px;display:flex;align-items:center;gap:7px}
.ds-sc .n{margin-left:auto;font-size:11px;opacity:.6;font-weight:400}
.ds-tk{display:flex;flex-wrap:wrap;gap:4px;margin-top:7px}
.ds-tk a{font-size:11.5px;padding:2px 7px;border-radius:6px;
  border:1px solid rgba(128,128,128,.32);text-decoration:none;color:inherit;
  font-family:ui-monospace,monospace}
.ds-tk a:hover{background:rgba(128,128,128,.18)}
.ds-empty{font-size:11.5px;opacity:.45;margin-top:6px;font-style:italic}
.ds-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
.ds-tbl th{text-align:right;font-size:10.5px;letter-spacing:.04em;
  text-transform:uppercase;opacity:.6;padding:6px 7px;border-bottom:1px solid rgba(128,128,128,.25);
  white-space:nowrap}
.ds-tbl td{text-align:left;padding:6px 7px;border-bottom:1px solid rgba(128,128,128,.1);
  white-space:nowrap}
.ds-tbl td.l,.ds-tbl th.l{text-align:left}
.ds-tbl tr:hover{background:rgba(128,128,128,.07)}
.ds-syma{color:inherit;text-decoration:none}
.ds-sym-buy{color:inherit;font-weight:800}
b{text-decoration:none}
[data-theme="dark"] .ds-sym-buy{color:inherit}
.ds-ext{color:#dc2626;font-weight:700}
.ds-ok{color:#16a34a}
.ds-tag{font-size:9.5px;padding:1px 6px;border-radius:999px;
  border:1px solid rgba(128,128,128,.35);font-weight:700}
/* ★ 2026-10-23 FOCUS 改橙色 */
.ds-tag.src-FOCUS{color:#f97316;border-color:rgba(249,115,22,.55);
  background:transparent}
/* ★ 2026-10-23 Excel 式可排序欄頭 */
.ds-tbl th.sortable{cursor:pointer;user-select:none;white-space:nowrap}
.ds-tbl th.sortable:hover{opacity:.95;color:#f97316}
.ds-tbl th .arr{display:inline-block;margin-left:3px;font-size:8px;
  opacity:.45;transition:transform .12s}
.ds-tbl th[data-dir="asc"] .arr{transform:rotate(180deg);opacity:1;color:#f97316}
.ds-tbl th[data-dir="desc"] .arr{opacity:1;color:#f97316}
/* ★ 2026-10-20 scan 卡 hover 方格 */
.ds-hasTip{position:relative}
.ds-tip{display:none;position:absolute;z-index:60;left:0;top:calc(100% + 5px);
  width:min(320px,84vw);padding:11px 13px;border-radius:11px;
  background:#1b1b19;border:1px solid #4A4A42;
  box-shadow:0 10px 26px rgba(0,0,0,.5);font-size:11.5px;line-height:1.6;
  color:#F0EDE8;text-align:left;white-space:normal;word-break:break-word}
html[data-theme="light"] .ds-tip{background:#FFFFFF;border-color:#DAD9D4;
  color:#1F1E1D;box-shadow:0 10px 26px rgba(0,0,0,.14)}
.ds-hasTip:hover .ds-tip,.ds-hasTip:focus-within .ds-tip{display:block}
.ds-tip>b{font-size:12.5px;font-weight:800;display:block}
.ds-tipzh{font-size:11px;opacity:.72;margin-bottom:6px}
.ds-tiprow{font-size:11.5px}
@media(hover:none){.ds-hasTip:active .ds-tip{display:block}}
.ds-f{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px}
.ds-f button{padding:6px 12px;border-radius:999px;font-size:12px;
  border:1px solid rgba(128,128,128,.34);background:rgba(128,128,128,.07);
  color:inherit;cursor:pointer;font-family:inherit}
.ds-f button.on{background:#2563eb;border-color:#2563eb;color:#fff}
.ds-wrap{overflow-x:auto}
"""

JS = """
function dsSort(btn, col){
  var tb=document.getElementById('dsbody');
  var rows=Array.from(tb.querySelectorAll('tr'));
  var dir = btn.dataset.dir==='desc'?'asc':'desc';
  btn.dataset.dir=dir;
  document.querySelectorAll('.ds-f button').forEach(b=>{if(b!==btn)b.dataset.dir='';});
  var idx=parseInt(col,10);
  rows.sort(function(a,b){
    var x=a.children[idx].dataset.v, y=b.children[idx].dataset.v;
    var nx=parseFloat(x), ny=parseFloat(y);
    var vx=isNaN(nx)?x:nx, vy=isNaN(ny)?y:ny;
    if(dir==='asc') return vx>vy?1:vx<vy?-1:0;
    return vx<vy?1:vx>vy?-1:0;
  });
  rows.forEach(r=>tb.appendChild(r));
}
function dsFilter(mode,btn){
  document.querySelectorAll('.ds-f button').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  document.querySelectorAll('#dsbody tr').forEach(r=>{
    var ok = mode==='all' ? true
      : mode==='buy' ? r.dataset.buy==='1'
      : mode==='ext' ? r.dataset.state==='EXTENDED'
      : mode==='focus' ? r.dataset.src==='FOCUS'
      : true;
    r.style.display=ok?'':'none';
  });
}
"""


def build(day=None):
    """day=YYYY-MM-DD 建該日快照（歷史頁）；None = 最新。"""
    scans, l1_asof = load_l1()
    if day:
        _dd = available_days()
        if _dd and day != _dd[0]:
            scans = {}          # L1 只保留最新（歷史 L1 冇逐日存檔，唔准扮）
    l2rows, l2_src = load_l2(day)
    ohlc, ohlc_asof = load_ohlc()
    metrics = compute_metrics(ohlc)

    # ★ 2026-10-23 hover 迷你 K 線（Desmond：「滑鼠移到個股可以出現股價圖」）
    #   重用 charts.py（純 Python SVG，唔靠 CDN），失敗就靜靜降級（冇圖但有 link）
    _mini = {}
    try:
        import charts as _charts
        _all = []
        if scans:
            _all += [t for v in scans.values() for t in v]
        if l2rows:
            _all += [r.get("ticker") for r in l2rows if r.get("ticker")]
        _all = sorted({t for t in _all if t})
        if _all:
            for _tk, _svg, _adr in _charts.build_grid(_all, max_cells=250):
                if _svg:
                    _mini[_tk] = _svg
    except Exception:                                        # noqa: BLE001
        _mini = {}

    # ★ 2026-10-23 「代號 / 行業」兩行式（跟領導股頁 stdcols 格式）
    _ind = {}
    try:
        _msp = os.path.join(HERE, "data", "market_scan.json")
        if os.path.exists(_msp):
            _ms = json.load(io.open(_msp, encoding="utf-8"))
            for _r in (_ms.get("nel") or []):
                _s = _r.get("symbol")
                if _s:
                    _ind[_s.upper()] = (_r.get("industry")
                                        or _r.get("sector") or "")
    except Exception:                                        # noqa: BLE001
        _ind = {}

    parts = [f'<style>{CSS}</style><script>{JS}</script>']
    parts.append('<h2>Daily Scan <small>L1 掃描 + L2 圖表隊列</small></h2>')

    # ★ 2026-10-24 Desmond：「返個選擇日期既按鈕／列表／上一日／下一日，
    #   比我 track record」→ 每一步都係獨立快照頁 dailyscan_<date>.html
    _days = available_days()
    if _days:
        _cur = day if (day in _days) else _days[0]
        _i = _days.index(_cur)
        _prev = _days[_i + 1] if _i + 1 < len(_days) else None   # 更舊
        _next = _days[_i - 1] if _i > 0 else None                # 更新
        _is_latest_day = (_cur == _days[0])

        def _href(d):
            return "dailyscan.html" if d == _days[0] else f"dailyscan_{d}.html"

        _opts = "".join(
            '<option value="%s"%s>%s</option>'
            % (_href(d), " selected" if d == _cur else "", d)
            for d in _days[:40])
        _left = (f'<a class="ds-dbtn" href="{_href(_prev)}">◀ 上一日</a>'
                 if _prev else '<span class="ds-dbtn off">◀ 上一日</span>')
        _right = (f'<a class="ds-dbtn" href="{_href(_next)}">下一日 ▶</a>'
                  if _next else '<span class="ds-dbtn off">下一日 ▶</span>')
        parts.append('<div class="ds-dbar">' + _left
                     + '<select class="ds-dsel" onchange="location.href=this.value">'
                     + _opts + '</select>' + _right
                     + f'<span class="ds-dn">{_cur}'
                     + ('' if _is_latest_day else '（歷史）') + '</span></div>')
        if not _is_latest_day:
            parts.append(
                '<div class="ds-histwarn">⚠ 歷史快照：<b>名單</b>係 %s 當日嘅 L2；'
                '但 RVOL／ATR%% 用<b>最新</b> OHLC 計（原始日線冇逐日存檔），'
                '所以呢兩欄唔可以當當日數。L1 只保留最新一日。</div>' % _cur)
    parts.append(
        f'<p class="crumb">L1 <code>{_esc(l1_asof or "—")}</code>｜'
        f'L2 <code>{_esc(l2_src or "—")}</code>｜'
        f'價格 <code>{_esc(ohlc_asof or "—")}</code>｜'
        '唯讀研究用途｜<b>非買入指令</b></p>')

    # ── L1 ──
    if scans:
        all_tk = sorted({t for v in scans.values() for t in v})
        parts.append(f'<div class="ds-h"><h3 style="margin:0">L1</h3>'
                     f'<span style="font-size:12.5px;opacity:.7">'
                     f'{len(all_tk)} tickers｜{len(scans)} 個 scan</span></div>')
        parts.append('<div class="ds-l1">')
        ordered = [s for s in SCAN_ORDER if s in scans]
        ordered += [s for s in scans if s not in SCAN_ORDER]
        for sc in ordered:
            tks = scans[sc]
            if not tks:
                continue
            kind = ("Small" if "Small" in sc else
                    "Large" if "Large" in sc else "")
            parts.append(f'<div class="ds-sc ds-hasTip">'
                         f'<div class="nm">{_esc(sc)}'
                         f'{f" <span class=ds-tag>{kind}</span>" if kind else ""}'
                         f'<span class="n">{len(tks)}</span></div>'
                         '<div class="ds-tk">')
            for t in tks:
                parts.append(f'<a href="https://www.tradingview.com/chart/?symbol={_esc(t)}"'
                             f' target="_blank" rel="noopener" data-sym="{_esc(t)}">'
                             f'{_esc(t)}</a>')
            _d = _sinfo(sc)
            parts.append(
                '</div>'
                f'<div class="ds-tip"><b>{_esc(_d["full"])}</b>'
                f'<div class="ds-tipzh">{_esc(_d["zh"])}</div>'
                f'<div class="ds-tiprow">{_esc(_d["how"])}</div></div>'
                '</div>')
        empty = [s for s in SCAN_ORDER if s not in scans]
        if empty:
            parts.append('<div class="ds-sc"><div class="nm">空 scan'
                         f'<span class="n">{len(empty)}</span></div>'
                         f'<div class="ds-empty">{", ".join(empty)}</div></div>')
        parts.append('</div>')

    # ── L2 ──
    if l2rows:
        tk_all = [r.get("ticker") for r in l2rows if r.get("ticker")]
        _days = available_days()
        _is_latest = (not day) or (not _days) or (day == _days[0])
        dayon = update_day_on(tk_all, read_only=not _is_latest)

        n_buy = sum(1 for r in l2rows
                    if (r.get("atr_ext_50ma") or 0) <= 4
                    and (r.get("atr_ext_50ma") or 0) >= 0)
        n_ext = sum(1 for r in l2rows if (r.get("atr_ext_50ma") or 0) > 4)

        parts.append('<div class="ds-h" style="margin-top:18px">'
                     f'<h3 style="margin:0">L2 圖表隊列</h3>'
                     f'<span style="font-size:12.5px;opacity:.7">'
                     f'{len(l2rows)} 隻｜買入區 {n_buy}｜EXT&gt;4 {n_ext}</span></div>')

        parts.append('<div class="ds-f">')
        parts.append('<button class="on" onclick="dsFilter(\'all\',this)">'
                     f'全部 {len(l2rows)}</button>')
        parts.append('<button onclick="dsFilter(\'buy\',this)">'
                     f'買入區 {n_buy}</button>')
        parts.append('<button onclick="dsFilter(\'ext\',this)">'
                     f'延伸 {n_ext}</button>')
        parts.append('<button onclick="dsFilter(\'focus\',this)">'
                     f'FOCUS</button>')
        parts.append('</div>')

        # ── X/Y 位置圖（同 RS Daily Scan 同一把尺，Desmond 2026-10-25）──
        try:
            import rs_scan as _rss
            _sc = []
            for _r in l2rows:
                _t = (_r.get("ticker") or "").upper()
                _m = metrics.get(_t) or {}
                _x = _m.get("x")
                _y = _r.get("atr_ext_50ma")
                if _x is None or _y is None:
                    continue
                try:
                    _x, _y = float(_x), float(_y)
                except (TypeError, ValueError):
                    continue
                _sc.append(dict(ticker=_t, x=_x, y=_y,
                                adr=_m.get("atr_pct"),
                                in_buy_box=(0 <= _x <= 1 and 0 <= _y <= 4)))
            if _sc:
                parts.append(_rss._scatter(_sc))
                parts.append(f'<div class="ds-note" style="margin:-6px 0 10px">'
                             f'X/Y 位置圖：{len(_sc)} 隻有齊 X/Y｜'
                             f'買入區 {sum(1 for r in _sc if r["in_buy_box"])} 隻'
                             '</div>')
        except Exception as _e:                              # noqa: BLE001
            parts.append(f'<div class="dim">位置圖失敗：{type(_e).__name__}</div>')

        # ★ 2026-10-23 Desmond：欄頭 clickable（Excel 三角）+ 新增 ATR 帶欄
        _cols = [
            ('來源', 0), ('代號/行業', 1), ('EXT', 3),
            ('RVOL(50D)', 4), ('ATR 帶', None), ('ATR%', 5),
            ('距 52 高', 6), ('評分', None), ('財報', 7), ('DAY ON', 2),
        ]
        th_parts = []
        for label, col in _cols:
            if col is None:
                th_parts.append(f'<th>{label}</th>')
            else:
                th_parts.append(
                    f'<th class="l sortable" onclick="dsSort(this,{col})" data-dir="">'
                    f'{label}<span class="arr">▼</span></th>')
        parts.append(
            '<div class="ds-wrap card" style="padding:0"><table class="ds-tbl">'
            '<thead><tr>'
            + "".join(th_parts)
            + '</tr></thead><tbody id="dsbody">')

        # ★ 排序：DAYON(desc) > EXT(asc) > RVOL(desc) > ATR%(desc)（Desmond 2026-10-23）
        def k(r):
            _t = (r.get("ticker") or "").upper()
            _m = metrics.get(_t) or {}
            ext = r.get("atr_ext_50ma")
            ext = ext if isinstance(ext, (int, float)) else 99
            rvol = _m.get("rvol50")
            rvol = rvol if isinstance(rvol, (int, float)) else -1
            atrp = _m.get("atr_pct")
            atrp = atrp if isinstance(atrp, (int, float)) else -1
            return (-dayon.get(r.get("ticker") or "", 0), ext, -rvol, -atrp)
        for r in sorted(l2rows, key=k):
            t = r.get("ticker") or ""
            m = metrics.get(t.upper()) or {}
            ext = r.get("atr_ext_50ma")
            ext_f = ext if isinstance(ext, (int, float)) else None
            inbox = ext_f is not None and 0 <= ext_f <= 4
            state = ("EXTENDED" if (ext_f or 0) > 4 else
                     "BELOW" if (ext_f or 0) < 0 else
                     "BUY" if inbox else "NA")
            rvol = m.get("rvol50")
            rvol_s = f"{rvol:.2f}x" if rvol is not None else "—"
            rvol_cls = ("ds-ext" if (rvol or 0) >= 2 else
                        "ds-ok" if (rvol or 0) >= 1.2 else "")
            dist = r.get("near_52w_high_pct")
            dist_s = (f"{dist:.0f}%" if isinstance(dist, (int, float)) else "—")
            es = r.get("earnings_status") or ""
            dtE = r.get("days_to_earnings")
            # ★ Desmond 2026-10-23：唔好打「OK」，只 SHOW 日子（例如 14D）
            if isinstance(dtE, int):
                es_s = f"{dtE}D"
            elif es and es not in ("OK", "—", ""):
                es_s = es
            else:
                es_s = "—"
            watch = (r.get("watch_price") or "").replace("trigger: ", "")
            inval = (r.get("invalidation") or "").replace("invalidation: ", "")

            parts.append(
                f'<tr '
                f'data-buy="{1 if inbox else 0}" data-state="{state}" '
                f'data-src="{_esc(r.get("_src",""))}">'
                f'<td class="l"><span class="ds-tag">{_esc(r.get("_src",""))}</span></td>'
                f'<td class="l"><span class="tk">'
                f'<a class="ds-syma" '
                f'href="https://www.tradingview.com/chart/?symbol={_esc(t)}" '
                f'target="_blank" rel="noopener" data-sym="{_esc(t)}">'
                f'<b class="{"ds-sym-buy" if inbox else ""}">{_esc(t)}</b></a></span>'
                f'<div class="dim" style="font-size:10.5px">'
                f'{_esc(_ind.get(t.upper(), ""))}</div></td>'
                f'<td data-v="{_f(ext_f,2)}" class="{"ds-ext" if (ext_f or 0)>4 else ""}">'
                f'{_f(ext_f,2)}</td>'
                f'<td data-v="{_f(rvol,2)}" class="{rvol_cls}">{rvol_s}</td>'
                f'<td>{_atr_band(ext_f)}</td>'
                f'<td data-v="{_f(m.get("atr_pct"),2)}">{_f(m.get("atr_pct"),1)}%</td>'
                f'<td data-v="{_f(dist,0)}">{dist_s}</td>'
                f'<td data-v="{_grade(ext_f, rvol, dist, m.get("atr_pct"))[1]}">'
                f'<b style="color:{_gcol(_grade(ext_f, rvol, dist, m.get("atr_pct"))[0])}">'
                f'{_grade(ext_f, rvol, dist, m.get("atr_pct"))[0]}</b></td>'
                f'<td>{_esc(es_s)}</td>'
                f'<td data-v="{dayon.get(t,0)}">{dayon.get(t,0)}</td>'
                '</tr>')
        parts.append('</tbody></table></div>')

        parts.append('<div style="font-size:12px;line-height:1.9;opacity:.8;'
                     'margin-top:10px">'
                     '<b>欄位定義</b>（全部寫死，唔准臨時改）<br>'
                     '<b>EXT</b> = ATRX =（收市 − SMA50）／ATR14，硬刪門檻 4.0（EDGE-009）<br>'
                     '<b>ATR%</b> = ATR14／收市 ×100 —— 決定止蝕闊度<br>'
                     '<b>RVOL(50D)</b> = 當日量／過去 50 日平均量。≥2x 紅字＝爆量<br>'
                     '<b>DAY ON</b> = 連續在名單幾日（新上榜 = 1）<br>'
                     '點欄名可以排序。'
                     '</div>')

    if not scans and not l2rows:
        parts.append('<div style="padding:20px;opacity:.6">⛔ DATA_UNAVAILABLE：'
                     '搵唔到 My_Scans_*.xlsx 或 layer2_*.json。'
                     '★ Missing ≠ Zero。</div>')

    # ★ 2026-10-23 hover 迷你 K 線（Desmond：滑鼠移到個股彈股價圖，click 去 TradingView）
    if _mini:
        _mc = ['<div id="dsminis" style="display:none">']
        for _mtk, _msvg in _mini.items():
            _mc.append(f'<div data-sym="{_esc(_mtk)}">{_msvg}</div>')
        _mc.append('</div>')
        _mc.append("""<style>
#dsmini{display:none;position:fixed;z-index:9999;width:250px;
  background:#0b1120;border:1px solid #2a3a5c;border-radius:10px;
  box-shadow:0 14px 36px rgba(0,0,0,.62);overflow:hidden}
#dsminibar{display:flex;align-items:center;gap:8px;padding:6px 9px;
  background:#111a2e;border-bottom:1px solid #1e2a44;font-size:12px}
#dsminisym{flex:1 1 auto;color:#9fd4ff;font-weight:700}
#dsminibar a{color:#7fd4a8;text-decoration:none;font-size:11px}
#dsminichart{padding:6px;background:#0b1120}
#dsminichart svg{width:100%;height:auto;display:block}
@media(max-width:700px){#dsmini{display:none!important}}
</style>
<script>
(function(){
  var pop=null,timer=null;
  function ensure(){
    if(pop)return pop;
    pop=document.createElement('div');pop.id='dsmini';
    pop.innerHTML='<div id="dsminibar"><b id="dsminisym"></b>'+
      '<a id="dsminitv" target="_blank" rel="noopener">TradingView \u2197</a></div>'+
      '<div id="dsminichart"></div>';
    document.body.appendChild(pop);return pop;
  }
  function show(a){
    var sym=a.getAttribute('data-sym');if(!sym)return;
    var src=document.querySelector('#dsminis div[data-sym="'+sym+'"]');
    if(!src)return;var p=ensure();
    document.getElementById('dsminisym').textContent=sym;
    document.getElementById('dsminitv').href=
      'https://www.tradingview.com/chart/?symbol='+encodeURIComponent(sym);
    document.getElementById('dsminichart').innerHTML=src.innerHTML;
    var r=a.getBoundingClientRect();p.style.display='block';
    var top=r.bottom+6,left=r.left;
    if(left+p.offsetWidth>window.innerWidth-8)
      left=window.innerWidth-p.offsetWidth-8;
    if(top+p.offsetHeight>window.innerHeight-8)
      top=r.top-p.offsetHeight-6;
    p.style.top=top+'px';p.style.left=Math.max(6,left)+'px';
  }
  function hide(){clearTimeout(timer);if(pop)pop.style.display='none';}
  document.addEventListener('mouseover',function(e){
    var a=e.target.closest('[data-sym]');
    if(!a||a.closest('#dsminis'))return;
    clearTimeout(timer);timer=setTimeout(function(){show(a);},160);
  });
  document.addEventListener('mouseout',function(e){
    var a=e.target.closest('[data-sym]');if(!a)return;
    setTimeout(function(){if(pop&&!pop.matches(':hover'))hide();},240);
  });
  document.addEventListener('scroll',hide,{passive:true});
})();
</script>""")
        parts.extend(_mc)

    return ("Daily Scan", "".join(parts))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    t, b = build()
    out = os.path.join(HERE, "dailyscan_body.html")
    io.open(out, "w", encoding="utf-8").write(b)
    print(f"✓ dailyscan body {len(b):,} 字 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
