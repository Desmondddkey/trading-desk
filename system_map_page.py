# -*- coding: utf-8 -*-
"""system_map_page.py — 系統地圖：每一個 cron job 做緊咩（知識可視化）

資料來源（全部唯讀）
  1. C:/Users/rain0/AppData/Local/hermes/cron/jobs.json     排程、狀態、腳本
  2. trading-os/edge_book/job_descriptions.json             功能／作用／出處
  3. 執行記錄（last_run_at / last_status）
"""
from __future__ import annotations

import html as _h
import io
import json
import os
from collections import Counter, defaultdict

JOBS = r"C:/Users/rain0/AppData/Local/hermes/cron/jobs.json"
DESC = r"C:/Users/rain0/trading-os/edge_book/job_descriptions.json"

_WD = ["日", "一", "二", "三", "四", "五", "六"]


def _expand(field, lo, hi):
    """cron 欄位 → 展開數字 list（支援 *、a-b、*/n、a,b）。"""
    out = []
    for part in str(field).split(","):
        part = part.strip()
        step = 1
        if part.startswith("*/"):
            step = int(part[2:])
            out.extend(range(lo, hi + 1, step))
            continue
        if "-" in part and "/" in part:
            rng, st = part.split("/")
            a, b = rng.split("-")
            out.extend(range(int(a), int(b) + 1, int(st)))
            continue
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
            continue
        if part == "*":
            out.extend(range(lo, hi + 1))
            continue
        out.append(int(part))
    return sorted(set(out))


def expr_like(v):
    """係唔係 5 欄 cron 表達式（唔係 'every 30m' 呢類人話）。"""
    if not isinstance(v, str):
        return False
    parts = v.split()
    if len(parts) != 5:
        return False
    for x in parts:
        core = x.replace("*", "").replace("/", "").replace(",", "").replace("-", "")
        if core and not core.isdigit():
            return False
    return True


def human_schedule(expr):
    """cron → 人話（HKT）。例：*/15 21-23,0-4 * * 2-6 → 21:00–04:59 每 15 分鐘｜週二–六"""
    try:
        f = str(expr).split()
        if len(f) != 5:
            return str(expr)
        mins = _expand(f[0], 0, 59)
        hours = _expand(f[1], 0, 23)
        dom = f[2]
        dow = _expand(f[4], 0, 6) if f[4] != "*" else list(range(7))
    except Exception:                                        # noqa: BLE001
        return str(expr)
    if not mins or not hours:
        return str(expr)

    # 連續小時（容許跨午夜）
    hs = sorted(hours)
    n = len(hs)
    if n == 1:
        start_h = end_h = hs[0]
        wrapped = False
    else:
        gaps = [(hs[(i + 1) % n] - hs[i]) % 24 for i in range(n)]
        k = max(range(n), key=lambda i: gaps[i])
        start_h, end_h = hs[(k + 1) % n], hs[k]
        wrapped = start_h > end_h
        contiguous = sum(gaps) - gaps[k] == n - 1
        if not contiguous:            # 唔連續 → 逐個列
            times = "、".join(f"{h:02d}:{mins[0]:02d}" for h in hs[:4])
            if len(mins) > 1:
                times = "、".join(f"{h:02d}:00" for h in hs[:4])
            pre = f"每月 {dom} 日 " if dom != "*" else ""
            return pre + times + _dow_txt(dow)

    step = None
    if len(mins) > 1:
        gaps_m = {mins[i + 1] - mins[i] for i in range(len(mins) - 1)}
        step = gaps_m.pop() if len(gaps_m) == 1 else None

    if len(mins) == 1:
        if n == 1:
            t = f"{hs[0]:02d}:{mins[0]:02d}"
        elif n <= 4:
            t = "、".join(f"{h:02d}:{mins[0]:02d}" for h in hs)
        else:
            t = f"{start_h:02d}:{mins[0]:02d}–{end_h:02d}:{mins[0]:02d}"
    else:
        ev = "每分鐘" if step == 1 else (f"每 {step} 分鐘" if step else f"每小時 {len(mins)} 次")
        if n == 1:
            t = f"{hs[0]:02d}:00–{hs[0]:02d}:59 {ev}"
        else:
            t = f"{start_h:02d}:00–{end_h:02d}:59 {ev}"

    if dom != "*":
        return f"每月 {dom} 日 {t}" + _dow_txt(dow).replace("｜每日", "")
    return t + _dow_txt(dow)


def _dow_txt(dow):
    if dow == list(range(7)):
        return "｜每日"
    if len(dow) == 1:
        return f"｜週{_WD[dow[0]]}"
    if dow == list(range(dow[0], dow[-1] + 1)):
        return f"｜週{_WD[dow[0]]}–{_WD[dow[-1]]}"
    return "｜" + "、".join(f"週{_WD[x]}" for x in dow[:4])


# 依實際流程排（HKT）。job 名 → 階段
PHASES = [
    ("盤中（美股開市）", "#22c55e", [
        "setup-alerts", "jeffsun-intraday-ORH-RVOL-alert", "rsw-radar-intraday",
        "regime-live-5min", "discipline-gate", "close-watch-exit",
        "osib-setup-alert", "yoyo-gap-alert", "ftd-pre-alert-daily",
        "morales-prone", "macro-tail-guard", "journal-open-check",
    ]),
    ("收市後（04:00–07:00）", "#3b82f6", [
        "competition-daily", "fleet-sim-daily", "earnings-daily", "labeller-daily",
        "leader-map-daily", "money-daily-benchmark", "usic-setup-daily-review",
        "jeffsun-intraday-rvol-record", "yoyo-gap-postclose",
        "notion-trade-journal-sync", "desk-refresh-daily",
    ]),
    ("盤前（17:00–21:00）", "#f97316", [
        "jeffsun-daily-scan-layer1+2", "Daily-Pre-market-Plan", "layer4-breadth-daily",
        "premarket-refresh-1850", "premarket-audit-daily", "premarket-list-daily",
        "rs-select-daily", "rs-alpha-daily", "rotation-map-weekly",
        "sector-rotation-daily", "theme-watch-daily", "setup-check",
        "yoyo-ball-alert", "trading-desk-daily (19:00)", "market-watch",
        "notion-records-daily", "site-db-daily",
    ]),
    ("夜間（22:00–00:00）", "#a855f7", [
        "digest-premarket", "notion-nightly-sync", "sim-trade-daily",
        "site-auto-rebuild", "freshness-guard-daily", "wave-ledger-daily",
        "gto-notion-sync", "l2-cell-backtest-daily",
        "cashdesk-daily", "digest-evening",
    ]),
    ("每週", "#eab308", [
        "modelbook-all-weekly", "top250-weekly", "quality-watch-weekly",
        "shadow-exit-weekly", "js3-stop-watch-weekly", "edge-question-weekly",
        "job-audit-weekly", "michelin-audit-weekly", "job-freshness-weekly",
        "tree-trace-weekly", "weekly-watchlist-sunday-0900", "gto-daily-weekly",
    ]),
    ("巡檢／備份", "#94a3b8", [
        "kitchen-watchdog", "trading-os-tests", "changelog-notion-sync",
        "hermes-icloud-backup", "edge-candidate-daily", "freshness-audit-daily",
        "notion-kb-sync", "usic-monthly-log-excel", "track-record-daily",
        "hermes-daily-digest", "kitchen-status-daily", "journal-daily-reminder",
        "memory-hygiene-weekly", "memory-hygiene-monthly", "fat-pitch-scan",
        "expansion-break-shadow", "model-book-weekly", "notion-records-daily",
    ]),
]


def _esc(x):
    return _h.escape(str(x if x is not None else ""))


def _load(p):
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return None


def _jobs():
    d = _load(JOBS) or []
    js = d if isinstance(d, list) else d.get("jobs", [])
    out = {}
    for j in js:
        n = j.get("name")
        if n:
            out[n] = j
    return out



def _flow_svg():
    """資料流圖（diagram-design 規格：8 節點、正交箭嘴、accent ≤2、有 title/desc）"""
    paper, ink, muted, accent, rule = "#0f1115", "#e5e7eb", "#94a3b8", "#f97316", "#2a2f3a"
    nodes = [
        ("數據源", "yfinance · TradingView screener", False),
        ("掃描 layer1+2", "18:05 · 每日 5 千隻 → 73 隻", False),
        ("計劃卡", "18:10 · pivot／止蝕／倉位／油門", False),
        ("盤中警報", "21:30–00:00 · ORH／RVOL／setup", False),
        ("模擬帳本", "fleet_sim · 每 job 獨立帳本", False),
        ("回測 & EV", "gto_daily · edge_audit · 分桶勝率", True),
        ("網站 + Notion", "23:50 重建 · 回測庫自動回填", False),
        ("你嘅決策", "每日流程 → 5 頁 · 人手落決定", True),
    ]
    W, H = 760, 866
    bw, bh, gap = 520, 68, 30
    x0 = (W - bw) / 2
    y = 34
    parts = [f'<svg role="img" aria-labelledby="wfm-title wfm-desc" viewBox="0 0 {W} {H}" '
             f'width="100%" style="min-width:{W}px;max-width:{W}px">',
             '<title id="wfm-title">系統資料流</title>',
             '<desc id="wfm-desc">由數據源經掃描、計劃、警報、模擬、回測到網站與決策的八步流程</desc>',
             f'<defs><marker id="wfm-ar" viewBox="0 0 10 10" refX="9" refY="5" '
             f'markerWidth="7" markerHeight="7" orient="auto">'
             f'<path d="M0,0 L10,5 L0,10 z" fill="{muted}"/></marker></defs>',
             f'<rect x="0" y="0" width="{W}" height="{H}" fill="{paper}"/>']
    for i, (name, sub, focal) in enumerate(nodes):
        col = accent if focal else rule
        fill = "#161a22" if not focal else "#1c1710"
        parts.append(f'<rect x="{x0}" y="{y}" width="{bw}" height="{bh}" rx="6" '
                     f'fill="{fill}" stroke="{col}" stroke-width="{2 if focal else 1}"/>')
        parts.append(f'<text x="{x0+18}" y="{y+27}" fill="{accent if focal else ink}" '
                     f'font-family="Geist,system-ui,sans-serif" font-size="15" '
                     f'font-weight="600">{_esc(name)}</text>')
        parts.append(f'<text x="{x0+18}" y="{y+49}" fill="{muted}" '
                     f'font-family="ui-monospace,SFMono-Regular,monospace" '
                     f'font-size="11.5">{_esc(sub)}</text>')
        if i < len(nodes) - 1:
            y2 = y + bh + gap
            parts.append(f'<line x1="{x0+bw/2}" y1="{y+bh}" x2="{x0+bw/2}" y2="{y2-6}" '
                         f'stroke="{muted}" stroke-width="1.4" marker-end="url(#wfm-ar)"/>')
        y += bh + gap
    parts.append(f'<text x="{x0}" y="{y+6}" fill="{muted}" font-size="10.5" '
                 f'font-family="ui-monospace,monospace">'
                 f'橙＝斷咗就成條鏈失效嘅兩環：回測（有冇 edge）同決策（做唔做）</text>')
    parts.append('</svg>')
    return ('<div style="overflow-x:auto;padding:10px 0">' + "".join(parts) + '</div>')


def build():
    jobs = _jobs()
    desc = _load(DESC) or {}
    listed = {n for _, _, names in PHASES for n in names}
    others = [n for n in jobs if n not in listed]

    ok = sum(1 for j in jobs.values() if j.get("last_status") == "ok")
    fail = [n for n, j in jobs.items()
            if j.get("last_status") not in (None, "ok")]
    noagent = sum(1 for j in jobs.values() if j.get("no_agent"))

    P = ['<h2>🗺 系統地圖 <small>每個 job 做緊咩</small></h2>']
    P.append('<div class="pf-mini2"><table><thead><tr>'
             '<th>項目</th><th class="n">數目</th><th>說明</th></tr></thead><tbody>')
    P.append(f'<tr><td>總 job</td><td class="n">{len(jobs)}</td>'
             f'<td>其中 <b>{noagent}</b> 個 no_agent（<b>零 token</b>，純腳本）</td></tr>')
    P.append(f'<tr><td>最近一次成功</td><td class="n">{ok}</td>'
             f'<td>狀態 ok</td></tr>')
    P.append(f'<tr><td>有問題</td><td class="n">{len(fail)}</td>'
             f'<td>{_esc(", ".join(fail[:6])) if fail else "冇"}</td></tr>')
    P.append('</tbody></table></div>')

    for phase, col, names in PHASES:
        rows = [n for n in names if n in jobs]
        if not rows:
            continue
        P.append(f'<h3 style="margin-top:16px;color:{col}">{_esc(phase)}'
                 f'　<span style="font-size:11px;opacity:.6">{len(rows)} 個</span></h3>')
        P.append('<div class="pf-mini2"><table><thead><tr>'
                 '<th>時間</th><th>Job</th><th>做咩</th><th>產物／去向</th>'
                 '<th>狀態</th></tr></thead><tbody>')
        for n in rows:
            j = jobs[n]
            sch = (j.get("schedule") or {})
            raw = sch.get("expr") or sch.get("display") or ""
            t = human_schedule(raw) if expr_like(raw) else (sch.get("display") or raw)
            dsc = desc.get(n) or {}
            fn = dsc.get("功能") or (j.get("prompt") or "")[:40]
            use = dsc.get("作用") or "—"
            script = j.get("script") or "（agent）"
            st = j.get("last_status") or "未跑"
            stc = "#22c55e" if st == "ok" else ("#ef4444" if st else "#94a3b8")
            P.append(f'<tr><td class="n" style="white-space:nowrap" title="{_esc(raw)}">'
                     f'{_esc(t)}</td>'
                     f'<td><b>{_esc(n)}</b><br><span style="font-size:10px;opacity:.5">'
                     f'{_esc(script)}</span></td>'
                     f'<td>{_esc(fn)}<br><span style="font-size:10.5px;opacity:.65">'
                     f'{_esc(use[:110])}</span></td>'
                     f'<td style="font-size:10.5px;opacity:.7">{_esc(dsc.get("出處") or "—")}</td>'
                     f'<td style="color:{stc};font-weight:700">{_esc(st)}</td></tr>')
        P.append('</tbody></table></div>')

    if others:
        P.append('<h3 style="margin-top:16px">其他</h3>')
        P.append('<div class="pf-mini2"><table><thead><tr><th>Job</th><th>做咩</th>'
                 '<th>狀態</th></tr></thead><tbody>')
        for n in others:
            dsc = desc.get(n) or {}
            P.append(f'<tr><td>{_esc(n)}</td><td>{_esc(dsc.get("功能") or "未描述")}</td>'
                     f'<td>{_esc(jobs[n].get("last_status") or "未跑")}</td></tr>')
        P.append('</tbody></table></div>')

    # 資料流（知識可視化：diagram-design 規格）
    P.append('<h3 style="margin-top:18px">資料流</h3>')
    P.append(_flow_svg())
    P.append('<div class="pf-note">每條箭嘴都係一個 cron job；'
             '任何一段斷，後面全部收唔到新數據。</div>')
    return ("系統地圖", "".join(P))


def main():
    t, b = build()
    print(f"{t} — {len(b):,} chars")


if __name__ == "__main__":
    main()
