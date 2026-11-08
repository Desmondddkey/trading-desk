# -*- coding: utf-8 -*-
"""qmb_page.py — Qullamaggie Model Book（中文版）

來源：Desmond 2026-11-08 提供嘅 Google Drive PDF（《Qullamaggie Model Book》）。
本頁只讀 content/qmb_zh.md（翻譯稿，離線），唔上網。
"""
from __future__ import annotations

import html as _h
import io
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(_HERE, "content", "qmb_zh.md")

CSS = """
<style>
.qmb-toc{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 0}
.qmb-toc a{font-size:11.5px;padding:3px 8px;border:1px solid var(--hair);
  border-radius:999px;text-decoration:none;color:inherit;opacity:.85}
.qmb-toc a:hover{opacity:1;border-color:#2f8f5b}
.qmb-theory p{margin:0 0 8px}
.qmb-theory blockquote{margin:10px 0;padding:8px 12px;border-left:3px solid #2f8f5b;
  background:rgba(47,143,91,.08);border-radius:0 6px 6px 0}
.qmb-theory blockquote p{margin:0;font-weight:600}
.qmb-theory h3{font-size:13px;margin:16px 0 6px}
.qmb-case{border:1px solid var(--hair);border-radius:8px;margin:0 0 6px;overflow:hidden}
.qmb-case>summary{cursor:pointer;padding:7px 10px;font-weight:700;font-size:12.5px;
  list-style:none;display:flex;justify-content:space-between;align-items:center}
.qmb-case>summary::-webkit-details-marker{display:none}
.qmb-case>summary::after{content:"＋";opacity:.45;font-weight:400}
.qmb-case[open]>summary::after{content:"－"}
.qmb-case[open]>summary{border-bottom:1px solid var(--hair)}
.qmb-case .qmb-body{padding:8px 12px;font-size:12.5px;line-height:1.65}
.qmb-case .qmb-body p{margin:0 0 6px}
.qmb-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
@media(max-width:820px){.qmb-grid{grid-template-columns:1fr}}
.qmb-note{font-size:11px;opacity:.6;margin-top:6px}
</style>
"""


def _md(txt):
    try:
        import markdown as _m
    except ImportError:                                       # pragma: no cover
        return "<p>" + _h.escape(txt).replace("\n\n", "</p><p>") + "</p>"
    return _m.markdown(txt, extensions=["tables", "sane_lists"])


def _clean(t):
    t = re.sub(r"^\s*\d+\s*[-–.]?\s*", "", t)                 # 去掉案例編號
    return t.strip()


def build():  # -> (title, html)
    if not os.path.exists(SRC):
        return ("Qullamaggie 手冊", '<div class="card"><div class="body dim">'
                'UNVERIFIED：找不到 content/qmb_zh.md</div></div>')
    with io.open(SRC, encoding="utf-8") as f:
        txt = f.read()

    parts = re.split(r"(?m)^##\s+", txt)
    theory_md = ""
    cases = []
    for p in parts[1:]:
        head, _, body = p.partition("\n")
        if head.startswith("一、"):
            theory_md = body.strip()
        elif head.startswith("二、"):
            for blk in re.split(r"(?m)^###\s+", body)[1:]:
                title, _, cb = blk.partition("\n")
                cases.append((_clean(title), cb.strip()))

    P = [CSS]
    P.append('<div class="card"><h2>Qullamaggie Model Book '
             '<small>中文版 · 全文翻譯</small></h2><div class="body">')
    P.append('<p>原文：《Qullamaggie Model Book》PDF（Desmond 2026-11-08 提供）。'
             '逐段翻譯，保留代號、年份、百分比與引言語氣。</p>')
    P.append(f'<p class="qmb-note">理論 {len(theory_md)} 字｜案例 {len(cases)} 個。'
             '原書以圖表為主，部分案例原文只有圖、冇文字，已在該案例標明。</p>')
    P.append('<div class="qmb-toc"><a href="#qmb-theory">理論</a>'
             '<a href="#qmb-cases">案例庫</a></div>')
    P.append("</div></div>")

    if theory_md:
        P.append('<div class="card" id="qmb-theory"><h2>一、理論</h2>'
                 '<div class="body qmb-theory">' + _md(theory_md) + "</div></div>")

    if cases:
        P.append('<div class="card" id="qmb-cases"><h2>二、案例庫'
                 f' <small>{len(cases)} 個</small></h2><div class="body">')
        P.append('<div class="qmb-grid">')
        for t, body in cases:
            P.append(f'<details class="qmb-case"><summary>{_h.escape(t)}</summary>'
                     f'<div class="qmb-body">{_md(body)}</div></details>')
        P.append("</div></div></div>")

    return ("Qullamaggie Model Book（中文版）", "".join(P))
