# -*- coding: utf-8 -*-
"""yoyo_page.py — YOYO Ball 交易頁（網站）

Desmond 2026-10-20：建頁 + 先證明盈利才出 alert。

★ 鐵律：回測 EV ≤ 0 → 頁頂紅字警告，並且唔列任何訊號。
   寧願冇卡，唔好誤導。
"""
import io
import json
import os

BASE = r"C:\Users\rain0\trading-os"
BT = os.path.join(BASE, "output", "yoyo_ball_backtest.json")

CSS = """
.yb-hd{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 14px}
.yb-k{flex:1 1 108px;padding:11px 13px;border-radius:10px;
  border:1px solid rgba(128,128,128,.26);background:rgba(128,128,128,.05)}
.yb-k .n{font-size:20px;font-weight:800;line-height:1.15}
.yb-k .l{font-size:10.5px;opacity:.6;margin-top:2px}
.yb-gate{border-radius:10px;padding:13px 15px;margin:0 0 15px;
  font-size:12.5px;line-height:1.8;font-weight:600}
.yb-pass{border:1px solid rgba(22,163,74,.45);background:rgba(22,163,74,.08);color:#16a34a}
.yb-fail{border:1px solid rgba(220,38,38,.5);background:rgba(220,38,38,.09);color:#dc2626}
.yb-rule{font-size:12.5px;line-height:1.95}
.yb-rule b{color:#c2410c}
.yb-tbl{width:100%;border-collapse:collapse;font-size:11.5px}
.yb-tbl th{text-align:left;font-size:10.5px;letter-spacing:.05em;
  text-transform:uppercase;opacity:.55;padding:7px 8px;font-weight:700;
  border-bottom:1px solid rgba(128,128,128,.28)}
.yb-tbl td{padding:7px 8px;border-bottom:1px solid rgba(128,128,128,.1);
  text-align:left!important}
@media(max-width:700px){
  .yb-tbl thead{display:none}
  .yb-tbl,.yb-tbl tbody,.yb-tbl tr{display:block;width:100%}
  .yb-tbl tr{padding:8px 0;border-bottom:1px solid rgba(128,128,128,.16)}
  .yb-tbl td{display:inline;border:0;padding:1px 4px 1px 0;font-size:11.5px}
  .yb-tbl td:first-child{display:block;font-weight:800;font-size:12.5px}
}
"""


def _load():
    try:
        with io.open(BT, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return {}


def build():
    d = _load()
    short = d.get("short") or {}
    long_ = d.get("long") or {}

    parts = [f"<style>{CSS}</style>",
             "<h2>YOYO Ball <small>MACD(6,20,9) + 9/21EMA + 窄止蝕</small></h2>",
             '<p class="crumb">Oliver Kell Wedge Drop → 9/21EMA Crossback｜'
             '做空同做多條件完全對稱</p>']

    ok_s = short.get("proven") is True
    ok_l = long_.get("proven") is True
    if ok_s or ok_l:
        parts.append('<div class="yb-gate yb-pass">✅ 有方向過閘'
                     '（樣本 ≥30 且 EV > 0）—— 可以出 alert</div>')
    else:
        parts.append(
            '<div class="yb-gate yb-fail">⛔ 未過閘 —— 唔會出任何 alert<br>'
            '規則：要「樣本 ≥ 30」<b>同時</b>「EV > 0」才准出。'
            '而家未達標，所以下面唔會有訊號卡。'
            '呢個機制係防止你收到未證實嘅建議。</div>')

    parts.append('<div class="yb-hd">')
    for r, name in ((short, "做空"), (long_, "做多")):
        if not r.get("n"):
            parts.append(f'<div class="yb-k"><div class="n" style="opacity:.4">'
                         f'—</div><div class="l">{name}</div></div>')
            continue
        col = "#16a34a" if r.get("ev_r", 0) > 0 else "#dc2626"
        parts.append(
            f'<div class="yb-k"><div class="n" style="color:{col}">'
            f'{r["ev_r"]:+.2f}R</div><div class="l">{name} EV（n={r["n"]}）'
            f'</div></div>')
        parts.append(
            f'<div class="yb-k"><div class="n">{r.get("win_rate",0)*100:.0f}%</div>'
            f'<div class="l">{name} 勝率</div></div>')
        parts.append(
            f'<div class="yb-k"><div class="n">{r.get("avg_win",0):+.1f}</div>'
            f'<div class="l">{name} 平均贏</div></div>')
        parts.append(
            f'<div class="yb-k"><div class="n">{r.get("stop_rate",0)*100:.0f}%</div>'
            f'<div class="l">{name} 止蝕率</div></div>')
    parts.append('</div>')

    parts.append('<div class="card"><h2>Setup 規則 <small>做空（做多完全反轉）</small></h2>'
                 '<div class="body"><div class="yb-rule">'
                 '<b>① MACD(6,20,9)</b> 柱由 <b>正轉負</b>（最早嘅轉向訊號）<br>'
                 '<b>② 價格</b> 同日跌穿 <b>9EMA</b><br>'
                 '<b>③ 趨勢</b> 9EMA <b>已跌穿</b> 21EMA（死叉）<br>'
                 '<b>④ 過熱</b> 之前 20 日內 EXT. 曾 ≥ 2.0（炒過龍，有下跌空間）<br>'
                 '<b>⑤ 止蝕</b> 入場價 +0.2%（<b>固定窄幅，唔用結構位</b>）<br>'
                 '<b>⑥ 出場</b> <b>只拖 10EMA，冇固定目標</b><br><br>'
                 '<b style="color:#dc2626">⚠ 最重要嘅一條：冇上限。</b>'
                 '回測顯示設 3R 上限 → EV −0.59R；冇上限 → EV +5.57R。'
                 '因為贏家跑到 60-130R，設上限等於自我閹割。'
                 '</div></div></div>')

    parts.append('<div class="card"><h2>止蝕寬度 vs EV <small>'
                 '同一批訊號，只改止蝕</small></h2><div class="body">'
                 '<table class="yb-tbl"><thead><tr>'
                 '<th>止蝕</th><th>EV</th><th>勝率</th><th>平均贏</th>'
                 '<th>止蝕率</th></tr></thead><tbody>')
    for row in (("0.2%", "+5.57R", "10%", "+63.0R", "90%"),
                ("0.3%", "+3.41R", "10%", "+42.0R", "90%"),
                ("0.5%", "+1.69R", "10%", "+25.2R", "90%"),
                ("1.5 ATR", "−0.32R", "24%", "+2.0R", "74%")):
        col = "#16a34a" if row[1].startswith("+") else "#dc2626"
        parts.append(f'<tr><td><b>{row[0]}</b></td>'
                     f'<td style="color:{col};font-weight:700">{row[1]}</td>'
                     f'<td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td></tr>')
    parts.append('</tbody></table>'
                 '<div style="margin-top:10px;font-size:11.5px;opacity:.65;'
                 'line-height:1.7">'
                 '止蝕越窄 → EV 越高，但勝率越低。呢個就係 USIC 數學：'
                 '低勝率 × 極高賠率。代價係你要連續接受 9 單止蝕。'
                 '</div></div></div>')

    parts.append('<div class="card"><h2>今日訊號</h2><div class="body">')
    if not (ok_s or ok_l):
        parts.append('<div style="font-size:12.5px;opacity:.7;line-height:1.8">'
                     '⚪ 未過閘，所以今日唔會出訊號。<br>'
                     '呢個唔係系統壞咗 —— 係系統仲未證明自己賺錢，'
                     '所以未夠資格叫你行動。</div>')
    else:
        parts.append('<div style="font-size:12.5px;opacity:.7">'
                     '（過閘後，呢度會出卡：代號、方向、入場、止蝕、'
                     '股數、風險金額、理由、到期時間）</div>')
    parts.append('</div></div>')

    parts.append('<div class="note" style="margin-top:14px;font-size:11.5px;'
                 'line-height:1.8">'
                 '<b>樣本限制</b>：回測用日線 + 433 隻股票。'
                 'Desmond 實際用 5 分鐘圖入場，理論上入場更精準，'
                 '但日線回測<b>無法模擬</b>分鐘級止蝕。<br>'
                 '<b>統計限制</b>：0.2% 止蝕嘅 39 個樣本只有 4 個贏家，'
                 '統計上脆弱。需要更多樣本才能確認。<br>'
                 '<b>未證實就唔出 alert</b> —— 呢個係唯一防止資金受損嘅機制。'
                 '</div>')
    return ("YOYO Ball", "".join(parts))


if __name__ == "__main__":
    t, b = build()
    print(t, len(b), "bytes")
