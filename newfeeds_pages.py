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
.sheetload{position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:14px;background:#0d1220;
  color:#9fb0cc;font-size:13px;z-index:2}
[data-theme="light"] .sheetload{background:#f6f8fb;color:#64748b}
.spin{width:26px;height:26px;border-radius:50%;border:3px solid rgba(128,128,128,.3);
  border-top-color:#2563eb;animation:sp .8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
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
    """Google Sheet iframe（/preview = 唯讀、可嵌入）。

    ★ Google 用 JS 渲染，實測要 15-20 秒才出表 → 加載入提示，唔好令人以為壞。
    """
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
        f'<div class="sheetbox">'
        f'<div id="ld_{gid}" class="sheetload">'
        '<div class="spin"></div>'
        '<div>載入 Google Sheet…（首次約 15-20 秒）</div>'
        '</div>'
        f'<iframe id="sb_{gid}" src="{src}" loading="lazy" '
        f'title="{_esc(title)}" '
        f'onload="var d=document.getElementById(\'ld_{gid}\');'
        "if(d)d.style.display='none'\"></iframe>"
        '</div>')


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
        mx = max([max(s["up4"] or 0, s["down4"] or 0) for s in series] or [1])
        HALF = 88          # 每邊最大像素
        out.append('<div class="card"><h2>近 40 日升跌家數 '
                   '<small>綠向左＝升 4%+，紅向右＝跌 4%+</small></h2>'
                   '<div style="padding:12px 14px">'
                   '<table style="width:100%;border-collapse:collapse;'
                   'font-size:12.5px;table-layout:fixed">'
                   '<colgroup><col style="width:74px"><col style="width:52px">'
                   '<col style="width:52px"><col style="width:60px">'
                   '<col></colgroup>'
                   '<thead><tr><th class="l">日期</th><th>升 4%+</th>'
                   '<th>跌 4%+</th><th>升/跌比</th>'
                   '<th class="l">分佈（中央對齊）</th></tr></thead><tbody>')
        for s in series[:40]:
            u = s["up4"] or 0
            dd = s["down4"] or 0
            wu = max(2, int(u / mx * HALF)) if u else 0
            wd = max(2, int(dd / mx * HALF)) if dd else 0
            ratio = (u / dd) if dd else (999 if u else 0)
            if dd == 0 and u == 0:
                rt_s, rt_c = "—", ""
            elif dd == 0:
                rt_s, rt_c = "∞", "up"
            else:
                rt_s = f"{ratio:.2f}"
                rt_c = "up" if ratio >= 1 else "dn"
            out.append(
                f'<tr>'
                f'<td class="l" style="font-size:11.5px">{_esc(s["date"])}</td>'
                f'<td class="up">{int(u)}</td>'
                f'<td class="dn">{int(dd)}</td>'
                f'<td class="{rt_c}" style="font-weight:700">{rt_s}</td>'
                '<td><div style="display:flex;align-items:center;'
                'width:100%;height:11px">'
                '<div style="flex:1;display:flex;justify-content:flex-end">'
                f'<span style="height:10px;width:{wu}px;background:#2fbf71;'
                'border-radius:3px 0 0 3px"></span></div>'
                '<div style="width:2px;height:15px;background:'
                'rgba(120,130,150,.75);flex:0 0 auto;border-radius:1px"></div>'
                '<div style="flex:1;display:flex;justify-content:flex-start">'
                f'<span style="height:10px;width:{wd}px;background:#e5484d;'
                'border-radius:0 3px 3px 0"></span></div>'
                '</div></td></tr>')
        out.append("</tbody></table>"
                   '<div class="note" style="margin-top:8px">'
                   '★ 中間灰線＝0。綠條長度＝升 4%+ 家數，紅條＝跌 4%+ 家數，'
                   '左綠右紅由中央向外。'
                   '<b>升/跌比 &gt;1</b> 綠字＝升多於跌；<b>&lt;1</b> 紅字＝跌多於升。'
                   '</div></div></div>')
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


# ══════════════════════════════════════════════════════════════
# 5. 納指權重股（NDX 100）
# ══════════════════════════════════════════════════════════════
def ndx_page(d):
    if not d or not d.get("rows"):
        return _unavail("納指權重股")
    out = [_head("🇺🇸 納指權重股", "NDX 100 成分 + 市值權重",
                 d.get("_asof", ""),
                 "https://www.nasdaq.com/market-activity/quotes/nasdaq-ndx-index",
                 "Nasdaq 官方")]

    rows = d["rows"]
    total = d.get("total_mcap") or 0
    out.append('<div class="card"><div style="padding:12px 16px;font-size:12.5px;'
               'line-height:1.7">'
               f'<b>{len(rows)} 隻｜總市值 ${total/1e12:.2f}T</b><br>'
               '⚠️ <b>權重 = 市值比（近似值）</b>。指數實際用 modified '
               'market-cap weighting（有上限機制），所以頭幾大嘅實際權重會'
               '略低過呢度顯示。<br>'
               '★ 用途：睇邊隻股一動就推／拖指數幾多'
               '</div></div>')

    # 前 10 大卡
    out.append('<div class="card"><h2>前 10 大 '
               f'<small>合共 {sum(x["weight"] or 0 for x in rows[:10]):.1f}%</small>'
               '</h2><div style="padding:14px 16px">'
               '<div style="display:grid;grid-template-columns:repeat(auto-fit,'
               'minmax(120px,1fr));gap:12px">')
    for x in rows[:10]:
        cls = "up" if (x.get("chgpct") or 0) > 0 else (
            "dn" if (x.get("chgpct") or 0) < 0 else "")
        out.append(f'<div><div style="font-size:13px;font-weight:700">'
                   f'{_esc(x["sym"])}</div>'
                   f'<div style="font-size:19px;font-weight:700;'
                   f'">{x["weight"] or 0:.2f}%</div>'
                   f'<div class="{cls}" style="font-size:12px">'
                   f'{_pct(x.get("chgpct"), 2)}</div></div>')
    out.append("</div></div></div>")

    # 完整表
    out.append('<div class="card"><h2>全部成分股 '
               '<small>按市值排序</small></h2>'
               '<div style="padding:14px 16px;overflow-x:auto">'
               '<table style="width:100%;border-collapse:collapse;font-size:13px">'
               '<thead><tr><th class="l">#</th><th class="l">代號</th>'
               '<th class="l">公司</th><th>市值</th><th>權重</th>'
               '<th>現價</th><th>漲跌%</th></tr></thead><tbody>')
    for i, x in enumerate(rows, 1):
        mc = (f"${x['mcap']/1e9:,.0f}B" if x.get("mcap") else "—")
        out.append(f'<tr><td class="l">{i}</td>'
                   '<td class="l"><a href="https://www.tradingview.com/chart/'
                   f'?symbol={_esc(x["sym"])}" target="_blank" rel="noopener">'
                   f'<b>{_esc(x["sym"])}</b></a></td>'
                   '<td class="l" style="max-width:230px;overflow:hidden;'
                   'text-overflow:ellipsis;white-space:nowrap">'
                   f'{_esc(x.get("name","")[:46])}</td>'
                   f'<td>{mc}</td>'
                   f'<td><b>{x["weight"] or 0:.2f}%</b></td>'
                   f'<td>{_num(x.get("px"), 2)}</td>'
                   f'<td{_tone(x.get("chgpct"))}>{_pct(x.get("chgpct"), 2)}</td>'
                   '</tr>')
    out.append("</tbody></table></div></div>")

    out.append('<div class="card"><h2>★ 點用</h2>'
               '<div style="padding:12px 16px;font-size:13px;line-height:1.75">'
               '① <b>權重 ≥3%</b> 嘅股（NVDA/AAPL/GOOGL/GOOG/MSFT/AMZN/SPCX）'
               '動 1% ≈ 指數動 0.03–0.11%<br>'
               '② 前 10 大佔 <b>69.5%</b> → 指數走勢基本上係呢 10 隻話事<br>'
               '③ 小品種（<0.5%）就算暴漲對指數影響都好細<br>'
               '④ 你持倉同呢張表重疊 = 集中度風險'
               '</div></div>')
    return "".join(out)


PAGES = {
    "mm": ("Market Monitor", mm_page),
    "bee50": ("Stockbee 50", bee50_page),
    "ndx": ("納指權重股", ndx_page),
    "jeffsun": ("Jeff Sun Mom.", jeffsun_page),
}
