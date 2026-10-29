# -*- coding: utf-8 -*-
"""audit_ui.py — 全站排版／可讀性／一致性審計（捉行為，唔係捉文字）

每個 HTML 頁計 9 個指標：
  1. tiny_fonts    font-size < 11.5px 嘅出現次數（手機睇唔到）
  2. long_rules    連續 ≥10 個 ━ ─ = — 嘅分隔線（視覺噪音）
  3. dup_heads     同頁重複嘅 h2/h3 文字（同一件事講兩次）
  4. inline_styles  inline style 屬性數量（越高越難一致化）
  5. viewport      有冇 meta viewport（手機縮放）
  6. unwrapped_tbl <table> 冇 overflow-x 容器（手機爆版）
  7. palette       頁面用到嘅 hex 色數量（越少越一致）
  8. important     !important 次數
  9. maxwidth      有冇 max-width 容器（超闊螢幕行長）

用法：python audit_ui.py [--json] [--top N]
"""
from __future__ import annotations

import argparse
import glob
import html as _h
import io
import json
import os
import re
from collections import Counter

DOCS = r"C:/Users/rain0/trading-os-web/docs"
OUT = r"C:/Users/rain0/trading-os/output/ui_audit.json"

RE_TINY = re.compile(r"font-size:\s*([0-9.]+)px")
RE_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
RE_H2 = re.compile(r"<h([23])[^>]*>(.*?)</h\1>", re.S)
RE_STYLE_ATTR = re.compile(r'\sstyle="')
RE_TABLE = re.compile(r"<table[^>]*>", re.I)
RE_RULE = re.compile(r"[━─═—]{10,}")


def _text(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def audit(path):
    c = io.open(path, encoding="utf-8", errors="ignore").read()
    name = os.path.basename(path)

    tiny = sum(1 for v in RE_TINY.findall(c) if float(v) < 11.5)
    rules = len(RE_RULE.findall(c))

    heads = [_text(m[1]) for m in RE_H2.findall(c)]
    dup = sum(n - 1 for n in Counter(heads).values() if n > 1)

    inline = len(RE_STYLE_ATTR.findall(c))
    viewport = 'name="viewport"' in c

    # table 前面 300 字內有冇 overflow-x 容器
    unwrapped = 0
    for m in RE_TABLE.finditer(c):
        head = c[max(0, m.start() - 400):m.start()]
        if ("overflow-x" not in head and "overflow:auto" not in head.replace(" ", "")
                and "tscroll" not in head):
            unwrapped += 1

    palette = len(set(x.lower() for x in RE_HEX.findall(c)))
    important = c.count("!important")
    maxw = "max-width" in c

    return {
        "page": name, "kb": round(len(c) / 1024, 1),
        "tiny_fonts": tiny, "long_rules": rules, "dup_heads": dup,
        "inline_styles": inline, "viewport": viewport,
        "unwrapped_tables": unwrapped, "palette": palette,
        "important": important, "maxwidth": maxw,
    }


def score(r):
    """越高越差（0 = 乾淨）。"""
    s = 0
    s += min(r["tiny_fonts"], 40) * 1.0
    s += min(r["long_rules"], 10) * 1.5
    s += r["dup_heads"] * 3
    s += min(r["inline_styles"] / 40.0, 15)
    s += 0 if r["viewport"] else 20
    s += min(r["unwrapped_tables"], 8) * 2
    s += max(0, r["palette"] - 12) * 0.4
    s += min(r["important"] / 10.0, 6)
    s += 0 if r["maxwidth"] else 4
    return round(s, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top", type=int, default=15)
    a = ap.parse_args()

    files = [f for f in glob.glob(os.path.join(DOCS, "*.html"))
             if not os.path.basename(f).startswith(("dailyscan_2026-", "rsscan_2026-"))]
    rows = []
    for f in files:
        try:
            r = audit(f)
        except Exception:                                    # noqa: BLE001
            continue
        r["score"] = score(r)
        rows.append(r)
    rows.sort(key=lambda r: -r["score"])

    summary = {
        "pages": len(rows),
        "avg_score": round(sum(r["score"] for r in rows) / len(rows), 1) if rows else 0,
        "tiny_total": sum(r["tiny_fonts"] for r in rows),
        "rules_total": sum(r["long_rules"] for r in rows),
        "dup_total": sum(r["dup_heads"] for r in rows),
        "missing_viewport": [r["page"] for r in rows if not r["viewport"]],
        "unwrapped_total": sum(r["unwrapped_tables"] for r in rows),
        "rows": rows,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    if a.json:
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        return 0

    print(f"頁數 {summary['pages']}｜平均分 {summary['avg_score']}（越低越好）")
    print(f"細字 <11.5px 合計 {summary['tiny_total']}｜長分隔線 {summary['rules_total']}"
          f"｜重複標題 {summary['dup_total']}｜冇包裝表格 {summary['unwrapped_total']}")
    print(f"冇 viewport：{summary['missing_viewport'] or '冇'}")
    print("\n最需要修（分數高→低）：")
    for r in rows[:a.top]:
        print(f"  {r['score']:>6.1f}  {r['page']:<28} 細字{r['tiny_fonts']:>3}"
              f" 長線{r['long_rules']:>2} 重複{r['dup_heads']:>2}"
              f" inline{r['inline_styles']:>4} 色{r['palette']:>3} 表{r['unwrapped_tables']:>2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
