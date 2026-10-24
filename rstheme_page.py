# -*- coding: utf-8 -*-
"""rstheme_page.py — RS THEME 頁（Desmond 2026-10-24 大改）

六個要求（原話）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
① 增加「階段／分／1週／1個月／3個月」呢幾行
② 統一返本身內容嘅風格
③ 默認全部排最左手邊
④ 縮近行距（手機睇得晒）
⑤ ETF 同名稱分開兩欄
⑥ 移除滑動 BAR（唔要橫向 scroll）

設計原則
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
· 所有數字欄左對齊、tabular-nums → 一眼掃落去
· 行高 3px padding（原本 7px）→ 一屏睇多 40%
· 唔用 overflow-x：`table-layout:fixed` + 名稱 ellipsis
· 每個回報旁邊一條微型 bar（手機自動隱藏，數字照留）
· 「分」係透明加權百分位：1M 50% / 3M 30% / 1W 20%（見註腳）
· 階段用 kell.stages()（同領導股頁同一把尺）
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _esc(v):
    import html as h
    return h.escape(str(v)) if v is not None else ""


def _f(v, d=1, plus=True):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "—"
    return (f"{x:+.{d}f}%" if plus else f"{x:.{d}f}%")


CSS = """
.rt-h{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:0 0 2px}
.rt-h h2{margin:0;font-size:19px}
/* ── 卡片頭（參考 Sectors 頁「行業輪動」排板，Desmond 2026-10-24）── */
.rt-shead{display:flex;align-items:center;gap:11px;padding:2px 0 9px;
  border-bottom:1px solid rgba(128,128,128,.22);margin-bottom:6px;flex-wrap:wrap}
.rt-ico{background:#2563eb;border-radius:9px;width:32px;height:32px;
  display:flex;align-items:center;justify-content:center;font-size:16px;
  flex:0 0 32px;line-height:1}
.rt-shead .ttl{font-size:18px;font-weight:800;line-height:1.15}
.rt-shead .sub{font-size:11.5px;opacity:.62;margin-top:2px}
.rt-shead .meta{margin-left:auto;font-size:11.5px;opacity:.72;text-align:right}
.rt-sub{font-size:11.5px;opacity:.62}
.rt-card{margin:10px 0}
.rt-card h3{margin:0 0 4px;font-size:14px;font-weight:800;
  display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
.rt-card h3 small{font-weight:400;font-size:11px;opacity:.6}
.rt-tbl{width:100%;max-width:1140px;border-collapse:collapse;font-size:12.5px;
  table-layout:fixed;font-variant-numeric:tabular-nums}
.rt-tbl th{text-align:left;font-size:10px;font-weight:700;letter-spacing:.04em;
  padding:4px 5px;opacity:.6;border-bottom:1px solid rgba(128,128,128,.3);
  white-space:nowrap}
.rt-tbl td{padding:3px 5px;border-bottom:1px solid rgba(128,128,128,.1);
  text-align:left;vertical-align:middle;line-height:1.25;overflow:hidden}
.rt-tbl tr:hover td{background:rgba(249,115,22,.055)}
.rt-tbl col.c-rs1m{width:76px}
.rt-tbl col.c-band{width:72px}
.rt-rsbar{display:inline-block;width:34px;height:6px;border-radius:3px;
  background:rgba(128,128,128,.18);vertical-align:middle;margin-left:4px;
  overflow:hidden}
.rt-rsbar>i{display:block;height:100%;border-radius:3px}
.rt-tbl col.c-stage{width:104px}
.rt-tbl col.c-etf{width:54px}
.rt-tbl col.c-name{width:150px}
.rt-tbl col.c-fill{width:auto}
.rt-tbl col.c-score{width:38px}
.rt-tbl col.c-p1w{width:68px}
.rt-tbl col.c-p1m{width:72px}
.rt-tbl col.c-p3m{width:72px}
.rt-tbl col.c-thrust{width:50px}
.rt-tbl col.c-ex1m{width:62px}
.rt-tbl col.c-spark{width:52px}
.rt-tbl col.c-off52{width:56px}
.rt-nm2{display:none}
.rt-st-abbr{display:none}
.rt-etf{font-weight:800;font-size:12px;letter-spacing:.01em}
.rt-etf a{color:inherit;text-decoration:none}
.rt-etf a:hover{color:#f97316}
.rt-name{font-size:11.5px;opacity:.72;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.rt-num{font-weight:700}
.rt-pos{color:#15803d}
.rt-neg{color:#dc2626}
.rt-flat{opacity:.55}
html[data-theme="dark"] .rt-pos{color:#7ce0a8}
html[data-theme="dark"] .rt-neg{color:#ff8f8f}
.rt-stage{font-size:10px;font-weight:800;padding:1px 4px;border-radius:999px;
  border:1px solid currentColor;display:inline-block;white-space:nowrap;
  line-height:1.45;max-width:100%;overflow:hidden;text-overflow:ellipsis;
  vertical-align:middle}
.rt-bar{display:block;width:100%;height:3px;margin-top:2px;border-radius:2px;
  background:rgba(128,128,128,.16);vertical-align:middle;margin-left:5px;
  position:relative;overflow:hidden}
.rt-bar>i{position:absolute;top:0;bottom:0;border-radius:3px;display:block}
/* 走位防護：所有格強制收窄，唔准頂出隔籬欄 */
.rt-tbl td{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rt-h3{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rt-warn{overflow-wrap:anywhere}
/* Excel 式三角排序 */
.rt-tbl th.sortable{cursor:pointer;user-select:none;white-space:nowrap}
.rt-tbl th.sortable:hover{color:#f97316}
.rt-tbl th.sortable::after{content:"▾";font-size:8px;opacity:.22;margin-left:2px}
.rt-tbl th.sortable.asc::after{content:"▴";opacity:.9}
.rt-tbl th.sortable.desc::after{content:"▾";opacity:.9}
.rt-note{font-size:11px;opacity:.6;line-height:1.65;margin-top:8px}
.rt-warn{font-size:11.5px;line-height:1.6;padding:7px 10px;border-radius:8px;
  background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.35);
  margin:0 0 8px}
/* ★ 2026-10-24 修：唔再「縮字」—— 窄螢幕改用卡片式（每隻股 2 行 + 標籤），
   字級維持 12.5px，唔會縮到睇唔到，亦都唔需要橫向 scroll。*/
@media(max-width:900px){
  .rt-bar{display:none}
  .rt-st-full{display:none}
  .rt-st-abbr{display:inline}
  .rt-tbl{max-width:none;table-layout:auto;font-size:12.5px}
  .rt-tbl colgroup,.rt-tbl thead{display:none}
  .rt-tbl,.rt-tbl tbody,.rt-tbl tr,.rt-tbl td{display:block;width:auto}
  .rt-tbl tr{padding:7px 2px;border-bottom:1px solid rgba(128,128,128,.16)}
  .rt-tbl td{border:0;padding:1px 0;display:inline-block;
    margin:0 12px 2px 0;font-size:12.5px}
  .rt-tbl td[data-l]::before{content:attr(data-l) " ";font-size:10.5px;
    opacity:.5;margin-right:2px}
  .rt-tbl td.c1,.rt-tbl td.c2{margin-right:8px}
  .rt-tbl td.c3{display:block;font-size:12px;opacity:.7;margin:1px 0 3px}
  .rt-tbl td:last-child{display:none}
  .rt-nm2{display:none}
  .rt-stage{font-size:10.5px;padding:1px 5px}
}
"""


def _bar(v, mx, lo=-1):
    """微型回報 bar（0 基線）。mx = 本欄最大絕對值。"""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return ""
    if not mx:
        return ""
    w = min(100.0, abs(x) / mx * 100)
    col = "#22c55e" if x >= 0 else "#ef4444"
    if x >= 0:
        return ('<span class="rt-bar"><i style="left:50%%;width:%.1f%%;'
                'background:%s"></i></span>' % (w / 2, col))
    return ('<span class="rt-bar"><i style="right:50%%;width:%.1f%%;'
            'background:%s"></i></span>' % (w / 2, col))


# ★ 2026-10-24 Desmond：「階段用返 Oliver Kell 既階段方式表達」
#   桌面：出全名（① Reversal Extension …）；手機：縮寫（① RE）。
#   名稱來源 = kell.py STAGES（同領導股頁完全一致），唔准另創一套。
STAGE_ABBR = {
    "①": "RE",   # Reversal Extension
    "②": "WP",   # Wedge Pop
    "③": "EC",   # EMA Crossback
    "④": "BB",   # Base 'n Break
    "⑤": "EE",   # Exhaustion Extension
    "⑥": "WD",   # Wedge Drop
}


def _stage_badge(st):
    if not st:
        return '<span class="rt-stage rt-flat">—</span>'
    full = (st.get("stage") or st.get("short") or "").strip()
    col = st.get("color") or "#94a3b8"
    num = full[:1] if full else "—"
    ab = STAGE_ABBR.get(num, full[:2] or "—")
    return (f'<span class="rt-stage" style="color:{col}" '
            f'title="{_esc(full)}">'
            f'<span class="rt-st-full">{_esc(full)}</span>'
            f'<span class="rt-st-abbr">{_esc(num)} {_esc(ab)}</span>'
            '</span>')


def _band(atrx):
    """ATR 帶（−3 … +5 ATR）。定義同 build_site.band_svg 一致：
    灰線＝0（50MA）、綠區＝0…+4（買入區）、紅虛線＝+4（過度延伸）、點＝現時 ATRX。
    ★ 2026-10-24 Desmond：「加埋 ATR 帶」。"""
    try:
        v = float(atrx)
    except (TypeError, ValueError):
        return ""
    lo, hi, w, h = -3.0, 5.0, 64, 12

    def px(x):
        return (max(lo, min(hi, x)) - lo) / (hi - lo) * w

    col = ("#f97316" if v > 4 else
           ("#22c55e" if v >= 0 else "#ef4444"))
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        'style="display:block;overflow:visible">'
        f'<rect x="0" y="4" width="{w}" height="4" rx="2" '
        'fill="rgba(128,128,128,.18)"/>'
        f'<rect x="{px(0):.1f}" y="4" width="{px(4) - px(0):.1f}" height="4" '
        'fill="rgba(34,197,94,.35)"/>'
        f'<line x1="{px(4):.1f}" y1="1" x2="{px(4):.1f}" y2="11" '
        'stroke="#ef4444" stroke-width="1" stroke-dasharray="2 2"/>'
        f'<line x1="{px(0):.1f}" y1="1" x2="{px(0):.1f}" y2="11" '
        'stroke="rgba(200,200,200,.8)" stroke-width="1.2"/>'
        f'<circle cx="{px(v):.1f}" cy="6" r="2.6" fill="{col}"/>'
        '</svg>')


def _rsbar(v):
    """1M RS（0–100 百分位）迷你 bar — 跟 RS Leader 頁做法：數值＋長度。"""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return ""
    w = max(0.0, min(100.0, x))
    col = "#22c55e" if x >= 80 else ("#f59e0b" if x >= 50 else "#ef4444")
    return ('<span class="rt-rsbar"><i style="width:%.0f%%;background:%s">'
            '</i></span>' % (w, col))


def _spark(vals):
    """30 日超額回報迷你線（原本 RS 板嗰條「走勢」，唔准刪）。"""
    try:
        v = [float(x) for x in (vals or [])]
    except (TypeError, ValueError):
        return ""
    if len(v) < 2:
        return ""
    w, h = 46, 14
    mn, mx = min(v), max(v)
    rng = (mx - mn) or 1.0
    pts = " ".join(
        "%.1f,%.1f" % (i / (len(v) - 1) * w, h - (x - mn) / rng * h)
        for i, x in enumerate(v))
    col = "#22c55e" if v[-1] >= 0 else "#ef4444"
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'style="display:block"><polyline points="{pts}" fill="none" '
            f'stroke="{col}" stroke-width="1.2"/></svg>')


# ── 欄位（Desmond 2026-10-24 定案）
#   ① 只用一個 RS（唔再開 1M RS），但保留「%」同 bar
#   ② 走勢跟喺名稱後面　③ 階段放最後　④ ATR 帶 改名 EXT
#   ⑤ 預設按 RS 排　⑥ 欄頭可撳（Excel 三角）排序
#    key, 表頭, <col> class, 額外 td class, 寬度
COLS = [
    ("score",  "RS",      "c-rs",     "rt-num",     78),
    ("etf",    "代號",     "c-etf",    "rt-etf c2",  54),
    ("name",   "名稱",     "c-name",   "rt-name c3", 138),
    ("spark",  "走勢",     "c-spark",  "",           52),
    ("r1w",    "1 週",     "c-p1w",    "",           62),
    ("r1m",    "1 個月",   "c-p1m",    "",           62),
    ("r3m",    "3 個月",   "c-p3m",    "",           62),
    ("thrust", "推力",     "c-thrust", "rt-num",     44),
    ("ex1m",   "1月超額",  "c-ex1m",   "",           58),
    ("off52w", "距52高",   "c-off52",  "",           52),
    ("atrx",   "EXT",      "c-band",   "",           64),
    ("stage",  "階段",     "c-stage",  "c1",        112),
]


def _sv(v):
    """排序用原始值（JS 用 parseFloat；非數字用字串）。"""
    if v is None:
        return ""
    try:
        return f"{float(v):.4f}"
    except (TypeError, ValueError):
        return str(v)


def _cell(key, r, stages, mx, cls):
    tk = r.get("etf") or ""
    nm = r.get("name") or ""
    if key == "score":
        sc = r.get("score")
        return (f'<td class="rt-num" data-l="RS" data-v="{_sv(sc)}">'
                f'{_esc(sc) if sc is not None else "—"}%'
                f'{_rsbar(sc)}</td>')
    if key == "etf":
        return (f'<td class="rt-etf c2" data-v="{_esc(tk)}">'
                f'<a class="tv" data-sym="{_esc(tk)}" '
                f'href="https://www.tradingview.com/chart/?symbol={_esc(tk)}" '
                f'target="_blank" rel="noopener">{_esc(tk)}</a>'
                f'<span class="rt-nm2">{_esc(nm)}</span></td>')
    if key == "name":
        st = stages.get(tk) or {}
        return (f'<td class="rt-name c3" data-v="{_esc(nm)}" '
                f'title="{_esc(nm)}">{_esc(nm)}</td>')
    if key == "spark":
        sp = r.get("spark") or []
        last = sp[-1] if sp else ""
        return f'<td data-l="走勢" data-v="{_sv(last)}">{_spark(sp)}</td>'
    if key in ("r1w", "r1m", "r3m"):
        lab = {"r1w": "1週", "r1m": "1月", "r3m": "3月"}[key]
        return (f'<td class="{cls(r.get(key))}" data-l="{lab}" '
                f'data-v="{_sv(r.get(key))}">'
                f'{_f(r.get(key))}{_bar(r.get(key), mx[key])}</td>')
    if key == "thrust":
        return (f'<td class="rt-num" data-l="推力" data-v="{_sv(r.get("thrust"))}">'
                f'{_esc(r.get("thrust"))}</td>')
    if key == "ex1m":
        return (f'<td class="{cls(r.get("ex1m"))}" data-l="超額" '
                f'data-v="{_sv(r.get("ex1m"))}">{_f(r.get("ex1m"))}</td>')
    if key == "off52w":
        return (f'<td class="{cls(r.get("off52w"))}" data-l="距高" '
                f'data-v="{_sv(r.get("off52w"))}">{_f(r.get("off52w"))}</td>')
    if key == "atrx":
        return (f'<td data-l="EXT" data-v="{_sv(r.get("atrx"))}" '
                f'title="ATRX {_esc(r.get("atrx"))}">'
                f'{_band(r.get("atrx"))}</td>')
    if key == "stage":
        st = stages.get(tk) or {}
        num = (st.get("stage") or st.get("short") or " ")[:1]
        return (f'<td class="c1" data-l="階段" data-v="{_esc(num)}">'
                f'{_stage_badge(stages.get(tk))}</td>')
    return "<td></td>"


SORT_JS = """
<script>
/* Excel 式三角排序：撳欄頭切換 升序／降序（Desmond 2026-10-24 要求） */
function rtSort(th){
  var tbl = th.closest('table');
  var tb  = tbl.tBodies[0];
  var idx = [].indexOf.call(th.parentNode.children, th);
  var desc = th.getAttribute('data-dir') !== 'desc';
  [].forEach.call(th.parentNode.children, function(h){
    if (h !== th){ h.removeAttribute('data-dir'); h.classList.remove('asc','desc'); }
  });
  th.setAttribute('data-dir', desc ? 'desc' : 'asc');
  th.classList.toggle('desc', desc); th.classList.toggle('asc', !desc);
  var rows = [].slice.call(tb.rows);
  rows.sort(function(a, b){
    var ca = a.cells[idx], cb = b.cells[idx];
    if (!ca || !cb) return 0;
    var x = ca.getAttribute('data-v'), y = cb.getAttribute('data-v');
    var nx = parseFloat(x), ny = parseFloat(y);
    var r;
    if (!isNaN(nx) && !isNaN(ny)) r = nx - ny;
    else r = (x || '') < (y || '') ? -1 : ((x || '') > (y || '') ? 1 : 0);
    return desc ? -r : r;
  });
  rows.forEach(function(r){ tb.appendChild(r); });
}
</script>
"""


def _table(rows, stages, title=None, max_rows=None, sub=None,
           icon="🎯", meta=""):
    """欄序：RS｜代號｜名稱｜走勢｜1週｜1個月｜3個月｜推力｜1月超額｜距52高｜EXT｜階段
    「加新野唔准鏟舊野」—— 舊欄位全部保留，只係搬位。"""
    if not rows:
        return ""
    shown = rows[:max_rows] if max_rows else rows
    mx = {}
    for k in ("r1w", "r1m", "r3m"):
        vals = [abs(float(r[k])) for r in shown if r.get(k) is not None]
        mx[k] = max(vals) if vals else 0

    def cls(v):
        try:
            x = float(v)
        except (TypeError, ValueError):
            return "rt-flat"
        return "rt-pos" if x > 0 else ("rt-neg" if x < 0 else "rt-flat")

    out = []
    if title:
        _sub = sub or f"{len(rows)} 隻"
        out.append(
            '<div class="rt-shead">'
            f'<span class="rt-ico">{icon}</span>'
            f'<div><div class="ttl">{title}</div>'
            f'<div class="sub">{_sub}</div></div>'
            f'<div class="meta">{meta}</div>'
            '</div>')
    out.append('<table class="rt-tbl"><colgroup>')
    for _k, _h, colcls, _td, w in COLS:
        out.append(f'<col class="{colcls}" style="width:{w}px">')
    out.append('<col class="c-fill"></colgroup><thead><tr>')
    out.append("".join(
        f'<th class="sortable" onclick="rtSort(this)">{h}</th>'
        for _k, h, _c, _t, _w in COLS))
    out.append('<th></th></tr></thead><tbody>')
    for r in shown:
        out.append("<tr>" + "".join(
            _cell(k, r, stages, mx, cls) for k, _h, _c, _t, _w in COLS)
            + "<td></td></tr>")
    out.append('</tbody></table>')
    return "".join(out)

def build():
    import extras
    rb = extras.rsboard_full()
    if not rb:
        return ("RS THEME",
                f'<style>{CSS}</style><div class="rt-h"><h2>RS THEME</h2></div>'
                '<div class="dim">DATA_UNAVAILABLE（ETF OHLC 抓唔到）</div>')

    try:
        import kell
        all_tk = [r["etf"] for r in
                  (rb["index"] + rb["group"] + rb["sector"])]
        stages = kell.stages(all_tk) or {}
    except Exception:                                          # noqa: BLE001
        stages = {}

    # ① 階段 × 表現：全部 ETF 按「分」排序（截 25 行）
    merged = sorted((rb["index"] + rb["group"] + rb["sector"]),
                    key=lambda r: -(r.get("score") or -1))
    # ★ 2026-10-24：同一隻 ETF 可以同時屬「群組」同「板塊」（例：XOP 出現兩次）
    #   → 合併表按 ticker 去重，保留分數最高嗰行；名跟中文（sector 名優先）
    def _cjk(s):
        return any("\u4e00" <= ch <= "\u9fff" for ch in (s or ""))

    _seen, _ded = {}, []
    for r in merged:
        tk = r.get("etf")
        if tk in _seen:
            if not _cjk(_seen[tk].get("name")) and _cjk(r.get("name")):
                _seen[tk]["name"] = r.get("name")
            continue
        _seen[tk] = r
        _ded.append(r)
    merged = _ded
    for r in merged:
        r["_sec"] = ""

    P = [f"<style>{CSS}</style>"]
    P.append('<div class="rt-h"><h2>RS THEME</h2>'
             f'<span class="rt-sub">相對強度主題／板塊｜資料至 {_esc(rb["as_of"])}'
             f'｜SPY 1M {_f(rb.get("spy1m"))}</span></div>')
    P.append('<div class="rt-warn">⚠ 「推力率」係<b>我嘅定義</b>（Jeff Sun 原文未取得）：'
             '最近 30 個交易日之中，ETF 嘅 21 日回報贏 SPY 嘅比例。唔會扮係佢嘅數。</div>')

    # ★ 2026-10-24 Desmond：① INDEX 排第一　② 每個分類都用 RS 降序
    def _by_rs(rows):
        return sorted(rows, key=lambda r: -(r.get("score") or -1))

    _asof = _esc(rb["as_of"])

    # ① 指數 Index（排第一）
    P.append('<div class="card rt-card">')
    P.append(_table(_by_rs(rb["index"]), stages, "指數 Index", icon="📈",
                    sub=f"按 RS 排序｜{len(rb['index'])} 隻", meta=f"資料至 {_asof}"))
    P.append('</div>')

    # ② 階段 × 表現（合併、去重）
    P.append('<div class="card rt-card">')
    P.append(_table(merged, stages, "階段 × 表現", max_rows=25,
                    sub=f"按 RS 排序｜{len(merged)} 隻｜撳欄頭可切換升／降序",
                    icon="🎯", meta=f"資料至 {_asof}"))
    P.append('<div class="rt-note">'
             '<b>RS</b>＝透明加權百分位（1個月 50%／3個月 30%／1週 20%），後面色條跟數值；'
             '即係「喺呢張表嘅排名」，唔係黑箱。'
             '<b>階段</b>用 <code>kell.stages()</code>，同領導股頁同一把尺。'
             '代號可 hover 睇 TV 圖。</div>')
    P.append('</div>')

    # ③ 群組　④ 板塊
    for title, rows, ico in (("群組 Group", rb["group"], "🧩"),
                             ("板塊 Sector", rb["sector"], "🏭")):
        P.append('<div class="card rt-card">'
                 + _table(_by_rs(rows), stages, title, icon=ico,
                          sub=f"按 RS 排序｜{len(rows)} 隻", meta=f"資料至 {_asof}")
                 + '</div>')

    P.append('<div class="rt-note">'
             '<b>1 週</b>＝5 個交易日；<b>1 個月</b>＝21 日；<b>3 個月</b>＝63 日，'
             '全部價格回報（未扣息）。bar 以 0 為中線：綠＝正、紅＝負。'
             '<br><b>推力</b>＝30 日內 21 日回報贏 SPY 嘅日數比例（0–100，我嘅定義）。'
             '<b>1月超額</b>＝1 個月回報 − SPY 1 個月。'
             '<b>走勢</b>＝每日超額回報迷你線（綠＝領先、紅＝落後）。'
             '<b>距52高</b>＝距 52 週高（%）。'
             '<b>EXT</b>＝距 50MA 延伸（ATRX，−3…+5，綠區 0–4 買入區，>4 過度延伸）。'
             '<br>手機（≤900px）改成卡片式：每隻一行標籤＋數字，13 個欄位全部保留，唔會縮字。</div>')
    P.append(SORT_JS)
    return ("RS THEME", "".join(P))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    t, b = build()
    print(f"{t} — {len(b):,} chars")
    for probe in ("階段", "代號", "名稱", "分", "1 週", "1 個月", "3 個月", "rt-bar"):
        print(("OK  " if probe in b else "MISS") + f" {probe}")
