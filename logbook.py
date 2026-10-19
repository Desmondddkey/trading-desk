# -*- coding: utf-8 -*-
"""logbook.py — 每頁最底嘅 LOG BOOK（更新記錄表）

Desmond 2026-10-19：「係最底留個LOG BOOK，用個表記錄每次更新D咩」

資料源：C:/Users/rain0/trading-os/CHANGELOG.jsonl（append-only，112 條）
每條：{id, ts, kind, title, detail, files, evidence, tags, ...}

設計：
  · 最新在上
  · 桌面 = 表（時間 / 類型 / 標題 / 詳情）
  · 手機 ≤700px = 卡片（唔橫滑）
  · 詳情同證據收埋喺 <details>，唔會爆版面
  · 只讀，永不寫
"""
import html as _h
import io
import json
import os

BOOK = r"C:\Users\rain0\trading-os\CHANGELOG.jsonl"

KIND = {
    "fix":      ("🐛", "修正", "#dc2626"),
    "rule":     ("📜", "規則", "#7c3aed"),
    "research": ("🔬", "研究", "#0891b2"),
    "tool":     ("🔧", "工具", "#f59e0b"),
    "feature":  ("✨", "功能", "#16a34a"),
    "config":   ("⚙️", "設定", "#64748b"),
    "data":     ("📊", "數據", "#2563eb"),
    "remove":   ("🗑", "移除", "#78716c"),
}

CSS = """
.lb-wrap{margin-top:26px}
.lb-h{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;
  margin:0 0 10px;font-size:15px;font-weight:800}
.lb-h small{font-size:11.5px;font-weight:600;opacity:.55}
.lb-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
.lb-tbl th{text-align:left;font-size:10.5px;letter-spacing:.05em;
  text-transform:uppercase;opacity:.55;padding:6px 8px;
  border-bottom:1px solid rgba(128,128,128,.28);font-weight:700}
.lb-tbl td{padding:7px 8px;border-bottom:1px solid rgba(128,128,128,.1);
  vertical-align:top;text-align:left}
.lb-tbl tr:hover{background:rgba(128,128,128,.06)}
.lb-when{font-family:ui-monospace,monospace;font-size:11px;
  opacity:.66;white-space:nowrap}
.lb-k{font-size:11px;font-weight:800;white-space:nowrap}
.lb-t{font-weight:700}
.lb-d{font-size:11.5px;opacity:.72;margin-top:2px;
  white-space:normal;word-break:break-word}
.lb-tbl details summary{font-size:11px;opacity:.6;cursor:pointer;
  list-style:none}
.lb-tbl details summary::-webkit-details-marker{display:none}
.lb-tbl details summary::before{content:"▸ ";font-size:9px}
.lb-tbl details[open] summary::before{content:"▾ "}
.lb-more{text-align:center;margin-top:10px}
.lb-more a{font-size:12px;opacity:.7}
@media(max-width:700px){
  .lb-tbl thead{display:none}
  .lb-tbl,.lb-tbl tbody,.lb-tbl tr{display:block;width:100%}
  .lb-tbl tr{padding:10px 0;border-bottom:1px solid rgba(128,128,128,.16)}
  .lb-tbl td{display:block;width:auto;text-align:left!important;
    border:0;padding:0}
  .lb-tbl td:nth-child(1){display:inline;font-size:11px;margin:0}
  .lb-tbl td:nth-child(2){display:inline;margin:0 0 0 8px}
  .lb-tbl td:nth-child(3){margin-top:5px;font-size:13.5px;line-height:1.4}
  .lb-tbl td:nth-child(4){margin-top:3px}
  .lb-d{font-size:12px;line-height:1.55}
}
"""


def _esc(v):
    return _h.escape(str(v)) if v not in (None, "") else ""


def load(limit=None):
    if not os.path.exists(BOOK):
        return None
    out = []
    try:
        for ln in io.open(BOOK, encoding="utf-8"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
    except OSError:
        return None
    out.sort(key=lambda r: r.get("ts") or "", reverse=True)
    return out[:limit] if limit else out


def build(n=60):
    rows = load(n)
    parts = [f"<style>{CSS}</style>", '<div class="lb-wrap">']
    if rows is None:
        parts.append('<div class="lb-h">📒 LOG BOOK'
                     '<small>CHANGELOG.jsonl 讀唔到</small></div></div>')
        return "".join(parts)
    total = len(load() or [])
    parts.append(
        f'<div class="lb-h">📒 LOG BOOK'
        f'<small>最近 {len(rows)} 條 / 共 {total} 條｜每次更新都記落嚟</small>'
        '</div>')
    parts.append('<table class="lb-tbl"><thead><tr>'
                 '<th style="width:96px">時間</th>'
                 '<th style="width:66px">類型</th>'
                 '<th>更新咩</th><th style="width:34%">詳情</th>'
                 '</tr></thead><tbody>')
    for r in rows:
        k = (r.get("kind") or "").lower()
        ic, kn, kc = KIND.get(k, ("•", k or "—", "#64748b"))
        ts = (r.get("ts") or "")[:16].replace("T", " ")
        title = _esc(r.get("title"))
        det = _esc(r.get("detail"))
        ev = _esc(r.get("evidence"))
        files = _esc(r.get("files"))
        dhtml = ""
        if det:
            dhtml = f'<div class="lb-d">{det[:170]}'
            if len(det) > 170 or ev or files:
                dhtml += (f'<details><summary>更多</summary>'
                          f'<div style="margin-top:4px">{det}</div>')
                if ev:
                    dhtml += (f'<div style="margin-top:5px;opacity:.8">'
                              f'<b>證據：</b>{ev}</div>')
                if files and files != "[]":
                    dhtml += (f'<div style="margin-top:3px;opacity:.62;'
                              f'font-size:11px"><b>檔案：</b>{files}</div>')
                dhtml += '</details>'
            dhtml += '</div>'
        parts.append(
            f'<tr><td class="lb-when">{ts}</td>'
            f'<td class="lb-k" style="color:{kc}">{ic} {kn}</td>'
            f'<td class="lb-t">{title}</td>'
            f'<td>{dhtml}</td></tr>')
    parts.append('</tbody></table>')
    if total > len(rows):
        parts.append(f'<div class="lb-more">'
                     f'<a href="logbook.html">睇全部 {total} 條 →</a></div>')
    parts.append("</div>")
    return "".join(parts)


def build_full():
    """獨立頁 logbook.html：全部條目。"""
    rows = load() or []
    css = CSS
    out = [f"<style>{css}</style>",
           '<h2>LOG BOOK <small>全部更新記錄</small></h2>',
           f'<p class="crumb">共 {len(rows)} 條｜'
           '來源 C:/Users/rain0/trading-os/CHANGELOG.jsonl（append-only）</p>',
           '<div class="lb-wrap"><table class="lb-tbl"><thead><tr>'
           '<th style="width:96px">時間</th>'
           '<th style="width:66px">類型</th>'
           '<th>更新咩</th><th style="width:36%">詳情</th>'
           '</tr></thead><tbody>']
    for r in rows:
        k = (r.get("kind") or "").lower()
        ic, kn, kc = KIND.get(k, ("•", k or "—", "#64748b"))
        ts = (r.get("ts") or "")[:16].replace("T", " ")
        det = _esc(r.get("detail"))
        ev = _esc(r.get("evidence"))
        files = _esc(r.get("files"))
        dhtml = ""
        if det:
            dhtml = f'<div class="lb-d">{det}'
            if ev or files:
                dhtml += '<details><summary>證據</summary>'
                if ev:
                    dhtml += f'<div style="margin-top:4px">{ev}</div>'
                if files and files != "[]":
                    dhtml += (f'<div style="margin-top:3px;opacity:.62;'
                              f'font-size:11px">{files}</div>')
                dhtml += '</details>'
            dhtml += '</div>'
        out.append(f'<tr><td class="lb-when">{ts}</td>'
                   f'<td class="lb-k" style="color:{kc}">{ic} {kn}</td>'
                   f'<td class="lb-t">{_esc(r.get("title"))}</td>'
                   f'<td>{dhtml}</td></tr>')
    out.append('</tbody></table></div>')
    return ("LOG BOOK", "".join(out))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    rs = load()
    print("條目:", len(rs or []))
    for r in (rs or [])[:5]:
        print(" ", (r.get("ts") or "")[:16], r.get("kind"), r.get("title")[:46])
