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
MAX_BODY = 6000


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
            cat = rel.split("/")[0] if "/" in rel else "其他"
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

    P.append('<div id="sklist">')
    for r in rows:
        meta = " · ".join(x for x in (r["cat"], r["src"],
                                      f'v{r["ver"]}' if r["ver"] else "",
                                      f'{len(r["files"])} 個支援檔' if r["files"] else "")
                          if x)
        P.append(f'<details class="skcard" data-c="{_h.escape(r["cat"])}">'
                 f'<summary><b>{_h.escape(r["name"])}</b>'
                 f'<span class="skd">{_h.escape(r["desc"])}</span>'
                 f'<span class="skm">{_h.escape(meta)}</span></summary>'
                 f'<div class="skbody">{_md(r["body"])}')
        if r["files"]:
            P.append('<div class="skfiles"><b>支援檔</b> ' +
                     " ".join(f'<code>{_h.escape(f)}</code>' for f in r["files"]) + "</div>")
        P.append('</div></details>')
    P.append('</div>')

    P.append("""<style>
.skcard{border:1px solid #cfc7bb;border-radius:8px;margin:0 0 8px;background:#fff}
.skcard>summary{cursor:pointer;padding:9px 12px;list-style:none;display:block}
.skcard>summary::-webkit-details-marker{display:none}
.skd{display:block;color:#5b564c;font-size:12.5px;margin-top:2px}
.skm{display:block;color:#7a7367;font-size:11.5px;margin-top:3px}
.skbody{padding:4px 14px 12px;border-top:1px solid #e6e0d6;font-size:13px;line-height:1.55}
.skbody h3{font-size:14px;margin:12px 0 4px}
.skbody pre{background:#f6f3ec;padding:8px 10px;border-radius:5px;overflow-x:auto;font-size:12px}
.skbody code{background:#f2eee5;padding:1px 4px;border-radius:3px;font-size:12px}
.skfiles{margin-top:10px;font-size:11.5px;color:#5b564c}
.skchip{padding:5px 10px;border:1px solid #cfc7bb;border-radius:999px;background:#fff;
  font-size:12px;cursor:pointer;color:#3a3730}
.skchip.on{background:#c2410c;border-color:#c2410c;color:#fff}
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
