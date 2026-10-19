# -*- coding: utf-8 -*-
"""newfeeds_pages.py — 四個外部數據源頁面（Desmond 2026-10-19 v2）

★ v2：改用【iframe 直接嵌入 Google Sheet 原表】，因為 Desmond 要原貌。
   實測（curl X-Frame-Options）：
     /preview    → 冇 X-Frame-Options  ✓ 可嵌入
     /htmlembed  → 冇 X-Frame-Options  ✓ 可嵌入
     Market Monitor (pub/ccc) → X-Frame-Options: SAMEORIGIN  ✗ 唔可以嵌入
   → 3 個 Sheet 用 iframe；Market Monitor 用自己 render（已 parse 好）。
"""
import html as _h


def _esc(v):
    return _h.escape(str(v)) if v is not None else ""


def _num(v, d=1, sign=False):
    if v is None:
        return "—"
    try:
        return f"{v:+,.{d}f}" if sign else f"{v:,.{d}f}"
    except (TypeError, ValueError):
        return "—"


def _pct(v, d=1):
    return "—" if v is None else f"{v:+.{d}f}%"


def _tone(v, pos=0, neg=0):
    if v is None:
        return ""
    return ' class="up"' if v > pos else (' class="dn"' if v < neg else "")


SHEET_CSS = """
.sheetbox{position:relative;width:100%;height:74vh;min-height:520px;
  border:1px solid rgba(128,128,128,.3);border-radius:12px;overflow:hidden;
  background:#fff;margin:0 0 16px}
.sheetbox iframe{width:100%;height:100%;border:0;display:block}
.sheetbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;
  margin:0 0 10px;font-size:12.5px}
.sheetbar a,.sheetbar button{display:inline-flex;align-items:center;gap:5px;
  padding:7px 12px;border-radius:8px;border:1px solid rgba(128,128,128,.38);
  background:rgba(128,128,128,.08);color:inherit;font-size:12.5px;
  text-decoration:none;cursor:pointer;font-family:inherit}
.sheetbar a:hover,.sheetbar button:hover{background:rgba(128,128,128,.18)}
details summary{cursor:pointer;font-weight:700;padding:10px 0;font-size:14px}
.up{color:#1a7f4b}
.dn{color:#c0262b}
[data-theme="dark"] .up{color:#7ce0a8}
[data-theme="dark"] .dn{color:#ff9a9d}
[data-theme="dark"] .sheetbox{background:#0b1220}
@media(max-width:900px){
  .sheetbox{height:64vh;min-height:440px}
}
"""


def _sheet_iframe(sheet_id, gid, title):
    """Google Sheet iframe（/preview = 唯讀、可嵌入）。"""
    src = (f"https://docs.google.com/spreadsheets/d/{sheet_id}/preview"
           f"?gid={gid}&rm=minimal&widget=true")
    full = (f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid={gid}")
    return (
        '<div class="sheetbar">'
        f'<a href="{full}" target="_blank" rel="noopener">↗ 開原表（可編輯）</a>'
        f'<button onclick="var f=document.getElementById(\'sb_{gid}\');'
        'if(f.requestFullscreen)f.requestFullscreen()">⛶ 全螢幕</button>'
        '<span style="opacity:.6">唯讀嵌入 · 自動跟原表更新</span>'
        '</div>'
        f'<div class="sheetbox"><iframe id="sb_{gid}" src="{src}" '
        f'loading="lazy" title="{_esc(title)}"></iframe></div>')


def _head(title, sub, asof, src_url="", src_label=""):
    link = (f'｜<a href="{src_url}" target="_blank" rel="noopener">{src_label}</a>'
            if src_url else "")
    return (f'<style>{SHEET_CSS}</style>'
            f'<h2>{title} <small>{_esc(sub)}</small></h2>\n'
            f'<p class="crumb">外部數據源｜快照 {_esc(asof)}{link}｜'
            '唯讀研究用途，<b>非買入指令</b></p>\n')


def _unavail(label, err=""):
    return (f'<style>{SHEET_CSS}</style>'
            f'<div class="card"><h2>{_esc(label)}</h2>'
            '<div style="padding:16px">'
            '<b>⛔ DATA_UNAVAILABLE</b><br>'
            f'抓唔到數據（{_esc(err) or "網絡或格式問題"}）。<br><br>'
            '★ Missing ≠ Zero —— 冇數據唔等於 0。</div></div>')


# ══════════════════════════════════════════════════════════════
# 1. Market Monitor（★ 封鎖 iframe → 自己 render）
# ══════════════════════════════════════════════════════════════
def mm_page(d):
    if not d:
        return _unavail("Market Monitor")
    out = [_head("🌊 Market Monitor", "Stockbee 每日 breadth",
                 d.get("_asof", ""),
                 "https://stockbee.blogspot.com/p/mm.html", "Stockbee 原頁")]

    out.append('<div class="card"><div style="padding:12px 16px;font-size:12.5px;'
               'line-height:1.7">'
               '<b>⚠️ 原表封鎖 iframe 嵌入</b>（X-Frame-Options: SAMEORIGIN），'
               '所以呢頁係由 CSV 重新整理，數據同原表一致。'
               '</div></div>')

    up, dn = d.get("up4"), d.get("down4")
    r5, r10 = d.get("r5"), d.get("r10")
    ratio = (up / dn) if (up is not None and dn) else None

    out.append('<div class="card"><h2>最新一日 '
               f'<small>{_esc(d.get("date",""))}</small></h2>'
               '<div style="padding:14px 16px">'
               '<div style="display:grid;grid-template-columns:repeat(auto-fit,'
               'minmax(140px,1fr));gap:14px">')
    for label, val, cls in (
            ("升 4%+ 家數", _num(up, 0), "up"),
            ("跌 4%+ 家數", _num(dn, 0), "dn"),
            ("升/跌 比", _num(ratio, 2), ""),
            ("5 日比率", _num(r5, 2), ""),
            ("10 日比率", _num(r10, 2), ""),
            ("升 25%+ (季)", _num(d.get("up25q"), 0), "up"),
            ("跌 25%+ (季)", _num(d.get("down25q"), 0), "dn"),
    ):
        out.append('<div><div style="font-size:11px;opacity:.65;'
                   'letter-spacing:.06em;text-transform:uppercase">'
                   f'{label}</div>'
                   f'<div class="{cls}" style="font-size:21px;font-weight:700">'
                   f'{val}</div></div>')
    out.append("</div></div></div>")

    series = d.get("series") or []
    if series:
        mx = max([(s["up4"] or 0) + (s["down4"] or 0) for s in series] or [1])
        out.append('<div class="card"><h2>近 40 日升跌家數</h2>'
                   '<div style="padding:14px 16px;overflow-x:auto">'
                   '<table style="width:100%;border-collapse:collapse;'
                   'font-size:12.5px">'
                   '<thead><tr><th class="l">日期</th><th>升 4%+</th>'
                   '<th>跌 4%+</th><th class="l">分佈</th></tr></thead><tbody>')
        for s in series[:40]:
            u = s["up4"] or 0
            dd = s["down4"] or 0
            wu = int(u / mx * 110)
            wd = int(dd / mx * 110)
            out.append(f'<tr><td class="l">{_esc(s["date"])}</td>'
                       f'<td class="up">{int(u)}</td>'
                       f'<td class="dn">{int(dd)}</td>'
                       '<td class="l" style="white-space:nowrap">'
                       f'<span style="display:inline-block;height:9px;'
                       f'width:{wu}px;background:#2fbf71;border-radius:2px">'
                       '</span>'
                       f'<span style="display:inline-block;height:9px;'
                       f'width:{wd}px;background:#e5484d;border-radius:2px;'
                       'margin-left:1px"></span></td></tr>')
        out.append("</tbody></table></div></div>")
    return "".join(out)


# ══════════════════════════════════════════════════════════════
# 2. Stockbee 50（iframe + 摘要）
# ══════════════════════════════════════════════════════════════
def bee50_page(d):
    SID, GID = "1xjbe9SF0HsxwY_Uy3NC2tT92BqK0nhArUaYU16Q0p9M", "1499398020"
    asof = (d or {}).get("_asof", "")
    out = [_head("🐝 Stockbee 50", "每日最強動能 50 隻", asof,
                 f"https://docs.google.com/spreadsheets/d/{SID}/edit#gid={GID}",
                 "原表")]
    out.append(_sheet_iframe(SID, GID, "Stockbee 50"))

    if d and d.get("dates"):
        dates, cols = d["dates"], d["columns"]
        out.append('<details><summary>▸ 我嘅整理：今日 50 隻'
                   '（可點入 TradingView）'
                   f'｜最新 {_esc(dates[0])}</summary>'
                   '<div style="padding:6px 0 14px">'
                   '<div style="display:flex;flex-wrap:wrap;gap:7px">')
        for t in (cols[0] if cols else []):
            out.append('<a href="https://www.tradingview.com/chart/?symbol='
                       f'{_esc(t)}" target="_blank" rel="noopener" '
                       'style="display:inline-block;padding:6px 11px;'
                       'border-radius:8px;border:1px solid rgba(128,128,128,.35);'
                       'font-size:13px;font-weight:600;text-decoration:none">'
                       f'{_esc(t)}</a>')
        out.append("</div></div></details>")
    return "".join(out)


# ══════════════════════════════════════════════════════════════
# 3. Sector RS（iframe + 摘要）
# ══════════════════════════════════════════════════════════════
def sectorrs_page(d):
    SID, GID = "1sR0Edn3q5PKEAcaAOSZIAAisn8bvEzzY8EwiKJTIlBQ", "539776210"
    asof = (d or {}).get("_asof", "")
    out = [_head("🏭 Sector RS", "相對強度（NSE 印度）", asof,
                 f"https://docs.google.com/spreadsheets/d/{SID}/edit#gid={GID}",
                 "原表")]
    out.append(_sheet_iframe(SID, GID, "Sector RS"))

    if d:
        rows = [x for x in (d.get("rows") or []) if x.get("m3") is not None]
        rows.sort(key=lambda x: -x["m3"])
        exchs = ", ".join(d.get("exchanges") or [])
        out.append('<details><summary>▸ 我嘅整理：按 3 個月排序'
                   f'（★ 呢個表係 {_esc(exchs)} 印度交易所，唔係美股）'
                   '</summary><div style="padding:6px 0 14px;overflow-x:auto">'
                   '<table style="width:100%;border-collapse:collapse;'
                   'font-size:13px">'
                   '<thead><tr><th class="l">#</th><th class="l">代號</th>'
                   '<th>LTP</th><th>日%</th><th>1M%</th><th>3M%</th><th>6M%</th>'
                   '</tr></thead><tbody>')
        for i, x in enumerate(rows[:30], 1):
            out.append(f'<tr><td class="l">{i}</td>'
                       '<td class="l"><a href="https://www.tradingview.com/chart/'
                       f'?symbol={_esc(x["exch"])}:{_esc(x["sym"])}" '
                       f'target="_blank" rel="noopener">{_esc(x["sym"])}</a></td>'
                       f'<td>{_num(x.get("ltp"), 1)}</td>'
                       f'<td{_tone(x.get("chg"))}>{_pct(x.get("chg"))}</td>'
                       f'<td{_tone(x.get("m1"))}>{_pct(x.get("m1"))}</td>'
                       f'<td{_tone(x.get("m3"))}><b>{_pct(x.get("m3"))}</b></td>'
                       f'<td{_tone(x.get("m6"))}>{_pct(x.get("m6"))}</td></tr>')
        out.append("</tbody></table></div></details>")
    return "".join(out)


# ══════════════════════════════════════════════════════════════
# 4. Jeff Sun Momentum（iframe + 摘要）
# ══════════════════════════════════════════════════════════════
def jeffsun_page(d):
    SID, GID = "1TDiU6Wt0YYoJ1YPEtcwqWY4UU8FMj1vLLYFxQitg6oE", "634720175"
    asof = (d or {}).get("_asof", "")
    out = [_head("🎯 Jeff Sun Momentum", "板塊 / ETF 動能", asof,
                 f"https://docs.google.com/spreadsheets/d/{SID}/edit#gid={GID}",
                 "原表")]
    out.append(_sheet_iframe(SID, GID, "Jeff Sun Momentum"))

    if d:
        rows = [x for x in (d.get("rows") or []) if x.get("rs") is not None]
        rows.sort(key=lambda x: -x["rs"])
        out.append('<details><summary>▸ 我嘅整理：按 1 個月 RS 排序'
                   f'（{len(rows)} 隻）</summary>'
                   '<div style="padding:6px 0 14px;overflow-x:auto">'
                   '<table style="width:100%;border-collapse:collapse;'
                   'font-size:13px">'
                   '<thead><tr><th class="l">代號</th><th class="l">名稱</th>'
                   '<th>RS</th><th>ADR%</th><th>1D</th><th>1W</th><th>1M</th>'
                   '<th>3M</th><th>6M</th><th>12M</th></tr></thead><tbody>')
        for x in rows:
            out.append('<tr><td class="l"><a href="https://www.tradingview.com/'
                       f'chart/?symbol={_esc(x["sym"])}" target="_blank" '
                       f'rel="noopener"><b>{_esc(x["sym"])}</b></a></td>'
                       '<td class="l" style="max-width:180px;overflow:hidden;'
                       'text-overflow:ellipsis;white-space:nowrap">'
                       f'{_esc(x.get("name",""))}</td>'
                       f'<td>{_num(x.get("rs"), 0)}</td>'
                       f'<td>{_num(x.get("adr"), 2)}</td>'
                       f'<td{_tone(x.get("d1"))}>{_pct(x.get("d1"))}</td>'
                       f'<td{_tone(x.get("w1"))}>{_pct(x.get("w1"))}</td>'
                       f'<td{_tone(x.get("m1"))}><b>{_pct(x.get("m1"))}</b></td>'
                       f'<td{_tone(x.get("m3"))}>{_pct(x.get("m3"))}</td>'
                       f'<td{_tone(x.get("m6"))}>{_pct(x.get("m6"))}</td>'
                       f'<td{_tone(x.get("m12"))}>{_pct(x.get("m12"))}</td>'
                       '</tr>')
        out.append("</tbody></table></div></details>")

        out.append('<div class="card"><h2>★ 讀法</h2>'
                   '<div style="padding:12px 16px;font-size:13px;'
                   'line-height:1.75">'
                   '① <b>RS 100</b> = 1 個月相對強度最高<br>'
                   '② <b>ADR%</b> = 平均日波幅 → 決定止蝕闊度（ATR）<br>'
                   '③ <b>12M 正 + 1M 正</b> = 長短期同向（最健康）<br>'
                   '④ 防守板塊（XLE / XLP / XLV / XLU）轉強 = 大市進入 '
                   'distribution</div></div>')
    return "".join(out)


PAGES = {
    "mm": ("Market Monitor", mm_page),
    "bee50": ("Stockbee 50", bee50_page),
    "sectorrs": ("Sector RS", sectorrs_page),
    "jeffsun": ("Jeff Sun Mom.", jeffsun_page),
}
