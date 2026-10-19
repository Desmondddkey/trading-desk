# -*- coding: utf-8 -*-
"""alerts_page.py — 所有 Alert 分類總覽

Desmond 2026-10-19：「我個廚房看板 將所有Alert 都做一個分類
我想完整睇到佢提示左d咩股」

資料源（只讀，唔改）：
  C:/Users/rain0/trading-os/output/setup_alerts_history.csv   89 筆
  C:/Users/rain0/trading-os/output/orh_alert_history.csv     150 筆

輸出兩部分：
  ① 分類卡：每個 setup 一個 block（幾多次、邊啲股、幾時、狀態分佈）
  ② 完整清單：全部 239 筆，最新在上

★ 誠實原則：ORH 150 筆之中 147 筆係 BLOCK_RVOL（從來冇真 fire），
  必須明確標示，唔可以當成 150 個可交易訊號。
"""
import csv
import datetime as dt
import html as _h
import io
import os
import sys

TO = r"C:\Users\rain0\trading-os\output"
SETUP_CSV = os.path.join(TO, "setup_alerts_history.csv")
ORH_CSV = os.path.join(TO, "orh_alert_history.csv")

# setup 名 → (emoji, 中文說明)
SETUP_INFO = {
    "JM":    ("📈", "Jeff Sun Momentum 延續"),
    "UCR":   ("⬆️", "UnderCut & Rally 反包"),
    "SHK":   ("💥", "Shakeout 洗盤後回升"),
    "PIV30": ("🎯", "Pivot 30 突破"),
    "YOYO":  ("🪀", "Yoyo 急跌反彈"),
    "DEP":   ("🕳", "Deep Pullback 深回調"),
    "HVE":   ("⚡", "High Volume Explosion 爆量"),
    "IAIN":  ("🌀", "Inside Day Break"),
    "OSIB":  ("📉", "OverSold Intraday Bounce"),
    "PEG":   ("🧷", "PEG 成長突破"),
    "ORH":   ("🔔", "Opening Range High 開盤高"),
}

STATUS_ZH = {
    "FIRED":          ("✅", "真 fire（可交易）", "#16a34a"),
    "REJECTED_CHASE": ("⛔", "被 CHASE 閘剔走", "#dc2626"),
    "BLOCK_RVOL":     ("🚫", "被 RVOL 閘擋", "#ea580c"),
    "BLOCK_CHASE":    ("⛔", "被 CHASE 閘擋", "#dc2626"),
    "SUSTAIN_PENDING":("⏳", "等確認", "#f59e0b"),
    "":               ("·", "未標記", "#64748b"),
}

CSS = """
.al-h{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;
  margin:0 0 6px;font-size:15px;font-weight:800}
.al-h small{font-size:11.5px;font-weight:600;opacity:.55}
.al-note{font-size:12px;opacity:.72;margin:0 0 14px;line-height:1.6}
.al-grid{display:grid;gap:11px;grid-template-columns:repeat(auto-fit,
  minmax(260px,1fr));margin:0 0 22px}
.al-card{border:1px solid rgba(128,128,128,.26);border-radius:12px;
  padding:12px 14px;background:rgba(128,128,128,.05)}
.al-top{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;
  margin:0 0 7px}
.al-name{font-size:14px;font-weight:800}
.al-cnt{font-size:11.5px;font-weight:700;padding:2px 8px;border-radius:999px;
  border:1px solid currentColor;opacity:.9}
.al-desc{font-size:11px;opacity:.6;margin:0 0 8px}
.al-tk{display:flex;flex-wrap:wrap;gap:5px}
.al-tk span{font-size:11.5px;font-family:ui-monospace,monospace;
  padding:2px 7px;border-radius:5px;background:rgba(128,128,128,.16);
  font-weight:700}
.al-tk span b{font-weight:800}
.al-st{font-size:11px;opacity:.75;margin-top:8px;line-height:1.7}
.al-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
.al-tbl th{text-align:left;font-size:10.5px;letter-spacing:.05em;
  text-transform:uppercase;opacity:.55;padding:6px 8px;font-weight:700;
  border-bottom:1px solid rgba(128,128,128,.28)}
.al-tbl td{padding:6px 8px;border-bottom:1px solid rgba(128,128,128,.1);
  text-align:left!important;white-space:nowrap}
.al-tbl tr:hover{background:rgba(128,128,128,.06)}
.al-fold{margin:0 0 18px}
.al-fold>summary{font-size:14px;font-weight:800;cursor:pointer;
  padding:9px 0;list-style:none}
.al-fold>summary::-webkit-details-marker{display:none}
.al-fold>summary::before{content:"▸ ";font-size:10px;opacity:.55}
.al-fold[open]>summary::before{content:"▾ "}
@media(max-width:700px){
  .al-tbl thead{display:none}
  .al-tbl,.al-tbl tbody,.al-tbl tr{display:block;width:100%}
  .al-tbl tr{padding:8px 0;border-bottom:1px solid rgba(128,128,128,.16)}
  .al-tbl td{display:block;width:auto;border:0;padding:0;
    white-space:normal;text-align:left!important}
  .al-tbl td:nth-child(1){display:inline;font-size:11px;opacity:.6}
  .al-tbl td:nth-child(2){display:inline;margin-left:7px;font-weight:800}
  .al-tbl td:nth-child(3){display:inline;margin-left:7px;font-size:11.5px}
  .al-tbl td:nth-child(4){display:inline;margin-left:7px;font-size:11px;
    opacity:.65}
  .al-tbl td:nth-child(5){margin-top:2px;font-size:11px;opacity:.75}
}
"""


def _esc(v):
    return _h.escape(str(v)) if v not in (None, "") else ""


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def load():
    rows = []
    if os.path.exists(SETUP_CSV):
        try:
            for r in csv.DictReader(io.open(SETUP_CSV, encoding="utf-8-sig")):
                rows.append(dict(
                    kind="setup", day=(r.get("day") or "").strip(),
                    ticker=(r.get("ticker") or "").strip().upper(),
                    setup=(r.get("setup") or "").strip().upper(),
                    px=_f(r.get("px")), rvol=_f(r.get("rvol")),
                    status=(r.get("status") or "").strip(),
                    outcome=(r.get("outcome") or "").strip(),
                    t3=r.get("t3_r") or "", t10=r.get("t10_r") or "",
                    fire=(r.get("fire_et") or "").strip()))
        except OSError:
            pass
    if os.path.exists(ORH_CSV):
        try:
            for r in csv.DictReader(io.open(ORH_CSV, encoding="utf-8-sig")):
                rows.append(dict(
                    kind="orh", day=(r.get("day") or "").strip(),
                    ticker=(r.get("ticker") or "").strip().upper(),
                    setup="ORH", px=_f(r.get("px")),
                    rvol=_f(r.get("rvol")),
                    status=(r.get("status") or "").strip(),
                    outcome="", t3="", t10="",
                    fire=(r.get("fire_et") or "").strip()))
        except OSError:
            pass
    rows.sort(key=lambda r: (r["day"], r["fire"]), reverse=True)
    return rows


def _cards(rows):
    by = {}
    for r in rows:
        by.setdefault(r["setup"], []).append(r)
    out = ['<div class="al-grid">']
    for s in sorted(by, key=lambda k: (-len(by[k]), k)):
        rs = by[s]
        ic, desc = SETUP_INFO.get(s, ("•", s))
        tk = {}
        for r in rs:
            tk[r["ticker"]] = tk.get(r["ticker"], 0) + 1
        st = {}
        for r in rs:
            st[r["status"]] = st.get(r["status"], 0) + 1
        days = sorted({r["day"] for r in rs if r["day"]})
        chips = "".join(
            f'<span><b>{_esc(t)}</b>{f"×{n}" if n > 1 else ""}</span>'
            for t, n in sorted(tk.items(), key=lambda kv: (-kv[1], kv[0])))
        stl = "　".join(
            f'{st.get(k, 0)}× {STATUS_ZH.get(k, ("·", k, "#647"))[1]}'
            for k in sorted(st, key=lambda k: -st[k]))
        out.append(
            f'<div class="al-card">'
            f'<div class="al-top"><span class="al-name">{ic} {_esc(s)}</span>'
            f'<span class="al-cnt" style="color:#d97757">{len(rs)} 次</span>'
            f'<span style="font-size:11px;opacity:.55">'
            f'{len(tk)} 隻股</span></div>'
            f'<div class="al-desc">{_esc(desc)}</div>'
            f'<div class="al-tk">{chips}</div>'
            f'<div class="al-st">{_esc(stl)}'
            + (f'<br><span style="opacity:.55">'
               f'{days[0]} → {days[-1]}</span>' if days else "")
            + '</div></div>')
    out.append('</div>')
    return "".join(out)


def _table(rows, limit=None):
    rs = rows[:limit] if limit else rows
    out = ['<table class="al-tbl"><thead><tr>'
           '<th style="width:86px">日期</th>'
           '<th style="width:74px">代號</th>'
           '<th style="width:70px">Setup</th>'
           '<th style="width:66px">價</th>'
           '<th>狀態 / 備註</th></tr></thead><tbody>']
    for r in rs:
        ic, zt, zc = STATUS_ZH.get(r["status"], ("·", r["status"] or "—",
                                                 "#64748b"))
        note = f'{ic} {zt}'
        if r.get("rvol"):
            note += f'｜RVOL {r["rvol"]:.2f}'
        if r.get("outcome"):
            note += f'｜{_esc(r["outcome"])}'
        if r.get("t3") not in ("", None):
            note += f'｜T3 {_esc(r["t3"])}R'
        out.append(
            f'<tr><td>{_esc(r["day"])}</td>'
            f'<td><b>{_esc(r["ticker"])}</b></td>'
            f'<td>{_esc(r["setup"])}</td>'
            f'<td>{r["px"]:.2f}</td>'
            f'<td style="color:{zc}">{note}</td></tr>')
    out.append('</tbody></table>')
    return "".join(out)


def build():
    rows = load()
    if not rows:
        return ("ALERTS", '<div class="card"><div class="body">'
                '⛔ DATA_UNAVAILABLE：搵唔到 alert history CSV</div></div>')
    n_setup = sum(1 for r in rows if r["kind"] == "setup")
    n_orh = sum(1 for r in rows if r["kind"] == "orh")
    n_fire = sum(1 for r in rows if r["status"] == "FIRED")
    parts = [f"<style>{CSS}</style>",
             '<h2>ALERTS <small>所有警報分類</small></h2>',
             f'<p class="al-note">共 <b>{len(rows)}</b> 筆 — '
             f'setup 警報 <b>{n_setup}</b>｜ORH 警報 <b>{n_orh}</b>'
             f'｜真正 fire <b>{n_fire}</b>。'
             '<br>⚠️ ORH 150 筆之中 <b>147 筆係 BLOCK_RVOL</b>'
             '（RVOL 閘擋住，從來冇真正 fire）—— 唔可以當 150 個可交易訊號。'
             '<br>來源 <code>trading-os/output/setup_alerts_history.csv</code>'
             ' ＋ <code>orh_alert_history.csv</code>（只讀）</p>',
             '<div class="al-h">📊 按 Setup 分類<small>'
             '每張卡＝一個 setup 提過邊啲股</small></div>',
             _cards(rows),
             '<div class="al-h">📋 完整清單<small>最新在上</small></div>',
             _table(rows)]
    return ("ALERTS", "".join(parts))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    rows = load()
    print("總筆數:", len(rows))
    by = {}
    for r in rows:
        by.setdefault(r["setup"], []).append(r["ticker"])
    for s in sorted(by, key=lambda k: -len(by[k])):
        tk = sorted(set(by[s]))
        print(f"  {s:<7}{len(by[s]):>4} 次  {len(tk):>2} 隻: "
              f"{', '.join(tk[:12])}")
