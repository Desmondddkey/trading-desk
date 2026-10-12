#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""site_db.py — 把網站上所有數據寫入一個 Excel database。

Desmond 2026-10-12：「最後建立一個 data base 用 excel 記錄，儲存網頁內的數據」

★ 第一性原理：一個 database 要有三個性質，缺一即唔算 database：
  ① **可追溯**：每張表要寫「數據日」「跑嘅時間」「來源檔」「產生器」——
     唔係一堆靚數字，係可以查返「呢個數邊嚟」。
  ② **可累積**：每次跑唔可以覆蓋舊嘅 —— 有「歷史」sheet 一路 append。
  ③ **Missing ≠ Zero**：缺數寫 "DATA_UNAVAILABLE"，唔准填 0 或空白（EDGE-016）。

★ 分兩個檔（唔可以一個）：
  · `site_db_<日期>.xlsx`  —— 每日快照（每張表 = 網站一頁嘅數據）
  · `site_db_history.xlsx` —— 累積歷史（每次跑 append 一行／一批）
  理由：快照要可以獨立送出去／歸檔；歷史要一路長大。撈埋一齊兩個用途都做唔好。

★ 唯一實作：每張表嘅數字呼叫既有 module，唔准喺呢度重算（EDGE-036）。

用法：
  python site_db.py                 # 出今日快照 + 更新歷史
  python site_db.py --no-history    # 只出快照
  python site_db.py --list          # 列出有咩表
"""
import argparse
import datetime
import glob
import io
import json
import os
import sys

HOME = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(os.path.dirname(HOME), "trading-os-lab")
OSDIR = os.path.join(os.path.dirname(HOME), "trading-os")
OUT = os.path.join(HOME, "output")
DBDIR = os.path.join(HOME, "db")

for _p in (HOME, LAB, OSDIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

NA = "DATA_UNAVAILABLE"


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def _jload(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return None


def _num(v):
    """數值：None → DATA_UNAVAILABLE（唔准當 0）。"""
    return NA if v is None else v


# ══════════════════ 每張表：回傳 (headers, rows) ══════════════════
def t_leaders():
    """領導股（NEL）—— 由 market_scan.json。"""
    d = _jload(os.path.join(HOME, "data", "market_scan.json")) or {}
    nel = d.get("nel") or []
    hdr = ["代號", "行業", "收市", "1週%", "1月%", "3月%", "6月%", "1年%",
           "延伸(ATRX)", "ADR%", "成交額", "距52週高%"]
    rows = []
    for r in nel:
        p = r.get("perf") or {}
        rows.append([r.get("symbol"), r.get("industry"), _num(r.get("close")),
                     _num(p.get("1w")), _num(p.get("1m")), _num(p.get("3m")),
                     _num(p.get("6m")), _num(p.get("1y")),
                     _num(r.get("extension")), _num(r.get("adr")),
                     _num(r.get("dvol")), _num(r.get("off52w"))])
    return hdr, rows


def t_week():
    d = _jload(os.path.join(HOME, "data", "market_scan.json")) or {}
    hdr = ["#", "代號", "行業", "1週%", "1月%", "3月%", "延伸(ATRX)",
           "ADR%", "成交額", "距52週高%"]
    rows = []
    for i, r in enumerate(d.get("week") or [], 1):
        p = r.get("perf") or {}
        rows.append([i, r.get("symbol"), r.get("industry"),
                     _num(p.get("1w")), _num(p.get("1m")), _num(p.get("3m")),
                     _num(r.get("extension")), _num(r.get("adr")),
                     _num(r.get("dvol")), _num(r.get("off52w"))])
    return hdr, rows


def t_cm():
    """1CM 回調（1chartmaster RS pullback）。"""
    try:
        import cm as _cm
        d = _jload(os.path.join(HOME, "data", "market_scan.json")) or {}
        syms = [r.get("symbol") for r in (d.get("nel") or [])]
        res = _cm.classify(syms)
    except Exception as e:                                   # noqa: BLE001
        log(f"  ⚠ 1CM：{type(e).__name__}")
        return (["代號", "1CM 評級", "命中數"], [[NA, NA, NA]])
    hdr = ["代號", "1CM 評級", "命中數/5", "L1 RS領導", "L2 回調支撐",
           "L3 量縮", "L4 買家守", "L5 風險窄", "距支撐%", "支撐位",
           "1M超額%", "3M超額%", "RVOL", "5日波幅%", "收市"]
    rows = []
    for tk, x in sorted(res.items(), key=lambda kv: -kv[1]["n"]):
        rows.append([tk, x["grade"], x["n"], x["c1"], x["c2"], x["c3"],
                     x["c4"], x["c5"], _num(x.get("sup_dist")),
                     _num(x.get("sup")), _num(x.get("ex1")), _num(x.get("ex3")),
                     _num(x.get("rvol")), _num(x.get("rng5")), x["close"]])
    return hdr, rows


def t_rotation():
    """行業輪動（34 ETF）—— 由 rotation_history.json + 即時重算。"""
    import rotation_map as rm
    d = rm.fetch()
    df, spy = rm.compute(d)
    if df is None or df.empty:
        return (["行業"], [[NA]])
    hdr = ["排名", "行業", "ETF", "階段", "分數", "1M超額%", "3M超額%"]
    rows = [[int(r["rank"]), r["name"], r.get("etf"), r["stage"],
             int(r["score"]), _num(r.get("x1m")), _num(r.get("x3m"))]
            for _, r in df.iterrows()]
    return hdr, rows


def t_rotation_delta():
    """行業前後差異（Item 3 嘅 delta）。"""
    h = _jload(os.path.join(LAB, "output", "rotation_history.json")) or {}
    snap = h.get("snapshots") or []
    if len(snap) < 2:
        return (["項目", "行業", "變動"],
                [[NA, NA, "只有一個快照，未有前後差異"]])
    old = snap[-2].get("ranks") or {}
    new = snap[-1].get("ranks") or {}
    hdr = ["行業ETF", f"{snap[-2].get('date')} 排名",
           f"{snap[-1].get('date')} 排名", "變動"]
    rows = []
    for e in sorted(set(old) | set(new)):
        o, n = old.get(e), new.get(e)
        if o is None or n is None:
            rows.append([e, _num(o), _num(n), NA])
        else:
            rows.append([e, o, n, o - n])
    rows.sort(key=lambda r: r[3] if isinstance(r[3], int) else -999,
              reverse=True)
    # 加一行標題分隔
    rows.insert(0, [f"數據日 {snap[-1].get('date')}　vs　"
                    f"{snap[-2].get('date')}", "", "", ""])
    return hdr, rows


def t_trail():
    """RS leader 位置尾巴（Item 5）。"""
    h = _jload(os.path.join(LAB, "output", "leader_trail_history.json")) or {}
    snap = h.get("snapshots") or []
    if not snap:
        return ([NA], [[NA]])
    pos = snap[-1].get("positions") or {}
    hdr = ["代號", "數據日", "X(21EMA/ATR)", "Y(ATRX)", "收市"]
    rows = []
    for tk, p in sorted(pos.items()):
        rows.append([tk, snap[-1].get("date"), _num(p.get("x")),
                     _num(p.get("y")), _num(p.get("close"))])
    return hdr, rows


def t_group_move():
    """Group move 閘（Item 6）。"""
    fs = sorted(glob.glob(os.path.join(LAB, "output", "group_move_*.json")))
    if not fs:
        return ([NA], [[NA]])
    d = _jload(fs[-1]) or {}
    hdr = ["代號", "行業", "RVOL 5m", "RVOL 15m", "RVOL 30m",
           "組達標窗數", "組隻數"]
    rows = [[m["ticker"], m["industry"], _num(m.get("rvol5")),
             _num(m.get("rvol15")), _num(m.get("rvol30")),
             m.get("group_hits"), m.get("group_n")]
            for m in (d.get("our_candidates") or [])]
    return hdr, rows


def t_breadth():
    fs = sorted(glob.glob(os.path.join(OSDIR, "output", "breadth_*.json")))
    if not fs:
        return (["指標", "值"], [["整體", NA]])
    d = _jload(fs[-1]) or {}
    adl = d.get("adl") or {}
    nn = d.get("nnnl") or {}
    post = d.get("posture")
    if isinstance(post, (list, tuple)):
        post = "；".join(str(x) for x in post[:3])
    elif isinstance(post, dict):
        post = post.get("text") or post.get("read")
    hdr = ["指標", "值", "說明"]
    rows = [
        ["數據日", str(d.get("as_of", NA))[:10], "breadth 快照時間"],
        ["池", _num(d.get("universe")), "計算範圍"],
        ["制度", _num(d.get("regime")), "regime 判定"],
        ["姿態", _num(post), "操作姿態"],
        ["ADL", _num(adl.get("value")), "上升下跌線（bull +100／bear −100）"],
        ["NNNL", _num(nn.get("value")), nn.get("method") or "10 日均（新高% − 新低%）"],
        ["% above 40MA", _num(d.get("pct40ma")), "市場參與度"],
        ["L/S 比率", _num(d.get("ls_ratio_proxy")), "long/short 代理"],
    ]
    return hdr, rows


def t_positioning():
    try:
        import nel_pages as np
        d = np.cftc_cot()
    except Exception as e:                                   # noqa: BLE001
        log(f"  ⚠ COT：{type(e).__name__}")
        d = {}
    if not d:
        return (["市場", "淨持倉"], [[NA, NA]])
    hdr = ["市場", "類別", "報告日", "淨持倉", "佔OI%", "52週位置",
           "讀法", "4週變化", "週數"]
    rows = []
    for code, m in sorted(d.items(), key=lambda kv: -kv[1]["extreme"]):
        ex = m["extreme"]
        tag = ("極度擁擠" if ex >= 90 else "偏擁擠" if ex >= 75
               else "偏淡" if ex <= 25 else "中性")
        rows.append([m["name"], m["group"], m["date"], m["net"],
                     _num(m.get("net_pct")), ex, tag,
                     _num(m.get("chg4")), m["weeks"]])
    return hdr, rows


def t_method():
    """方法分類（Layer2 Focus/Stalk）。"""
    src = None
    for p in (os.path.join(OSDIR, "output", "layer2_focus_stalk.json"),
              os.path.join(OSDIR, "data", "layer2_focus_stalk.json")):
        if os.path.exists(p):
            src = p
            break
    if not src:
        return (["代號", "分數"], [[NA, NA]])
    d = _jload(src) or {}
    hdr = ["組別", "代號", "分數", "ATRX", "買入線", "失效線", "理由"]
    rows = []
    for g in d.get("groups") or []:
        for r in sorted(g.get("rows") or [],
                        key=lambda z: -(z.get("score") or 0)):
            rows.append([g.get("label"), r.get("ticker"), _num(r.get("score")),
                         _num(r.get("atrx") or r.get("extension")),
                         _num(r.get("watch_price")), _num(r.get("invalidation")),
                         "、".join((r.get("reasons") or [])[:3])])
    return hdr, rows


def t_setups():
    """每日計劃（The Plan）。"""
    try:
        import build_site as bs
        st = bs.load_setups()
    except Exception:                                        # noqa: BLE001
        st = None
    if not st:
        return (["代號"], [[NA]])
    hdr = ["代號", "收市", "買入線", "失效線", "X(21EMA)", "Y(ATRX)",
           "止蝕%", "倉位%", "風險%"]
    rows = []
    for r in st.get("rows") or []:
        rows.append([r.get("ticker"), _num(r.get("close")),
                     _num(r.get("watch_price")), _num(r.get("invalidation")),
                     _num(r.get("x")), _num(r.get("y")),
                     _num(r.get("stop_pct")), _num(r.get("size_pct")),
                     _num(r.get("risk_pct"))])
    return hdr, rows


def t_rsboard():
    try:
        import extras
        d = extras.rsboard_full()
    except Exception:                                        # noqa: BLE001
        d = None
    if not d:
        return (["名稱"], [[NA]])
    hdr = ["類別", "#", "ETF／名稱", "推力率", "1月超額%", "RS 百分位",
           "距52週高%"]
    rows = []
    # ★ dict 入面除咗組別 list，仲有 as_of(str)／spy1m(float) 等非表欄位 —— 要濾
    for grp, lst in (d.items() if isinstance(d, dict) else []):
        if not isinstance(lst, list):
            continue
        for i, r in enumerate(lst, 1):
            if not isinstance(r, dict):
                continue
            rows.append([grp, i, r.get("name") or r.get("etf") or r.get("ticker"),
                         _num(r.get("thrust")), _num(r.get("ex1m")),
                         _num(r.get("pctile")), _num(r.get("off52w"))])
    if not rows:
        return (hdr, [[NA, NA, NA, NA, NA, NA, NA]])
    return hdr, rows


TABLES = [
    ("領導股", t_leaders),
    ("最強1週", t_week),
    ("1CM回調", t_cm),
    ("行業輪動", t_rotation),
    ("行業差異", t_rotation_delta),
    ("位置尾巴", t_trail),
    ("群組動量", t_group_move),
    ("Breadth", t_breadth),
    ("Positioning", t_positioning),
    ("方法分類", t_method),
    ("每日計劃", t_setups),
    ("RS板", t_rsboard),
]


def _meta_rows():
    return [
        ["產生器", "trading-os-web/site_db.py"],
        ["跑嘅時間（本機）", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["數據日", _latest_data_date()],
        ["URL", "https://desmondddkey.github.io/trading-desk/"],
        ["Missing ≠ Zero 政策",
         f"缺數一律寫 {NA}，唔准填 0 或空白（EDGE-016）"],
        ["唯一實作政策",
         "每張表嘅數字呼叫既有 module（daily_plan／rotation_map／cm／"
         "nel_pages…），呢個檔唔重算任何公式（EDGE-036）"],
    ]


def _latest_data_date():
    h = _jload(os.path.join(LAB, "output", "rotation_history.json")) or {}
    return h.get("data_date") or datetime.date.today().isoformat()


def _style(ws):
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    hdr_fill = PatternFill("solid", fgColor="1F3864")
    hdr_font = Font(bold=True, color="FFFFFF")
    for c in ws[1]:
        c.fill, c.font = hdr_fill, hdr_font
        c.alignment = Alignment(vertical="center", wrap_text=True)
    widths = {}
    for row in ws.iter_rows():
        for c in row:
            if c.value is None:
                continue
            L = min(30, max(len(str(c.value)), 6))
            widths[c.column] = max(widths.get(c.column, 8), L + 2)
    for col, w in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def build_snapshot(day=None):
    from openpyxl import Workbook
    day = day or _latest_data_date()
    wb = Workbook()
    ws = wb.active
    ws.title = "說明"
    ws.append(["項目", "值"])
    for k, v in _meta_rows():
        ws.append([k, v])
    ws.append(["表", "內容"])
    for name, _ in TABLES:
        ws.append([name, ""])
    _style(ws)

    ok, fail = [], []
    for name, fn in TABLES:
        try:
            hdr, rows = fn()
        except Exception as e:                               # noqa: BLE001
            log(f"  ✗ {name}：{type(e).__name__}: {e}")
            hdr, rows = ["錯誤"], [[f"{type(e).__name__}: {e}"]]
            fail.append(name)
        else:
            ok.append(name)
        ws2 = wb.create_sheet(name[:31])
        ws2.append(hdr)
        for r in rows:
            ws2.append(r)
        _style(ws2)
    os.makedirs(DBDIR, exist_ok=True)
    p = os.path.join(DBDIR, f"site_db_{day}.xlsx")
    wb.save(p)
    return p, day, ok, fail


def append_history(day=None):
    """累積歷史：每日一行摘要（唔覆蓋舊嘅）。"""
    from openpyxl import Workbook, load_workbook
    day = day or _latest_data_date()
    p = os.path.join(DBDIR, "site_db_history.xlsx")
    os.makedirs(DBDIR, exist_ok=True)
    if os.path.exists(p):
        wb = load_workbook(p)
        ws = wb["歷史"] if "歷史" in wb.sheetnames else wb.create_sheet("歷史")
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "歷史"
        ws.append(["數據日", "跑嘅時間", "領導股數", "最強1週數", "1CM A級數",
                   "行業數", "行業最強", "Breadth ADL", "Breadth %40MA",
                   "群組候選數", "COT 最擁擠"])
    exist = {ws.cell(r, 1).value for r in range(2, ws.max_row + 1)}
    if day in exist:
        log(f"  ⏭ 歷史已有 {day}（冪等，唔重覆加）")
    else:
        row = [day, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")]
        for name, fn in TABLES:
            try:
                hdr, rows = fn()
            except Exception:                                # noqa: BLE001
                rows = []
            if name == "領導股":
                row.append(len(rows))
            elif name == "最強1週":
                row.append(len(rows))
            elif name == "1CM回調":
                row.append(sum(1 for r in rows if isinstance(r[1], str)
                               and r[1].startswith("A")))
            elif name == "行業輪動":
                row.append(len(rows))
                row.append(rows[0][1] if rows else NA)
            elif name == "Breadth":
                m = {r[0]: r[1] for r in rows}
                row.append(m.get("ADL", NA))
                row.append(m.get("% above 40MA", NA))
            elif name == "群組動量":
                row.append(len(rows))
            elif name == "Positioning":
                row.append(rows[0][0] if rows else NA)
        ws.append(row)
        _style(ws)
    wb.save(p)
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description="網站數據 → Excel database")
    ap.add_argument("--no-history", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    if a.list:
        for n, _ in TABLES:
            print(n)
        return 0
    p, day, ok, fail = build_snapshot()
    log(f"✓ {p}")
    log(f"  {len(ok)} 張表 OK｜{len(fail)} 張失敗"
        + (f"：{', '.join(fail)}" if fail else ""))
    if not a.no_history:
        hp = append_history(day)
        log(f"✓ {hp}")
    print(json.dumps({"xlsx": p, "data_date": day,
                      "tables_ok": ok, "tables_failed": fail},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
