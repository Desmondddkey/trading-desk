# -*- coding: utf-8 -*-
"""mb_burst_page.py — Model Book：升幅時間集中度（深入研究）

命題（TraderGoku 2026-09-23 tweet + Art of Speculation 回覆）：
  市場大部分升幅喺短時間發生，70-80% 時間震盪，20-30% 單邊。
  由 mb_burst.py 用 403 隻 × 500 日量化。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"C:\Users\rain0\trading-os\output\model_book\burst.json"

CSS = """
.burst{font-size:12.5px;line-height:1.85}
.burst .quote{border-left:3px solid #c2410c;background:rgba(194,65,12,.07);
  padding:11px 14px;border-radius:0 10px 10px 0;margin:0 0 14px}
.burst .big{font-size:30px;font-weight:800;font-family:ui-monospace;
  line-height:1.05;color:#c2410c}
.burst .sub{font-size:11px;opacity:.55;font-family:ui-monospace}
.burst .cards{display:grid;grid-template-columns:repeat(auto-fit,
  minmax(200px,1fr));gap:10px;margin:0 0 14px}
.burst .c{border:1px solid rgba(128,128,128,.22);border-radius:12px;
  padding:13px 15px;background:rgba(128,128,128,.04)}
.burst .c b{font-size:13px}
.burst .c .v{font-size:24px;font-weight:800;font-family:ui-monospace}
.burst .c .v.red{color:#b91c1c}
.burst .c .v.grn{color:#15803d}
.burst table{width:100%;border-collapse:collapse;font-size:12px;
  margin:0 0 14px}
.burst th{text-align:left;padding:6px 8px;font-size:10px;
  text-transform:uppercase;letter-spacing:.04em;opacity:.55;
  border-bottom:1px solid rgba(128,128,128,.25)}
.burst td{padding:6px 8px;border-bottom:1px solid rgba(128,128,128,.09);
  font-family:ui-monospace}
.burst .concl{background:rgba(21,128,61,.08);border:1px solid
  rgba(21,128,61,.3);border-radius:12px;padding:13px 15px;
  font-size:12.5px;line-height:1.9}
.burst .concl b{color:#15803d}
@media(max-width:700px){
  .burst .cards{grid-template-columns:1fr 1fr}
  .burst .big{font-size:24px}
}
"""


def block():
    if not os.path.exists(SRC):
        return ""
    d = json.load(io.open(SRC, encoding="utf-8"))
    dist = d["daily_dist"]
    conc = d["concentration"]
    tc = d["trend_vs_chop"]
    cmp = d["compounding"]

    out = [f"<style>{CSS}</style>", '<div class="card burst">']
    out.append("<h3>⏱️ 升幅嘅時間集中度（深入研究）</h3>")

    out.append('<div class="quote">'
               '<b>命題（TraderGoku 2026-09-23）：</b>'
               '「股市大部分升幅發生喺很短嘅時間內，其餘時間多數橫盤。」'
               '<br><b>Art of Speculation：</b>'
               '「市場 70-80% 時間震盪，只有 20-30% 單邊值得把握。」'
               '<br><span class="sub">用我哋 '
               f'{d["n_stocks"]} 隻股票 × 500 日（{d["n_days"]:,} 個日回報）'
               '實測</span></div>')

    # 核心卡
    out.append('<div class="cards">')
    out.append(f'<div class="c"><b>最好 5% 日子</b>'
               f'<div class="v red">{conc["best5_pct_contribution"]["median"]}%'
               f'</div><div class="sub">貢獻咗總升幅（中位）。'
               f'即係其餘 95% 日子加埋係【蝕】</div></div>')
    out.append(f'<div class="c"><b>錯過最好 5 日</b>'
               f'<div class="v red">{conc["miss_best5"]["med"]}%'
               f'</div><div class="sub">剩返利潤（中位），'
               f'{conc["miss_best5"]["neg_frac"]}% 股票會轉蝕</div></div>')
    out.append(f'<div class="c"><b>錯過最好 10 日</b>'
               f'<div class="v red">{conc["miss_best10"]["med"]}%'
               f'</div><div class="sub">'
               f'{conc["miss_best10"]["neg_frac"]}% 股票轉蝕</div></div>')
    out.append(f'<div class="c"><b>錯過最好 20 日</b>'
               f'<div class="v red">{conc["miss_best20"]["med"]}%'
               f'</div><div class="sub">'
               f'{conc["miss_best20"]["neg_frac"]}% 股票轉蝕 —— 全軍覆沒'
               f'</div></div>')
    out.append("</div>")

    # 每日分布
    out.append("<h4>每日回報分布</h4>")
    out.append("<table><tr><th>狀態</th><th>比例</th><th>意義</th></tr>")
    out.append(f"<tr><td>升市日</td><td>{dist['up']}%</td>"
               f"<td rowspan='3'>升跌近乎擲毫 —— "
               f"單日方向冇 edge，edge 喺「捕捉大動日」</td></tr>")
    out.append(f"<tr><td>跌市日</td><td>{dist['down']}%</td></tr>")
    out.append(f"<tr><td>橫行 ±0.2%</td><td>{dist['flat_02']}%</td></tr>")
    out.append(f"<tr><td>大動日（|回報|≥2%）</td><td>{dist['big_02']}%</td>"
               f"<td>超過一半日子係大動 —— 呢個市場波動極高</td></tr>")
    out.append(f"<tr><td>大動日（|回報|≥3%）</td><td>{dist['big_03']}%</td>"
               f"<td>三分一日子 ±3% 以上</td></tr>")
    out.append("</table>")

    # 趨勢 vs 震盪
    out.append("<h4>趨勢 vs 震盪（20MA 向上 = 趨勢）</h4>")
    out.append(f"<table><tr><td>趨勢日（中位）</td>"
               f"<td>{tc['median_trending_pct']}%</td></tr>"
               f"<tr><td>震盪日（中位）</td>"
               f"<td>{tc['median_chop_pct']}%</td></tr></table>")

    # 複利
    out.append("<h4>0→1 嘅複利數學</h4>")
    out.append(f"<p>假設每月 +3%、60 個月（{cmp['note']}）：</p>")
    out.append("<table><tr><th>階段</th><th>絕對金額</th><th>倍數</th></tr>")
    out.append(f"<tr><td>頭 30 個月</td><td>1 → {1+cmp['first_30m_gain']/100:.2f}"
               f"</td><td>×{1+cmp['first_30m_gain']/100:.1f}</td></tr>")
    out.append(f"<tr><td>尾 30 個月</td><td>再多 "
               f"{cmp['second_30m_gain']}%</td>"
               f"<td><b>×{cmp['ratio']:.1f} 絕對金額</b></td></tr>")
    out.append(f"<tr><td>總共 60 個月</td><td>+{cmp['total']}%</td>"
               f"<td>×{1+cmp['total']/100:.1f}</td></tr></table>")
    out.append('<p class="sub">同一個 +3%/月，尾 30 個月賺嘅【金額】'
               f'係頭 30 個月嘅 {cmp["ratio"]:.1f} 倍 —— '
               '因為本金大咗。呢個就係「0→1 之後加速複利」。</p>')

    # 結論
    out.append('<div class="concl"><b>★ 三個結論（有數據支撐）：</b><br>'
               '① 升幅極度集中 —— 最好 5% 日子已經係全部升幅，'
               '其餘 95% 日子加埋係蝕。<br>'
               '② 錯過最好 5 日 = 冇咗一半以上利潤；'
               '錯過 20 日 = 100% 轉蝕。<br>'
               '③ 所以【唔可以擇時離場】—— '
               '你唔知邊 5 日係「最好嗰 5 日」。'
               '唯一做法 = <b>揀啱趨勢股 + 揸實唔放手</b>'
               '（同 Jeff Sun 3 段 stop + 拖 10EMA 一致）。'
               '</div>')

    out.append("</div>")
    return "".join(out)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    h = block()
    print(f"✓ {len(h):,} 字")
    p = os.path.join(HERE, "docs", "modelbook_burst.html")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(h)
    print(f"✓ {p}")


if __name__ == "__main__":
    main()
