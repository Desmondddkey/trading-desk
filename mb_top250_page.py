# -*- coding: utf-8 -*-
"""mb_top250_page.py — Model Book：Top 250 贏家名單區塊

來源：Desmond 2026-10-23 提供嘅 new.xlsx
  3 個工作表：1Y / 3Y / 5Y Top 250 US Gainers

★★ 重要限制（誠實聲明，唔可以扮最新）★★
  1Y：2025-06-04 → 2026-06-03
  3Y：2023-06-05 → 2026-06-03
  5Y：2021-06-04 → 2026-06-03
  全部截至 2026-06-03 —— 距今約 4.7 個月。
  呢個係【歷史回顧】，唔係今日選股名單。

為咩仍然有價值（Clement Ang 原文）：
  「歷史唔會重複，但會押韻」
  「1930s 鐵路/鋼鐵 → 今日 AI/data center/space/uranium」
  呢 750 隻就係「上一次押韻」嘅完整名單 —— 用嚟做形態研究。

輸出：docs/modelbook_top250.html（由 mb_page.py 讀入）
"""
import io
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"C:\Users\rain0\trading-os\output\model_book\top250.json"
CASES = r"C:\Users\rain0\trading-os\output\model_book"

CSS = """
.t2w{border-left:3px solid #c2410c;background:rgba(194,65,12,.07);
  padding:11px 14px;border-radius:0 10px 10px 0;font-size:12.5px;
  line-height:1.85;margin:0 0 14px}
.t2tabs{display:flex;gap:6px;margin:0 0 12px;flex-wrap:wrap}
.t2tabs button{flex:1;min-width:90px;padding:9px 12px;font-size:12.5px;
  font-weight:700;border-radius:9px;border:1px solid rgba(128,128,128,.3);
  background:transparent;cursor:pointer;font-family:inherit}
.t2tabs button.on{background:#c2410c;border-color:#c2410c;color:#fff}
.t2pane{display:none}
.t2pane.on{display:block}
.t2sec{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px;font-size:11px}
.t2sec span{padding:3px 9px;border-radius:20px;
  border:1px solid rgba(128,128,128,.25);font-family:ui-monospace}
.t2tb{width:100%;border-collapse:collapse;font-size:11.5px}
.t2tb th{text-align:left;padding:6px 7px;font-size:10px;
  text-transform:uppercase;letter-spacing:.04em;opacity:.55;
  border-bottom:1px solid rgba(128,128,128,.25);position:sticky;top:0}
.t2tb td{padding:5px 7px;border-bottom:1px solid rgba(128,128,128,.09);
  font-family:ui-monospace}
.t2tb td.nm{font-family:inherit;max-width:170px;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.t2tb .g{color:#15803d;font-weight:700;text-align:right}
.t2tb .hit:after{content:"★";color:#c2410c;margin-left:4px}
.t2more{font-size:11.5px;opacity:.6;margin:8px 0 0}
@media(max-width:700px){
  .t2tb{font-size:10.5px}
  .t2tb th,.t2tb td{padding:4px 4px}
  .t2tb td.nm{max-width:88px}
  .t2tabs button{min-width:64px;font-size:11.5px;padding:7px 8px}
}
"""

TAB_KEY = {"1Y Top 250": "1y", "3Y Top 250": "3y", "5Y Top 250": "5y"}
TAB_LBL = {"1Y Top 250": "1 年", "3Y Top 250": "3 年", "5Y Top 250": "5 年"}


def _case_tickers():
    """由 mb_cases 案例庫抽所有出現過嘅 ticker"""
    s = set()
    if not os.path.isdir(CASES):
        return s
    fs = sorted(f for f in os.listdir(CASES)
                if f.endswith(".json") and f[0].isdigit())
    if not fs:
        return s
    try:
        d = json.load(io.open(os.path.join(CASES, fs[-1]), encoding="utf-8"))
        for c in d.get("cases", []):
            s.add(c.get("ticker"))
    except Exception:                                    # noqa: BLE001
        pass
    return s


def block():
    if not os.path.exists(SRC):
        return ""
    d = json.load(io.open(SRC, encoding="utf-8"))
    hit_set = _case_tickers()

    out = [f"<style>{CSS}</style>", '<div class="card">']
    out.append("<h3>🏆 Top 250 US Gainers（1Y / 3Y / 5Y）</h3>")
    out.append(
        '<div class="t2w">'
        '<b>⚠️ 數據截止 2026-06-03</b>（距今約 4.7 個月）—— '
        '呢度係<b>歷史回顧</b>，唔係今日選股名單。<br>'
        '但仍然有價值：Clement Ang 原文「歷史唔會重複，但會押韻」——'
        '呢 750 隻就係上一次押韻嘅完整名單，'
        '用嚟做形態研究、對照你嘅 model book。<br>'
        '<b>★ 標記</b> = 呢隻股喺我哋 2,377 個案例庫入面出現過'
        '（即係我哋嘅 detector 有捉到）。'
        '</div>')

    # tabs
    out.append('<div class="t2tabs">')
    for i, sheet in enumerate(("1Y Top 250", "3Y Top 250", "5Y Top 250")):
        on = " on" if i == 0 else ""
        out.append(f'<button class="t2b{on}" data-t2="{TAB_KEY[sheet]}">'
                   f'{TAB_LBL[sheet]}</button>')
    out.append("</div>")

    for i, sheet in enumerate(("1Y Top 250", "3Y Top 250", "5Y Top 250")):
        v = d.get(sheet)
        if not v:
            continue
        rows = v["rows"]
        on = " on" if i == 0 else ""
        out.append(f'<div class="t2pane{on}" id="t2-{TAB_KEY[sheet]}">')
        out.append(f'<p class="t2more">{v["range"][:110]}</p>')
        # sector chips
        c = Counter(x["sector"] for x in rows if x["sector"])
        out.append('<div class="t2sec">')
        for sec, n in c.most_common(6):
            out.append(f'<span>{sec} {n}</span>')
        out.append("</div>")
        # table
        n_hit = sum(1 for x in rows if x["ticker"] in hit_set)
        out.append(f'<p class="t2more">{len(rows)} 隻｜'
                   f'其中 {n_hit} 隻（{n_hit/len(rows)*100:.0f}%）'
                   f'出現喺我哋案例庫</p>')
        out.append('<table class="t2tb"><tr><th>#</th><th>股票</th>'
                   '<th>公司</th><th>Sector</th><th>升幅</th></tr>')
        for x in rows[:40]:
            mk = " hit" if x["ticker"] in hit_set else ""
            out.append(
                f'<tr><td>{x["rank"]}</td>'
                f'<td class="{mk}">{x["ticker"]}</td>'
                f'<td class="nm">{x["company"][:34]}</td>'
                f'<td class="nm">{x["sector"][:16]}</td>'
                f'<td class="g">+{x["gain"]:,.0f}%</td></tr>')
        out.append("</table>")
        if len(rows) > 40:
            out.append(f'<p class="t2more">'
                       f'（只顯示頭 40 名；完整 {len(rows)} 隻見 '
                       f'<code>output/model_book/top250.json</code>）</p>')
        out.append("</div>")
    out.append("</div>")

    # JS：切 tab
    out.append("""<script>
(function(){
  var bs=document.querySelectorAll('.t2b');
  bs.forEach(function(b){
    b.onclick=function(){
      bs.forEach(function(x){x.classList.remove('on')});
      b.classList.add('on');
      document.querySelectorAll('.t2pane').forEach(function(p){
        p.classList.remove('on')});
      var t=document.getElementById('t2-'+b.dataset.t2);
      if(t) t.classList.add('on');
    };
  });
})();
</script>""")
    return "".join(out)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    h = block()
    print(f"✓ {len(h):,} 字")
    p = os.path.join(HERE, "docs", "modelbook_top250.html")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(h)
    print(f"✓ {p}")


if __name__ == "__main__":
    main()
