# -*- coding: utf-8 -*-
"""ui_tokens.py — 一次性把 CSS 收成一套 token（design-taste-frontend V1/V2/V3/V6）

問題（實測）：每頁圓角 7–10 種、字級 16–18 種、殘留陰影 7–10 處。
做法：只改 .py 內嵌 CSS 字面值，唔改 HTML 結構、唔改資料。

  V1 圓角   7/8/9/11/12 → 8；      10 保留；≥16 → 999（pill）
  V2 字級   收成 8 級：10 / 10.5 / 11.5 / 12.5 / 14 / 17 / 20 / 26
  V3 陰影   只保留「浮層」兩個（sticky nav / dropdown），其餘刪

用法：
  python ui_tokens.py --dry     # 只印會改幾多處
  python ui_tokens.py           # 實際寫入
"""
import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = [f for f in os.listdir(HERE) if f.endswith(".py")]

SCALE = [10, 10.5, 11.5, 12.5, 14, 17, 20, 26, 34]
RADIUS = {7: 8, 8: 8, 9: 8, 11: 10, 12: 10, 13: 10}

FS = re.compile(r"font-size:([\d.]+)px")
BR = re.compile(r"border-radius:(\d+)px")
SH = re.compile(r"box-shadow:[^;\"'}\n]+;?")


def near(v):
    return min(SCALE, key=lambda s: abs(s - v))


def transform(txt):
    n = {"fs": 0, "br": 0, "sh": 0}

    def _fs(m):
        v = float(m.group(1))
        nv = near(v)
        if abs(nv - v) > 0.01:
            n["fs"] += 1
            return f"font-size:{('%g' % nv)}px"
        return m.group(0)

    def _br(m):
        v = int(m.group(1))
        if v >= 16:
            if v != 999:
                n["br"] += 1
                return "border-radius:999px"
            return m.group(0)
        nv = RADIUS.get(v, v)
        if nv != v:
            n["br"] += 1
        return f"border-radius:{nv}px"

    def _sh(m):
        s = m.group(0)
        if "inset" in s or "sticky" in s:
            return s
        n["sh"] += 1
        return ""

    txt = FS.sub(_fs, txt)
    txt = BR.sub(_br, txt)
    txt = SH.sub(_sh, txt)
    return txt, n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    tot = {"fs": 0, "br": 0, "sh": 0}
    touched = 0
    for f in sorted(FILES):
        if f in ("ui_tokens.py",):
            continue
        p = os.path.join(HERE, f)
        try:
            txt = io.open(p, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        new, n = transform(txt)
        if new != txt:
            touched += 1
            for k in tot:
                tot[k] += n[k]
            if not a.dry:
                io.open(p, "w", encoding="utf-8", newline="\n").write(new)
    print(f"{'DRY ' if a.dry else ''}檔案 {touched}｜字級 {tot['fs']}｜"
          f"圓角 {tot['br']}｜陰影 {tot['sh']}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
