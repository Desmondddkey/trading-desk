# -*- coding: utf-8 -*-
"""mindmap.py — 網站頁面 Mind Map（用嚟決定留／合併／刪）。

輸出 cache/mindmap.html（SVG），再由瀏覽器截圖成 PNG。
分層：中心「Trading OS」→ 6-7 個決策階段 → 頁面。
顏色：每日（綠）／每週（黃）／倉庫（灰）／建議合併（紅虛線框）。
"""
from __future__ import annotations

import ast
import html
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "build_site.py")
OUT = os.path.join(HERE, "cache", "mindmap.html")

DAILY = {"process.html", "screener.html", "screenwall.html", "regimeheat.html",
         "index.html", "alerts.html", "peg.html", "rsnewhigh.html",
         "dailyscan.html", "rsscan.html", "calculator.html", "howto.html"}
WEEKLY = {"backtest.html", "audit.html", "edgeimprove.html", "review.html",
          "review2.html", "thinkinr.html", "positioning.html", "week.html",
          "earningscal.html", "modelbook.html", "mb_top250.html", "finish.html",
          "jobboard.html", "datahealth.html"}
MERGE = {
    "leaders.html": "合併入 Screener（RS Leader 篩選）",
    "rsbeforeprice.html": "合併入 Screener tag",
    "cm.html": "合併入 Screener preset",
    "tightscan.html": "合併入 Screener（TIGHT 欄已有）",
    "yoyo_ball.html": "合併入 Alerts（已有 YOYO 引擎）",
    "fatpitch.html": "合併入 Alerts（已有肥球掃描）",
    "wave.html": "合併入 Sectors",
    "sectorrot.html": "合併入 Sectors",
    "sectorrot2.html": "合併入 Sectors（同 sectorrot 重複）",
    "rsboard.html": "合併入 Sectors／THEME",
    "mmmodel.html": "合併入 Market Monitor",
    "topwatch.html": "合併入 Market Monitor",
    "qqqstruct.html": "合併入 Market Regime",
    "regime.html": "合併入環境熱力圖",
    "regime_mri.html": "合併入環境熱力圖",
    "stage.html": "合併入環境熱力圖",
    "setupfactory.html": "合併入 The Plan",
    "setups.html": "＝ The Plan（保留）",
    "gto.html": "合併入 Review",
    "vantharp.html": "合併入 Review",
    "optledger.html": "合併入 Review",
    "logbook.html": "合併入 Review",
    "levelup.html": "合併入 Review",
    "cycle.html": "合併入 Review",
    "martinluk.html": "合併入 PLAYBOOK",
    "lukplaybook.html": "合併入 PLAYBOOK",
    "qmb.html": "合併入 PLAYBOOK",
    "room.html": "合併入 PLAYBOOK",
}


def sidebar():
    src = io.open(SRC, encoding="utf-8").read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "SIDEBAR_LINKS" for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit("SIDEBAR_LINKS not found")


def groups(rows):
    out, cur, head = [], None, []
    for r in rows:
        k = r[0]
        if k == "_grp":
            cur = (r[1], [])
            out.append(cur)
        elif k in ("_link", "_ext"):
            item = (r[2], r[3], k)
            (cur[1] if cur else head).append(item)
        elif k == "_fold":
            if cur:
                out.append((r[2], [(l, h, "_link") for l, h in r[4]]))
    return head, out


def colour(href):
    if href in DAILY:
        return "#22c55e"
    if href in WEEKLY:
        return "#eab308"
    return "#94a3b8"


def main():
    head, gs = groups(sidebar())
    gs = [g for g in gs if g[1]]
    n_leaf = sum(len(g[1]) for g in gs)
    row_h, top = 25, 70
    H = top + n_leaf * row_h + 150
    W = 1500
    x0, x1, x2 = 60, 430, 760

    P = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    # 中心
    P.append(f'<rect x="{x0}" y="{H/2-46}" width="190" height="92" rx="12" fill="#0f172a"/>')
    P.append(f'<text x="{x0+95}" y="{H/2-8}" text-anchor="middle" fill="#fff" font-size="19" '
             f'font-weight="700">Trading OS</text>')
    P.append(f'<text x="{x0+95}" y="{H/2+16}" text-anchor="middle" fill="#94a3b8" '
             f'font-size="11">{n_leaf} 頁</text>')

    y = top
    for gname, items in gs:
        yc = y + len(items) * row_h / 2
        P.append(f'<path d="M{x0+190} {H/2} C{(x0+190+x1)/2} {H/2} {(x0+190+x1)/2} {yc} {x1} {yc}" '
                 f'stroke="#cbd5e1" stroke-width="1.6" fill="none"/>')
        P.append(f'<rect x="{x1}" y="{yc-15}" width="290" height="30" rx="8" fill="#f1f5f9" '
                 f'stroke="#cbd5e1"/>')
        P.append(f'<text x="{x1+12}" y="{yc+5}" font-size="13" font-weight="700" fill="#0f172a">'
                 f'{html.escape(gname)}</text>')
        P.append(f'<text x="{x1+272}" y="{yc+5}" font-size="11" fill="#64748b" '
                 f'text-anchor="end">{len(items)}</text>')
        for label, href, kind in items:
            c = colour(href)
            merge = href in MERGE
            dash = ' stroke="#ef4444" stroke-dasharray="4 3"' if merge else ""
            P.append(f'<path d="M{x1+290} {yc} C{(x1+290+x2)/2} {yc} {(x1+290+x2)/2} {y+12} {x2} {y+12}" '
                     f'stroke="#e2e8f0" stroke-width="1.1" fill="none"/>')
            P.append(f'<rect x="{x2}" y="{y+1}" width="640" height="22" rx="5" fill="#fff" '
                     f'stroke="#e2e8f0"{dash}/>')
            P.append(f'<circle cx="{x2+12}" cy="{y+12}" r="4" fill="{c}"/>')
            P.append(f'<text x="{x2+24}" y="{y+16}" font-size="12" fill="#111827">'
                     f'{html.escape(label)}</text>')
            if merge:
                P.append(f'<text x="{x2+330}" y="{y+16}" font-size="10.5" fill="#ef4444">'
                         f'⇄ {html.escape(MERGE[href])}</text>')
            y += row_h
        y += 10

    # 圖例
    ly = H - 108
    P.append(f'<text x="{x0}" y="{ly}" font-size="12" font-weight="700" fill="#0f172a">圖例</text>')
    for i, (c, t) in enumerate([("#22c55e", "每日要睇"), ("#eab308", "每週／每月"),
                                ("#94a3b8", "倉庫（有需要才開）"),
                                ("#ef4444", "⇄ 建議合併／收起")]):
        yy = ly + 22 + i * 18
        P.append(f'<circle cx="{x0+6}" cy="{yy-4}" r="4" fill="{c}"/>')
        P.append(f'<text x="{x0+18}" y="{yy}" font-size="11.5" fill="#334155">{t}</text>')
    P.append('</svg>')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(
        "<html><body style='margin:0;background:#fff'>" + "".join(P) + "</body></html>")
    print(f"✓ {OUT}｜{n_leaf} 頁｜{len(gs)} 組")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
