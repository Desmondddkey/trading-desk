# -*- coding: utf-8 -*-
"""review_page.py — 覆盤頁（唯讀）

Desmond 2026-10-24：覆盤數據一直有跑但頁面見唔到 → 起一頁睇 R 分佈／期望值／執行偏差。

數據來源（全部唯讀，唔會改任何帳本）
  sim_ledger/fleet/champion/trades.jsonl   Champion 組合逐單（r、hold_days…）
  output/edge_audit.csv                    各出場規則 R（edge 審計）
  output/setup_alerts_history.csv           警報歷史（有 alert_px 才有執行偏差）

原則
  1. 冇數據 = 講「DATA_UNAVAILABLE」，唔准填 0。
  2. 所有 KPI 同一把尺：R（已按 3 段止蝕計）。
  3. 只顯示 n；n < 20 標「樣本不足」，唔准下結論（SOUL §8.14）。
"""
import csv
import io
import json
import os
import sys

ROOT = r"C:/Users/rain0/trading-os"
LEDGER = os.path.join(ROOT, "sim_ledger", "fleet", "champion", "trades.jsonl")
AUDIT = os.path.join(ROOT, "output", "edge_audit.csv")
HIST = os.path.join(ROOT, "output", "setup_alerts_history.csv")
MIN_N = 20

CSS = """
.rv-kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
  gap:9px;margin:8px 0 14px}
.rv-k{background:rgba(128,128,128,.06);border:1px solid rgba(128,128,128,.22);
  border-radius:10px;padding:9px 11px}
.rv-k .l{font-size:10.5px;opacity:.6}
.rv-k .v{font-size:21px;font-weight:800;line-height:1.15;margin-top:2px}
.rv-k .s{font-size:10.5px;opacity:.55;margin-top:1px}
.rv-t{width:100%;border-collapse:collapse;font-size:12px;text-align:left}
.rv-t th{text-align:left;font-size:10px;opacity:.55;padding:5px 6px;
  border-bottom:1px solid rgba(128,128,128,.3)}
.rv-t td{padding:4px 6px;border-bottom:1px solid rgba(128,128,128,.1);text-align:left}
.rv-pos{color:#22c55e}.rv-neg{color:#ef4444}
.rv-note{font-size:11.5px;opacity:.65;line-height:1.75;margin-top:10px}
"""


def _trades():
    if not os.path.exists(LEDGER):
        return None
    out = []
    for ln in io.open(LEDGER, encoding="utf-8"):
        try:
            j = json.loads(ln)
        except Exception:                                      # noqa: BLE001
            continue
        r = j.get("r")
        try:
            r = float(r)
        except (TypeError, ValueError):
            continue
        out.append(dict(t=j.get("ticker") or j.get("sym") or "?", r=r,
                        hold=j.get("hold_days")))
    return out


def _audit():
    if not os.path.exists(AUDIT):
        return None
    rows = []
    with io.open(AUDIT, encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            rows.append(row)
    return rows


def _kpi(label, val, sub="", col=""):
    return (f'<div class="rv-k"><div class="l">{label}</div>'
            f'<div class="v" style="color:{col}">{val}</div>'
            f'<div class="s">{sub}</div></div>')


def _hist(rs):
    """R 分佈：-1 以下、-1~0、0~1、1~2、2~3、3+"""
    edges = [(-9, -1), (-1, 0), (0, 1), (1, 2), (2, 3), (3, 99)]
    labels = ["<-1", "-1~0", "0~1", "1~2", "2~3", "3+"]
    cnt = [0] * len(edges)
    for r in rs:
        for i, (a, b) in enumerate(edges):
            if a <= r < b:
                cnt[i] += 1
                break
    mx = max(cnt) or 1
    bars = "".join(
        f'<div style="flex:1;text-align:center">'
        f'<div style="height:{int(c / mx * 70)}px;background:'
        f'{"#ef4444" if i < 2 else "#22c55e"};border-radius:3px 3px 0 0;'
        f'margin:0 3px"></div>'
        f'<div style="font-size:10px;opacity:.6;margin-top:2px">{labels[i]}</div>'
        f'<div style="font-size:10px;opacity:.45">{c}</div></div>'
        for i, c in enumerate(cnt))
    return ('<div style="display:flex;align-items:flex-end;height:100px;'
            'margin:6px 0 4px">' + bars + '</div>')


def build():
    P = [f"<style>{CSS}</style>", '<div class="card">']
    P.append('<h2 style="margin:0 0 2px">覆盤</h2>'
             '<div style="font-size:11.5px;opacity:.62">'
             '唯讀｜R 全部按 3 段止蝕計｜n &lt; 20 唔准下結論</div>')

    tr = _trades()
    if tr is None:
        P.append('<div class="dim" style="margin-top:10px">'
                 'Champion 帳本 DATA_UNAVAILABLE（sim_ledger/fleet/champion/trades.jsonl）'
                 '</div>')
    else:
        rs = [t["r"] for t in tr]
        n = len(rs)
        win = sum(1 for r in rs if r > 0) / n * 100 if n else 0
        m = sum(rs) / n if n else 0
        gw = [r for r in rs if r > 0]
        gl = [r for r in rs if r < 0]
        payoff = (sum(gw) / len(gw)) / abs(sum(gl) / len(gl)) if gw and gl else None
        streak, mx = 0, 0
        for r in rs:
            streak = streak + 1 if r < 0 else 0
            mx = max(mx, streak)
        col = "#22c55e" if m > 0 else "#ef4444"
        P.append('<div class="rv-kpi">')
        P.append(_kpi("淨 R", f"{sum(rs):+.2f}", f"{n} 單", "#22c55e" if sum(rs) > 0 else "#ef4444"))
        P.append(_kpi("每單期望值", f"{m:+.3f}R", "要 > 0 才可持續", col))
        P.append(_kpi("勝率", f"{win:.1f}%", "目標 ≥30%（你實盤 32.1%）",
                      "#22c55e" if win >= 30 else "#f59e0b"))
        P.append(_kpi("贏輸比", f"{payoff:.2f}:1" if payoff else "—",
                      "目標 ≥4.38:1",
                      "#22c55e" if (payoff or 0) >= 4.38 else "#f59e0b"))
        P.append(_kpi("最大連蝕", f"{mx} 單", "≥3 觸發停手", "#f59e0b" if mx >= 3 else ""))
        P.append('</div>')
        P.append('<div style="font-size:12px;font-weight:700;opacity:.75">R 分佈</div>')
        P.append(_hist(rs))
        if n < MIN_N:
            P.append(f'<div class="rv-note">⚠ 樣本只有 {n} 單（&lt;{MIN_N}）—— '
                     '以上全部係「觀察」，唔可以當結論。</div>')
        last = tr[-15:][::-1]
        P.append('<div style="font-size:12px;font-weight:700;opacity:.75;'
                 'margin-top:12px">最近 15 單</div>')
        P.append('<table class="rv-t"><thead><tr><th>代號</th><th>R</th>'
                 '<th>持倉日</th></tr></thead><tbody>')
        for t in last:
            c = "rv-pos" if t["r"] > 0 else "rv-neg"
            P.append(f'<tr><td>{t["t"]}</td><td class="{c}">{t["r"]:+.2f}</td>'
                     f'<td>{t.get("hold") if t.get("hold") is not None else "—"}</td></tr>')
        P.append('</tbody></table>')

    au = _audit()
    if au:
        P.append('<div style="font-size:12px;font-weight:700;opacity:.75;'
                 'margin-top:14px">各出場規則（edge_audit.csv）</div>')
        P.append('<table class="rv-t"><thead><tr><th>規則</th><th>n</th>'
                 '<th>平均 R</th></tr></thead><tbody>')
        for row in au[:10]:
            k = (row.get("rule") or row.get("exit") or "—")
            try:
                nn = int(float(row.get("n") or 0))
                mm = float(row.get("mean_r") or row.get("avg_r") or 0)
            except (TypeError, ValueError):
                continue
            c = "rv-pos" if mm > 0 else "rv-neg"
            P.append(f'<tr><td>{k}</td><td>{nn}</td>'
                     f'<td class="{c}">{mm:+.3f}</td></tr>')
        P.append('</tbody></table>')

    P.append('<div class="rv-note">'
             '期望值 = 平均每單 R。只要 > 0 而且樣本 ≥20，就可以放大倉位；'
             '≤ 0 就要先修規則，唔係加倉。<br>'
             '贏輸比 4.38:1 係你實盤要補嘅缺口（現時 1.68:1）。'
             '</div>')
    P.append('</div>')
    return ("覆盤", "".join(P))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    t, b = build()
    print(f"{t} — {len(b):,} 字")
