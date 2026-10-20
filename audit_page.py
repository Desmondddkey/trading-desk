# -*- coding: utf-8 -*-
"""audit_page.py — 系統審計頁（只答一條問題：賺幾多錢）

Desmond 2026-10-21：
  「我淨係要見到你賺幾多錢 唔係講廢話」
  「直到你見到 Kelly Criterion 上有進步」

讀 output/system_audit.json → 錢 + Kelly + 判決 + 化繁為簡清單
"""
import io
import json
import os

AUD = r"C:\Users\rain0\trading-os\output\system_audit.json"

CSS = """
.au-hero{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 14px}
.au-hero>div{flex:1 1 130px;padding:14px 16px;border-radius:12px;
  border:1px solid rgba(128,128,128,.28);background:rgba(128,128,128,.05)}
.au-hero .n{font-size:26px;font-weight:800;line-height:1.1;
  font-variant-numeric:tabular-nums}
.au-hero .l{font-size:10.5px;opacity:.6;margin-top:3px}
.au-t td,.au-t th{font-size:11.5px;padding:5px 7px;white-space:nowrap;
  text-align:left}
.au-t th{font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;
  opacity:.65;font-weight:700}
.au-t .pos{color:#16a34a;font-weight:700}
.au-t .neg{color:#dc2626;font-weight:700}
.au-v{display:inline-block;padding:1px 7px;border-radius:20px;
  font-size:10px;font-weight:800;white-space:nowrap}
.v-red{background:#fee2e2;color:#991b1b;border:1px solid #ef4444}
.v-amber{background:#fef3c7;color:#92400e;border:1px solid #f59e0b}
.v-green{background:#dcfce7;color:#166534;border:1px solid #22c55e}
.v-gold{background:#fef9c3;color:#854d0e;border:1px solid #eab308}
.v-grey{background:#e2e8f0;color:#475569;border:1px solid #94a3b8}
.au-card{border:1px solid rgba(128,128,128,.26);border-radius:12px;
  padding:12px 15px;margin:0 0 10px;font-size:12.5px;line-height:1.9}
.au-card.red{border-color:rgba(220,38,38,.4);background:rgba(220,38,38,.06)}
.au-card.green{border-color:rgba(22,163,74,.4);background:rgba(22,163,74,.06)}
.au-kpi{font-family:ui-monospace;font-size:12px}
@media(max-width:700px){
  .au-t thead{display:none}
  .au-t tr{display:block;border:1px solid rgba(128,128,128,.25);
    border-radius:10px;margin-bottom:8px;padding:8px 10px}
  .au-t td{display:flex;justify-content:space-between;border:0;
    padding:2px 0;white-space:normal}
  .au-t td::before{content:attr(data-l);opacity:.55;font-weight:600}
  .au-hero>div{flex:1 1 45%;padding:11px 12px}
  .au-hero .n{font-size:21px}
}
"""

EXIT_LABEL = {"js3": "Jeff Sun 3-stop", "t3": "T+3 收市",
              "t10": "T+10 收市", "stop": "單層 LoD"}


def load():
    if not os.path.exists(AUD):
        return None
    try:
        with io.open(AUD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return None


def build():
    d = load()
    L = [f"<style>{CSS}</style>",
         "<h2>系統審計 <small>賺幾多錢 · Kelly</small></h2>"]

    if not d:
        L.append('<div class="warn">⛔ 未跑過審計。<br>'
                 '執行 <code>python system_audit.py</code>。</div>')
        return ("系統審計", "".join(L))

    s = d["system"]
    L.append(f'<p class="crumb">審計日 {d["date"]}｜'
             f'{s["days"]} 個交易日｜{s["n"]} 個 round-trip</p>')

    # 四巨頭 KPI（錢行先）
    pnl_col = "#16a34a" if s["pnl"] > 0 else "#dc2626"
    ann_col = ("#16a34a" if (s["annual_pct"] or 0) > 0 else "#dc2626")
    kel_col = "#16a34a" if (s["kelly"] or 0) > 0 else "#dc2626"
    L.append('<div class="au-hero">')
    for v, lab, col in (
            (f'${s["pnl"]:+,.0f}', "賺蝕（美元）", pnl_col),
            (f'{s["ret_pct"]:+.2f}%', "總報酬", pnl_col),
            (f'{s["annual_pct"]:+.0f}%' if s["annual_pct"] is not None
             else "—", "年化", ann_col),
            (f'{s["kelly"]:+.3f}' if s["kelly"] is not None else "—",
             "Kelly", kel_col),
            (f'${s["nav"]:,.0f}', "而家資金", "")):
        cc = f' style="color:{col}"' if col else ""
        L.append(f'<div><div class="n"{cc}>{v}</div>'
                 f'<div class="l">{lab}</div></div>')
    L.append("</div>")

    # 距離 USIC
    g = s.get("gap_to_usic_monthly")
    if g is not None:
        L.append(f'<div class="au-card red">'
                 f'🏆 <b>距離 USIC 冠軍（月化 8.23%）</b>：'
                 f'你月化 <b>{s["monthly_pct"]:+.2f}%</b>，'
                 f'差 <b>{g:.2f} 個百分點</b>。<br>'
                 f'最低合格線（月化 5%）：'
                 f'{"已達到" if (s["monthly_pct"] or -99) >= 5 else "未達到"}。</div>')

    # 化繁為簡
    keep = d.get("keep") or []
    cut = d.get("cut") or []
    if keep:
        L.append(f'<div class="au-card green">✅ <b>保留（Kelly &gt; 0）</b>：'
                 f'{"、".join(keep)}</div>')
    if cut:
        L.append(f'<div class="au-card red">🗑 <b>刪除（Kelly ≤ 0 = 空中樓閣）</b>：'
                 f'{"、".join(cut)}<br>'
                 f'<b>唔係講理論 —— 呢啲 job 出嘅位置長期係負期望。</b></div>')

    # 主表
    L.append('<div class="card"><h2>每個 Job 賺幾多 '
             '<small>按賺蝕排序</small></h2>'
             '<div class="body"><div style="overflow-x:auto">'
             '<table class="au-t"><thead><tr>'
             '<th>Job</th><th>錢</th><th>報酬</th><th>年化</th>'
             '<th>Kelly</th><th>最佳出場</th><th>判決</th>'
             '</tr></thead><tbody>')
    for j, v in sorted(d["jobs"].items(), key=lambda kv: -kv[1]["pnl"]):
        pc = "pos" if v["pnl"] > 0 else "neg" if v["pnl"] < 0 else ""
        ac = ("pos" if (v["annual_pct"] or 0) > 0 else
              "neg" if (v["annual_pct"] or 0) < 0 else "")
        kc = ("pos" if (v["kelly"] or 0) > 0 else
              "neg" if (v["kelly"] or 0) < 0 else "")
        L.append(
            f'<tr>'
            f'<td data-l="Job"><b>{j}</b></td>'
            f'<td data-l="錢" class="{pc}">${v["pnl"]:+,.0f}</td>'
            f'<td data-l="報酬" class="{pc}">{v["ret_pct"]:+.2f}%</td>'
            f'<td data-l="年化" class="{ac}">'
            f'{v["annual_pct"]:+.0f}%</td>'
            f'<td data-l="Kelly" class="{kc}">'
            f'{v["kelly"]:+.2f}</td>'
            f'<td data-l="最佳出場">{EXIT_LABEL.get(v.get("best_exit"), "—")}'
            f'</td>'
            f'<td data-l="判決"><span class="au-v v-{v["vclass"]}">'
            f'{v["verdict"]}</span></td>'
            f'</tr>')
    L.append("</tbody></table></div></div></div>")

    # 出場規則 Kelly 對比（化繁為簡核心）
    L.append('<div class="card"><h2>出場規則 Kelly 對比 '
             '<small>邊個出場最賺錢</small></h2><div class="body">'
             '<div style="overflow-x:auto">'
             '<table class="au-t"><thead><tr>'
             '<th>Job</th><th>出場</th><th>n</th><th>EV</th>'
             '<th>勝率</th><th>贏輸比</th><th>Kelly</th>'
             '</tr></thead><tbody>')
    rows = []
    for j, v in d["jobs"].items():
        for k, x in (v.get("exits") or {}).items():
            if k == "stop":
                continue
            rows.append((j, k, x))
    rows.sort(key=lambda r: -(r[2].get("kelly") or -9))
    for j, k, x in rows:
        kc = ("pos" if (x.get("kelly") or 0) > 0 else
              "neg" if (x.get("kelly") or 0) < 0 else "")
        ec = "pos" if (x.get("ev") or 0) > 0 else "neg"
        L.append(
            f'<tr>'
            f'<td data-l="Job"><b>{j}</b></td>'
            f'<td data-l="出場">{EXIT_LABEL.get(k, k)}</td>'
            f'<td data-l="n">{x.get("n")}</td>'
            f'<td data-l="EV" class="{ec}">{x.get("ev"):+.2f}R</td>'
            f'<td data-l="勝率">{x.get("wr"):.1f}%</td>'
            f'<td data-l="贏輸比">{x.get("payoff"):.2f}</td>'
            f'<td data-l="Kelly" class="{kc}">{x.get("kelly"):+.2f}</td>'
            f'</tr>')
    L.append("</tbody></table></div></div></div>")

    # Kelly 解說（簡短）
    L.append('<div class="card"><h2>Kelly 點讀</h2><div class="body">'
             '<div style="font-size:12.5px;line-height:2">'
             '<b>公式</b>　f* = W − (1−W)/R<br>'
             '　W = 勝率　R = 贏輸比（平均贏 ÷ 平均輸）<br><br>'
             '<b>f* ≤ 0</b>　冇 edge，唔應該落注 → <b>空中樓閣</b><br>'
             '<b>f* = 0.59</b>　每單位資金可以落 59%（全 Kelly）<br>'
             '　實務用 1/4 Kelly = 15%（避免回撤）<br><br>'
             '<b>★ 呢頁只講錢</b>　唔講故事、唔講希望、唔講「有潛力」。'
             'Kelly ≤ 0 就係唔賺錢，要刪。</div></div></div>')

    L.append('<div class="note" style="margin-top:14px;font-size:11.5px;'
             'line-height:1.85">'
             '<b>數據</b>　sim_ledger/fleet/*/equity.csv + '
             'signal_backtest.json<br>'
             '<b>重跑</b>　<code>python system_audit.py</code><br>'
             '<b>★ 限制</b>　樣本只有 7 個交易日。Kelly 會隨樣本變動，'
             '足夠樣本（≥15 個訊號日）後才穩定。<br>'
             '<b>★ 年化</b>　年化 = (期末/期初)^(252/日數) − 1。'
             '短樣本年化會極端放大，只作方向參考。</div>')
    return ("系統審計", "".join(L))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    t, b = build()
    print(t, len(b) // 1024, "KB")
