# -*- coding: utf-8 -*-
"""split_desk.py — 將「機會」頁拆返三個獨立頁

Desmond 2026-10-20：「呢張圖唔洗再出 website
將 1同2修改返去指定地方」

原本 dashboard.py 生成一張大頁（desk.html，634 KB）內含三塊：
  ① 📍 RS Leader 位置圖
  ② 🔄 行業輪動
  ③ ⚠️ ATRX 風險

拆成：
  leadermap.html  ← ①（側欄「RS Leader 位置圖」）
  sectors.html    ← ②（側欄「Sectors」）
  atrxrisk.html   ← ③（側欄「ATRX 風險」，新）

做法：喺 dashboard 產出嘅 HTML 用 <h2> 標記切片，
每片保留原 CSS + 圖表（SVG），再套網站側欄。
"""
import io
import os
import re
import sys

WEB = r"C:\Users\rain0\trading-os-web"
LAB = r"C:\Users\rain0\trading-os-lab\output"
DOCS = os.path.join(WEB, "docs")

# 三塊嘅起始標記（dashboard.py 產出嘅 h2 文字）
MARKS = {
    "leadermap": "RS Leader 位置圖",
    "sectors": "行業輪動",
    "atrxrisk": "ATRX 風險",
}


def newest_dashboard():
    import glob
    c = sorted(glob.glob(os.path.join(LAB, "dashboard_*.html")))
    return c[-1] if c else None


def split(html):
    """按 h2 位置切成三段。回 {key: html_string}。"""
    # 搵所有 <h2 ...>...</h2> 嘅位置
    pos = []
    for m in re.finditer(r"<h2[^>]*>(.*?)</h2>", html, re.S):
        raw = re.sub(r"<[^>]+>", "", m.group(1))
        pos.append((m.start(), raw.strip()))
    if len(pos) < 2:
        return {}

    # 每段 = 由自己 h2 到下一個 h2（最後一段到 </div> 結尾）
    segs = {}
    for i, (st, title) in enumerate(pos):
        ed = pos[i + 1][0] if i + 1 < len(pos) else len(html)
        segs[title] = html[st:ed]
    return segs


def pick(segs, needle):
    for t, s in segs.items():
        if needle in t:
            return s
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    src = newest_dashboard()
    if not src:
        sys.stderr.write("✗ 搵唔到 dashboard_*.html\n")
        return 2
    html = io.open(src, encoding="utf-8", errors="replace").read()
    # 攞 <style> 全部（保持圖表外觀）
    styles = "".join(re.findall(r"<style[^>]*>.*?</style>", html, re.S))
    segs = split(html)
    if not segs:
        sys.stderr.write("✗ 切唔開（冇 h2）\n")
        return 2

    print(f"來源：{os.path.basename(src)}")
    print(f"切出 {len(segs)} 段：")
    for t in segs:
        print(f"  · {t[:40]}")

    out = {}
    for key, needle in MARKS.items():
        body = pick(segs, needle)
        if body is None:
            sys.stderr.write(f"⚠ 搵唔到「{needle}」\n")
            continue
        out[key] = body
    # 寫入暫存，等 build_site 讀
    p = os.path.join(WEB, "cache", "desk_parts.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    import json
    json.dump({"styles": styles, "parts": out,
               "src": os.path.basename(src)},
              io.open(p, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"\n→ {p}")
    for k, v in out.items():
        print(f"  {k:<12} {len(v)//1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
