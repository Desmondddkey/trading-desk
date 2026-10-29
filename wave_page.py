# -*- coding: utf-8 -*-
"""wave_page.py — 肥波總覽（大市 → 板塊 → RS → setup 漏斗 + 每日／每週可視化）"""
from __future__ import annotations

import html as _h
import io
import json
import os
from collections import defaultdict

LIVE = r"C:/Users/rain0/trading-os"
LEDGER = os.path.join(LIVE, "output", "wave_ledger.jsonl")
GTO = os.path.join(LIVE, "output", "gto_daily.json")


def _esc(x):
    return _h.escape(str(x if x is not None else ""))


def _load_ledger():
    if not os.path.exists(LEDGER):
        return []
    out = []
    with io.open(LEDGER, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:                                # noqa: BLE001
                continue
    return sorted(out, key=lambda o: o["date"])


def _spark(vals, w=260, h=46):
    vals = [v for v in vals if isinstance(v, (int, float))]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    step = w / (len(vals) - 1)
    pts = [(i * step, h - (v - lo) / rng * (h - 6) - 3) for i, v in enumerate(vals)]
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    col = "#22c55e" if vals[-1] >= 50 else "#f97316"
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="2"/>'
            f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3" fill="{col}"/></svg>')


def render_html() -> str:
    L = _load_ledger()
    P = ['<h2>🌊 肥波總覽 <small>大市 → 板塊 → RS → 設置</small></h2>']
    if not L:
        return "".join(P) + '<div class="dim">DATA_UNAVAILABLE：wave_ledger.jsonl 未有資料</div>'
    last = L[-1]
    f = last.get("funnel") or {}

    # ① 大市 + 漏斗
    P.append('<div class="pf-mini2"><table><thead><tr>'
             '<th>大市</th><th class="n">MRI</th><th class="n">MMTW</th>'
             '<th class="n">候選</th><th class="n">RS ≥ 70</th>'
             '<th class="n">板塊前 5</th><th class="n">Setup 過</th>'
             '<th>結論</th></tr></thead><tbody>')
    verdict = ("可做" if (f.get("setup_ok") or 0) >= 3 else
               "觀察" if (f.get("setup_ok") or 0) >= 1 else "唔做")
    col = "#22c55e" if verdict == "可做" else ("#f97316" if verdict == "觀察" else "#94a3b8")
    P.append(f'<tr><td>{_esc(last.get("state"))}</td>'
             f'<td class="n">{last.get("mri")}</td>'
             f'<td class="n">{round(last.get("mmtw") or 0, 1)}%</td>'
             f'<td class="n">{f.get("universe")}</td>'
             f'<td class="n">{f.get("rs70")}</td>'
             f'<td class="n">{f.get("sector_top5")}</td>'
             f'<td class="n">{f.get("setup_ok")}</td>'
             f'<td style="color:{col};font-weight:800">{verdict}</td></tr>')
    P.append('</tbody></table></div>')

    # ② MRI 走勢 + 每週
    mri = [o.get("mri") for o in L[-20:]]
    P.append('<div class="card" style="margin-top:10px"><div style="padding:10px 14px">'
             f'<b style="font-size:12.5px">MRI 近 {len(mri)} 次</b>　{_spark(mri)}'
             '<span style="font-size:11px;opacity:.6;margin-left:8px">'
             '≥65 綠燈｜50–64 黃｜&lt;50 橙紅</span></div></div>')

    wk = defaultdict(list)
    for o in L:
        import datetime as _dt
        try:
            y, w, _ = _dt.date.fromisoformat(o["date"]).isocalendar()
        except Exception:                                    # noqa: BLE001
            continue
        wk[f"{y}-W{w:02d}"].append(o)
    P.append('<h3 style="margin-top:14px">每週</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr><th>週</th><th class="n">日數</th>'
             '<th class="n">平均 MRI</th><th class="n">候選合計</th>'
             '<th class="n">Setup 過合計</th><th class="n">過關率</th></tr></thead><tbody>')
    for k in sorted(wk)[-8:]:
        days = wk[k]
        mris = [d.get("mri") for d in days if isinstance(d.get("mri"), (int, float))]
        u = sum((d.get("funnel") or {}).get("universe") or 0 for d in days)
        s = sum((d.get("funnel") or {}).get("setup_ok") or 0 for d in days)
        rate = (s / u * 100) if u else 0
        P.append(f'<tr><td>{k}</td><td class="n">{len(days)}</td>'
                 f'<td class="n">{round(sum(mris)/len(mris), 1) if mris else "—"}</td>'
                 f'<td class="n">{u}</td><td class="n">{s}</td>'
                 f'<td class="n">{rate:.1f}%</td></tr>')
    P.append('</tbody></table></div>')

    # ③ 板塊
    P.append('<h3 style="margin-top:14px">板塊 RS 前 5</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr><th>#</th><th>板塊</th>'
             '<th class="n">RS</th></tr></thead><tbody>')
    for i, (g, rs) in enumerate(last.get("sectors_top") or [], 1):
        P.append(f'<tr><td class="n">{i}</td><td>{_esc(g)}</td>'
                 f'<td class="n">{round(rs, 1)}</td></tr>')
    P.append('</tbody></table></div>')

    # ④ 今日候選（confluence 排序）
    P.append('<h3 style="margin-top:14px">今日候選（RS 先、Setup 後）</h3>')
    P.append('<div class="pf-mini2"><table><thead><tr><th>代號</th><th>行業</th>'
             '<th class="n">RS%</th><th class="n">板塊RS</th><th class="n">X</th>'
             '<th class="n">EXT</th><th class="n">距52高</th><th class="n">RVOL</th>'
             '<th class="n">TIGHT</th><th class="n">評分</th>'
             '<th class="n">Confluence</th><th>狀態</th></tr></thead><tbody>')
    for r in (last.get("rows") or [])[:14]:
        ok_rs = (r.get("rs_pct") or 0) >= 70
        ok_sec = (r.get("grp_rank") or 99) <= 5
        st = "✅" if (ok_rs and ok_sec) else ("RS✓" if ok_rs else "—")
        P.append('<tr>'
                 f'<td><a class="tv" data-sym="{_esc(r["ticker"])}" '
                 f'href="https://www.tradingview.com/chart/?symbol={_esc(r["ticker"])}" '
                 f'target="_blank" rel="noopener">{_esc(r["ticker"])}</a></td>'
                 f'<td>{_esc(r.get("ind"))}</td>'
                 f'<td class="n">{r.get("rs_pct")}</td>'
                 f'<td class="n">{r.get("grp_rs") if r.get("grp_rs") is not None else "—"}</td>'
                 f'<td class="n">{r.get("x")}</td>'
                 f'<td class="n">{r.get("ext")}</td>'
                 f'<td class="n">{r.get("dist")}%</td>'
                 f'<td class="n">{r.get("rvol")}</td>'
                 f'<td class="n">{int(r.get("tight") or 0)}</td>'
                 f'<td class="n">{_esc(r.get("score"))}</td>'
                 f'<td class="n">{r.get("conf")}</td><td>{st}</td></tr>')
    P.append('</tbody></table></div>')

    # ⑤ 預測：用 GTO 分桶 EV 估算今日組合期望值
    try:
        with io.open(GTO, encoding="utf-8") as fh:
            g = json.load(fh)
    except Exception:                                        # noqa: BLE001
        g = None
    if g:
        def b_ext(v):
            v = v if isinstance(v, (int, float)) else 0
            return "<0" if v < 0 else "0–1" if v < 1 else "1–2" if v < 2 else "2–3" if v < 3 else "3–4" if v < 4 else "≥4"
        def b_dist(v):
            v = v if isinstance(v, (int, float)) else 0
            return "0～−3%" if v > -3 else "−3～−8%" if v > -8 else "−8～−15%" if v > -15 else "≤−15%"
        ev_x = (g.get("by_x") or {})
        ev_d = (g.get("by_dist") or {})
        tot, cnt = 0.0, 0
        for r in (last.get("rows") or []):
            if (r.get("rs_pct") or 0) < 70:
                continue
            xb = ("<0" if (r.get("x") or 0) < 0 else "0–0.5" if (r.get("x") or 0) < 0.5
                  else "0.5–1" if (r.get("x") or 0) < 1 else "1–2" if (r.get("x") or 0) < 2 else "≥2")
            a = (ev_x.get(xb) or {}).get("ev_r")
            b = (ev_d.get(b_dist(r.get("dist"))) or {}).get("ev_r")
            vals = [v for v in (a, b) if isinstance(v, (int, float))]
            if vals:
                tot += sum(vals) / len(vals)
                cnt += 1
        if cnt:
            P.append('<h3 style="margin-top:14px">預測（今日 RS≥70 候選）</h3>')
            P.append(f'<div class="pf-note">按歷史分桶 EV 估算：{cnt} 隻，'
                     f'平均 <b>{tot/cnt:+.2f}R</b>／單（未扣成本、未計相關性）。'
                     f'呢個係<b>假設值</b>，唔係已證實 edge；樣本 16 日。</div>')

    P.append('<div class="pf-note">漏斗邏輯：大市（MRI）→ 板塊 RS 前 5 → 個股 RS ≥ 70 百分位 → '
             '最後才睇 setup（評分/X/EXT/RVOL/TIGHT）。任何一層斷，期望值都接近 0。</div>')
    return "".join(P)
