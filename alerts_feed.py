# -*- coding: utf-8 -*-
"""alerts_feed.py — 把「所有 job 嘅 setup」統一成一張清單

問題（Desmond 2026-10-28）：「呢堆 SETUP ALERT 完全無哂，我想你完完整整
將我有既 CRON 同 JOB SETUP 都出落 Setup Alert 到」

已持久化、可以直接讀嘅來源
  setup_alerts_history.csv   6-setup 盤中警報（含 REJECTED_CHASE 等狀態）
  orh_alert_history.csv      ORH / RVOL 警報
  rs_alpha_latest.json       EXT 階段（A+/A 且 EXT 0–4 = 今日可留意）
  today_six.json             每日計劃卡（FOCUS 名單 + 入場/止蝕）

未持久化（只推 Telegram，冇寫檔）
  osib_alert / yoyo_gap_scan / ftd_pre_alert / yoyo_alert
  → 呢四個要另外加寫檔，先可以入呢張清單（誠實標示）

輸出：output/alerts_feed.json
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = r"C:/Users/rain0/trading-os/output"
OUT = os.path.join(HERE, "output")
TODAY = date.today().isoformat()


def log(m):
    print(m, file=sys.stderr)


def _csv(p):
    try:
        with io.open(p, encoding="utf-8", errors="replace") as f:
            return list(csv.reader(f))
    except OSError:
        return []


def _tail(path, days=5):
    """只取最近 N 日（按第一欄日期）"""
    rows = _csv(path)
    if not rows:
        return []
    cut = (date.today() - timedelta(days=days)).isoformat()
    return [r for r in rows if r and str(r[0])[:10] >= cut]


def from_setup(rows):
    out = []
    for r in rows:
        if len(r) < 4:
            continue
        out.append(dict(source="6-SETUP", date=str(r[0])[:10], ticker=r[1],
                        setup=r[2], time=r[3],
                        price=r[4] if len(r) > 4 else "",
                        stop=r[5] if len(r) > 5 else "",
                        status=(r[15] if len(r) > 15 else "") or "—",
                        note="｜".join(x for x in r[11:14] if x)[:80]))
    return out


def from_orh(rows):
    out = []
    for r in rows:
        if len(r) < 4:
            continue
        out.append(dict(source="ORH/RVOL", date=str(r[0])[:10], ticker=r[1],
                        setup=r[2], time=r[3],
                        price=r[4] if len(r) > 4 else "",
                        stop=r[5] if len(r) > 5 else "",
                        status="FIRED",
                        note="｜".join(x for x in r[6:10] if x)[:80]))
    return out


def from_alpha():
    p = os.path.join(LIVE, "rs_alpha_latest.json")
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for r in (d.get("rows") or []):
        ax = r.get("atrx")
        if not isinstance(ax, (int, float)) or not (0 <= float(ax) <= 4):
            continue
        rs = r.get("rs_rating")
        # 只留相對強（RS ≥ 90）＋ EXT 在買入區
        if not isinstance(rs, (int, float)) or rs < 90:
            continue
        out.append(dict(source="EXT 階段", date=str(r.get("date") or d.get("as_of"))[:10],
                        ticker=r.get("sym"), setup=str(r.get("phase") or "—"),
                        time="",
                        price=r.get("close") if r.get("close") is not None else "",
                        stop="", status=f"EXT {float(ax):.2f}",
                        note=f"RS {rs}｜α {'✓' if r.get('alpha') else '—'}"))
    return out


def from_plan():
    p = os.path.join(LIVE, "today_six.json")
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for r in (d.get("picks") or []):
        out.append(dict(source="計劃卡", date=str(d.get("day") or TODAY)[:10],
                        ticker=r.get("ticker"), setup="FOCUS", time="",
                        price=r.get("close") or "", stop="",
                        status=f"{d.get('regime') or ''}／cap {d.get('trade_cap')}",
                        note=f"pivot {r.get('pivot')}｜距 {r.get('dist_pivot_atr')} ATR"
                             f"｜{r.get('src') or ''}"))
    return out


CSS = """
.af-tbl{width:100%;border-collapse:collapse;font-size:12px}
.af-tbl th{text-align:left;font-size:10px;letter-spacing:.04em;opacity:.55;
  font-weight:800;padding:5px 7px;border-bottom:1px solid rgba(148,163,184,.25);
  white-space:nowrap}
.af-tbl td{padding:4px 7px;border-bottom:1px solid rgba(148,163,184,.1);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.af-tbl td.n{text-align:right}
.af-src{font-size:10px;padding:1px 6px;border-radius:999px;
  background:rgba(148,163,184,.16)}
.af-note{font-size:10.5px;line-height:1.6;opacity:.6;margin-top:8px}
"""


def render_html(limit=60):
    """回傳 HTML 區塊（讀 output/alerts_feed.json）"""
    try:
        d = json.load(io.open(os.path.join(OUT, "alerts_feed.json"),
                              encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    rows = (d.get("rows") or [])[:limit]
    if not rows:
        return ""
    L = [f"<style>{CSS}</style>", '<div class="card">',
         '<h2 style="margin:0 0 4px">所有 JOB 訊號</h2>',
         f'<div style="font-size:11px;opacity:.55;margin:0 0 8px">'
         f'{d.get("generated")}｜{len(d.get("rows") or [])} 筆｜'
         + "、".join(f"{k} {v}" for k, v in (d.get("counts") or {}).items())
         + '</div>',
         '<table class="af-tbl"><thead><tr>'
         '<th>日期</th><th>時間</th><th>來源</th><th>代號</th>'
         '<th>SETUP</th><th class="n">價</th><th>狀態</th><th>備註</th>'
         '</tr></thead><tbody>']
    for r in rows:
        tk = str(r.get("ticker") or "")
        L.append('<tr>'
                 f'<td>{_esc(r.get("date"))}</td>'
                 f'<td>{_esc(r.get("time") or "—")}</td>'
                 f'<td><span class="af-src">{_esc(r.get("source"))}</span></td>'
                 f'<td><a class="tv" data-sym="{_esc(tk)}" '
                 f'href="https://www.tradingview.com/chart/?symbol={_esc(tk)}" '
                 f'target="_blank" rel="noopener">{_esc(tk)}</a></td>'
                 f'<td>{_esc(r.get("setup"))}</td>'
                 f'<td class="n">{_esc(r.get("price"))}</td>'
                 f'<td>{_esc(r.get("status"))}</td>'
                 f'<td style="font-size:10.5px;opacity:.7">{_esc(r.get("note"))}</td>'
                 '</tr>')
    L.append('</tbody></table>')
    L.append('<div class="af-note">'
             '未持久化（只推 Telegram，冇寫檔）：'
             + _esc("、".join(d.get("not_persisted") or []))
             + '。要入呢張表，先要佢哋每次寫一行記錄。</div>')
    L.append('</div>')
    return "".join(L)


def _esc(x):
    return (str(x).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def main():
    srcs = {
        "6-SETUP": from_setup(_tail(os.path.join(LIVE, "setup_alerts_history.csv"), 7)),
        "ORH/RVOL": from_orh(_tail(os.path.join(LIVE, "orh_alert_history.csv"), 3)),
        "EXT 階段": from_alpha(),
        "計劃卡": from_plan(),
    }
    rows = []
    for k, v in srcs.items():
        rows.extend(v)
    rows.sort(key=lambda r: (r["date"], r.get("time") or ""), reverse=True)
    payload = {
        "generated": TODAY,
        "counts": {k: len(v) for k, v in srcs.items()},
        "not_persisted": ["osib_alert", "yoyo_gap_scan", "ftd_pre_alert", "yoyo_alert"],
        "rows": rows[:300],
    }
    os.makedirs(OUT, exist_ok=True)
    json.dump(payload, io.open(os.path.join(OUT, "alerts_feed.json"), "w",
                               encoding="utf-8"), ensure_ascii=False, indent=0)
    log(f"✓ alerts_feed.json｜{len(rows)} 筆｜" +
        "、".join(f"{k} {v}" for k, v in payload["counts"].items()))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
