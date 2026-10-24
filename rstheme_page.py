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
.rt-sub{font-size:11.5px;opacity:.62}
.rt-card{margin:10px 0}
.rt-card h3{margin:0 0 4px;font-size:14px;font-weight:800;
  display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
.rt-card h3 small{font-weight:400;font-size:11px;opacity:.6}
.rt-tbl{width:100%;max-width:1040px;border-collapse:collapse;font-size:12px;
  table-layout:fixed;font-variant-numeric:tabular-nums}
.rt-tbl th{text-align:left;font-size:10px;font-weight:700;letter-spacing:.04em;
  padding:4px 5px;opacity:.6;border-bottom:1px solid rgba(128,128,128,.3);
  white-space:nowrap}
.rt-tbl td{padding:3px 5px;border-bottom:1px solid rgba(128,128,128,.1);
  text-align:left;vertical-align:middle;line-height:1.25;overflow:hidden}
.rt-tbl tr:hover td{background:rgba(249,115,22,.055)}
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
.rt-tbl col.c-pct{width:44px}
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
.rt-bar{display:inline-block;width:40px;height:6px;border-radius:3px;
  background:rgba(128,128,128,.16);vertical-align:middle;margin-left:5px;
  position:relative;overflow:hidden}
.rt-bar>i{position:absolute;top:0;bottom:0;border-radius:3px;display:block}
.rt-note{font-size:11px;opacity:.6;line-height:1.65;margin-top:8px}
.rt-warn{font-size:11.5px;line-height:1.6;padding:7px 10px;border-radius:8px;
  background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.35);
  margin:0 0 8px}
@media(max-width:760px){
  .rt-bar{display:none}
  .rt-st-full{display:none}
  .rt-st-abbr{display:inline}
  .rt-tbl col.c-stage{width:46px}
  /* 12 欄太闊 → 手機隱藏「走勢」同「名稱」兩欄；名稱改喺代號下面一行顯示 */
  .rt-tbl th:nth-child(10),.rt-tbl td:nth-child(10),
  .rt-tbl th:nth-child(3),.rt-tbl td:nth-child(3){display:none}
  .rt-nm2{display:block;font-size:9.5px;opacity:.6;font-weight:400;
    max-width:88px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .rt-tbl{font-size:11px}
  .rt-tbl th,.rt-tbl td{padding:3px 3px}
  .rt-tbl col.c-stage{width:58px}
  .rt-tbl col.c-etf{width:46px}
  .rt-tbl col.c-score{width:34px}
  .rt-tbl col.c-p1w{width:60px}
  .rt-tbl col.c-p1m{width:64px}
  .rt-tbl col.c-p3m{width:64px}
  .rt-stage{font-size:9px;padding:0 4px}
}
@media(max-width:480px){
  /* 手機最窄：8 欄，全部數字都睇到（只收起 推力／RS%）*/
  .rt-tbl{font-size:10px}
  .rt-tbl th:nth-child(8),.rt-tbl td:nth-child(8),
  .rt-tbl th:nth-child(11),.rt-tbl td:nth-child(11){display:none}
  .rt-tbl col.c-stage{width:44px}
  .rt-tbl col.c-etf{width:42px}
  .rt-tbl col.c-score{width:28px}
  .rt-tbl col.c-p1w{width:48px}
  .rt-tbl col.c-p1m{width:52px}
  .rt-tbl col.c-p3m{width:52px}
  .rt-tbl col.c-ex1m{width:46px}
  .rt-tbl col.c-off52{width:42px}
  .rt-tbl th,.rt-tbl td{padding:2px}
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


def _table(rows, stages, title=None, max_rows=None):
    """★ 2026-10-24 修：Desmond「我叫你加新野，唔係連舊野都鏟走埋」
    → 新舊並存：階段/分/1週/1個月/3個月（新）＋
      推力率/1月超額/走勢/RS%/距52高（原本，全部保留）。"""
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
        out.append(f'<h3>{title} <small>{len(rows)} 隻</small></h3>')
    out.append('<table class="rt-tbl"><colgroup>'
               '<col class="c-stage"><col class="c-etf"><col class="c-name">'
               '<col class="c-score"><col class="c-p1w"><col class="c-p1m">'
               '<col class="c-p3m"><col class="c-thrust"><col class="c-ex1m">'
               '<col class="c-spark"><col class="c-pct"><col class="c-off52">'
               '<col class="c-fill">'
               '</colgroup><thead><tr>'
               '<th>階段</th><th>代號</th><th>名稱</th><th>RS</th>'
               '<th>1 週</th><th>1 個月</th><th>3 個月</th>'
               '<th>推力</th><th>1月超額</th><th>走勢</th>'
               '<th>RS%</th><th>距52高</th><th></th>'
               '</tr></thead><tbody>')
    for r in shown:
        tk = r.get("etf") or ""
        nm = r.get("name") or ""
        out.append(
            '<tr>'
            f'<td>{_stage_badge(stages.get(tk))}</td>'
            f'<td class="rt-etf"><a class="tv" data-sym="{_esc(tk)}" '
            f'href="https://www.tradingview.com/chart/?symbol={_esc(tk)}" '
            f'target="_blank" rel="noopener">{_esc(tk)}</a>'
            f'<span class="rt-nm2">{_esc(nm)}</span></td>'
            f'<td class="rt-name" title="{_esc(nm)}">{_esc(nm)}</td>'
            f'<td class="rt-num">'
            f'{_esc(r.get("score")) if r.get("score") is not None else "—"}</td>'
            f'<td class="{cls(r.get("r1w"))}">{_f(r.get("r1w"))}'
            f'{_bar(r.get("r1w"), mx["r1w"])}</td>'
            f'<td class="{cls(r.get("r1m"))}">{_f(r.get("r1m"))}'
            f'{_bar(r.get("r1m"), mx["r1m"])}</td>'
            f'<td class="{cls(r.get("r3m"))}">{_f(r.get("r3m"))}'
            f'{_bar(r.get("r3m"), mx["r3m"])}</td>'
            f'<td class="rt-num">{_esc(r.get("thrust"))}</td>'
            f'<td class="{cls(r.get("ex1m"))}">{_f(r.get("ex1m"))}</td>'
            f'<td>{_spark(r.get("spark"))}</td>'
            f'<td class="rt-num">{_esc(r.get("pct"))}</td>'
            f'<td class="{cls(r.get("off52w"))}">{_f(r.get("off52w"))}</td>'
            '<td></td>'
            '</tr>')
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
    for r in merged:
        r["_sec"] = ""

    P = [f"<style>{CSS}</style>"]
    P.append('<div class="rt-h"><h2>RS THEME</h2>'
             f'<span class="rt-sub">相對強度主題／板塊｜資料至 {_esc(rb["as_of"])}'
             f'｜SPY 1M {_f(rb.get("spy1m"))}</span></div>')
    P.append('<div class="rt-warn">⚠ 「推力率」係<b>我嘅定義</b>（Jeff Sun 原文未取得）：'
             '最近 30 個交易日之中，ETF 嘅 21 日回報贏 SPY 嘅比例。唔會扮係佢嘅數。</div>')

    P.append('<div class="card rt-card">')
    P.append(_table(merged, stages, "階段 × 表現（按 RS 排序）", max_rows=25))
    P.append('<div class="rt-note">'
             '<b>RS</b>＝透明加權百分位（1個月 50%／3個月 30%／1週 20%），'
             '即係「喺呢張表嘅排名」，唔係黑箱。'
             '<b>階段</b>用 <code>kell.stages()</code>，同領導股頁同一把尺。'
             '代號可 hover 睇 TV 圖。</div>')
    P.append('</div>')

    for title, rows in (("指數 Index", rb["index"]),
                        ("群組 Group", rb["group"]),
                        ("板塊 Sector", rb["sector"])):
        P.append(f'<div class="card rt-card">{_table(rows, stages, title)}</div>')

    P.append('<div class="rt-note">'
             '<b>1 週</b>＝5 個交易日；<b>1 個月</b>＝21 日；<b>3 個月</b>＝63 日，'
             '全部價格回報（未扣息）。bar 以 0 為中線：綠＝正、紅＝負。'
             '<br><b>推力</b>＝30 日內 21 日回報贏 SPY 嘅日數比例（0–100，我嘅定義）。'
             '<b>1月超額</b>＝1 個月回報 − SPY 1 個月。'
             '<b>走勢</b>＝每日超額回報迷你線（綠＝領先、紅＝落後）。'
             '<b>RS%</b>＝1 月超額喺本表嘅百分位。'
             '<b>距52高</b>＝距 52 週高（%）。'
             '<br>手機（≤760px）會收起「名稱」同「走勢」兩欄，名稱改喺代號下面一行；'
             '其餘數字全部保留。</div>')
    return ("RS THEME", "".join(P))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    t, b = build()
    print(f"{t} — {len(b):,} chars")
    for probe in ("階段", "代號", "名稱", "分", "1 週", "1 個月", "3 個月", "rt-bar"):
        print(("OK  " if probe in b else "MISS") + f" {probe}")
