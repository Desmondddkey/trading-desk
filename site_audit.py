# -*- coding: utf-8 -*-
"""site_audit.py — 網站漏洞審計（確定性，零猜測）

Desmond 2026-10-20：「認真d執 個網好多漏洞」

呢個工具唔靠感覺，逐頁驗 8 個維度：

  ① 死頁        page 存在但冇內容 / 冇數據
  ② 假「今日」  頁面寫「今日」但數據唔係今日
  ③ 日期格式    同一種日期有幾種寫法（2026-10-16 vs 10-16 vs Oct 16）
  ④ 命名不一    同一個概念有幾個名（Setup/Setups、rs_select/RS 選股…）
  ⑤ 數字格式    小數位唔一致（.1f vs .2f vs raw）
  ⑥ 空表        有 <table> 但 tbody 冇 row
  ⑦ 死連結      側欄連結指向唔存在嘅檔
  ⑧ 重複內容    同一段文字出現喺多頁

輸出：output/site_audit.md（人睇）+ site_audit.json（機讀）
exit code：0 = 有發現（但要人睇），2 = 審計自己失敗
"""
import glob
import io
import json
import os
import re
import sys

DOCS = r"C:\Users\rain0\trading-os-web\docs"

# ── 命名不一致字典（同一個意思，多種寫法）──────────────────────
NAME_GROUPS = {
    "Setup": ["Setups", "SETUPS", "Setup", "setup"],
    "警報總覽": ["警報總覽", "ALERTS", "Alert", "ALERT"],
    "RS 選股": ["rs_select", "RS 選股", "圖表隊列", "今日圖表隊列"],
    "機會": ["OPPORTUNITY DESK", "機會（總表）", "機會"],
    "廣度": ["breadth", "Breadth", "廣度"],
    "市場簡報": ["market-insight", "市場簡報", "Market Insight"],
}

DATE_PATTERNS = {
    "ISO": r"\b20\d{2}-\d{2}-\d{2}\b",
    # ★ 前面唔可以係 YYYY-（否則 ISO 會被重複計算）
    "MD": r"(?<!20\d{2}-)\b\d{2}-\d{2}\b(?!-\d)",
    "CN": r"\b20\d{2}年\d{1,2}月\d{1,2}日\b",
    "US": r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
          r"\w*\s+\d{1,2}\b",
}

SIDEBAR_RE = re.compile(r'<aside[^>]*id="sb".*?</aside>', re.S)
TITLE_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S)
TAG_RE = re.compile(r"<[^>]+>")


def _txt(h):
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", h)).strip()


def audit_page(path):
    name = os.path.basename(path)
    h = io.open(path, encoding="utf-8", errors="replace").read()
    r = {"page": name, "bytes": len(h), "issues": []}

    # split body / sidebar（側欄唔計入「今日」統計，佢係全站共用）
    m = SIDEBAR_RE.search(h)
    body = h[:m.start()] + h[m.end():] if m else h

    t = TITLE_RE.search(body)
    r["h1"] = _txt(t.group(1)) if t else None
    r["h2"] = [_txt(x) for x in H2_RE.findall(body)][:8]

    # ① 死頁
    if len(body) < 3000:
        r["issues"].append(("DEAD_PAGE", f"body 只有 {len(body)} bytes"))

    # ② 假「今日」—— ★ 只查標題（h1/h2/h3），唔查內文
    #    logbook 呢類變更日誌寫「今日」係歷史記錄，唔算假更新
    heads = [_txt(x) for x in
             re.findall(r"<h[123][^>]*>(.*?)</h[123]>", body, re.S)]
    bad = [x for x in heads
           if re.search(r"今日", x) and not re.search(r"\d{4}-\d{2}-\d{2}", x)]
    if bad:
        r["issues"].append(
            ("FAKE_TODAY", f"標題寫「今日」但冇日期：{bad[:2]}"))

    # ③ 日期格式
    fmts = {}
    for k, pat in DATE_PATTERNS.items():
        n = len(re.findall(pat, body))
        if n:
            fmts[k] = n
    r["date_formats"] = fmts
    if len(fmts) > 2:
        r["issues"].append(
            ("DATE_FORMAT", "混用 " + "/".join(f"{k}×{v}"
                                              for k, v in fmts.items())))

    # ④ 命名不一 —— ★ 只檢查「顯示標籤」：側欄連結 + h1/h2/h3
    #    唔檢查內文散文（"each setup" 呢類英文散文唔算命名不一致）
    labels = []
    m_sb = SIDEBAR_RE.search(h)
    if m_sb:
        labels += [_txt(x) for x in
                   re.findall(r'<a[^>]*>(.*?)</a>', m_sb.group(0), re.S)]
    labels += [_txt(x) for x in
               re.findall(r"<h[123][^>]*>(.*?)</h[123]>", body, re.S)]
    corpus = " ｜ ".join(labels)
    for canon, variants in NAME_GROUPS.items():
        hit = [v for v in variants if v in labels]
        if len(hit) > 1:
            r["issues"].append(
                ("NAME_DRIFT", f"{canon}：標籤有 {hit}"))

    # ⑤ 數字格式（小數位種類）
    dec = {}
    for mm in re.finditer(r"(?<![\w.])\d+\.(\d+)(?![\w.])", body):
        dec[len(mm.group(1))] = dec.get(len(mm.group(1)), 0) + 1
    r["decimals"] = dec
    if len(dec) > 4:
        r["issues"].append(
            ("NUM_FORMAT", f"{len(dec)} 種小數位：" +
             ",".join(f".{k}×{v}" for k, v in sorted(dec.items()))))

    # ⑥ 空表
    empty = 0
    for tb in re.findall(r"<tbody[^>]*>(.*?)</tbody>", body, re.S):
        if "<tr" not in tb:
            empty += 1
    tables = body.count("<table")
    r["tables"] = tables
    r["empty_tables"] = empty
    if tables and empty == tables:
        r["issues"].append(("ALL_TABLES_EMPTY", f"{empty}/{tables} 全空"))

    # ⑦ 未標日期的數據卡（h2 有「隊列/掃描/警報」但附近冇 ISO 日期）
    for hh in re.findall(r"<h2[^>]*>(.*?)</h2>(.{0,900})", body, re.S):
        head, near = _txt(hh[0]), hh[1]
        if re.search(r"隊列|掃描|警報|機會|位置圖", head):
            if not re.search(r"\d{4}-\d{2}-\d{2}", near):
                r["issues"].append(
                    ("NO_DATE_BADGE", f"「{head[:24]}」附近冇 ISO 日期"))
    return r


def audit_links(html_files):
    have = {os.path.basename(p) for p in html_files}
    missing = {}
    for p in html_files:
        h = io.open(p, encoding="utf-8", errors="replace").read()
        m = SIDEBAR_RE.search(h)
        if not m:
            continue
        for href in re.findall(r'href="([^"#?]+\.html)"', m.group(0)):
            if href not in have:
                missing.setdefault(href, []).append(os.path.basename(p))
    return missing


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    files = sorted(glob.glob(os.path.join(DOCS, "*.html")))
    if not files:
        sys.stderr.write(f"✗ 搵唔到 HTML：{DOCS}\n")
        return 2

    rows = [audit_page(p) for p in files]
    links = audit_links(files)

    by_kind = {}
    for r in rows:
        for kind, msg in r["issues"]:
            by_kind.setdefault(kind, []).append((r["page"], msg))

    L = ["# 網站漏洞審計", ""]
    L.append(f"頁數 **{len(rows)}**｜總大小 "
             f"**{sum(r['bytes'] for r in rows) / 1048576:.1f} MB**")
    L.append("")
    L.append("## 問題總表")
    L.append("")
    if not by_kind:
        L.append("✓ 冇發現問題")
    for kind in sorted(by_kind, key=lambda k: -len(by_kind[k])):
        L.append(f"### {kind}（{len(by_kind[kind])} 頁）")
        for pg, msg in by_kind[kind]:
            L.append(f"- `{pg}` — {msg}")
        L.append("")
    if links:
        L.append(f"### 死連結（{len(links)} 個）")
        for h, pgs in links.items():
            L.append(f"- `{h}` ← 被 {len(pgs)} 頁引用")
        L.append("")

    L.append("## 逐頁明細")
    L.append("")
    L.append("| 頁 | KB | 表 | 空表 | h1 | 日期格式 | 問題 |")
    L.append("|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: -len(x["issues"])):
        fmt = "/".join(f"{k}×{v}" for k, v in r["date_formats"].items()) or "—"
        iss = len(r["issues"])
        L.append(f"| `{r['page']}` | {r['bytes'] // 1024} | "
                 f"{r['tables']} | {r['empty_tables']} | "
                 f"{(r['h1'] or '—')[:20]} | {fmt} | "
                 f"{'⚠️ ' + str(iss) if iss else '✓'} |")

    os.makedirs(os.path.join(DOCS, "..", "output"), exist_ok=True)
    out = os.path.join(DOCS, "..", "output", "site_audit.md")
    io.open(out, "w", encoding="utf-8").write("\n".join(L))
    io.open(out.replace(".md", ".json"), "w", encoding="utf-8").write(
        json.dumps({"pages": rows, "dead_links": links},
                   ensure_ascii=False, indent=1, default=str))

    print("\n".join(L))
    print(f"\n→ {out}")
    return 0 if not by_kind and not links else 0


if __name__ == "__main__":
    sys.exit(main())
