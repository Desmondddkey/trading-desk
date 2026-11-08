# -*- coding: utf-8 -*-
"""skills_page.py — 技能庫（掃描 Hermes skills 目錄，自動更新）

輸出：skills.html
每個 skill 一行；展開見全文（已渲染 Markdown）、標籤、來源、支援檔。
"""
from __future__ import annotations

import html as _h
import io
import os
import re

ROOTS = [
    (r"C:/Users/rain0/AppData/Local/hermes/skills", "Hermes"),
    (r"C:/Users/rain0/AppData/Local/omh/skills", "OMH"),
]
MAX_BODY = 4000

_ZH_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "content", "skills_zh.json")
try:
    import json as _json
    with io.open(_ZH_PATH, encoding="utf-8") as _f:
        ZH = _json.load(_f)
except Exception:                                            # noqa: BLE001
    ZH = {}


def _fm(text):
    """frontmatter → dict（只支援 key: value 單行）。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    raw, body = text[3:end], text[end + 4:]
    d = {}
    for line in raw.splitlines():
        m = re.match(r"^([a-zA-Z_-]+):\s*(.+)$", line.strip())
        if m:
            d[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return d, body.lstrip("\n")


def _md(text):
    """極簡 Markdown → HTML（標題／清單／code fence／粗體／行內碼／連結）。"""
    _cut = len(text) > MAX_BODY
    t = _h.escape(text[:MAX_BODY])
    out, code = [], False
    for line in t.splitlines():
        if line.strip().startswith("```"):
            out.append("</pre>" if code else "<pre>")
            code = not code
            continue
        if code:
            out.append(line)
            continue
        s = line.rstrip()
        if not s:
            out.append("")
        elif s.startswith("######"):
            out.append(f"<h6>{s[6:].strip()}</h6>")
        elif s.startswith("#####"):
            out.append(f"<h5>{s[5:].strip()}</h5>")
        elif s.startswith("####"):
            out.append(f"<h4>{s[4:].strip()}</h4>")
        elif s.startswith("###"):
            out.append(f"<h3>{s[3:].strip()}</h3>")
        elif s.startswith("##"):
            out.append(f"<h3>{s[2:].strip()}</h3>")
        elif s.startswith("#"):
            out.append(f"<h3>{s[1:].strip()}</h3>")
        elif re.match(r"^[-*]\s+", s):
            _li = re.sub(r"^[-*]\s+", "", s)
            out.append("<li>" + _li + "</li>")
        elif re.match(r"^\d+\.\s+", s):
            _li2 = re.sub(r"^\d+\.\s+", "", s)
            out.append("<li>" + _li2 + "</li>")
        elif s.startswith("|"):
            out.append(f"<div class='sk-tr'>{s}</div>")
        else:
            out.append(f"<p>{s}</p>")
    if code:
        out.append("</pre>")
    if _cut:
        out.append("<p class=\"pf-note\">✂ 正文超過 4,000 字元，此處只顯示前段；完整內容在 skill 檔（SKILL.md）。</p>")
    h = "\n".join(out)
    h = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", h)
    h = re.sub(r"`([^`]+)`", r"<code>\1</code>", h)
    h = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', h)
    return h


def _collect():
    rows = []
    for root, label in ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if "SKILL.md" not in filenames:
                continue
            p = os.path.join(dirpath, "SKILL.md")
            try:
                with io.open(p, encoding="utf-8") as f:
                    text = f.read()
            except Exception:                                # noqa: BLE001
                continue
            fm, body = _fm(text)
            rel = os.path.relpath(dirpath, root).replace("\\", "/")
            parts = rel.split("/")
            if parts[0] in ("mp", "omh") and len(parts) > 1:
                cat = parts[1]                      # mp/engineering → engineering
            else:
                cat = parts[0] if len(parts) > 1 else "其他"
            extras = []
            for sub in ("references", "scripts", "templates", "assets"):
                d2 = os.path.join(dirpath, sub)
                if os.path.isdir(d2):
                    for fn in sorted(os.listdir(d2)):
                        extras.append(f"{sub}/{fn}")
            bins = os.path.basename(dirpath)
            rows.append({
                "name": fm.get("name") or bins,
                "desc": fm.get("description", ""),
                "cat": cat,
                "src": label,
                "ver": fm.get("version", ""),
                "body": body,
                "files": extras,
                "bytes": len(text.encode("utf-8")),
            })
    rows.sort(key=lambda r: (r["cat"], r["name"].lower()))
    return rows


USAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "skill_usage.json")


def _top_usage(n=10):
    try:
        import json as _j
        with io.open(USAGE, encoding="utf-8") as f:
            d = _j.load(f)
        return list((d.get("counts") or {}).items())[:n]
    except Exception:                                        # noqa: BLE001
        return []


def build():
    rows = _collect()
    cats = sorted({r["cat"] for r in rows})

    P = ['<h2>🧰 技能庫 <small>我識做嘅嘢，一目了然</small></h2>']
    P.append(f'<p class="crumb">{len(rows)} 個技能｜{len(cats)} 個分類｜'
             '每晚安 build 時自動重掃，唔需要人手更新</p>')

    P.append('<div style="display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px">'
             '<input id="skq" placeholder="搜尋技能名／描述…" '
             'style="flex:1;min-width:220px;padding:8px 10px;border:1px solid #cfc7bb;'
             'border-radius:6px;font-size:13px;background:#fff">'
             f'<span id="skn" class="crumb" style="align-self:center">{len(rows)} 個</span></div>')

    P.append('<div id="skchips" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">')
    P.append('<button class="skchip on" data-c="">全部</button>')
    for c in cats:
        n = sum(1 for r in rows if r["cat"] == c)
        P.append(f'<button class="skchip" data-c="{_h.escape(c)}">{_h.escape(c)} {n}</button>')
    P.append('</div>')

    top = _top_usage(10)
    if top:
        mx = max(c for _, c in top) or 1
        P.append('<div class="card"><h2>Top 10 · 按使用次數 '
                 '<small>累計 skill_view 呼叫</small></h2><div class="body">')
        P.append('<div class="sktop">')
        for i, (nm, c) in enumerate(top, 1):
            P.append(f'<div class="skrow"><span class="skrank">{i}</span>'
                     f'<span class="skname">{_h.escape(nm)}</span>'
                     f'<span class="skzh2">{_h.escape(ZH.get(nm, ""))}</span>'
                     f'<span class="skbar"><i style="width:{c / mx * 100:.0f}%"></i></span>'
                     f'<span class="skcnt">{c}</span></div>')
        P.append('</div><div class="sknote">由 state.db 嘅 tool_calls 統計；'
                 '每朝 build 會更新。</div></div></div>')
    P.append('<div id="sklist">')
    for r in rows:
        meta = " · ".join(x for x in (r["cat"], r["src"],
                                      f'v{r["ver"]}' if r["ver"] else "",
                                      f'{len(r["files"])} 個支援檔' if r["files"] else "")
                          if x)
        P.append(f'<details class="skcard" data-c="{_h.escape(r["cat"])}">'
                 f'<summary><b>{_h.escape(r["name"])}</b>'
                 f'<span class="skzh">{_h.escape(ZH.get(r["name"], ""))}</span>'
                 f'<span class="skd">{_h.escape(r["desc"])}</span>'
                 f'<span class="skm">{_h.escape(meta)}</span></summary>'
                 f'<div class="skbody">{_md(r["body"])}')
        if r["files"]:
            P.append('<div class="skfiles"><b>支援檔</b> ' +
                     " ".join(f'<code>{_h.escape(f)}</code>' for f in r["files"]) + "</div>")
        P.append('</div></details>')
    P.append('</div>')

    P.append("""<style>
.skcard{border:1px solid #cfc7bb;border-radius:8px;margin:0 0 8px;background:#fff;color:#1f1e1d}
.skcard>summary{cursor:pointer;padding:9px 12px;list-style:none;display:block;color:#1f1e1d}
.skcard>summary::-webkit-details-marker{display:none}
.skzh{display:block;color:#1f1e1d;font-size:13px;margin-top:3px;font-weight:600}
.skd{display:block;color:#6b6a63;font-size:11.5px;margin-top:2px}
.skm{display:block;color:#7a7367;font-size:11.5px;margin-top:3px}
.skbody{padding:4px 14px 12px;border-top:1px solid #e6e0d6;font-size:13px;line-height:1.55;color:#1f1e1d}
.skbody h3{font-size:14px;margin:12px 0 4px;color:#1f1e1d}
.skbody pre{background:#f6f3ec;padding:8px 10px;border-radius:5px;overflow-x:auto;font-size:12px}
.skbody code{background:#f2eee5;padding:1px 4px;border-radius:3px;font-size:12px}
.skfiles{margin-top:10px;font-size:11.5px;color:#5b564c}
.skchip{padding:5px 10px;border:1px solid #cfc7bb;border-radius:999px;background:#fff;
  font-size:12px;cursor:pointer;color:#3a3730}
.skchip.on{background:#c2410c;border-color:#c2410c;color:#fff}
.sktop{display:flex;flex-direction:column;gap:2px}
.skrow{display:grid;grid-template-columns:22px 190px 1fr 130px 40px;gap:10px;
  align-items:center;padding:4px 0;border-bottom:1px solid rgba(148,163,184,.12);font-size:12.5px}
.skrank{opacity:.5;font-weight:800;text-align:right}
.skname{font-weight:800}
.skzh2{opacity:.7;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.skbar{height:5px;background:rgba(148,163,184,.18);border-radius:3px;overflow:hidden}
.skbar i{display:block;height:100%;background:#2f8f5b}
.skcnt{text-align:right;font-variant-numeric:tabular-nums;opacity:.8}
.sknote{font-size:10.5px;opacity:.55;margin-top:8px}
@media(max-width:760px){.skrow{grid-template-columns:20px 120px 1fr 60px 34px;gap:6px}}
.hide{display:none}
</style>
<script>
(function(){
  var q=document.getElementById('skq'),n=document.getElementById('skn'),
      cards=[].slice.call(document.querySelectorAll('.skcard')),
      chips=[].slice.call(document.querySelectorAll('.skchip')),cat='';
  function apply(){
    var s=(q.value||'').trim().toLowerCase(),k=0;
    cards.forEach(function(c){
      var ok=(!cat||c.dataset.c===cat)&&(!s||c.textContent.toLowerCase().indexOf(s)>=0);
      c.classList.toggle('hide',!ok); if(ok)k++;
    });
    n.textContent=k+' 個';
  }
  q.addEventListener('input',apply);
  chips.forEach(function(b){b.addEventListener('click',function(){
    chips.forEach(function(x){x.classList.remove('on')});
    b.classList.add('on');cat=b.dataset.c;apply();});});
})();
</script>""")
    return ("技能庫", "".join(P))


def main():
    t, b = build()
    print(f"{t} — {len(b):,} chars｜{b.count('<details')} 個 skill")


if __name__ == "__main__":
    main()
