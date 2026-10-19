# -*- coding: utf-8 -*-
"""rocketstock.py — RocketStock 公開 API 頁（Desmond 2026-10-19）

★ 背景：Desmond 要求加 https://rocketstock.app/rs-ranking?tab=sepa 去外部數據。
   實測原站唔可以 iframe（X-Frame-Options: SAMEORIGIN + CSP frame-ancestors）。

★★ 但 robots.txt 明確允許以下 4 個端點（Disallow: /api/ 之後逐條 Allow）：
     Allow: /api/track-record
     Allow: /api/fundamental-track-public
     Allow: /api/landing-picks
     Allow: /api/landing-preview
   → 呢 4 個係站方主動開放，唔需要登入，唔係爬蟲。

★ 實測資料（2026-10-19）：
   /api/landing-preview  → date, rs_top(20: rank/symbol/rs/roc_1m),
                           sector_flow(5: ticker/name/chg_5d/flow_5d/spark[22])
   /api/landing-picks    → date, market_state, picks(3: symbol/theme/rs/roc_1m/
                           roc_3m/sector/reason/chg/last/price)
   /api/track-record     → sepa(open_count/recent[50]/windows{1m,3m,6m,12m}),
                           sepa_open, twr(ytd_pct/weekly_pct/beat_qqq/ytd_curve), watch
   /api/fundamental-track-public → 15 筆（eps_*/revenue_*/target_*/recommendation）

★ 只讀公開端點，唔登入、唔繞過任何保護。
"""
import datetime as dt
import html as _h
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache", "rocketstock")
BASE = "https://rocketstock.app"

ENDPOINTS = (
    ("preview", "/api/landing-preview"),
    ("picks", "/api/landing-picks"),
    ("track", "/api/track-record"),
    ("fund", "/api/fundamental-track-public"),
)


def _esc(v):
    return _h.escape(str(v)) if v is not None else ""


def _num(v, d=2):
    try:
        return f"{float(v):,.{d}f}"
    except (TypeError, ValueError):
        return "—"


def _pct(v, d=2):
    try:
        return f"{float(v):+.{d}f}%"
    except (TypeError, ValueError):
        return "—"


def _tone(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    return "up" if f > 0 else "dn" if f < 0 else ""


def _fetch(key, path):
    """抓 → (data, from_cache, err)。失敗用當日／最近快取。"""
    os.makedirs(CACHE, exist_ok=True)
    day = dt.date.today().strftime("%Y%m%d")
    p = os.path.join(CACHE, f"{key}_{day}.json")
    if os.path.exists(p):
        try:
            return json.load(io.open(p, encoding="utf-8")), True, None
        except (OSError, ValueError):
            pass
    try:
        q = urllib.request.Request(BASE + path,
                                   headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(q, timeout=30).read()
        d = json.loads(raw.decode("utf-8"))
        io.open(p, "w", encoding="utf-8").write(
            json.dumps(d, ensure_ascii=False))
        return d, False, None
    except Exception as e:                                   # noqa: BLE001
        try:
            fs = sorted(f for f in os.listdir(CACHE)
                        if f.startswith(key + "_") and f.endswith(".json"))
            if fs:
                d = json.load(io.open(os.path.join(CACHE, fs[-1]),
                                      encoding="utf-8"))
                return d, True, None
        except (OSError, ValueError):
            pass
        return None, False, f"{type(e).__name__}: {e}"


CSS = """
.rs-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));
  gap:11px;margin:0 0 16px}
.rs-kpi{padding:13px 15px;border-radius:11px;
  border:1px solid rgba(128,128,128,.26);background:rgba(128,128,128,.045)}
.rs-kpi .k{font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;
  opacity:.6}
.rs-kpi .v{font-size:22px;font-weight:800;margin-top:3px}
.rs-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
.rs-tbl th{text-align:right;font-size:10.5px;letter-spacing:.04em;
  text-transform:uppercase;opacity:.6;padding:6px 8px;
  border-bottom:1px solid rgba(128,128,128,.25);white-space:nowrap}
.rs-tbl td{text-align:right;padding:6px 8px;
  border-bottom:1px solid rgba(128,128,128,.1);white-space:nowrap}
.rs-tbl td.l,.rs-tbl th.l{text-align:left}
.rs-tbl tr:hover{background:rgba(128,128,128,.07)}
.rs-pill{font-size:10px;padding:1px 7px;border-radius:999px;
  border:1px solid rgba(128,128,128,.35);font-weight:700}
.rs-sec{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));
  gap:9px}
.rs-sec>div{border:1px solid rgba(128,128,128,.24);border-radius:10px;
  padding:9px 11px;font-size:12.5px}
"""


def build():
    parts = [f"<style>{CSS}</style>"]
    parts.append('<h2>RocketStock <small>SEPA 相對強弱排名（公開 API）</small></h2>')
    parts.append(
        '<p class="crumb">資料源 <code>rocketstock.app/api/*</code>｜'
        '只用 robots.txt 明確允許嘅 4 個公開端點｜<b>唔登入、唔繞過保護</b>｜'
        '<a href="https://rocketstock.app/rs-ranking?tab=sepa" target="_blank" '
        'rel="noopener noreferrer">↗ 原站（要登入）</a></p>')

    data = {}
    for key, path in ENDPOINTS:
        d, cached, err = _fetch(key, path)
        data[key] = (d, cached, err)

    # ── ① 今日精選 ──
    pk, pk_c, pk_e = data["picks"]
    if pk:
        parts.append('<div class="card"><h2>今日精選 '
                     f'<small>{_esc(pk.get("date"))}｜'
                     f'市場狀態 {_esc(pk.get("market_state"))}｜'
                     f'{len(pk.get("picks") or [])} 隻</small></h2>'
                     '<div style="padding:12px 14px">')
        parts.append('<div class="rs-sec">')
        for p in (pk.get("picks") or []):
            parts.append(
                '<div>'
                f'<div style="display:flex;gap:8px;align-items:baseline">'
                f'<b style="font-size:15px">{_esc(p.get("symbol"))}</b>'
                f'<span class="rs-pill">RS {_esc(p.get("rs"))}</span>'
                f'<span style="margin-left:auto" class="{_tone(p.get("chg"))}">'
                f'{_pct(p.get("chg"))}</span></div>'
                f'<div style="opacity:.72;font-size:11.5px;margin-top:3px">'
                f'{_esc(p.get("theme"))}｜{_esc(p.get("sector"))}</div>'
                f'<div style="opacity:.85;font-size:11.5px;margin-top:4px">'
                f'1月 {_pct(p.get("roc_1m"))}｜3月 {_pct(p.get("roc_3m"))}</div>'
                f'<div style="opacity:.62;font-size:11px;margin-top:5px;'
                f'line-height:1.55">{_esc(p.get("reason"))}</div>'
                '</div>')
        parts.append('</div></div></div>')

    # ── ② RS Top 20 ──
    pv, pv_c, pv_e = data["preview"]
    if pv:
        parts.append('<div class="card"><h2>RS 排名 Top 20 '
                     f'<small>{_esc(pv.get("date"))}</small></h2>'
                     '<div style="padding:12px 14px">'
                     '<div class="scroll"><table class="rs-tbl">'
                     '<thead><tr><th>#</th><th class="l">代號</th>'
                     '<th>RS</th><th>1 月 %</th></tr></thead><tbody>')
        for r in (pv.get("rs_top") or []):
            parts.append(
                f'<tr><td>{_esc(r.get("rank"))}</td>'
                f'<td class="l"><b>{_esc(r.get("symbol"))}</b></td>'
                f'<td>{_esc(r.get("rs"))}</td>'
                f'<td class="{_tone(r.get("roc_1m"))}">'
                f'{_pct(r.get("roc_1m"))}</td></tr>')
        parts.append('</tbody></table></div></div></div>')

        sf = pv.get("sector_flow") or []
        if sf:
            parts.append('<div class="card"><h2>板塊資金流 '
                         '<small>5 日</small></h2>'
                         '<div style="padding:12px 14px"><div class="rs-sec">')
            for s in sf:
                parts.append(
                    '<div>'
                    f'<div style="display:flex;gap:8px;align-items:baseline">'
                    f'<b>{_esc(s.get("ticker"))}</b>'
                    f'<span style="opacity:.7;font-size:11.5px">'
                    f'{_esc(s.get("name"))}</span>'
                    f'<span style="margin-left:auto" class="{_tone(s.get("chg_5d"))}">'
                    f'{_pct(s.get("chg_5d"))}</span></div>'
                    f'<div style="opacity:.7;font-size:11.5px;margin-top:3px">'
                    f'流入 {_num(s.get("flow_5d"), 1)}</div></div>')
            parts.append('</div></div></div>')

    # ── ③ SEPA 實績 ──
    tr, tr_c, tr_e = data["track"]
    if tr:
        sepa = tr.get("sepa") or {}
        twr = tr.get("twr") or {}
        win = sepa.get("windows") or {}
        parts.append('<div class="card"><h2>SEPA 實績 '
                     '<small>站方自己公布｜未平倉 '
                     f'{_esc(sepa.get("open_count"))} 隻</small></h2>'
                     '<div style="padding:12px 14px">')
        if win:
            parts.append('<div class="rs-kpis">')
            for lbl, k in (("1 個月", "1m"), ("3 個月", "3m"),
                           ("6 個月", "6m"), ("12 個月", "12m")):
                w = win.get(k) or {}
                if not w:
                    continue
                wr = w.get("win_rate")
                parts.append(
                    f'<div class="rs-kpi"><div class="k">{lbl}勝率</div>'
                    f'<div class="v" style="color:'
                    f'{"#16a34a" if (wr or 0) >= 50 else "#dc2626"}">'
                    f'{_num(wr, 1)}%</div>'
                    f'<div style="font-size:11px;opacity:.62;margin-top:2px">'
                    f'{_esc(w.get("win"))} 贏 / {_esc(w.get("loss"))} 輸'
                    f'（{_esc(w.get("total"))} 單）</div></div>')
            parts.append('</div>')
        if twr.get("ytd_pct") is not None:
            parts.append('<div class="rs-kpis" style="margin-top:2px">'
                         f'<div class="rs-kpi"><div class="k">YTD</div>'
                         f'<div class="v {_tone(twr.get("ytd_pct"))}">'
                         f'{_pct(twr.get("ytd_pct"))}</div></div>'
                         f'<div class="rs-kpi"><div class="k">本週</div>'
                         f'<div class="v {_tone(twr.get("weekly_pct"))}">'
                         f'{_pct(twr.get("weekly_pct"))}</div></div>'
                         f'<div class="rs-kpi"><div class="k">跑贏 QQQ</div>'
                         f'<div class="v">{_esc(twr.get("beat_qqq"))}</div></div>'
                         '</div>')
        rec = sepa.get("recent") or []
        if rec:
            parts.append('<div class="scroll" style="margin-top:10px">'
                         '<table class="rs-tbl"><thead><tr>'
                         '<th class="l">代號</th><th>入場</th><th>出場</th>'
                         '<th>持倉日</th><th>回報</th></tr></thead><tbody>')
            for t in rec[:30]:
                parts.append(
                    f'<tr><td class="l"><b>{_esc(t.get("symbol"))}</b></td>'
                    f'<td>{_esc(t.get("entry_date"))}</td>'
                    f'<td>{_esc(t.get("exit_date"))}</td>'
                    f'<td>{_esc(t.get("days_held"))}</td>'
                    f'<td class="{_tone(t.get("return_pct"))}">'
                    f'{_pct(t.get("return_pct"))}</td></tr>')
            parts.append('</tbody></table></div>')
        parts.append('</div></div>')

    # ── ④ 基本面追蹤 ──
    fu, fu_c, fu_e = data["fund"]
    if isinstance(fu, list) and fu:
        parts.append('<div class="card"><h2>基本面追蹤 '
                     f'<small>{len(fu)} 隻</small></h2>'
                     '<div style="padding:12px 14px">'
                     '<div class="scroll"><table class="rs-tbl"><thead><tr>'
                     '<th class="l">代號</th><th class="l">公司</th>'
                     '<th>EPS 實際</th><th>EPS 預期</th><th>目標價</th>'
                     '<th>評級</th></tr></thead><tbody>')
        for r in fu:
            parts.append(
                f'<tr><td class="l"><b>{_esc(r.get("ticker"))}</b></td>'
                f'<td class="l" style="max-width:180px;overflow:hidden;'
                f'text-overflow:ellipsis">{_esc(r.get("longName"))}</td>'
                f'<td>{_num(r.get("eps_latest_actual"))}</td>'
                f'<td>{_num(r.get("eps_latest_est"))}</td>'
                f'<td>{_num(r.get("target_mean"))}</td>'
                f'<td>{_esc(r.get("recommendation"))}</td></tr>')
        parts.append('</tbody></table></div></div></div>')

    # 失敗提示
    fails = [k for k, (d, c, e) in data.items() if d is None]
    if fails:
        parts.append('<div class="card"><div class="body" '
                     'style="color:#e5484d">⛔ DATA_UNAVAILABLE：'
                     f'{", ".join(fails)} —— Missing ≠ Zero。</div></div>')

    parts.append(
        '<div class="note" style="font-size:12px;line-height:1.8">'
        '<b>★ 為什麼唔直接嵌入原站？</b> '
        'rocketstock.app 回 <code>X-Frame-Options: SAMEORIGIN</code> 同 '
        '<code>CSP frame-ancestors &quot;self&quot;</code>，'
        '明確禁止第三方網站包住。'
        '本頁改用 robots.txt 主動開放的 4 個 <code>/api/</code> 端點，'
        '屬站方預期用途，唔係爬蟲。'
        '<br><b>★ 排名 Top 20 / 板塊資金流 / 實績</b> 由公開端點提供；'
        '<b>完整 RS ranking 全表（tab=sepa）</b> 需要付費登入，'
        '本頁唔會代你登入，請用上方「↗ 原站」。</div>')
    return ("RocketStock", "".join(parts))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    _t, b = build()
    out = os.path.join(HERE, "rocketstock_body.html")
    io.open(out, "w", encoding="utf-8").write(b)
    print(f"✓ rocketstock body {len(b):,} 字 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
