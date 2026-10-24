# -*- coding: utf-8 -*-
"""process_page.py — 每日流程（Jeff Sun 版）

Desmond 2026-10-24：
  「我想執到好似 Jeff 咁每日做一個流程 俾我充分了解當前嘅情況
   之後我就可以 9:30 去 ready」

Jeff Sun 嘅流程 = 一個決策漏斗，唔係一堆 page：
  ① 市場環境（5 燈）→ ② 廣度 → ③ 板塊 RS → ④ 候選
  → ⑤ 計劃（pivot/stop/size）→ ⑥ 9:30 READY

原則（寫死，唔准改）：
  · 環境 > setup：5 燈唔過，後面全部唔使睇
  · 計劃先於觸發：pivot/stop/size 寫好先算 ready
  · 冇 A+ = 0 單，唔硬做

數據源（全部係既有產物，唔自己再算一次）：
  output/daily_plan_card_<date>.txt   5 燈 + 風控參數
  output/today_six.json               regime / trade_cap / picks
  output/breadth_<date>.json          ADL / NNNL / %40MA
  output/group_rs_<date>.json         板塊 RS + 創新高家數
  output/rs_select_<date>.json        買入區候選
  sim_ledger/fleet/champion/equity.csv 錢
"""
import csv
import datetime
import glob
import html as _h
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = r"C:/Users/rain0/trading-os/output"
CHAMP = r"C:/Users/rain0/trading-os/sim_ledger/fleet/champion"


def _newest(pat):
    fs = sorted(glob.glob(os.path.join(DATA, pat)))
    return fs[-1] if fs else None


def _esc(v):
    return _h.escape(str(v)) if v is not None else ""


def _num(v, d=1):
    try:
        return f"{float(v):,.{d}f}"
    except (TypeError, ValueError):
        return "—"


CSS = """
.pf-h{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:0 0 4px}
.pf-h h2{margin:0;font-size:20px}
.pf-sub{font-size:11.5px;opacity:.66}
.pf-step{border-left:4px solid rgba(128,128,128,.35);padding:10px 14px;
  margin:12px 0;border-radius:0 10px 10px 0;background:rgba(128,128,128,.05)}
.pf-step.ok{border-left-color:#22c55e}
.pf-step.warn{border-left-color:#f59e0b}
.pf-step.bad{border-left-color:#ef4444}
.ex-idx{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:6px 0 9px}
.ex-card{border:1px solid rgba(128,128,128,.3);border-radius:9px;padding:7px 9px;
  background:rgba(128,128,128,.05)}
.ex-card .tk{font-size:13px;font-weight:800;letter-spacing:.02em}
.ex-card .ph{font-size:11.5px;font-weight:700;margin:1px 0 3px}
.ex-card .row{font-size:11px;opacity:.82}
.ex-card .row b{font-weight:800}
@media(max-width:700px){.ex-idx{grid-template-columns:1fr}}
.ex-bar{display:flex;height:12px;border-radius:6px;overflow:hidden;
  background:rgba(128,128,128,.15);margin:6px 0 5px}
.ex-bar>i{display:block;height:100%}
.ex-legend{display:flex;flex-wrap:wrap;gap:10px;font-size:11px;opacity:.8;margin-bottom:8px}
.ex-legend em{font-style:normal;font-weight:800}
.ex-tbl{width:100%;border-collapse:collapse;font-size:12px;
  font-variant-numeric:tabular-nums}
.ex-tbl th{text-align:left;font-size:10px;font-weight:700;opacity:.55;
  padding:4px;border-bottom:1px solid rgba(128,128,128,.3)}
.ex-tbl td{padding:3px 4px;border-bottom:1px solid rgba(128,128,128,.1)}
.ex-tbl tr:hover td{background:rgba(249,115,22,.05)}
@media(max-width:700px){.ex-tbl th:nth-child(6),.ex-tbl td:nth-child(6),
  .ex-tbl th:nth-child(7),.ex-tbl td:nth-child(7){display:none}}
.pf-step h3{margin:0 0 6px;font-size:14.5px;display:flex;gap:8px;
  align-items:baseline;flex-wrap:wrap}
.pf-step h3 small{font-weight:400;font-size:11px;opacity:.6}
.pf-row{display:flex;gap:10px;align-items:baseline;padding:3px 0;
  font-size:13px;flex-wrap:wrap}
.pf-row b{min-width:8.5em;font-weight:700;opacity:.85}
.pf-tag{font-size:10px;padding:1px 7px;border-radius:999px;font-weight:800}
.pf-tag.g{background:rgba(34,197,94,.18);color:#22c55e;border:1px solid rgba(34,197,94,.5)}
.pf-tag.r{background:rgba(239,68,68,.16);color:#ef4444;border:1px solid rgba(239,68,68,.5)}
.pf-tag.y{background:rgba(245,158,11,.16);color:#f59e0b;border:1px solid rgba(245,158,11,.5)}
.pf-verdict{font-size:17px;font-weight:800;margin:6px 0 2px}
.pf-list{margin:6px 0 0;padding-left:20px;font-size:12.5px;line-height:1.85}
.pf-note{font-size:11.5px;opacity:.62;margin-top:6px;line-height:1.7}
.pf-cands{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.pf-cand{font-size:11.5px;padding:2px 8px;border-radius:6px;
  border:1px solid rgba(128,128,128,.3);font-weight:700;
  text-decoration:none;cursor:pointer;display:inline-block}
a.pf-cand:hover{filter:brightness(1.12)}
.pf-cand.buy{background:#f97316;border-color:#f97316;color:#fff}
.pf-bar{height:9px;border-radius:999px;background:rgba(128,128,128,.18);
  position:relative;width:100%;max-width:280px}
.pf-bar>span{display:block;height:100%;border-radius:999px;transition:width .2s}
.pf-bar>i{position:absolute;top:-3px;bottom:-3px;width:2px;
  background:rgba(215,215,215,.85);border-radius:1px;transform:translateX(-1px)}
.pf-big{margin:12px 0 14px}
.pf-big .top{display:flex;justify-content:space-between;gap:14px;
  align-items:baseline;flex-wrap:wrap}
.pf-big .lab{font-size:10.5px;letter-spacing:.06em;font-weight:700;opacity:.66}
.pf-big .zn{font-size:12px;font-weight:800}
.pf-big .num{font-size:34px;font-weight:800;line-height:1.05;margin:2px 0 4px}
.pf-big .bar{height:10px;border-radius:999px;background:rgba(128,128,128,.18);
  position:relative;width:100%}
.pf-big .bar>span{display:block;height:100%;border-radius:999px}
.pf-big .desc{font-size:11px;opacity:.62;margin-top:5px;line-height:1.5}
.pf-sub2{margin:14px 0 4px;font-size:11px;letter-spacing:.05em;
  text-transform:uppercase;opacity:.5;font-weight:700}
.pf-brow{display:grid;grid-template-columns:92px 60px minmax(150px,300px) 1fr;
  gap:12px;align-items:center;padding:6px 0;font-size:12.5px}
.pf-brow .nm{font-weight:700;opacity:.92}
.pf-tvsym{color:inherit;text-decoration:none;cursor:pointer;
  border-bottom:1px dotted rgba(128,128,128,.55)}
.pf-tvsym:hover{color:#f97316;border-bottom-color:#f97316}
.pf-brow .vv{font-variant-numeric:tabular-nums;font-weight:800;text-align:right}
.pf-brow .bw{display:flex;justify-content:center}
.pf-brow .nt{font-size:11px;opacity:.72;line-height:1.4;white-space:normal}
@media(max-width:720px){
  .pf-brow{grid-template-columns:84px 54px 1fr;grid-template-areas:"nm vv bw" "nt nt nt"}
  .pf-brow .nt{grid-area:nt;margin-top:2px}
}
"""


def _parse_card(path):
    """由每日卡抽 5 燈 + 風控參數"""
    if not path or not os.path.exists(path):
        return dict(lights=[], risks=[], day="", raw="")
    txt = io.open(path, encoding="utf-8", errors="replace").read()
    day = ""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
    if m:
        day = m.group(1)
    lights = []
    for line in txt.split("\n"):
        s = line.strip()
        if not s:
            continue
        if not re.match(r"^[🔴🟢🔔⚠️🟡]", s):
            continue
        if not re.search(r"入市|價格行為|新高|動能", s):
            continue
        ok = "🟢" in s
        # 抽出主標題（第一個 ｜ 之前）
        head = re.sub(r"^[^\w（(]*", "", s.split("｜")[0]).strip()
        note = s.split("｜", 1)[1].strip() if "｜" in s else ""
        lights.append(dict(ok=ok, head=head, note=note))
    risks = []
    for line in txt.split("\n"):
        m = re.match(r"^\s*\d+\.\s*([A-Z][A-Z0-9.]{0,5})\s*(?:入|entry)\s*"
                     r"([\d.]+)\s*[｜|]\s*(?:止|stop)\s*([\d.]+)(.*)$", line.strip())
        if m:
            risks.append(dict(sym=m.group(1), entry=float(m.group(2)),
                              stop=float(m.group(3)), rest=m.group(4).strip()))
    return dict(lights=lights, risks=risks, day=day, raw=txt)


def _breadth():
    p = _newest("breadth_*.json")
    if not p:
        return {}
    try:
        d = json.load(io.open(p, encoding="utf-8"))
        return dict(asof=(d.get("as_of") or "")[:10],
                    adl=(d.get("adl") or {}).get("value"),
                    nnnl=(d.get("nnnl") or {}).get("value"),
                    pct40=d.get("pct40ma"),
                    lsr=d.get("ls_ratio_proxy"),
                    regime=d.get("regime"),
                    posture=((d.get("posture") or {}) or {}).get("posture"),
                    spy=d.get("spy_close"))
    except Exception:                                         # noqa: BLE001
        return {}


def _groups():
    p = _newest("group_rs_*.json")
    if not p:
        return dict(rows=[], n_new=None, total=None, trend="")
    try:
        d = json.load(io.open(p, encoding="utf-8"))
        return dict(rows=d.get("rows") or [],
                    n_new=d.get("new_high_count"),
                    total=d.get("groups_total"),
                    trend=d.get("trend") or "")
    except Exception:                                         # noqa: BLE001
        return dict(rows=[], n_new=None, total=None, trend="")


def _six():
    p = os.path.join(DATA, "today_six.json")
    if not os.path.exists(p):
        return {}
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:                                         # noqa: BLE001
        return {}


def _rs_buybox():
    p = _newest("rs_select_*.json")
    if not p:
        return [], 0
    try:
        d = json.load(io.open(p, encoding="utf-8"))
        rows = d.get("rows") or []
        box = [r for r in rows if r.get("in_buy_box")]
        return box, d.get("n_buy_box_all") or len(box)
    except Exception:                                         # noqa: BLE001
        return [], 0


def _champion():
    eq = os.path.join(CHAMP, "equity.csv")
    nav, day = None, ""
    if os.path.exists(eq):
        try:
            with io.open(eq, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if rows:
                nav = float(rows[-1].get("equity") or 0)
                day = rows[-1].get("date") or ""
        except Exception:                                     # noqa: BLE001
            pass
    return nav, day



# ── 廣度 bar + 更新時間（Desmond 2026-10-24：「加返條 BAR + MMTW/MMFI」）──
def _regime_live():
    """讀 docs/regime_live.json（market_regime 產物）—— 唔自己再算"""
    p = os.path.join(HERE, "docs", "regime_live.json")
    if not os.path.exists(p):
        return {}
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:                                         # noqa: BLE001
        return {}


def _bar(pct, color="#f59e0b", mid=None):
    """橫向 bar；mid = 中線（牛熊分界）。有中線你先一眼睇到偏多定偏空。"""
    pct = max(0.0, min(100.0, float(pct or 0)))
    tick = ("" if mid is None
            else '<i style="left:%.1f%%"></i>' % max(0.0, min(100.0, float(mid))))
    return ('<div class="pf-bar"><span style="width:%.1f%%;background:%s">'
            '</span>%s</div>' % (pct, color, tick))


def _tone(v, lo=40, hi=60):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "#9ca3af", "—"
    if x >= hi:
        return "#22c55e", "強"
    if x >= lo:
        return "#f59e0b", "中性"
    return "#ef4444", "弱"


def _next_update():
    """site-auto-rebuild = 08:50 + 23:50 HKT"""
    now = datetime.datetime.now()
    slots = [now.replace(hour=8, minute=50, second=0, microsecond=0),
             now.replace(hour=23, minute=50, second=0, microsecond=0)]
    for s in slots:
        if s > now:
            return s
    return slots[0] + datetime.timedelta(days=1)


# ── EXT 階段分析（RS Alpha v9.0 日線部分）────────────────────────────
RS_ALPHA = r"C:/Users/rain0/trading-os/output/rs_alpha_latest.json"
PHASE_ORDER = ["EXPANSION 7+", "NO NEW RISK 4-7", "GREEN 0-4",
               "RESET -2/0", "RESET -4/-2", "DEEP <-4"]
PHASE_COL = {"EXPANSION 7+": "#ef4444", "NO NEW RISK 4-7": "#f97316",
             "GREEN 0-4": "#22c55e", "RESET -2/0": "#38bdf8",
             "RESET -4/-2": "#6366f1", "DEEP <-4": "#94a3b8"}


def _ex_grade(r):
    """EXT 階段表嘅 SETUP 評分（A+ 最高）。只用表內已有數字。"""
    x = r.get("atrx")
    if x is None:
        return "—", 0
    if x > 4:
        return "D", 0
    pts = 3 if 0 <= x <= 2 else 2
    rs = r.get("rs_rating")
    if rs is not None:
        pts += 3 if rs >= 95 else (2 if rs >= 90 else (1 if rs >= 80 else 0))
    if str(r.get("launch") or "").startswith("READY"):
        pts += 1
    if r.get("alpha") and not r.get("lead_weak"):
        pts += 1
    return ("A+" if pts >= 7 else "A" if pts >= 5
            else "B" if pts >= 3 else "C"), pts


def _gcol(g):
    return {"A+": "#a855f7", "A": "#22c55e", "B": "#f59e0b",
            "C": "#94a3b8", "D": "#ef4444"}.get(g, "#94a3b8")


def _ext_phase():
    import io
    import json
    import os
    if not os.path.exists(RS_ALPHA):
        return ('<div class="pf-step"><h3>🧪 EXT 階段（RS Alpha v9）</h3>'
                '<div class="pf-dim">DATA_UNAVAILABLE — 未跑 rs_alpha.py</div></div>')
    try:
        d = json.load(io.open(RS_ALPHA, encoding="utf-8"))
    except Exception as e:                                     # noqa: BLE001
        return (f'<div class="pf-step"><h3>🧪 EXT 階段（RS Alpha v9）</h3>'
                f'<div class="pf-dim">讀唔到：{type(e).__name__}</div></div>')

    rows = d.get("rows") or []
    if not rows:
        return ('<div class="pf-step"><h3>🧪 EXT 階段（RS Alpha v9）</h3>'
                '<div class="pf-dim">今日冇數據</div></div>')

    cnt = {k: 0 for k in PHASE_ORDER}
    for r in rows:
        cnt[r.get("phase")] = cnt.get(r.get("phase"), 0) + 1
    tot = sum(cnt.values()) or 1

    P = ['<div class="pf-step"><h3>🧪 EXT 階段（RS Alpha v9）'
         f'<small>{len(rows)} 隻｜資料 {_esc(d.get("as_of"))}｜'
         'EXT＝距 50MA 嘅 ATR 倍數｜大盤 SPY／QQQ／IWM 用同一把尺</small></h3>']

    # ── 大盤指數（SPY / QQQ / IWM）同一套 EXT 階段 ──
    idx = d.get("indices") or []
    if idx:
        P.append('<div class="ex-idx">')
        for r in idx:
            col = PHASE_COL.get(r.get("phase"), "#94a3b8")
            tk = r.get("sym") or ""
            P.append(
                f'<div class="ex-card" style="border-color:{col}66">'
                f'<div class="tk"><a class="tv" data-sym="{_esc(tk)}" '
                f'href="https://www.tradingview.com/chart/?symbol={_esc(tk)}" '
                f'target="_blank" rel="noopener">{_esc(tk)}</a></div>'
                f'<div class="ph" style="color:{col}">{_esc(r.get("phase"))}</div>'
                f'<div class="row">EXT <b>{_num(r.get("atrx"), 2)}</b>'
                f'　距MA {_num(r.get("ma_dist"), 2)}%'
                f'　ATR% {_num(r.get("atr_pct"), 2)}</div>'
                '</div>')
        P.append('</div>')

    # 階段分佈條
    P.append('<div class="ex-bar">')
    for k in PHASE_ORDER:
        if not cnt.get(k):
            continue
        w = cnt[k] / tot * 100
        P.append(f'<i style="width:{w:.1f}%;background:{PHASE_COL[k]}" '
                 f'title="{k} {cnt[k]} 隻"></i>')
    P.append('</div><div class="ex-legend">')
    P.append("".join(
        f'<span><b style="color:{PHASE_COL[k]}">■</b> {k} <em>{cnt[k]}</em></span>'
        for k in PHASE_ORDER if cnt.get(k)))
    P.append('</div>')

    # 表：按階段順序，再按 RS 降序
    # ── SETUP 評分（2026-10-24 Desmond：「欠缺 SETUP 評分 最高質量為 A+」）──
    #   只用現有欄位計分，唔引入新數據。原則：冇 A+ = 0 單，唔硬做。
    def _grade(r):
        pts, hard = 0, False
        x = r.get("atrx")
        if x is not None:
            if 0 <= x <= 2:
                pts += 3          # 貼近 50MA＝最佳入場區
            elif 2 < x <= 4:
                pts += 1          # 可接受
            elif x > 7:
                hard = True       # 極端延伸，結構性否定
        rs = r.get("rs_rating") or 0
        pts += 3 if rs >= 95 else (2 if rs >= 90 else (1 if rs >= 80 else 0))
        if r.get("alpha") and not r.get("lead_weak"):
            pts += 2              # α 穩健
        t = (r.get("t_state") or "").upper()
        if t.startswith("CONFIRMED"):
            pts += 2
        elif t.startswith("FAILED"):
            hard = True
        elif t.startswith("T"):
            pts += 1
        ph = (r.get("phase") or "").upper()
        if ph.startswith("GREEN"):
            pts += 1
        elif ph.startswith("EXPANSION"):
            hard = True
        elif ph.startswith("NO NEW RISK"):
            pts -= 1
        if (r.get("launch") or "").upper() in ("BUILD", "NH"):
            pts += 1
        if r.get("nh_age") is not None and r["nh_age"] <= 3:
            pts += 1
        if hard:
            return "D", pts
        if pts >= 12:
            return "A+", pts
        if pts >= 9:
            return "A", pts
        if pts >= 6:
            return "B", pts
        return "C", pts

    rows = sorted(rows, key=lambda r: (
        PHASE_ORDER.index(r["phase"]) if r.get("phase") in PHASE_ORDER else 9,
        -(r.get("rs_rating") or 0)))
    P.append('<table class="ex-tbl"><thead><tr>'
             '<th>代號</th><th>評分</th><th>階段</th><th>EXT</th><th>RS</th>'
             '<th>α</th><th>Launch</th><th>NH</th><th>T</th>'
             '</tr></thead><tbody>')
    for r in rows:
        ph = r.get("phase")
        col = PHASE_COL.get(ph, "#94a3b8")
        tk = r.get("sym") or ""
        alpha = r.get("alpha")
        a_txt = ("穩健" if alpha and not r.get("lead_weak")
                 else ("轉弱" if alpha else "未確認"))
        a_col = ("#22c55e" if alpha and not r.get("lead_weak")
                 else ("#f59e0b" if alpha else "#94a3b8"))
        t = r.get("t_state") or "WAIT"
        t_col = ("#22c55e" if t.startswith("CONFIRMED") else
                 "#ef4444" if t.startswith("FAILED") else
                 "#38bdf8" if t.startswith("T") else "#94a3b8")
        P.append(
            '<tr>'
            f'<td><a class="tv" data-sym="{_esc(tk)}" '
            f'href="https://www.tradingview.com/chart/?symbol={_esc(tk)}" '
            f'target="_blank" rel="noopener">{_esc(tk)}</a></td>'
            f'<td><b style="color:{_gcol(_ex_grade(r)[0])}">'
            f'{_ex_grade(r)[0]}</b></td>'
            f'<td style="color:{col};font-weight:700">{_esc(ph)}</td>'
            f'<td>{_num(r.get("atrx"), 2)}</td>'
            f'<td>{_esc(r.get("rs_rating"))}</td>'
            f'<td style="color:{a_col}">{a_txt}</td>'
            f'<td>{_esc(r.get("launch"))}</td>'
            f'<td>{_esc(r.get("nh_age")) if r.get("nh_age") is not None else "—"}</td>'
            f'<td style="color:{t_col}">{_esc(t)}</td>'
            '</tr>')
    P.append('</tbody></table>')
    P.append('<div class="pf-dim" style="margin-top:6px">'
             '階段：<b>GREEN 0-4</b>＝可新增風險區｜<b>NO NEW RISK 4-7</b>＝持有唔加｜'
             '<b>EXPANSION 7+</b>＝極端延伸｜<b>RESET</b>＝回氣區｜'
             '<b>DEEP</b>＝跌穿 4 ATR。'
             '<br>⚠ 5 分鐘 intraday 觸發／Margin 資格／TV alert 係 TradingView 專有，'
             '網站只計日線部分。</div>')
    P.append('</div>')
    return "".join(P)


def build():
    card = _parse_card(_newest("daily_plan_card_*.txt"))
    b = _breadth()
    g = _groups()
    six = _six()
    box, n_box = _rs_buybox()
    nav, nav_day = _champion()

    red = sum(1 for L in card["lights"] if not L["ok"])
    total_l = len(card["lights"])
    regime = six.get("regime") or b.get("regime") or "—"
    cap = six.get("trade_cap")
    veto = (regime == "BEAR" or cap == 0)
    ready = (total_l >= 4 and red <= 2 and not veto)

    P = [f"<style>{CSS}</style>"]
    _now = datetime.datetime.now()
    _nxt = _next_update()
    P.append('<div class="pf-h"><h2>每日流程</h2>'
             f'<span class="pf-sub">Jeff Sun 決策漏斗｜卡片 {_esc(card["day"])}'
             f'｜{total_l} 燈中 {red} 紅</span></div>')
    P.append(f'<div style="font-size:11.5px;opacity:.66;margin:0 0 6px">'
             f'🕒 頁面生成 {_now:%Y-%m-%d %H:%M}（HKT）｜'
             f'資料截止 卡片 {_esc(card["day"])}／廣度 {_esc(b.get("asof") or b.get("as_of") or "—")}｜'
             f'下次自動更新 {_nxt:%m-%d %H:%M}</div>')
    P.append('<div style="font-size:12.5px;opacity:.75;margin:2px 0 6px">'
             '順序 = 環境 → 廣度 → 板塊 → 候選 → 計劃 → 9:30 ready。'
             '<b>5 燈唔過，後面唔使睇。</b></div>')

    # ── ① 市場 ──
    st = "bad" if red >= 3 else ("warn" if red >= 1 else "ok")
    P.append(f'<div class="pf-step {st}"><h3>① 市場環境 '
             f'<small>5 燈｜{red}/{total_l} 紅</small></h3>')
    for L in card["lights"]:
        tag = ('<span class="pf-tag g">綠</span>' if L["ok"]
               else '<span class="pf-tag r">紅</span>')
        P.append(f'<div class="pf-row">{tag}<b>{_esc(L["head"])}</b>'
                 f'<span style="opacity:.8">{_esc(L["note"])}</span></div>')
    if not card["lights"]:
        P.append('<div class="dim">讀唔到每日卡</div>')
    P.append('</div>')

    # ── ② 廣度（bar + MMTW/MMFI）──
    rl = _regime_live()
    P.append('<div class="pf-step"><h3>② 廣度 '
             f'<small>{_esc(b.get("regime") or "—")}｜'
             f'{_esc(b.get("posture") or "—")}</small></h3>')

    def brow(name, val, pct, mid=50.0, note="", sym=None):
        """一行廣度指標。

        ★ 2026-10-24 Desmond：「係支 BAR 中間個條線，咁我就知佢 bearish 定 bullish」
          → 每個指標都有中線（mid）＝牛熊分界；顏色同標籤全部由「偏離中線」決定，
            唔再靠我自己寫嘅含糊描述。
        """
        try:
            p = float(pct)
        except (TypeError, ValueError):
            p = 0.0
        p = max(0.0, min(100.0, p))
        mid = float(mid)
        d = p - mid
        if d > 4:
            tag, col = "▲ 偏多", "#22c55e"
        elif d < -4:
            tag, col = "▼ 偏空", "#ef4444"
        else:
            tag, col = "— 中性", "#f59e0b"
        if sym:
            nm = ('<a class="pf-tvsym tv" data-sym="%s" '
                  'href="https://www.tradingview.com/chart/?symbol=%s" '
                  'target="_blank" rel="noopener">%s</a>' % (sym, sym, name))
        else:
            nm = name
        P.append('<div class="pf-brow"><span class="nm">%s</span>'
                 '<span class="vv" style="color:%s">%s</span>'
                 '<span class="bw">%s</span>'
                 '<span class="nt"><b style="color:%s">%s</b>%s</span></div>'
                 % (nm, col, val, _bar(p, col, mid), col, tag,
                    ("　·　" + note) if note else ""))

    # ── 大卡：MMTW / MMFI（同 Market Regime 同一把尺，唔自己寫第二套）──
    try:
        import market_regime as _mr
        _mmtw_lab, _mmfi_lab = _mr._mmtw_label, _mr._mmfi_label
    except Exception:                                         # noqa: BLE001
        _mmtw_lab = _mmfi_lab = None

    def big(name, sub, val, pct, zone, col, desc, sym=None):
        nm = name
        if sym:
            nm = ('<a class="pf-tvsym tv" data-sym="%s" '
                  'href="https://www.tradingview.com/chart/?symbol=%s" '
                  'target="_blank" rel="noopener">%s</a>' % (sym, sym, name))
        P.append('<div class="pf-big"><div class="top">'
                 '<span class="lab">%s <span style="opacity:.75">%s</span></span>'
                 '<span class="zn" style="color:%s">%s</span></div>'
                 '<div class="num" style="color:%s">%s</div>'
                 '<div class="bar"><span style="width:%.1f%%;background:%s"></span>'
                 '</div><div class="desc">%s</div></div>'
                 % (nm, sub, col, zone, col, val,
                    max(0.0, min(100.0, float(pct))), col, desc))

    if rl.get("mmtw") is not None:
        _v = float(rl["mmtw"])
        if _mmtw_lab:
            z, c, d = _mmtw_lab(_v, rl.get("mmtw_rising"))
        else:
            c, z, d = "#f59e0b", "—", ""
        big("MMTW 寬度", "（% ABOVE 20MA）· 短線廣度振盪",
            "%.1f%%" % _v, _v, z, c, d, sym="MMTW")
    if rl.get("mmfi") is not None:
        _v = float(rl["mmfi"])
        if _mmfi_lab:
            z, c, d = _mmfi_lab(_v)
        else:
            c, z, d = "#f59e0b", "—", ""
        big("MMFI", "（% ABOVE 50MA）· 中期趨勢參與度",
            "%.1f%%" % _v, _v, z, c, d, sym="MMFI")
    P.append('<div class="pf-sub2">其他廣度</div>')
    if b.get("pct40") is not None:
        brow("% 企 40MA", "%s%%" % _num(b.get("pct40")), b.get("pct40"), 50,
             "中期參與度")
    if b.get("adl") is not None:
        try:
            av = float(b.get("adl"))
        except (TypeError, ValueError):
            av = 0
        brow("ADL", _num(av), (av + 200) / 400 * 100, 50,
             "0 以上偏多（升跌線，−200…+200）")
    if b.get("nnnl") is not None:
        try:
            nv = float(b.get("nnnl"))
        except (TypeError, ValueError):
            nv = 0
        brow("NNNL", _num(nv), (nv + 100) / 200 * 100, 50,
             "0 以上偏多（新高−新低）")
    if b.get("lsr") is not None:
        try:
            lv = float(b.get("lsr"))
        except (TypeError, ValueError):
            lv = 0
        # LS ratio：0–2.5 映射（≥2.5:1 已經極強），中線 1.0 → 40%
        brow("LS ratio", "%s : 1" % _num(lv, 2),
             min(100, lv / 2.5 * 100), 40,
             "1.0 以上偏多（升股 ÷ 跌股）")
    if rl.get("mri") is not None:
        try:
            mv = float(rl.get("mri"))
        except (TypeError, ValueError):
            mv = 0
        brow("MRI 0–100", "%.0f" % mv, mv, 50,
             _esc(rl.get("state") or ""))
    P.append('<div class="pf-note">MMTW/MMFI 來源：'
             + _esc(rl.get("asof") or "—")
             + f'｜更新 {_esc(rl.get("updated") or "—")}'
             '（Market Regime 頁同一個源，唔會兩把尺）</div>')
    P.append('</div>')

    # ── ③ 板塊 ──
    P.append('<div class="pf-step"><h3>③ 板塊 RS '
             f'<small>創新高 {_esc(g.get("n_new"))}/{_esc(g.get("total"))}'
             f'｜趨勢 {_esc(g.get("trend"))}</small></h3>')
    rows = sorted(g.get("rows") or [], key=lambda r: -(r.get("rs") or 0))[:5]
    for r in rows:
        star = " 🆕" if r.get("new_high") else ""
        P.append(f'<div class="pf-row"><b>{_esc(r.get("group"))}</b>'
                 f'<span style="opacity:.8">RS {_num(r.get("rs"), 3)}</span>'
                 f'<span style="opacity:.55">n={_esc(r.get("n"))}</span>{star}</div>')
    if not rows:
        P.append('<div class="dim">讀唔到板塊 RS</div>')
    P.append('</div>')

    # ── ④ 候選 ──
    P.append('<div class="pf-step"><h3>④ 候選 '
             f'<small>買入區 {_esc(n_box)} 隻</small></h3>')
    if box:
        P.append('<div class="pf-cands">')
        for r in box[:14]:
            _tk = _esc(r.get("ticker"))
            # ★ 2026-10-24 Desmond：hover 出 TV 預覽，左鍵入 TradingView
            # ★ JS 只認 a.tv（closest('a.tv')）—— 冇 tv class 就唔會彈
            P.append(f'<a class="pf-cand buy tv" data-sym="{_tk}" '
                     f'href="https://www.tradingview.com/chart/?symbol={_tk}" '
                     f'target="_blank" rel="noopener">{_tk}</a>')
        P.append('</div>')
        P.append('<div class="pf-note">來源：RS Daily Scan（6 閘：價／成交額／ADR／'
                 'ATRX／距 52 高／財報黑名單）</div>')
    else:
        P.append('<div class="dim">今日冇買入區候選</div>')
    P.append('</div>')

    # ── ⑤ 計劃 ──
    P.append(_ext_phase())
    P.append('<div class="pf-step"><h3>⑤ 計劃（pivot／止蝕／倉位）</h3>')
    if veto:
        P.append(f'<div class="pf-verdict" style="color:#ef4444">'
                 f'🛑 環境否決：regime={_esc(regime)}／trade_cap={_esc(cap)} → 0 單</div>')
        P.append('<div class="pf-note">卡片仍然列出候選（觀察用），'
                 '但環境否決期間唔入場。呢個就係「唔硬做」。</div>')
    if card["risks"]:
        for r in card["risks"][:6]:
            pct = (r["stop"] / r["entry"] - 1) * 100 if r["entry"] else 0
            P.append(f'<div class="pf-row"><b>{_esc(r["sym"])}</b>'
                     f'入 {_num(r["entry"], 2)}｜止 {_num(r["stop"], 2)}'
                     f'（{pct:+.1f}%）{_esc(r["rest"])}</div>')
    elif not veto:
        P.append('<div class="dim">今日卡冇風控參數段</div>')
    P.append('</div>')

    # ── ⑥ 9:30 READY ──
    if ready:
        P.append('<div class="pf-step ok"><h3>⑥ 9:30 READY</h3>'
                 '<div class="pf-verdict" style="color:#22c55e">✅ 可以落場（最多 3 條）</div>'
                 '<div class="pf-note">條件：5 燈 ≤2 紅 + 環境未否決 + 有買入區候選。<br>'
                 '入場只做計劃內嘅 pivot，止蝕用 LOD（≤0.60 ATR），'
                 '單筆風險 0.5%。</div></div>')
    else:
        reason = []
        if veto:
            reason.append(f"環境否決（regime={regime}／cap={cap}）")
        if total_l and red >= 3:
            reason.append(f"5 燈有 {red} 紅")
        P.append('<div class="pf-step bad"><h3>⑥ 9:30 READY</h3>'
                 '<div class="pf-verdict" style="color:#ef4444">❌ 未 READY — 今日 0 單</div>'
                 f'<div class="pf-note">原因：{_esc("；".join(reason) or "環境未確認")}。<br>'
                 '唔需要盯盤。等下一次流程重跑（市場狀態改變）再判斷。</div>'
                 '</div>')

    # ── ⑦ 錢 ──
    if nav:
        ret = (nav / 100000 - 1) * 100
        cls = "#22c55e" if ret >= 0 else "#ef4444"
        P.append('<div class="pf-step"><h3>⑦ 錢（Champion 組合）</h3>'
                 f'<div class="pf-verdict" style="color:{cls}">'
                 f'${nav:,.0f}　{ret:+.2f}%</div>'
                 f'<div class="pf-note">數據截至 {_esc(nav_day)}｜'
                 '完整曲線見首頁。熊市 0 單，曲線企定 = 唔蝕。</div></div>')

    P.append('<div class="pf-note">★ 整個流程嘅目的：開市前用 3 分鐘知道'
             '「做／唔做、做邊隻、止蝕喺邊」。唔需要即場判斷。</div>')
    return ("每日流程", "".join(P))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    t, bd = build()
    print(f"{t} — {len(bd):,} chars")
    for probe in ("每日流程", "9:30 READY", "板塊 RS", "買入區"):
        print(("OK  " if probe in bd else "MISS") + f" {probe}")
