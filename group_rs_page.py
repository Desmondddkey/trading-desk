# -*- coding: utf-8 -*-
"""group_rs_page.py — 群組 RS 新高家數（MARKET REGIME 頁內區塊）

Desmond 2026-10-23
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Jeff Sun：「加強廣度必須同行業群組達到新一個月 RS 高位嘅數量增加一齊進行」

呢個區塊量化咗呢條規則：
  ① 14+ 個行業群組，每個計 21 日 RS（相對大市）
  ② 數「創 20 日新高」嘅群組家數
  ③ 出趨勢線，對照 MMTW

判讀（寫死，唔准事後改）：
  創新高家數 ≥ 30% 且上升  → 領導擴闊，可以開始做
  創新高家數 < 15%          → 領導收窄，唔好加倉
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "trading-os", "output")


def load():
    """搵最新 group_rs_*.json"""
    import glob
    files = []
    for f in glob.glob(os.path.join(OUT, "group_rs_20*.json")):
        b = os.path.basename(f)
        # 只接受 group_rs_YYYY-MM-DD.json
        tail = b.replace("group_rs_", "").replace(".json", "")
        if len(tail) == 10 and tail[4] == "-":
            files.append(f)
    if not files:
        return None
    files.sort()
    try:
        return json.load(io.open(files[-1], encoding="utf-8"))
    except Exception:                                     # noqa: BLE001
        return None


def _spark(hist, w=320, h=54):
    """歷史家數趨勢線（純 SVG）"""
    if not hist or len(hist) < 2:
        return ""
    vals = [h["count"] for h in hist]
    tot = hist[-1].get("total") or 1
    mx = max(max(vals), 1)
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = 2 + i / (n - 1) * (w - 4)
        y = h - 4 - (v / mx) * (h - 10)
        pts.append(f"{x:.1f},{y:.1f}")
    # 30% 警戒線
    y30 = h - 4 - (tot * 0.3 / mx) * (h - 10)
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'xmlns="http://www.w3.org/2000/svg" style="max-width:100%">'
            f'<line x1="0" y1="{y30:.1f}" x2="{w}" y2="{y30:.1f}" '
            f'stroke="#f59e0b" stroke-width="1" stroke-dasharray="3 3" opacity=".55"/>'
            f'<polyline points="{" ".join(pts)}" fill="none" '
            f'stroke="#38bdf8" stroke-width="1.8"/>'
            f'<circle cx="{pts[-1].split(",")[0]}" cy="{pts[-1].split(",")[1]}" '
            f'r="2.6" fill="#38bdf8"/>'
            f'</svg>')


def _potential(group, limit=3):
    """由 Daily Scan（L2 focus/stalk）搵出行業＝呢個群組嘅股。"""
    import glob
    if not group:
        return '<span style="opacity:.3">—</span>'
    try:
        ind = {str(k).upper(): (v.get("industry") or "")
               for k, v in json.load(io.open(
                   os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "data", "tv_meta.json"), encoding="utf-8")).items()}
    except Exception:                                         # noqa: BLE001
        ind = {}
    rows = []
    fs = sorted(glob.glob(r"C:/Users/rain0/trading-os/output/layer2_*.json"))
    if fs:
        try:
            d = json.load(io.open(fs[-1], encoding="utf-8"))
            rows = (d.get("focus_list") or []) + (d.get("stalk_list") or [])
        except Exception:                                     # noqa: BLE001
            rows = []
    gl = group.strip().lower()
    hits = [(r.get("ticker") or "").upper() for r in rows
            if (ind.get((r.get("ticker") or "").upper()) or "").strip().lower() == gl]
    if not hits:
        return '<span style="opacity:.3">—</span>'
    return " ".join(
        f'<a class="tv" data-sym="{h}" href="https://www.tradingview.com/chart/?symbol={h}" '
        f'target="_blank" rel="noopener" style="color:#f97316;font-weight:700;'
        f'text-decoration:none;margin-right:6px">{h}</a>' for h in hits[:limit])


def card():
    """回傳 HTML 區塊（冇數據就回空字串，唔會扮有）"""
    d = load()
    if not d:
        return ""

    cnt = d.get("new_high_count", 0)
    tot = d.get("groups_total", 0)
    pct = d.get("new_high_pct", 0)
    prev = d.get("prev20_count")
    trend = d.get("trend", "—")

    # 判讀（寫死）
    if pct >= 30 and trend == "擴闊":
        verdict, vcol = "領導擴闊 — 可以開始做", "#16a34a"
    elif pct >= 30:
        verdict, vcol = "廣度夠但未擴闊 — 觀察", "#f59e0b"
    elif pct >= 15:
        verdict, vcol = "領導中性 — 只做最強", "#f59e0b"
    else:
        verdict, vcol = "領導收窄 — 唔好加倉", "#dc2626"

    rows = d.get("rows") or []
    top = rows[:8]
    bot = rows[-5:] if len(rows) > 8 else []

    L = ['<div class="card" style="margin-top:14px">']
    L.append('<h2>RS GROUP MOVE '
             f'<small>{d.get("benchmark", "等權")} 基準'
             f'｜{d.get("lookback", 21)} 日 RS｜{d.get("date", "")}</small></h2>')
    L.append('<div class="body">')

    # KPI
    L.append('<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">')
    for val, lab, col in (
            (f"{cnt} / {tot}", "創新高群組", vcol),
            (f"{pct:.1f}%", "佔比", vcol),
            (f"{prev}" if prev is not None else "—", "20 日前", "#94a3b8"),
            (trend, "趨勢",
             "#16a34a" if trend == "擴闊" else
             "#dc2626" if trend == "收窄" else "#94a3b8")):
        L.append(f'<div style="flex:1 1 110px;padding:10px 12px;border-radius:10px;'
                 f'border:1px solid rgba(128,128,128,.26);'
                 f'background:rgba(128,128,128,.05)">'
                 f'<div style="font-size:20px;font-weight:800;color:{col}">{val}</div>'
                 f'<div style="font-size:10.5px;opacity:.65;margin-top:2px">{lab}</div>'
                 f'</div>')
    L.append('</div>')

    # 趨勢線
    hist = d.get("history") or []
    if hist:
        L.append('<div style="margin:4px 0 6px">' + _spark(hist) + '</div>')
        L.append('<div style="font-size:10.5px;opacity:.6;margin-bottom:12px">'
                 '藍線＝創新高群組家數（近 90 個交易日）｜'
                 '橙色虛線＝30% 警戒線（上面 = 領導擴闊）</div>')

    # 判讀
    L.append(f'<div style="font-size:12.5px;line-height:1.75;margin-bottom:14px">'
             f'<b style="color:{vcol}">{verdict}</b><br>'
             '<span style="opacity:.8">'
             'Jeff Sun 規則：廣度改善 + 群組創新高家數增加 = 真輪動；'
             '只有廣度升而群組冇擴大 = 弱勢股反彈。</span></div>')

    # 強弱表
    if top:
        L.append('<div style="overflow-x:auto"><table class="eh-t" '
                 'style="width:100%;border-collapse:collapse;font-size:12.5px">'
                 '<thead><tr><th style="text-align:left">群組</th>'
                 '<th style="text-align:right">21日 RS</th>'
                 '<th style="text-align:right">成員</th>'
                 '<th style="text-align:right">新高</th>'
                 '<th style="text-align:left">Potential Stock</th>'
                 '</tr></thead><tbody>')
        for r in top + ([{"_sep": True}] if bot else []) + bot:
            if r.get("_sep"):
                L.append('<tr><td colspan="5" style="padding:4px;'
                         'border-bottom:1px solid rgba(128,128,128,.25);'
                         'font-size:10px;opacity:.5">—— 最弱 ——</td></tr>')
                continue
            rs = r.get("rs") or 0
            col = "#16a34a" if rs > 0 else "#dc2626"
            _pot = _potential(r.get("group"))
            nh = ('<span style="color:#f59e0b;font-weight:700">★</span>'
                  if r.get("new_high") else "—")
            L.append(f'<tr><td style="text-align:left">{r.get("group","")}</td>'
                     f'<td style="text-align:right;color:{col}">{rs:+.3f}</td>'
                     f'<td style="text-align:right">{r.get("n",0)}</td>'
                     f'<td style="text-align:right">{nh}</td>'
                     f'<td style="text-align:left">{_pot}</td></tr>')
        L.append('</tbody></table></div>')

    L.append('<div style="font-size:10.5px;opacity:.55;margin-top:10px;line-height:1.7">'
             '<b>計法</b>：每隻股 21 日回報 → 行業群組平均 → 減基準回報 = 群組 RS。'
             '「新高」＝今日 RS > 過去 20 日最大。<br>'
             '<b>來源</b>：Jeff Sun「情境意識」帖（2026-10-23）——'
             '「加強廣度必須同行業群組達到新一個月 RS 高位嘅數量增加一齊進行」。'
             '</div>')
    L.append('</div></div>')
    return "".join(L)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    h = card()
    print(f"group_rs card: {len(h)//1024} KB" if h else "冇數據")
