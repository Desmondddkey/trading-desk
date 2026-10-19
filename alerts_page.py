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

# setup 名 → dict（全名 / 中文 / 分類 / 用法 / 止蝕 / emoji）
# ★ 2026-10-19 Desmond：滑鼠移過去顯示方格詳情 + Full name；
#   分一分邊啲係 PULLBACK；講每個 setup 點用；JM 改做 M.E.T.A
CAT_ORDER = ["PULLBACK", "BREAKOUT", "REVERSAL", "MOMENTUM"]
CAT_INFO = {
    "PULLBACK": ("📉", "回調買入 — 等股票跌到支撐再買，唔追高"),
    "BREAKOUT": ("🚀", "突破買入 — 等價格衝穿阻力"),
    "REVERSAL": ("🔄", "反轉買入 — 恐慌／假跌破之後買反彈"),
    "MOMENTUM": ("📈", "動能延續 — 已經行緊，順勢加"),
}

SETUP_INFO = {
    "UCR": dict(
        full="UnderCut & Rally",
        zh="下探回升",
        cat="REVERSAL",
        src="Martin Luk",
        how="開盤先跌破昨日低位或 ORL（Undercut），造出假突破殺止蝕，"
            "15 分鐘內 1 分鐘收市價重新站回被跌破嗰個位。等「收回」買。",
        stop="插針低位（當日 Low of Day）",
        emoji="⬆️"),
    "YOYO": dict(
        full="Yo-yo Ball",
        zh="溜溜球",
        cat="REVERSAL",
        src="1chartmaster",
        how="連續 ≥2 個 V 型腳（跌 ≥0.4 ATR、10 分鐘內收回 ≥90%、低點逐步抬高），"
            "突破整個 cluster 高位就買。★ 呢個係震盪型，唔係回調型。",
        stop="插針低位",
        emoji="🪀"),
    "DEP": dict(
        full="Delayed Entry Point",
        zh="延遲入場點",
        cat="PULLBACK",
        src="Jeff Sun 系",
        how="股票已經升咗一輪，回調到支撐（ATR 距離足夠）先入。"
            "唔喺第一日追，等回調確認。",
        stop="Low of Day，距入場 ≤0.60 ATR",
        emoji="🕳"),
    "IAIN": dict(
        full="Weekly 9EMA + LTF Confirm",
        zh="週線 9EMA ＋ 低時框確認",
        cat="PULLBACK",
        src="iain",
        how="股價回到週線 9EMA 附近，再用日內（低時框）出現確認信號才入。",
        stop="當日低位，用 ATR 計風險",
        emoji="🌀"),
    "PIV30": dict(
        full="30-Minute Pivot",
        zh="30 分鐘樞紐",
        cat="BREAKOUT",
        src="1chartmaster",
        how="開市頭 30 分鐘形成高低區間；第 31 分鐘之後衝穿高位就買。",
        stop="30 分鐘區間低位",
        emoji="🎯"),
    "HVE": dict(
        full="High Volume Explosion",
        zh="史上最高量",
        cat="BREAKOUT",
        src="Omar / 1chartmaster",
        how="成交量創歷史新高（milestone volume）＋ 新鮮度 ＋ RVOL 確認。"
            "代表有大戶入場。",
        stop="當日低位",
        emoji="⚡"),
    "ORH": dict(
        full="Opening Range High",
        zh="開盤區間高位",
        cat="BREAKOUT",
        src="我方主策略",
        how="開市後形成開盤區間，價格衝穿區間高位 + RVOL 達標才 fire。",
        stop="Low of Day，距入場 ≤0.60 ATR",
        emoji="🔔"),
    "SHK": dict(
        full="Shakeout",
        zh="假跌破概率疊加",
        cat="REVERSAL",
        src="多方方法疊加",
        how="價格跌穿明顯支撐（製造恐慌）但即刻收回，"
            "多個「假跌破」條件同時成立才買。",
        stop="假跌破最低點",
        emoji="💥"),
    "OSIB": dict(
        full="Oversold Intraday Bounce",
        zh="超賣板塊日內反彈",
        cat="REVERSAL",
        src="Jeff Sun 認可",
        how="板塊極度超賣（距 20 日高），日內出現錘子（開≈低）就博反彈。",
        stop="當日低位",
        emoji="📉"),
    "PEG": dict(
        full="PEG Delayed Reaction Breakout",
        zh="PEG 延遲反應突破",
        cat="BREAKOUT",
        src="Jeff Sun",
        how="爆量事件日（PEG）→ 之後多週淡出 → 收窄 → 回升到 2 個月高位正下方；"
            "開市頭 30 分鐘跌穿前一日高位（RVOL ≥20%）就入。",
        stop="當日低位",
        emoji="🧷"),
    "M.E.T.A": dict(
        full="M.E.T.A — Multiple Edge Territory Accumulation",
        zh="多重邊際區（原 JM）",
        cat="MOMENTUM",
        src="J Law",
        how="數「邊際優勢」數量（0–6 個條件同時成立）："
            "趨勢、相對強度、量能、結構、延伸度、大市。"
            "越多邊際同時出現，勝率越高。",
        stop="當日低位",
        emoji="🎖"),
}
# 舊代號 → 新代號（CSV 仍然寫 JM）
ALIAS = {"JM": "M.E.T.A"}


def info(key):
    k = ALIAS.get(key, key)
    return SETUP_INFO.get(k) or dict(
        full=k, zh=k, cat="MOMENTUM", src="—", how="—", stop="—", emoji="•")

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
/* ★ 分類標題 */
.al-cat{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;
  margin:20px 0 9px;padding:8px 12px;border-radius:9px;
  background:rgba(217,119,87,.09);border-left:3px solid #d97757}
.al-catn{font-size:13.5px;font-weight:800;letter-spacing:.03em}
.al-catd{font-size:11.5px;opacity:.68}
.al-catc{margin-left:auto;font-size:11.5px;font-weight:700;opacity:.65}
/* ★ Hover 詳情方格 */
.al-hasTip{position:relative}
.al-tip{display:none;position:absolute;z-index:50;left:0;top:calc(100% + 6px);
  width:min(340px,86vw);padding:12px 14px;border-radius:11px;
  background:#1b1b19;border:1px solid #4A4A42;box-shadow:0 10px 28px rgba(0,0,0,.5);
  font-size:12px;line-height:1.65;color:#F0EDE8;text-align:left;
  white-space:normal;word-break:break-word}
html[data-theme="light"] .al-tip{background:#FFFFFF;border-color:#DAD9D4;
  color:#1F1E1D;box-shadow:0 10px 28px rgba(0,0,0,.14)}
.al-hasTip:hover .al-tip,.al-hasTip:focus-within .al-tip{display:block}
.al-tip>b{font-size:13px;font-weight:800;display:block;margin-bottom:3px}
.al-tipzh{font-size:11.5px;opacity:.75;margin-bottom:7px}
.al-tipcat{font-size:10px;font-weight:800;padding:1px 7px;border-radius:999px;
  border:1px solid currentColor;margin-left:7px;opacity:.9}
.al-tiprow{margin-top:5px;font-size:11.5px}
.al-tiprow b{opacity:.7;font-weight:700}
@media(hover:none){.al-hasTip:active .al-tip{display:block}}
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
        k = ALIAS.get(r["setup"], r["setup"])
        by.setdefault(k, []).append(r)
    # 按分類分組：PULLBACK → BREAKOUT → REVERSAL → MOMENTUM
    groups = {}
    for s, rs in by.items():
        groups.setdefault(info(s)["cat"], []).append((s, rs))
    out = []
    for cat in CAT_ORDER:
        if cat not in groups:
            continue
        ci, cdesc = CAT_INFO[cat]
        n = sum(len(x[1]) for x in groups[cat])
        out.append(
            f'<div class="al-cat"><span class="al-catn">{ci} {cat}</span>'
            f'<span class="al-catd">{_esc(cdesc)}</span>'
            f'<span class="al-catc">{n} 次</span></div>')
        out.append('<div class="al-grid">')
        for s, rs in sorted(groups[cat], key=lambda kv: -len(kv[1])):
            d = info(s)
            tk = {}
            for r in rs:
                tk[r["ticker"]] = tk.get(r["ticker"], 0) + 1
            st = {}
            for r in rs:
                st[r["status"]] = st.get(r["status"], 0) + 1
            days = sorted({r["day"] for r in rs if r["day"]})
            chips = "".join(
                f'<span><b>{_esc(t)}</b>{f"×{n2}" if n2 > 1 else ""}</span>'
                for t, n2 in sorted(tk.items(), key=lambda kv: (-kv[1], kv[0])))
            stl = "　".join(
                f'{st.get(k, 0)}× {STATUS_ZH.get(k, ("·", k, "#647"))[1]}'
                for k in sorted(st, key=lambda k: -st[k]))
            tip = (f'<div class="al-tip">'
                   f'<b>{_esc(d["full"])}</b>'
                   f'<div class="al-tipzh">{_esc(d["zh"])}'
                   f'<span class="al-tipcat">{_esc(d["cat"])}</span></div>'
                   f'<div class="al-tiprow"><b>點用：</b>{_esc(d["how"])}</div>'
                   f'<div class="al-tiprow"><b>止蝕：</b>{_esc(d["stop"])}</div>'
                   f'<div class="al-tiprow" style="opacity:.6">'
                   f'來源 {_esc(d["src"])}</div></div>')
            out.append(
                f'<div class="al-card al-hasTip">'
                f'<div class="al-top"><span class="al-name">{d["emoji"]} '
                f'{_esc(s)}</span>'
                f'<span class="al-cnt" style="color:#d97757">{len(rs)} 次</span>'
                f'<span style="font-size:11px;opacity:.55">'
                f'{len(tk)} 隻股</span></div>'
                f'<div class="al-desc">{_esc(d["full"])}</div>'
                f'<div class="al-tk">{chips}</div>'
                f'<div class="al-st">{_esc(stl)}'
                + (f'<br><span style="opacity:.55">'
                   f'{days[0]} → {days[-1]}</span>' if days else "")
                + '</div>' + tip + '</div>')
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
            f'<td>{_esc(ALIAS.get(r["setup"], r["setup"]))}</td>'
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
