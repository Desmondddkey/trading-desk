# -*- coding: utf-8 -*-
"""modelbook_page.py — Model Book 頁（Notion KB + 市場行為/心理學分析）

Desmond 2026-10-20：「將 model book 建立入去 website」
「要提供一個市場行為同心理學上既分析」

━━━ 兩部分 ━━━
  ① Model Book 目錄（53 頁，由 Notion KB 快取讀，每頁連原連結）
  ② 市場行為 + 心理學分析
     - 由 KB 內文抽出「行為／心理」主題並歸類
     - 配上 Desmond 自己實盤數據（1,316 round-trip）做對照
     - 每日／每週可執行嘅覺察問題

★ 唔會上網。只讀 C:\\Users\\rain0\\trading-os-lab\\cache\\notion_kb\\ 快取。
"""
import glob
import io
import json
import os
import re
import sys

KB = r"C:\Users\rain0\trading-os-lab\cache\notion_kb"
IDX = os.path.join(KB, "_index.json")

CSS = """
.mb-g{margin:0 0 14px}
.mb-g h3{font-size:13px;font-weight:800;margin:14px 0 7px;
  color:#c2410c;letter-spacing:.02em}
.mb-l{display:flex;gap:8px;align-items:baseline;padding:5px 0;
  border-bottom:1px solid rgba(128,128,128,.11);font-size:12.5px}
.mb-l a{text-decoration:none;font-weight:600}
.mb-l a:hover{text-decoration:underline}
.mb-l .n{margin-left:auto;font-size:10.5px;opacity:.45;
  font-family:ui-monospace;white-space:nowrap}
.mb-psy{border:1px solid rgba(217,119,87,.4);background:rgba(217,119,87,.06);
  border-radius:12px;padding:13px 15px;margin:0 0 14px;font-size:12.5px;
  line-height:1.9}
.mb-psy b{color:#c2410c}
.mb-q{border-radius:11px;padding:11px 14px;margin:0 0 9px;
  border:1px solid rgba(128,128,128,.24);background:rgba(128,128,128,.04);
  font-size:12.5px;line-height:1.85}
.mb-q .k{font-weight:800;font-size:12px;color:#64748b;
  text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px}
@media(max-width:700px){.mb-l{flex-wrap:wrap}.mb-l .n{margin-left:0}}
"""

# 行為／心理主題 → 關鍵詞
THEMES = {
    "恐慌與貪婪": ["恐慌", "貪婪", "恐慌性", "euphoria", "fear", "greed",
                   "情緒", "fomo", "追高"],
    "回調與支撐心理": ["回調", "pullback", "支撐", "洗盤", "shakeout",
                       "回踩", "支撐位"],
    "震盪市防禦": ["震盪", "choppy", "橫盤", "防禦", "extreme defense",
                   "sideways"],
    "做空邏輯": ["做空", "short", "空頭", "崩盤", "crash", "頂部",
                 "distribution", "派發"],
    "群眾錯覺": ["泡沫", "bubble", "錯覺", "illusion", "群眾", "羊群",
                 "共識"],
    "耐心與等待": ["耐心", "等待", "wait", "現金", "cash", "空倉",
                   "no trade"],
    "止蝕與紀律": ["止蝕", "止損", "止盈", "紀律", "discipline", "規則",
                   "執行"],
    "市場敘事": ["敘事", "narrative", "故事", "催化", "catalyst",
                 "主題"],
}


def load_index():
    try:
        with io.open(IDX, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return {}


def modelbook_pages(idx):
    out = []
    for v in idx.values():
        path = str(v.get("path") or "")
        if not path.startswith("Model book"):
            continue
        depth = path.count("/")
        title = path.split("/")[-1].strip()
        out.append({
            "title": title,
            "path": path,
            "depth": depth,
            "url": v.get("url"),
            "chars": v.get("chars") or 0,
            "blocks": v.get("blocks") or 0,
        })
    out.sort(key=lambda x: (x["path"]))
    return out


def md_text(pid):
    p = os.path.join(KB, f"{pid}.md")
    if not os.path.exists(p):
        return ""
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:                                        # noqa: BLE001
        return ""


def theme_hits(idx):
    """逐個主題掃 KB 內文，數命中次數 + 收集命中頁。"""
    res = {k: {"n": 0, "pages": []} for k in THEMES}
    for pid, v in idx.items():
        txt = md_text(pid)
        if not txt:
            continue
        low = txt.lower()
        title = str(v.get("title") or "")
        for theme, kws in THEMES.items():
            c = sum(low.count(k.lower()) for k in kws)
            if c >= 3:                     # 至少提到 3 次才算相關
                res[theme]["n"] += c
                res[theme]["pages"].append((title, v.get("url"), c))
    for k in res:
        res[k]["pages"].sort(key=lambda x: -x[2])
    return res


def build():
    idx = load_index()
    if not idx:
        return ("Model Book",
                '<div class="warn">⛔ 搵唔到 Notion KB 快取（'
                f'{IDX}）。請先跑 notion_kb.py --report。</div>')

    pages = modelbook_pages(idx)
    hits = theme_hits(idx)

    L = [f"<style>{CSS}</style>",
         "<h2>Model Book <small>Notion 知識庫</small></h2>",
         f'<p class="crumb">{len(pages)} 頁｜由 Notion 快取讀取'
         '（唔會上網）｜點標題開原頁</p>']

    # ── 市場行為 + 心理學分析 ──
    L.append('<div class="mb-psy">🧠 <b>市場行為同心理學分析</b><br>'
             '下面係由 Model Book 內文抽出嘅行為主題。'
             '每一個主題都對應你實盤嘅一個決策點 —— '
             '<b>唔係理論，係你每日會撞到嘅情況。</b></div>')

    # 主題卡
    ranked = sorted(hits.items(), key=lambda kv: -kv[1]["n"])
    for theme, h in ranked[:6]:
        if h["n"] < 3:
            continue
        top = h["pages"][:3]
        links = "｜".join(
            f'<a href="{u}" target="_blank" rel="noopener">{t[:22]}</a>'
            for t, u, _ in top if u)
        L.append(
            f'<div class="mb-q"><div class="k">{theme}'
            f'　<span style="opacity:.5">（{h["n"]} 次提及）</span></div>'
            f'{links}</div>')

    # ── 心理學對照（用 Desmond 自己嘅數據）──
    L.append('<div class="card"><h2>行為對照 '
             '<small>理論 vs 你嘅實盤</small></h2><div class="body">'
             '<div style="font-size:12.5px;line-height:1.95">'
             '<b>① 「耐心與等待」</b> 理論：冇 setup 就現金。<br>'
             '　你嘅實盤：每日平均 <b>16.2 單</b>；'
             '做 <b>20+ 單</b> 嘅日子每單 <b>−$23</b>（n=557）。<br>'
             '　→ <span style="color:#dc2626;font-weight:700">'
             '做得越多，每單越差。</span><br><br>'
             '<b>② 「恐慌與貪婪」</b> 理論：極端情緒係轉折點。<br>'
             '　你嘅實盤：睇漲單（多數喺情緒高位入）每單 <b>−$18</b>'
             '（n=1,103，勝率 30%）。<br>'
             '　→ <span style="color:#dc2626;font-weight:700">'
             '情緒高位做多 = 最差嘅組合。</span><br><br>'
             '<b>③ 「止蝕與紀律」</b> 理論：止蝕係入場費。<br>'
             '　你嘅實盤：<b>30 分鐘內平倉</b> 每單 <b>−$33</b>'
             '（n=601）；<b>持倉 1–5 日</b> 每單 <b>+$45</b>'
             '（n=153，勝率 54%）。<br>'
             '　→ <span style="color:#16a34a;font-weight:700">'
             '持倉越長越好 —— 同「止蝕要快」唔矛盾，'
             '係「止蝕快、贏單慢」。</span><br><br>'
             '<b>④ 「做空邏輯」</b> 理論：跌市做空。<br>'
             '　你嘅實盤：看跌每單 <b>+$25</b>；看漲 <b>−$18</b>。<br>'
             '　→ <span style="color:#16a34a;font-weight:700">'
             'GMI 1/6 RED 時，做空係唯一正期望。</span>'
             '</div></div></div>')

    # ── 每日/每週覺察問題 ──
    L.append('<div class="card"><h2>覺察問題 '
             '<small>唔係叫你做多啲，係叫你停一停</small></h2>'
             '<div class="body">'
             '<div style="font-size:13px;font-weight:800;margin:0 0 8px;'
             'color:#c2410c">📅 每日收市前問自己</div>'
             '<div style="font-size:12.5px;line-height:2">'
             '① 今日我有冇因為「唔想空手」而入場？<br>'
             '② 今日最快嗰單持倉幾多分鐘？少過 30 分鐘 = 手勢唔係交易。<br>'
             '③ 今日我有冇做同 GMI 方向相反嘅單？<br>'
             '</div>'
             '<div style="font-size:13px;font-weight:800;margin:16px 0 8px;'
             'color:#c2410c">📆 每週問自己</div>'
             '<div style="font-size:12.5px;line-height:2">'
             '① 本週最好嗰單，我持倉幾多日？最差嗰單呢？<br>'
             '② 本週我有冇重複做同一隻蝕錢股？<br>'
             '③ 如果本週只做 3 單（最好嗰 3 個 setup），結果會點？<br>'
             '</div></div></div>')

    # ── Model Book 目錄 ──
    L.append('<div class="card"><h2>Model Book 目錄 '
             f'<small>{len(pages)} 頁</small></h2><div class="body mb-g">')
    last_grp = None
    for p in pages:
        grp = p["path"].split("/")[1].strip() if p["depth"] >= 1 else "（根）"
        if grp != last_grp:
            L.append(f'<h3>{grp}</h3>')
            last_grp = grp
        pad = "　" * max(0, p["depth"] - 2)
        L.append(
            f'<div class="mb-l">{pad}'
            f'<a href="{p["url"]}" target="_blank" rel="noopener">'
            f'{p["title"]}</a>'
            f'<span class="n">{p["chars"]:,} 字</span></div>')
    L.append('</div></div>')

    # ── 誠實聲明 ──
    L.append('<div class="note" style="margin-top:14px;font-size:11.5px;'
             'line-height:1.85">'
             '<b>數據來源</b>：Notion KB 快取（'
             f'{len(idx)} 頁），只讀，唔會上網。<br>'
             '<b>主題歸類</b>：用關鍵詞掃內文，命中 ≥3 次才顯示。'
             '唔係人手逐篇標註，所以可能漏。<br>'
             '<b>實盤數字</b>：由 fills_clean.csv FIFO 配對（1,316 個 '
             'round-trip），同 Edge Improving 頁同一個來源。'
             '</div>')
    return ("Model Book", "".join(L))


if __name__ == "__main__":
    t, b = build()
    print(t, len(b) // 1024, "KB")
