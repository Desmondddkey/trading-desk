# -*- coding: utf-8 -*-
"""theme_guard.py — 深色模式隱形字守門（Desmond 2026-11-07：「下次唔可以再有」）

病因：頁面寫死淺色卡（background:#fff / #f6f3ec…），但深色主題預設字係淺色
→ 白底白字，字消失。

做法（快、無瀏覽器）：掃 docs/*.html 內 <style> 嘅 CSS 規則
  · 有淺色背景、同一條規則冇指定 color → 可疑
  · 跳過 html[data-theme="light"] 前綴（呢啲係刻意嘅淺色主題覆寫）
exit 1 = 有可疑規則（可以掛 cron／build gate）
"""
from __future__ import annotations

import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "docs")
LIGHT = ("#fff", "#ffffff", "white", "#fafafa", "#f8f8f8", "#f6f3ec", "#f2eee5", "#fffdf6")
STYLE = re.compile(r"<style[^>]*>(.*?)</style>", re.S)


def scan(path):
    html = io.open(path, encoding="utf-8", errors="ignore").read()
    bad = []
    for m in STYLE.finditer(html):
        for chunk in m.group(1).split("}"):
            if "{" not in chunk:
                continue
            sel, body = chunk.split("{", 1)
            sel = sel.strip()
            if not sel or sel.startswith("html[data-theme"):
                continue
            low = body.lower().replace(" ", "")
            if not any(k in low for k in LIGHT):
                continue
            if "color:" in low or "background-image" in low:
                continue
            # iframe（嵌外部頁）／圓角 chip（顏色由父層繼承）→ 唔算
            if "height:" in low and "border:0" in low:
                continue
            if "border-radius:999px" in low or "border-radius:9999px" in low:
                continue
            if re.search(r"frame", sel, re.I):
                continue
            if sel.endswith("pre") or sel.endswith("code"):
                continue
            # 只報「文字容器」（卡／summary／panel／框）；th/td/pre 通常喺已修好嘅卡內
            if not re.search(r"card|summary|panel|frame|article|\.art|skbody|jb-", sel, re.I):
                continue
            bad.append(sel[:80])
    return bad


def main(argv=None):
    quiet = "--quiet" in (sys.argv[1:] if argv is None else argv)
    files = sorted(glob.glob(os.path.join(SITE, "*.html")))
    total = 0
    for f in files:
        bad = scan(f)
        if not bad:
            continue
        total += len(bad)
        if not quiet:
            print(""); print(os.path.basename(f))
        for sel in bad[:5]:
            print("  ✗ " + sel)
    print(""); print(("FAIL" if total else "OK") + f"：{total} 條可疑淺底規則（{len(files)} 頁）")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
