# -*- coding: utf-8 -*-
"""mindmap2.py — 需求質疑 Mind Map（Musk × Jeff Sun）。

每個頁面一個判決：
  keep  ✓  今日會改變決定
  merge ⇄  同另一頁講同一件事 → 併入（唔再獨立存在）
  del   ✗  冇任何決策用途 → 鏟
輸出 cache/mindmap2.html（SVG），再用 Chrome 截 PNG。
"""
from __future__ import annotations

import ast
import html
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "build_site.py")
OUT = os.path.join(HERE, "cache", "mindmap2.html")

# href → (verdict, note)
V = {
    # ── 保留：直接影響今日決定 ──
    "nel.html": ("keep", "唯一答案：燈／做唔做／關鍵球"),
    "screener.html": ("keep", "選股唯一入口（744 隻＋止蝕股數）"),
    "alerts.html": ("keep", "即時觸發"),
    "process.html": ("keep", "流程（含 howto／finish）"),
    "review.html": ("keep", "成績（R／期望值）"),
    "regimeheat.html": ("keep", "環境（Musk：保留唯一環境尺）"),
    "peg.html": ("keep", "季度名單（每季凍結）"),
    "earningscal.html": ("keep", "財報黑名單閘"),
    "calculator.html": ("keep", "倉位（人手覆核用）"),
    # ── 合併 ──
    "briefing.html": ("merge", "→ nel 大市"),
    "dailyscan.html": ("merge", "→ screener"),
    "rsscan.html": ("merge", "→ screener preset"),
    "leaders.html": ("merge", "→ screener RS≥90"),
    "leadermap.html": ("merge", "→ screener 位置欄"),
    "rsbeforeprice.html": ("merge", "→ screener tag"),
    "cm.html": ("merge", "→ screener 回調"),
    "tightscan.html": ("merge", "→ screener TIGHT 欄"),
    "rsnewhigh.html": ("merge", "→ screener tag"),
    "week.html": ("merge", "→ screener Weekly"),
    "yoyo_ball.html": ("merge", "→ alerts"),
    "fatpitch.html": ("merge", "→ alerts"),
    "wave.html": ("merge", "→ sectors"),
    "sectorrot.html": ("merge", "→ sectors"),
    "rsboard.html": ("merge", "→ sectors"),
    "mm.html": ("del", "同上"),
    "mmmodel.html": ("del", "同上"),
    "topwatch.html": ("del", "同上"),
    "regime_mri.html": ("del", "同上"),
    "stage.html": ("del", "同 nel 大市重複"),
    "margin.html": ("del", "保證金債務唔會改變今日決定"),
    "ntmflow.html": ("del", "期權流每日噪音大於訊號"),
    "feargauge.html": ("merge", "→ nel 大市"),
    "putcall.html": ("merge", "→ nel 大市"),
    "positioning.html": ("merge", "→ nel 大市（已內置）"),
    "review2.html": ("merge", "→ review"),
    "thinkinr.html": ("merge", "→ review"),
    "backtest.html": ("merge", "→ review"),
    "edgeimprove.html": ("merge", "→ review"),
    "audit.html": ("merge", "→ review"),
    "datahealth.html": ("merge", "→ jobboard"),
    "sysmap.html": ("merge", "→ jobboard"),
    "jobboard.html": ("keep", "系統狀態（合併 5 頁後）"),
    # ── 鏟 ──
    "sectorrot2.html": ("del", "同 sectorrot 重複"),
    "finish.html": ("del", "併入 process 已足夠"),
    "mb_top250.html": ("del", "季度名單已由 PEG 取代"),
    "hermesdir.html": ("del", "我嘅檔案目錄，同你決策無關"),
    "skills.html": ("del", "同上"),
    "vantharp.html": ("del", "閱讀材料，入 playbook 一段"),
    "room.html": ("del", "同上"),
    "lukplaybook.html": ("merge", "→ playbook 一頁"),
    "qmb.html": ("merge", "→ playbook 一頁"),
    "modelbook.html": ("merge", "→ playbook 一頁"),
    "external.html": ("keep", "外部來源（合併 3 頁後）"),
    "martinluk.html": ("merge", "→ external"),
    "levelup.html": ("merge", "→ external"),
    "howto.html": ("merge", "→ process"),
    "qqqstruct.html": ("del", "同上"),
    "sectors.html": ("keep", "唯一板塊入口（合併 3 頁後）"),
    "setups.html": ("merge", "→ nel 今日（The Plan 已入）"),
    "regime.html": ("merge", "→ nel 大市（Setup×環境）"),
    "https://jfsrev.substack.com/p/my-trading-tools-process-routine": ("keep", "外部：Jeff Sun 原文"),
    "https://traderslab.gitbook.io/primetrading": ("keep", "外部：PrimeTrading"),
    "https://qullamaggie.net/": ("keep", "外部：Qullamaggie"),
    "https://qullamaggie.com/my-3-timeless-setups-that-have-made-me-tens-of-millions/":
        ("keep", "外部：QM 3 setups"),
    "https://qullamaggie.net/alex-desjardins-method/": ("keep", "外部：Alex D"),
}

COLOUR = {"keep": "#22c55e", "merge": "#f59e0b", "del": "#ef4444"}
ICON = {"keep": "✓", "merge": "⇄", "del": "✗"}


def sidebar():
    tree = ast.parse(io.open(SRC, encoding="utf-8").read())
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(
                getattr(t, "id", "") == "SIDEBAR_LINKS" for t in n.targets):
            return ast.literal_eval(n.value)
    raise SystemExit("SIDEBAR_LINKS not found")


def groups(rows):
    out, cur, head = [], None, []
    for r in rows:
        k = r[0]
        if k == "_grp":
            cur = (r[1], [])
            out.append(cur)
        elif k in ("_link", "_ext"):
            (cur[1] if cur else head).append((r[2], r[3]))
        elif k == "_pinned":
            head.append((r[2], r[3]))
        elif k == "_fold":
            head.append((r[2], r[3]))
    return head, [g for g in out if g[1]]


def main():
    head, gs = groups(sidebar())
    rows = []
    for name, items in [("常用", head)] + gs:
        for label, href in items:
            v, note = V.get(href, ("del", "未分類：預設鏟，除非你話要"))
            rows.append((name, label, href, v, note))

    n_keep = sum(1 for r in rows if r[3] == "keep")
    n_merge = sum(1 for r in rows if r[3] == "merge")
    n_del = sum(1 for r in rows if r[3] == "del")
    total = len(rows)

    row_h, top, grp_h = 26, 96, 22
    n_grp = len({r[0] for r in rows})
    H = top + len(rows) * row_h + n_grp * grp_h + 170
    W = 1500
    x_g, x_l, x_s, x_n = 48, 330, 700, 880

    P = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    # 標題
    P.append(f'<text x="{x_g}" y="34" font-size="21" font-weight="800" fill="#0f172a">'
             f'Trading OS 需求質疑 — 鏟零件</text>')
    P.append(f'<text x="{x_g}" y="56" font-size="12" fill="#64748b">'
             f'Musk：最多人錯喺「優化一件本來唔應該存在嘅零件」｜'
             f'Jeff Sun：只留會改變今日決定嘅嘢</text>')
    P.append(f'<text x="{x_g}" y="78" font-size="12.5" font-weight="700" fill="#0f172a">'
             f'{total} 頁 → 保留 {n_keep}｜合併 {n_merge}｜鏟 {n_del}</text>')

    y = top
    last_g = None
    for gname, label, href, v, note in rows:
        if gname != last_g:
            if last_g is not None:
                y += 6
            P.append(f'<text x="{x_g}" y="{y+4}" font-size="11" font-weight="800" '
                     f'letter-spacing="1.2" fill="#94a3b8">{html.escape(gname).upper()}</text>')
            y += 22
            last_g = gname
        c = COLOUR[v]
        strike = (' stroke="#94a3b8" stroke-width="1" ' if v == "del" else "")
        P.append(f'<circle cx="{x_g+6}" cy="{y+8}" r="5" fill="{c}"/>')
        P.append(f'<text x="{x_g+6}" y="{y+12}" font-size="8" font-weight="800" '
                 f'text-anchor="middle" fill="#fff">{ICON[v]}</text>')
        op = ".42" if v == "del" else ".95"
        dec = ' text-decoration="line-through"' if v == "del" else ""
        P.append(f'<text x="{x_l}" y="{y+12}" font-size="12.5" fill="#0f172a" opacity="{op}"{dec}>'
                 f'{html.escape(label)}</text>')
        if strike:
            P.append(f'<line x1="{x_l}" y1="{y+8}" x2="{x_s-12}" y2="{y+8}" stroke="#cbd5e1" '
                     f'stroke-width="1"/>')
        if href.startswith("http"):
            _h = "外部"
        else:
            _h = href if len(href) <= 30 else href[:27] + "…"
        P.append(f'<text x="{x_s}" y="{y+12}" font-size="10" fill="#94a3b8">{_h}</text>')
        P.append(f'<text x="{x_n}" y="{y+12}" font-size="11" fill="{c}">{html.escape(note)}</text>')
        y += row_h

    ly = H - 96
    P.append(f'<text x="{x_g}" y="{ly}" font-size="11" font-weight="800" fill="#0f172a">'
             f'判決規則</text>')
    for i, (c, t) in enumerate([
            ("#22c55e", "保留：答一條今日會問嘅問題（做唔做／做邊隻／幾大注／幾時走）"),
            ("#f59e0b", "合併：同一問題嘅第二個答案 → 併入唯一入口，舊頁 302"),
            ("#ef4444", "鏟：答唔到任何決策問題，或者只係我嘅工作紀錄")]):
        yy = ly + 18 + i * 17
        P.append(f'<circle cx="{x_g+5}" cy="{yy-4}" r="4" fill="{c}"/>')
        P.append(f'<text x="{x_g+16}" y="{yy}" font-size="11" fill="#475569">{t}</text>')
    P.append(f'<text x="{x_g}" y="{H-24}" font-size="10.5" fill="#94a3b8">'
             f'合併後實際頁數：{n_keep + 4}（nel／screener／alerts／review／playbook／'
             f'external／jobboard／process 等）</text>')
    P.append('</svg>')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(
        '<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}</style>'
        '</head><body>' + "".join(P) + '</body></html>')
    print(f"OK {OUT}｜{total} 頁｜keep {n_keep} merge {n_merge} del {n_del}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
