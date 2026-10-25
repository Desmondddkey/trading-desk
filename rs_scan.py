# -*- coding: utf-8 -*-
"""rs_scan.py — RS Daily Scan 頁（Desmond 2026-10-24）

放喺 Daily Scan 下面（側欄「選股」組）。

數據來源：trading-os/output/rs_select_<YYYY-MM-DD>.json（rs-select-v1.1）
內容：61 隻 RS 宇宙 → gate 過濾 → 買入區
欄位全部有出處（唔准自己发明）：
  X      距 21EMA，ATR 單位（買入區通常 0-1）
  Y      距 50MA，ATR 單位（= ATRX，Jeff Sun 上限 4）
  距52高  同 52 週高距離（%）
  ADR%   平均日波幅
  RS1M/3M 相對 SPY 超額回報

冇數據時顯示 DATA_UNAVAILABLE，唔准用舊檔扮今日（零假更新鐵律）。
"""
import glob
import html as _h
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = r"C:/Users/rain0/trading-os/output"


def _latest(pattern):
    fs = sorted(glob.glob(os.path.join(DATA, pattern)))
    return fs[-1] if fs else None


# ── 散點軌跡歷史（Desmond 2026-10-24：「睇同一隻股一星期點移動」）──
HIST_PATH = os.path.join(DATA, "rs_xy_history.jsonl")


def _hist_read():
    out = []
    if not os.path.exists(HIST_PATH):
        return out
    try:
        with io.open(HIST_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:                             # noqa: BLE001
                    continue
    except Exception:                                         # noqa: BLE001
        return []
    return out


def _hist_append(as_of, rows):
    """今日（as_of）未記錄就 append 一次；回傳全部歷史"""
    hist = _hist_read()
    if any(h.get("date") == as_of for h in hist):
        return hist
    pts = []
    for r in rows:
        try:
            x = float(r.get("x"))
            y = float(r.get("y"))
        except (TypeError, ValueError):
            continue
        if x != x or y != y:          # NaN
            continue
        pts.append(dict(t=r.get("ticker"), x=round(x, 3), y=round(y, 3),
                        box=bool(r.get("in_buy_box"))))
    rec = dict(date=as_of, pts=pts)
    try:
        with io.open(HIST_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:                                    # noqa: BLE001
        print(f"hist write: {type(e).__name__}")
        return hist
    hist.append(rec)
    return hist



def _hist_backfill(rows, as_of, hist):
    """歷史上唔夠點時，用日線價自己算 X/Y（同一個定義），補回最近 6 個交易日。

    ★ 定義必須同 rs_select 一致：
        X = (close - EMA21) / ATR14
        Y = (close - SMA50) / ATR14
    """
    if len(hist) >= 2 or not rows:
        return hist
    tick = [r.get("ticker") for r in rows if r.get("ticker")]
    if not tick:
        return hist
    try:
        import yfinance as yf
        import pandas as pd
        d = yf.download(tick, period="8mo", interval="1d", progress=False,
                        auto_adjust=False, group_by="ticker", threads=True)
    except Exception as e:                                    # noqa: BLE001
        print(f"backfill: {type(e).__name__}")
        return hist

    # 每日聚合
    per_date = {}
    for t in tick:
        try:
            x = d[t] if isinstance(d.columns, pd.MultiIndex) else d
            x = x.dropna(subset=["Close"])
            if len(x) < 60:
                continue
            c, h, l = (x["Close"].astype(float), x["High"].astype(float),
                       x["Low"].astype(float))
            tr = pd.concat([h - l, (h - c.shift()).abs(),
                            (l - c.shift()).abs()], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
            ema21 = c.ewm(span=21).mean()
            sma50 = c.rolling(50).mean()
            df = pd.DataFrame({"c": c, "atr": atr, "e21": ema21,
                               "s50": sma50}).dropna()
            for dt, rr in df.tail(6).iterrows():
                key = str(dt.date())
                per_date.setdefault(key, []).append(dict(
                    t=t, x=round(float((rr["c"] - rr["e21"]) / rr["atr"]), 3),
                    y=round(float((rr["c"] - rr["s50"]) / rr["atr"]), 3),
                    box=False))
        except Exception:                                     # noqa: BLE001
            continue

    have = {h.get("date") for h in hist}
    added = 0
    try:
        with io.open(HIST_PATH, "a", encoding="utf-8") as f:
            for key in sorted(per_date):
                if key in have:
                    continue
                rec = dict(date=key, pts=per_date[key], backfilled=True)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                hist.append(rec)
                added += 1
    except Exception as e:                                    # noqa: BLE001
        print(f"backfill write: {type(e).__name__}")
    if added:
        hist.sort(key=lambda h: h.get("date") or "")
    return hist


def _esc(v):
    return _h.escape(str(v)) if v is not None else ""


def _f(v, d=2, plus=False):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "—"
    return (f"{x:+,.{d}f}" if plus else f"{x:,.{d}f}")


CSS = """
.rs-h{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:0 0 6px}
.rs-h h2{margin:0;font-size:20px}
.rs-sub{font-size:11.5px;opacity:.66}
.rs-f{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
.rs-f button{font:inherit;font-size:11.5px;padding:5px 11px;border-radius:999px;
  border:1px solid rgba(128,128,128,.35);background:transparent;color:inherit;
  cursor:pointer}
.rs-f button.on{background:#f97316;border-color:#f97316;color:#fff;font-weight:700}
.rs-wrap{overflow-x:auto}
.rs-xnote{font-size:9.5px;line-height:1.55;opacity:.7;margin:5px 2px 0;
  text-align:left;max-width:760px}
.rs-nav{display:flex;gap:8px;align-items:center;margin:0 0 12px;flex-wrap:wrap}
.rs-nav-b{padding:6px 12px;border-radius:8px;font-size:11.5px;font-weight:700;
  border:1px solid rgba(128,128,128,.35);text-decoration:none;color:inherit}
.rs-nav-b:hover{border-color:#f97316;color:#f97316}
.rs-nav-b.off{opacity:.3;pointer-events:none}
.rs-nav-s{padding:6px 10px;border-radius:8px;font-size:11.5px;font-family:inherit;
  background:transparent;color:inherit;border:1px solid rgba(128,128,128,.35)}
.rs-nav-d{font-size:11.5px;font-weight:800;opacity:.75;margin-left:2px}
.rs-tbl{width:100%;border-collapse:collapse;font-size:11.5px;
  font-variant-numeric:tabular-nums}
.rs-tbl th{position:sticky;top:0;background:var(--card,#1b1b19);text-align:right;
  padding:8px 7px;font-size:10.5px;font-weight:700;letter-spacing:.03em;
  border-bottom:1px solid rgba(128,128,128,.3);white-space:nowrap;opacity:.8}
.rs-tbl th.l,.rs-tbl td.l{text-align:left}
.rs-tbl th:first-child,.rs-tbl td:first-child{padding-left:14px;
  min-width:104px;white-space:nowrap}
.rs-dot{margin-right:7px;vertical-align:middle}
.rs-tbl th.sortable{cursor:pointer;user-select:none}
.rs-tbl th.sortable:hover{color:#f97316;opacity:1}
.rs-tbl th .arr{display:inline-block;margin-left:3px;font-size:10px;opacity:.4}
.rs-tbl th[data-dir="asc"] .arr{transform:rotate(180deg);opacity:1;color:#f97316}
.rs-tbl th[data-dir="desc"] .arr{opacity:1;color:#f97316}
.rs-tbl td{padding:7px;border-bottom:1px solid rgba(128,128,128,.12)}
.rs-tbl tr:hover td{background:rgba(249,115,22,.06)}
.rs-tk{font-weight:800;font-size:12.5px}
.rs-tk a{color:inherit;text-decoration:none;border-bottom:1px dotted rgba(128,128,128,.5)}
.rs-dot{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:5px}
.rs-in{background:#22c55e}
.rs-out{background:#6b7280}
.rs-pos{color:#15803d;font-weight:700}
.rs-neg{color:#dc2626;font-weight:700}
html[data-theme="dark"] .rs-pos{color:#7ce0a8}
html[data-theme="dark"] .rs-neg{color:#ff8f8f}
.rs-tag{font-size:10px;padding:1px 6px;border-radius:999px;
  border:1px solid rgba(128,128,128,.35);font-weight:700}
.rs-tag.buy{background:#f97316;border-color:#f97316;color:#fff}
.rs-tag.fail{border-color:#dc2626;color:#dc2626}
.rs-note{font-size:10.5px;opacity:.6;margin-top:10px;line-height:1.7}
.rs-meta{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;opacity:.75;
  margin:4px 0 10px}
.rs-meta b{font-weight:800;opacity:1}
"""

JS = """
function rsFilter(mode,btn){
  document.querySelectorAll('.rs-f button').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  document.querySelectorAll('#rsbody tr').forEach(r=>{
    var ok = mode==='all' ? true
      : mode==='buy' ? r.dataset.buy==='1'
      : mode==='pass' ? r.dataset.pass==='1'
      : mode==='focus' ? r.dataset.bucket==='focus'
      : true;
    r.style.display = ok ? '' : 'none';
  });
}
function rsSort(btn, idx){
  var tb=document.getElementById('rsbody');
  if(!tb) return;
  var rows=Array.from(tb.querySelectorAll('tr'));
  var dir = btn.dataset.dir==='desc' ? 'asc' : 'desc';
  document.querySelectorAll('.rs-tbl th').forEach(function(t){ if(t!==btn) t.dataset.dir=''; });
  btn.dataset.dir = dir;
  var sign = dir==='asc' ? 1 : -1;
  rows.sort(function(a,b){
    var x=a.children[idx].dataset.v, y=b.children[idx].dataset.v;
    var nx=parseFloat(x), ny=parseFloat(y);
    var vx=isNaN(nx)?x:nx, vy=isNaN(ny)?y:ny;
    if(typeof vx==='number' && typeof vy==='number') return (vx-vy)*sign;
    return String(vx).localeCompare(String(vy))*sign;
  });
  rows.forEach(function(r){tb.appendChild(r);});
}
"""

try:                                    # ATR 帶用 RS THEME 同一把尺（單一來源）
    from rstheme_page import _band
except Exception:                                    # noqa: BLE001
    def _band(_v):
        return ""


def _gcol(g):
    return {"A+": "#a855f7", "A": "#22c55e", "B": "#f59e0b",
            "C": "#94a3b8", "D": "#ef4444"}.get(g, "#94a3b8")


def grade_of(r):
    """SETUP 品質 A+ → D（只用呢頁已有數字，唔引入新數據）。"""
    y = r.get("y")
    if y is None:
        return "—", 0
    if y > 4:
        return "D", 0                    # 過度延伸直接 D
    pts = 3 if 0 <= y <= 2 else 2
    x = r.get("x")
    if x is not None:
        pts += 2 if 0 <= x <= 1 else (1 if 1 < x <= 1.5 else 0)
    d52 = r.get("dist52w")
    if d52 is not None:
        pts += 2 if d52 >= -5 else (1 if d52 >= -12 else 0)
    rv = r.get("rvol")
    if rv is not None:
        pts += 2 if rv >= 2 else (1 if rv >= 1.2 else 0)
    if pts >= 8:
        return "A+", pts
    if pts >= 6:
        return "A", pts
    if pts >= 4:
        return "B", pts
    return "C", pts


COLS = [
    ("代號", "ticker", "l", None),
    ("RS 1M", "r1m", "", 1),
    ("RS 3M", "r3m", "", 1),
    ("ATR%", "atr_pct", "", 1),
    ("X 距21EMA", "x", "", 2),
    ("Y 距50MA", "y", "", 2),
    ("EXT", "y", "", 2),
    ("距 52 高", "dist52w", "", 1),
    ("評分", "grade", "", None),
    ("財報", "days_to_earn", "", 0),
    ("狀態", None, "l", None),
]


# ── X/Y 散點圖（Desmond 2026-10-24：「加 X/Y 散點圖喺頁頂」）──────────
SC_W, SC_H = 720, 340
SC_PADL, SC_PADR, SC_PADT, SC_PADB = 46, 14, 14, 30
SC_XMIN, SC_XMAX = -0.5, 2.5      # X = 距 21EMA（ATR）
SC_YMIN, SC_YMAX = -1.0, 5.0      # Y = 距 50MA（ATR）= ATRX


def _scatter(rows, hist=None):
    """SVG 散點：X=距21EMA、Y=距50MA。買入區（X 0-1、Y 0-4）highlight。"""
    W, H = SC_W, SC_H
    pw = W - SC_PADL - SC_PADR
    ph = H - SC_PADT - SC_PADB

    def px(x):
        return SC_PADL + (x - SC_XMIN) / (SC_XMAX - SC_XMIN) * pw

    def py(y):
        return SC_PADT + ph - (y - SC_YMIN) / (SC_YMAX - SC_YMIN) * ph

    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" '
           'style="max-width:100%;height:auto;display:block">']
    # 買入區
    out.append(f'<rect x="{px(0):.1f}" y="{py(4):.1f}" '
               f'width="{(px(1) - px(0)):.1f}" height="{(py(0) - py(4)):.1f}" '
               'fill="rgba(34,197,94,.13)" stroke="rgba(34,197,94,.5)" '
               'stroke-dasharray="4 3" rx="3"/>')
    out.append(f'<text x="{px(0.5):.1f}" y="{py(4) - 5:.1f}" font-size="10" '
               'fill="#22c55e" text-anchor="middle">買入區 X 0–1 / Y 0–4</text>')
    # 格線
    for gx in (0, 0.5, 1.0, 1.5, 2.0):
        out.append(f'<line x1="{px(gx):.1f}" y1="{SC_PADT}" x2="{px(gx):.1f}" '
                   f'y2="{SC_PADT + ph}" stroke="rgba(128,128,128,.16)"/>')
        out.append(f'<text x="{px(gx):.1f}" y="{SC_PADT + ph + 15}" '
                   'font-size="10" fill="currentColor" opacity=".55" '
                   f'text-anchor="middle">{gx:g}</text>')
    for gy in (0, 1, 2, 3, 4):
        out.append(f'<line x1="{SC_PADL}" y1="{py(gy):.1f}" '
                   f'x2="{SC_PADL + pw}" y2="{py(gy):.1f}" '
                   'stroke="rgba(128,128,128,.16)"/>')
        out.append(f'<text x="{SC_PADL - 7}" y="{py(gy) + 3.5:.1f}" font-size="10" '
                   'fill="currentColor" opacity=".55" '
                   f'text-anchor="end">{gy:g}</text>')
    # Y=4 過度延伸線
    out.append(f'<line x1="{SC_PADL}" y1="{py(4):.1f}" x2="{SC_PADL + pw}" '
               f'y2="{py(4):.1f}" stroke="#dc2626" stroke-width="1.2" '
               'stroke-dasharray="6 4" opacity=".8"/>')
    out.append(f'<text x="{SC_PADL + pw - 2}" y="{py(4) - 5:.1f}" font-size="10" '
               'fill="#dc2626" text-anchor="end">ATRX 4 = 過度延伸（硬刪）</text>')
    # 軸標題
    out.append(f'<text x="{SC_PADL + pw / 2:.1f}" y="{H - 3}" font-size="11" '
               'fill="currentColor" opacity=".75" text-anchor="middle">'
               'X = 距 21EMA（ATR 單位）</text>')
    out.append(f'<text x="12" y="{SC_PADT + ph / 2:.1f}" font-size="11" '
               'fill="currentColor" opacity=".75" text-anchor="middle" '
               f'transform="rotate(-90 12 {SC_PADT + ph / 2:.1f})">'
               'Y = 距 50MA（ATR）</text>')
    # ── 軌跡：過去幾個交易日同一隻股點移動（虛線）──
    hist = hist or []
    if len(hist) >= 2:
        trail = {}
        for h in hist[-6:]:
            for p in h.get("pts") or []:
                try:
                    trail.setdefault(p["t"], []).append(
                        (p["x"], p["y"], h.get("date")))
                except Exception:                             # noqa: BLE001
                    continue
        cur_box = {r.get("ticker") for r in rows if r.get("in_buy_box")}
        drawn = 0
        for tk, pts in trail.items():
            # 只畫買入區嗰幾隻：全畫 = 一版亂線，冇人睇得出邊條打邊條
            if tk not in cur_box or len(pts) < 2:
                continue
            if drawn >= 12:
                break
            coords = " ".join(
                f"{px(max(SC_XMIN, min(SC_XMAX, x))):.1f},"
                f"{py(max(SC_YMIN, min(SC_YMAX, y))):.1f}"
                for x, y, _d in pts)
            out.append(f'<polyline points="{coords}" fill="none" '
                       'stroke="#f97316" stroke-width="1" stroke-opacity=".3" '
                       'stroke-linejoin="round"/>')
            drawn += 1
        out.append(f'<text x="{SC_PADL + 4}" y="{SC_PADT + 12}" font-size="10" '
                   'fill="currentColor" opacity=".55">'
                   '幼線 = 買入區股票過去走勢方向</text>')

    # 點
    labelled = []
    for r in rows:
        try:
            x = float(r.get("x"))
            y = float(r.get("y"))
        except (TypeError, ValueError):
            continue
        if not (-1e9 < x < 1e9 and -1e9 < y < 1e9):
            continue
        cx = px(max(SC_XMIN, min(SC_XMAX, x)))
        cy = py(max(SC_YMIN, min(SC_YMAX, y)))
        box = bool(r.get("in_buy_box"))
        # ★ 2026-10-25 Desmond：點色 = 評分（A+ 綠／A 橙／B 藍／C 紅）
        _g = r.get("grade")
        if _g is None:
            try:
                _g = grade_of(r)[0]
            except Exception:                                  # noqa: BLE001
                _g = "—"
        col = {"A+": "#22c55e", "A": "#f97316", "B": "#3b82f6",
               "C": "#ef4444", "D": "#7f1d1d"}.get(_g, "rgba(148,163,184,.75)")
        rad = 5.4 if box else 3.6
        tip = (f'{r.get("ticker")}｜X {x:.2f}｜Y {y:.2f}'
               f'｜ADR {r.get("adr") or "—"}%')
        _url = f"https://www.tradingview.com/chart/?symbol={_esc(r.get('ticker'))}"
        out.append(f'<a href="{_url}" target="_blank" rel="noopener">'
                   f'<title>{_esc(tip)}</title>'
                   f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad}" fill="{col}" '
                   'fill-opacity=".95"'
                   + (' stroke="#fff" stroke-width="1.2"' if box else "")
                   + ' style="cursor:pointer"/></a>')
        if box:
            labelled.append((cx, cy, r.get("ticker")))
    used = []
    for cx, cy, tk in sorted(labelled, key=lambda z: (z[1], z[0])):
        dy = 0
        for _cx, _cy in used:                     # 防重疊：撞到就向下推
            if abs(cx - _cx) < 34 and abs((cy + dy) - _cy) < 11:
                dy += 12
        used.append((cx, cy + dy))
        out.append(f'<a href="https://www.tradingview.com/chart/?symbol={_esc(tk)}" '
                   'target="_blank" rel="noopener">'
                   f'<text x="{cx + 7:.1f}" y="{cy + dy - 5:.1f}" font-size="10" '
                   f'font-weight="700" fill="currentColor" opacity=".92" '
                   'style="cursor:pointer">'
                   f'{_esc(tk)}</text></a>')
    out.append('</svg>')
    out.append(
        '<div class="rs-xnote">'
        '<b>點睇：</b>'
        '綠框＝買入區（X 0–1、Y 0–4）；點色＝評分：<b style="color:#22c55e">A+</b><b style="color:#f97316">A</b><b style="color:#3b82f6">B</b><b style="color:#ef4444">C</b>；白邊＝今日喺框內；
        '幼橙線＝買入區股票過去 6 日嘅移動方向；'
        '紅虛線＝ATRX 4，越過即過度延伸（硬刪）。'
        '<br>最有做功課價值＝<b>橙點 ＋ 軌跡向上（由左下走入框）</b>；'
        '右上角灰點＝已升盡、風險最高。'
        '</div>')
    return ('<div class="card" style="padding:10px 12px 6px">'
            '<div style="font-size:11.5px;opacity:.7;margin:0 0 4px">'
            f'RS 位置圖（{len(rows)} 隻｜橙 = 買入區 {len(labelled)} 隻）</div>'
            + "".join(out) + '</div>')


# ── RS 弱勢雷達區塊（rsw_radar，watch-only，唔推 Telegram）──────────
def _weakness():
    try:
        import sys
        if r"C:/Users/rain0/trading-os" not in sys.path:
            sys.path.insert(0, r"C:/Users/rain0/trading-os")
        import rsw_radar as _rw
        pool = _rw.build_pool()
        rows = _rw.scan_live(pool)
    except Exception as e:                                    # noqa: BLE001
        return ('<div class="card" style="padding:12px">'
                '<div style="font-size:12.5px;font-weight:800;margin-bottom:6px">'
                'RS 弱勢雷達</div>'
                f'<div class="dim">DATA_UNAVAILABLE（{_esc(type(e).__name__)}）</div>'
                '</div>')
    if not rows:
        return ('<div class="card" style="padding:12px">'
                '<div style="font-size:12.5px;font-weight:800;margin-bottom:6px">'
                'RS 弱勢雷達</div><div class="dim">今日冇領導股出現弱勢回氣。</div>'
                '</div>')
    rows = rows[:14]
    day = rows[0].get("day") or ""
    h = ['<div class="card" style="padding:0">',
         '<div style="padding:10px 12px 6px;display:flex;gap:10px;'
         'align-items:baseline;flex-wrap:wrap">',
         '<b style="font-size:12.5px">RS 弱勢雷達</b>',
         f'<span style="font-size:10.5px;opacity:.62">{_esc(day)}｜'
         f'池 {len(pool)} 隻｜命中 {len(rows)}｜WATCH-ONLY，唔係入場訊號</span>',
         '</div>',
         '<div class="rs-wrap"><table class="rs-tbl"><thead><tr>'
         '<th class="l">代號</th><th>現價</th><th>日內 %</th>'
         '<th>回氣 ATR</th><th>距低 ATR</th><th>低位</th>'
         '<th>15m</th><th>30m</th><th>60m</th><th>連續</th>'
         '<th>回升</th><th>RVOL</th></tr></thead><tbody>']
    for r in rows:
        rec = r.get("reclaim")
        pct = r.get("pct")
        pct_cls = "rs-pos" if (pct or 0) > 0 else "rs-neg"
        _st = int(r.get("streak") or 1)
        _hl = ' style="background:rgba(220,38,38,.13)"' if _st >= 4 else ""
        h.append(
            f'<tr{_hl}>'
            f'<td class="l"><span class="rs-tk">{_esc(r.get("t"))}</span></td>'
            f'<td>{_f(r.get("last"), 2)}</td>'
            f'<td class="{pct_cls}">{_f(pct, 1, True)}%</td>'
            f'<td>{_f(r.get("drop_atr"), 2)}</td>'
            f'<td>{_f(r.get("risk_atr"), 2)}</td>'
            f'<td>{_f(r.get("low"), 2)}</td>'
            + "".join(
                f'<td class="{"rs-pos" if (r.get(f"d{m}") or 0) > 0 else "rs-neg"}">'
                f'{_f(r.get(f"d{m}"), 1, True)}%</td>'
                if r.get(f"d{m}") is not None else '<td class="dim">—</td>'
                for m in (15, 30, 60))
            + (f'<td style="color:#dc2626;font-weight:800">{_st}×</td>'
               if _st >= 4 else f'<td>{_st}×</td>')
            + f'<td class="l">{"✅ 已回升" if rec else "⏳ 未回升"}</td>'
            + f'<td>{_f(r.get("rvol"), 1) + "x" if r.get("rvol") else "—"}</td>'
            + '</tr>')
    h.append('</tbody></table></div>')
    h.append('<div class="rs-note" style="padding:8px 12px 12px">'
             '回氣 ATR = 由開市／前收較高者跌到今日低位嘅深度。'
             '回測（n=257）機械化呢個規則 = −0.032R、t=−0.40 → 冇統計 edge，'
             '所以只列監察，唔出股數。</div></div>')
    return "".join(h)


def _all_snaps():
    """全部 rs_select_<date>.json，舊→新。"""
    import glob
    fs = sorted(glob.glob(os.path.join(DATA, "rs_select_????-??-??.json")))
    return fs


def _nav(cur_date):
    """上一日／日期下拉／下一日（Desmond 2026-10-24）。"""
    snaps = _all_snaps()
    dates = [os.path.basename(f)[10:20] for f in snaps]
    if cur_date not in dates:
        return ""
    i = dates.index(cur_date)
    prev_d = dates[i - 1] if i > 0 else None
    next_d = dates[i + 1] if i + 1 < len(dates) else None

    def btn(d, label):
        if not d:
            return f'<span class="rs-nav-b off">{label}</span>'
        return (f'<a class="rs-nav-b" href="rsscan_{d}.html">{label}</a>')

    opts = "".join(
        f'<option value="rsscan_{x}.html"{" selected" if x == cur_date else ""}>'
        f'{x}</option>' for x in reversed(dates))
    return ('<div class="rs-nav">'
            + btn(prev_d, "◀ 上一日")
            + f'<select class="rs-nav-s" onchange="location.href=this.value">{opts}</select>'
            + btn(next_d, "下一日 ▶")
            + f'<span class="rs-nav-d">{cur_date}</span>'
            + '</div>')


def build(snap=None):
    p = snap or _latest("rs_select_*.json")
    if not p:
        return ("RS Daily Scan",
                f'<style>{CSS}</style><div class="rs-h"><h2>RS Daily Scan</h2></div>'
                '<div class="dim">DATA_UNAVAILABLE（冇 rs_select_*.json）</div>')
    d = json.load(io.open(p, encoding="utf-8"))
    rows = d.get("rows") or []
    # ★ 2026-10-24 Desmond：全部優先顯示買入區（綠／橙），再按評分分數
    rows = sorted(rows, key=lambda r: (
        0 if r.get("in_buy_box") else 1, -grade_of(r)[1],
        (r.get("y") if r.get("y") is not None else 99)))
    as_of = (d.get("as_of") or "")[:10]
    gates = d.get("gates") or {}
    n_univ = d.get("n_universe")
    n_pass = d.get("n_gate_pass")
    n_box = d.get("n_buy_box_all")

    parts = [f"<style>{CSS}</style><script>{JS}</script>"]
    parts.append('<div class="rs-h"><h2>RS Daily Scan</h2>'
                 f'<span class="rs-sub">{_esc(as_of)}｜rs-select-v1.1</span></div>')
    parts.append(_nav(as_of))
    parts.append(
        '<div class="rs-meta">'
        f'<span>宇宙 <b>{_esc(n_univ)}</b></span>'
        f'<span>過閘 <b>{_esc(n_pass)}</b></span>'
        f'<span>買入區 <b>{_esc(n_box)}</b></span>'
        f'<span>價 ≥{_esc(gates.get("min_price"))}</span>'
        f'<span>成交額 ≥{_f((gates.get("min_dollar_vol") or 0)/1e6,0)}M</span>'
        f'<span>ADR ≥{_esc(gates.get("min_adr"))}%</span>'
        f'<span>ATRX ≤{_esc(gates.get("max_atrx"))}</span>'
        f'<span>距52高 ≥{_esc(gates.get("min_dist52w"))}%</span>'
        '</div>')

    _hist = _hist_backfill(rows, as_of, _hist_append(as_of, rows))
    parts.append(_scatter(rows, _hist))

    parts.append('<div class="rs-f">'
                 '<button class="on" onclick="rsFilter(\'all\',this)">'
                 f'全部 {len(rows)}</button>'
                 f'<button onclick="rsFilter(\'buy\',this)">買入區 {n_box or 0}</button>'
                 f'<button onclick="rsFilter(\'pass\',this)">過閘 {n_pass or 0}</button>'
                 '<button onclick="rsFilter(\'focus\',this)">FOCUS</button></div>')

    th = []
    for i, (label, _k, cls, _dp) in enumerate(COLS):
        if i == len(COLS) - 1:
            th.append(f'<th class="l">{label}</th>')
        else:
            th.append(f'<th class="sortable {cls}" onclick="rsSort(this,{i})" '
                      f'data-dir="">{label}<span class="arr">▼</span></th>')
    parts.append('<div class="rs-wrap card" style="padding:0"><table class="rs-tbl">'
                 '<thead><tr>' + "".join(th) + '</tr></thead><tbody id="rsbody">')

    for r in rows:
        t = r.get("ticker") or ""
        in_box = bool(r.get("in_buy_box"))
        passed = bool(r.get("gate_pass"))
        fails = r.get("gate_fail") or []
        if in_box:
            status = '<span class="rs-tag buy">買入區</span>'
        elif not passed:
            status = ('<span class="rs-tag fail">閘：'
                      + _esc("、".join(str(x) for x in fails[:2])) + '</span>')
        else:
            status = '<span class="rs-tag">過閘</span>'
        dte = r.get("days_to_earn")
        dte_s = (f"{int(dte)}D" if isinstance(dte, (int, float))
                 and dte == dte else "—")   # NaN 檢查（dte != dte）
        note = r.get("watch_price") or ""
        inval = r.get("invalidation") or ""
        tip = f'{note}｜{inval}' if (note or inval) else ""

        parts.append(
            f'<tr data-buy="{1 if in_box else 0}" data-pass="{1 if passed else 0}" '
            f'data-bucket="{_esc(r.get("bucket") or "")}">'
            f'<td class="l"><span class="rs-dot {"rs-in" if in_box else "rs-out"}">'
            f'</span><span class="rs-tk"><a href="https://www.tradingview.com/chart/'
            f'?symbol={_esc(t)}" target="_blank" rel="noopener" '
            f'title="{_esc(tip)}">{_esc(t)}</a></span>'
            f'</td>'
            f'<td data-v="{_esc(r.get("r1m"))}" class="rs-pos">'
            f'{_f(r.get("r1m"), 1, True)}%</td>'
            f'<td data-v="{_esc(r.get("r3m"))}" class="rs-pos">'
            f'{_f(r.get("r3m"), 1, True)}%</td>'
            f'<td data-v="{_esc(r.get("atr_pct"))}">{_f(r.get("atr_pct"), 1)}</td>'
            f'<td data-v="{_esc(r.get("x"))}">{_f(r.get("x"), 2)}</td>'
            f'<td data-v="{_esc(r.get("y"))}" class="'
            f'{"rs-neg" if (r.get("y") or 0) > 4 else ""}">{_f(r.get("y"), 2)}</td>'
            f'<td data-v="{_esc(r.get("dist52w"))}">{_f(r.get("dist52w"), 1)}%</td>'
            f'<td data-v="{_esc(r.get("y"))}" title="ATRX {_f(r.get("y"), 2)}">'
            f'{_band(r.get("y"))}</td>'
            f'<td class="rs-grade" data-v="{_esc(grade_of(r)[1])}">'
            f'<b style="color:{_gcol(grade_of(r)[0])}">{_esc(grade_of(r)[0])}</b></td>'
            f'<td data-v="{_esc(dte)}">{dte_s}</td>'
            f'<td class="l">{status}</td></tr>')

    parts.append('</tbody></table></div>')

    # ── RS 弱勢雷達（watch-only，唔推 Telegram）──
    parts.append('<div style="height:14px"></div>')
    parts.append(_weakness())

    parts.append(
        '<div class="rs-note">'
        'X＝距 21EMA｜Y＝距 50MA（ATRX）｜EXT＝ATRX 帶（綠區 0–4）。'
        '評分 A+→D：Y 0–2 得 3 分、X 0–1 得 2、距52高 ≥−5% 得 2、'
        'RVOL ≥2x 得 2；Y>4 直接 D。'
        '<br>呢頁係資格清單，唔係買入訊號。</div>')
    return ("RS Daily Scan", "".join(parts))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    t, b = build()
    print(f"{t} — {len(b):,} chars")
    for probe in ("rsbody", "rsSort", "買入區", "ATR"):
        print(("OK  " if probe in b else "MISS") + f" {probe}")
