# -*- coding: utf-8 -*-
"""backtest_page.py — 回測證據頁

Desmond 2026-10-21：「淨係出位置無回測好無用」

讀 output/signal_backtest.json → 表格化：
  每個 job / 每種出場 → n、EV(R)、勝率、贏輸比、t 值、判決
"""
import io
import json
import os

OUT = r"C:\Users\rain0\trading-os\output\signal_backtest.json"

CSS = """
.bt-t td,.bt-t th{font-size:11.5px;padding:5px 7px;white-space:nowrap;
  text-align:left}
.bt-t th{font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;
  opacity:.65;font-weight:700}
.bt-t .pos{color:#16a34a;font-weight:700}
.bt-t .neg{color:#dc2626;font-weight:700}
.bt-t .g{color:#16a34a;font-weight:800}
.bt-t .r{color:#dc2626;font-weight:800}
.bt-t .y{color:#d97706;font-weight:800}
.bt-k{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px}
.bt-k>div{flex:1 1 100px;padding:10px 12px;border-radius:10px;
  border:1px solid rgba(128,128,128,.26);background:rgba(128,128,128,.05)}
.bt-k .n{font-size:19px;font-weight:800;line-height:1.15}
.bt-k .l{font-size:10px;opacity:.6;margin-top:2px}
.bt-warn{border-left:3px solid #dc2626;background:rgba(220,38,38,.09);
  padding:10px 13px;border-radius:9px;margin:0 0 12px;font-size:12px;
  line-height:1.85}
.bt-good{border-left:3px solid #16a34a;background:rgba(22,163,74,.09);
  padding:10px 13px;border-radius:9px;margin:0 0 12px;font-size:12px;
  line-height:1.85}
@media(max-width:700px){
  .bt-t thead{display:none}
  .bt-t tr{display:block;border:1px solid rgba(128,128,128,.25);
    border-radius:10px;margin-bottom:8px;padding:8px 10px}
  .bt-t td{display:flex;justify-content:space-between;border:0;
    padding:2px 0;white-space:normal}
  .bt-t td::before{content:attr(data-l);opacity:.55;font-weight:600}
  .bt-k>div{flex:1 1 80px}
}
"""

LABELS = {
    "layer1_layer2": "L1/L2 掃描",
    "layer2a_rs": "L2a RS 領導股",
    "daily_plan": "每日計劃卡",
    "setup_alerts": "Setup 警報",
    "orh_rvol": "ORH / RVOL",
    "weekly_watch": "週線觀察",
}
KIND_LABELS = {
    "t3": "T+3 收市",
    "t10": "T+10 收市",
    "stop": "LOD 止蝕",
}


def load():
    if not os.path.exists(OUT):
        return None
    try:
        with io.open(OUT, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return None


def build():
    d = load()
    L = [f"<style>{CSS}</style>",
         "<h2>Backtest <small>每個訊號源嘅實測 EV</small></h2>"]

    if not d:
        L.append('<div class="warn">⛔ 未跑過回測。<br>'
                 '執行 <code>python signal_backtest.py</code> 生成 '
                 '<code>output/signal_backtest.json</code>。</div>')
        return ("Backtest", "".join(L))

    # 找最佳 / 最差
    rows = []
    for job, v in d.items():
        for kind, s in (v.get("stats") or {}).items():
            if not s:
                continue
            rows.append((job, kind, s))

    good = [r for r in rows if r[2]["verdict"] == "有 edge"]
    bad = [r for r in rows
           if r[2]["n"] >= 20 and r[2]["ev"] < 0 and r[1] != "stop"]

    L.append('<div class="bt-k">')
    for v, lab, col in (
            (len(d), "訊號源", ""),
            (len(good), "有 edge", "#16a34a" if good else ""),
            (len(bad), "負 EV", "#dc2626" if bad else ""),
            (f'{sum(x[2]["n"] for x in rows if x[1] == "t3")}',
             "可測樣本", "")):
        cc = f' style="color:{col}"' if col else ""
        L.append(f'<div><div class="n"{cc}>{v}</div>'
                 f'<div class="l">{lab}</div></div>')
    L.append('</div>')

    if good:
        for job, kind, s in good:
            L.append(
                '<div class="bt-good">✅ <b>'
                f'{LABELS.get(job, job)}</b> — {KIND_LABELS.get(kind, kind)}'
                f'　n={s["n"]}　EV <b>{s["ev"]:+.2f}R</b>'
                f'　勝率 {s["wr"]:.1f}%　贏輸比 {s["payoff"]:.2f}'
                f'　t=<b>{s["t"]:+.2f}</b>（顯著）<br>'
                '<b>→ 呢個源真係有 edge，值得加大資源。</b></div>')

    if bad:
        for job, kind, s in bad:
            L.append(
                '<div class="bt-warn">🩸 <b>'
                f'{LABELS.get(job, job)}</b> — {KIND_LABELS.get(kind, kind)}'
                f'　n={s["n"]}　EV <b>{s["ev"]:+.2f}R</b>'
                f'　勝率 {s["wr"]:.1f}%　t={s["t"]:+.2f}<br>'
                '<b>→ 負 EV，呢個源出嘅位置唔應該照跟。</b></div>')

    # 全表
    L.append('<div class="card"><h2>全表 '
             '<small>T+1 開盤入場、無前視</small></h2>'
             '<div class="body"><div style="overflow-x:auto">'
             '<table class="bt-t"><thead><tr>'
             '<th>訊號源</th><th>出場</th><th>訊號數</th><th>n</th>'
             '<th>EV</th><th>勝率</th><th>平均贏</th><th>平均輸</th>'
             '<th>贏輸比</th><th>t</th><th>判決</th>'
             '</tr></thead><tbody>')
    rows.sort(key=lambda x: (-x[2]["ev"]))
    for job, kind, s in rows:
        ec = "pos" if s["ev"] > 0 else "neg"
        vc = {"有 edge": "g", "未證實": "y", "樣本不足": ""}.get(
            s["verdict"], "r")
        L.append(
            f'<tr>'
            f'<td data-l="訊號源"><b>{LABELS.get(job, job)}</b></td>'
            f'<td data-l="出場">{KIND_LABELS.get(kind, kind)}</td>'
            f'<td data-l="訊號數">{d[job]["n_signals"]}</td>'
            f'<td data-l="n">{s["n"]}</td>'
            f'<td data-l="EV" class="{ec}">{s["ev"]:+.2f}R</td>'
            f'<td data-l="勝率">{s["wr"]:.1f}%</td>'
            f'<td data-l="平均贏">{s["avg_w"]:+.2f}R</td>'
            f'<td data-l="平均輸">{s["avg_l"]:+.2f}R</td>'
            f'<td data-l="贏輸比">{s["payoff"]:.2f}</td>'
            f'<td data-l="t">{s["t"]:+.2f}</td>'
            f'<td data-l="判決" class="{vc}">{s["verdict"]}</td>'
            f'</tr>')
    L.append('</tbody></table></div></div></div>')

    # 方法說明
    L.append('<div class="card"><h2>點量出嚟 '
             '<small>可覆核</small></h2><div class="body">'
             '<div style="font-size:12.5px;line-height:2">'
             '<b>① 入場</b>　訊號日<b>下一個交易日開盤</b>（T+1）—— '
             '唔用訊號日收市，避免前視<br>'
             '<b>② 止蝕</b>　訊號記錄嘅 LOD；冇記錄就用訊號價 −3%<br>'
             '<b>③ 出場</b>　T+3 收市／T+10 收市／LOD 止蝕三種獨立量<br>'
             '<b>④ R 單位</b>　1R = 入場價 − 止蝕價。EV 以 R 計，'
             '唔受股價高低影響<br>'
             '<b>⑤ 判決門檻（事先寫死）</b>　n≥30 且 EV>0 且 |t|≥1.96 '
             '→ 有 edge；否則「未證實」或「樣本不足」</div></div></div>')

    L.append('<div class="note" style="margin-top:14px;font-size:11.5px;'
             'line-height:1.85">'
             '<b>數據</b>　sim_ledger/fleet/&lt;job&gt;/signals.jsonl + '
             'cache/sim_prices.pkl<br>'
             '<b>重跑</b>　<code>python signal_backtest.py</code><br>'
             '<b>★ 限制</b>　訊號歷史只有 7 個交易日（2026-10-12 → 10-20），'
             '樣本細。<br>'
             '<b>★ 「LOD 止蝕」行嘅 0% 勝率係定義使然</b>　'
             '呢行只計「撞止蝕嗰批」，全部都係 −1R，所以 0% 勝率係必然，'
             '唔係「冇贏過」。要睇有冇效請睇 EV 對比。</div>')
    return ("Backtest", "".join(L))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    t, b = build()
    print(t, len(b) // 1024, "KB")
