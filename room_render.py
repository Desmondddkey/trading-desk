# -*- coding: utf-8 -*-
"""room_render.py — 畫「系統房間」深／淺兩版（1600×900 SVG → PNG 由瀏覽器截）

用法：python room_render.py        # 出 docs/room_dark.png 用嘅 room_dark.html / room_light.html
（PNG 由 browser 截；呢支只負責 SVG，確保兩版同一構圖、只換色）
"""
from __future__ import annotations

import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1600, 900

DARK = dict(bg="#05080d", wall_l="#0d141d", wall_r="#0a1119", floor="#080e15", ceil="#0b1119",
            edge="#1e2c3f", txt="#e8eef8", mut="#8ba0bd", red="#c0554a", grn="#2f8f5b",
            gold="#c2a04a", card="#0d1622", card2="#0e1826", screen="#080e16", pool="#16324a")
LIGHT = dict(bg="#f4f1ea", wall_l="#ffffff", wall_r="#f7f5ef", floor="#e9e4d9", ceil="#faf8f3",
             edge="#d6d0c4", txt="#1f1e1d", mut="#5f5c54", red="#b04a3e", grn="#2f7d52",
             gold="#9a7b2e", card="#ffffff", card2="#faf8f3", screen="#ffffff", pool="#dcd6c8")


def render(theme="dark"):
    C = DARK if theme == "dark" else LIGHT
    P = []

    def poly(pts, fill, op=1):
        P.append(f'<polygon points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="{fill}" opacity="{op}"/>')

    def t(x, y, s, size=18, fill=None, weight="400", anchor="start", op=1):
        fill = fill or C["txt"]
        P.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
                 f'text-anchor="{anchor}" opacity="{op}" '
                 f'font-family="Segoe UI,Microsoft JhengHei,sans-serif">{s}</text>')

    def card(x, y, w, h, fill=None, r=10):
        P.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill or C["card"]}" '
                 f'stroke="{C["edge"]}" stroke-width="1"/>')

    P.append(f'<rect width="{W}" height="{H}" fill="{C["bg"]}"/>')
    poly([(0, 0), (W, 0), (980, 300), (620, 300)], C["ceil"])
    poly([(0, H), (W, H), (980, 600), (620, 600)], C["floor"])
    poly([(0, 0), (620, 300), (620, 600), (0, H)], C["wall_l"])
    poly([(W, 0), (980, 300), (980, 600), (W, H)], C["wall_r"])
    poly([(620, 300), (980, 300), (980, 600), (620, 600)], C["screen"])
    P.append(f'<ellipse cx="800" cy="760" rx="520" ry="120" fill="{C["pool"]}" opacity="0.35"/>')

    t(800, 110, "深色主題 · 冇白底白字", 15, C["mut"], "700", "middle")
    t(800, 140, "止蝕係入場費，唔係懲罰", 13, C["mut"], "400", "middle", 0.85)

    for x, lab, val, col in [(648, "QQQ", "RISK OFF", C["red"]),
                             (762, "MM MODEL", "48 / 100", C["mut"]),
                             (876, "ROTATION", "XLV 100", C["grn"])]:
        card(x, 318, 100, 128, C["screen"])
        t(x + 8, 338, lab, 11, C["mut"], "700")
        t(x + 50, 382, val, 14, col, "800", "middle")
        for i in range(5):
            P.append(f'<rect x="{x + 9}" y="{396 + i * 8}" width="{82 - i * 12}" height="3" '
                     f'rx="1.5" fill="{col}" opacity="{0.35 - 0.05 * i:.2f}"/>')
    t(800, 478, "17:10", 30, C["txt"], "800", "middle")
    t(800, 500, "collector → 18:00 前更新", 11, C["mut"], "400", "middle")

    card(60, 235, 420, 265)
    t(82, 268, "1,279 單 · 真實帳戶", 19, C["txt"], "800")
    for i, (a, b, c) in enumerate([("<30 分鐘　631 單", "−19,317", C["red"]),
                                   ("SNDK　35 次", "−8,470", C["red"]),
                                   ("贏輸比", "1.68 : 1", C["gold"])]):
        y = 310 + i * 40
        t(82, y, a, 14, C["mut"])
        t(456, y, b, 15, c, "800", "end")
    t(82, 432, "唔係輸喺揀股，係輸喺倉位。", 15, C["txt"], "700")
    t(82, 458, "倉位 = 風險% ÷ 止蝕%", 12, C["mut"])

    card(1110, 225, 425, 290)
    t(1132, 256, "四把聲", 19, C["txt"], "800")
    for i, (n, q, c) in enumerate([("Jeff Sun", "三層止蝕 −0.67R", C["mut"]),
                                   ("Martin Luk", "GME 一單 54R", C["gold"]),
                                   ("J Law", "規則係保護你", C["mut"]),
                                   ("Minervini", "VCP · 33,500%", C["grn"])]):
        y = 300 + i * 50
        t(1132, y, n, 14, c, "800")
        t(1252, y, q, 13, C["mut"])
    card(1110, 530, 425, 54)
    t(1132, 564, "門牌：18:00 前更新", 14, C["txt"], "800")

    card(455, 615, 690, 120, C["card2"])
    t(480, 648, "今日 3 條", 12, C["mut"], "700")
    for i, o in enumerate(["1   Watchlist", "2   MM 校準", "3   一頁睇晒", "4   你決定"]):
        card(480 + i * 164, 660, 152, 46, C["card"])
        t(556 + i * 164, 688, o, 14, C["txt"], "700", "middle")

    t(250, 690, "出場階梯（SOUL §4.3）", 13, C["txt"], "800")
    card(250, 704, 540, 38, C["card2"])
    t(272, 729, "2R 減 33%　→　ATRX 8 再減 33%　→　拖 10EMA 全清", 13, C["mut"], "700")

    card(1330, 700, 200, 118, C["card2"])
    t(1352, 728, "垃圾桶", 12, C["red"], "800")
    t(1352, 750, "追高 · 報復交易", 11, C["mut"])
    t(1352, 770, "加單救返 · 好肯定", 11, C["mut"])
    t(1352, 798, "每單風險 0.5%", 12, C["grn"], "800")

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}">' + "".join(P) + "</svg>")
    out = os.path.join(HERE, "output", f"room_{theme}.html")
    io.open(out, "w", encoding="utf-8").write(
        f'<!doctype html><html><body style="margin:0;background:{C["bg"]}">{svg}</body></html>')
    return out


if __name__ == "__main__":
    print(render("dark"))
    print(render("light"))
