# -*- coding: utf-8 -*-
"""finish_line.py — 網站「收工標準」頁（Definition of Done）

Desmond 2026-10-24：「我覺得改呢個網要有一個終點，執好哂我就唔 UPDATE，
等你跑數，睇你表演。」

→ 呢頁唔係願望清單，係**機器自動檢查**出嚟嘅勾表：
   每一項都由 docs/*.html 同 output/*.json 實際內容讀出嚟，
   唔係手寫承諾。全部 ✅ = 你唔需要再改網站。
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")
OUT = r"C:/Users/rain0/trading-os/output"
WEB_DATA = os.path.join(HERE, "data")

# 文件 → (叫咩名, 必要特徵)
PAGES = {
    "process.html": ("每日流程", ["EXT 階段", "9:30 READY"]),
    "rsscan.html": ("RS Daily Scan", ["rs-nav", "rs-xnote", "EXT"]),
    "dailyscan.html": ("Daily Scan", ["評分", "DAY ON"]),
    "rsboard.html": ("RS THEME", ["rtSort", "EXT"]),
    "week.html": ("Weekly MM", ["EXT"]),
    "sectors.html": ("Sectors", ["行業輪動"]),
}
FRESH = [
    (os.path.join(OUT, "rs_alpha_latest.json"), "EXT 階段數據", 3),
    (os.path.join(WEB_DATA, "market_scan.json"), "市場掃描", 3),
    (os.path.join(OUT, "model_book", "top250.json"), "Top 250", 10),
]


def _read(name):
    p = os.path.join(DOCS, name)
    if not os.path.exists(p):
        return None
    return io.open(p, encoding="utf-8", errors="replace").read()


def check_tables():
    """每張表：表頭格數 == 第一行格數（走位 = 兩者唔同）。"""
    bad, n = [], 0
    for f in sorted(glob.glob(os.path.join(DOCS, "*.html"))):
        c = io.open(f, encoding="utf-8", errors="replace").read()
        for i, tab in enumerate(re.findall(r"<table[^>]*>(.*?)</table>", c, re.S)):
            th = re.search(r"<thead>(.*?)</thead>", tab, re.S)
            tb = re.search(r"<tbody[^>]*>(.*?)</tbody>", tab, re.S)
            if not th or not tb:
                continue
            n += 1
            nh = len(re.findall(r"<th", th.group(1)))
            row = re.search(r"<tr[^>]*>(.*?)</tr>", tb.group(1), re.S)
            if not row:
                continue
            nd = len(re.findall(r"<td", row.group(1)))
            # colspan 合併列（例如分組標題）唔算走位
            if "colspan" in row.group(1):
                continue
            if nh != nd:
                bad.append(f"{os.path.basename(f)} #{i+1}: 表頭 {nh}／行 {nd}")
    return n, bad


def check_features():
    out = []
    for name, (label, feats) in PAGES.items():
        c = _read(name)
        if c is None:
            out.append((label, False, "檔案未生成"))
            continue
        miss = [f for f in feats if f not in c]
        has_date = bool(re.search(r"20\d\d-\d\d-\d\d", c))
        ok = (not miss) and has_date
        why = ("缺：" + "、".join(miss)) if miss else ("" if has_date else "冇日期")
        out.append((label, ok, why))
    return out


def check_fresh():
    import datetime
    out = []
    for path, label, days in FRESH:
        if not os.path.exists(path):
            out.append((label, False, "檔案唔存在"))
            continue
        mt = datetime.date.fromtimestamp(os.path.getmtime(path))
        age = (datetime.date.today() - mt).days
        out.append((label, age <= days, f"{age} 日前"))
    return out


CSS = """
.fl-h{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:0 0 4px}
.fl-h h2{margin:0;font-size:19px}
.fl-sub{font-size:11.5px;opacity:.62}
.fl-score{font-size:26px;font-weight:800;margin:8px 0 2px}
.fl-bar{height:10px;border-radius:5px;background:rgba(128,128,128,.2);
  overflow:hidden;margin:4px 0 14px}
.fl-bar>i{display:block;height:100%;background:#22c55e}
.fl-sec{font-size:12.5px;font-weight:800;margin:14px 0 6px;opacity:.75}
.fl-tbl{width:100%;border-collapse:collapse;font-size:12.5px;text-align:left}
.fl-tbl td{padding:4px 6px;border-bottom:1px solid rgba(128,128,128,.1);
  text-align:left}
.fl-ok{color:#22c55e;font-weight:800}
.fl-no{color:#ef4444;font-weight:800}
.fl-why{opacity:.6;font-size:11.5px}
.fl-note{font-size:11.5px;opacity:.7;line-height:1.8;margin-top:10px}
"""


def build():
    ntab, bad = check_tables()
    feats = check_features()
    fresh = check_fresh()

    items = []
    items.append(("表格欄數一致（防走位）", not bad,
                  f"{ntab} 張表" + (f"｜{len(bad)} 張唔一致" if bad else "")))
    items += feats
    items += fresh
    ok_n = sum(1 for _l, o, _w in items if o)
    tot = len(items)
    pct = ok_n / tot * 100 if tot else 0

    P = [f"<style>{CSS}</style>", '<div class="card">']
    P.append('<div class="fl-h"><h2>🎯 收工標準（Definition of Done）</h2>'
             '<span class="fl-sub">機器自動檢查，唔係手寫承諾｜每次 build 重算</span></div>')
    P.append(f'<div class="fl-score" style="color:'
             f'{"#22c55e" if pct >= 100 else "#f59e0b"}">{ok_n}/{tot}</div>')
    P.append(f'<div class="fl-bar"><i style="width:{pct:.0f}%"></i></div>')

    for title, rows in (("頁面完成度", items[:1 + len(feats)]),
                        ("數據新鮮度", items[1 + len(feats):])):
        P.append(f'<div class="fl-sec">{title}</div>')
        P.append('<table class="fl-tbl">')
        for label, ok, why in rows:
            mark = '<span class="fl-ok">✅</span>' if ok else '<span class="fl-no">❌</span>'
            P.append(f'<tr><td>{mark}</td><td>{label}</td>'
                     f'<td class="fl-why">{why}</td></tr>')
        P.append('</table>')

    if bad:
        P.append('<div class="fl-sec">走位明細</div><table class="fl-tbl">')
        for b in bad[:12]:
            P.append(f'<tr><td class="fl-no">❌</td><td colspan="2">{b}</td></tr>')
        P.append('</table>')

    P.append(
        '<div class="fl-note">'
        '<b>終點定義：</b>上面全部 ✅ = 網站唔需要再改，Desmond 停止改版，'
        '由 Hermes 每日跑數。<br>'
        '<b>之後我做咩：</b>每週出 Champion 曲線 vs SPY、規則 A/B（shadow_exit）、'
        '寫入 EDGE_BOOK；每月對照 USIC 目標（≥ +5%）；每季淘汰負 edge 規則'
        '（改風控 = 單向門，要你批）。<br>'
        '<b>我唔會承諾：</b>保證賺錢。regime 轉熊 = 0 單，'
        '呢個係設計，唔係失敗。<br>'
        '<b>檢查範圍：</b>表格對齊（全部 docs/*.html）、每頁必要元素、'
        '數據檔案年齡。測試同 cron 健康由 kitchen-watchdog 負責，唔喺呢頁重複。'
        '</div>')
    P.append('</div>')
    return ("收工標準", "".join(P))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    t, b = build()
    print(f"✓ {t} — {len(b):,} 字")
    n, bad = check_tables()
    print(f"表格 {n} 張｜唔一致 {len(bad)}")
    for x in bad[:5]:
        print("  ", x)


if __name__ == "__main__":
    main()
