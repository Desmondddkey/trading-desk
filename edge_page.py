# -*- coding: utf-8 -*-
"""edge_page.py — Edge Improving（針對實盤交易記錄做強弱分析）

Desmond 2026-10-20：「建立一個page做 Edge improving
呢個係要針對我既交易記錄做改善
要有優化強處 同針對弱點改善」

━━━ 數據來源 ━━━
trading-os-lab/output/fills_clean.csv（2,063 張成交單，2025-10-24 → 2026-10-09）
用 FIFO 配對成 round-trip，再逐個維度切開睇 EV。

━━━ 分析維度 ━━━
  ① 持倉時間   <30min / 30min-1日 / 1-5日 / >5日
  ② 方向 × 工具  真股多/空 · 槓桿多/空
  ③ 每日單數   1-3 / 4-9 / 10-19 / 20+
  ④ 入場時段   開市 0-30 分 / 其餘
  ⑤ 同一隻股重複次數
  ⑥ 贏輸比    平均贏 vs 平均輸

━━━ 輸出 ━━━
  強處（EV > 0，樣本 ≥ 20）→ 建議「加大」
  弱點（EV < 0，樣本 ≥ 20）→ 建議「停止」
  未定（樣本 < 20）→ 只記錄，唔准改

★ 鐵律：樣本 < 20 唔准下結論（SOUL §8.14）
"""
import csv
import io
import os
import statistics as st
import sys
from collections import deque, defaultdict

FILLS = r"C:\Users\rain0\trading-os-lab\output\fills_clean.csv"
MIN_N = 20

# ★ 反向 / 做空 ETF（買入 = 睇跌）
INVERSE = ("SOXS", "SQQQ", "SPXS", "TZA", "LABD", "FNGD", "SDOW", "TECS",
           "YANG", "KOLD", "DRIP", "WEBS", "FAZ", "ERY", "JDST", "DUST",
           "QID", "SPXU", "SDS", "SMDD", "TQQQ_INV", "UVXY", "VIXY",
           "SARK", "BZFD", "GGLS", "TSLS", "NVD", "METD", "AMZD",
           "OKLL", "RAMZ", "SETH", "BITI")

# 槓桿 / 反向 ETF 名單（2x / 3x）
LEV_PREFIX = ("SOXL", "SOXS", "TQQQ", "SQQQ", "SPXL", "SPXS", "TNA", "TZA",
              "LABU", "LABD", "FNGU", "FNGD", "UDOW", "SDOW", "TECL", "TECS",
              "YINN", "YANG", "BOIL", "KOLD", "GUSH", "DRIP", "NAIL", "DFEN",
              "WEBL", "WEBS", "FAS", "FAZ", "ERX", "ERY", "JNUG", "JDST",
              "NUGT", "DUST", "RAMZ", "OKLL", "SSO", "SDS", "QLD", "QID",
              "UPRO", "SPXU", "UVXY", "SVIX", "VIXY", "SARK", "BZFD",
              "GGLS", "TSLS", "METD", "AMZD", "SETH", "BITI")


def is_lev(sym):
    s = (sym or "").upper()
    return any(s.startswith(p) for p in LEV_PREFIX)


def is_inverse(sym):
    """★ 買入呢隻 ETF = 睇跌。所以「方向」係 BEAR 唔係 LONG。"""
    s = (sym or "").upper()
    return any(s.startswith(p) for p in INVERSE if not p.endswith("_INV"))


def load_fills():
    """讀 fills_clean.csv，回 list of {sym, side, qty, px, dt, date}。"""
    rows = []
    if not os.path.exists(FILLS):
        return rows
    with io.open(FILLS, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            # 第 2 行係中文說明列，跳過
            if (r.get("name") or "").strip() == "名稱":
                continue
            sym = (r.get("symbol") or "").strip().upper()
            side = (r.get("side") or "").strip().upper()
            if not sym or side not in ("BUY", "SELL"):
                continue
            try:
                qty = float(r.get("filled_qty") or 0)
                px = float(r.get("avg_px") or 0)
            except ValueError:
                continue
            if qty <= 0 or px <= 0:
                continue
            dt = (r.get("fill_dt") or r.get("submit_dt") or "").strip()
            date = (r.get("date") or dt[:10]).strip()
            tm = ""
            if " " in dt:
                tm = dt.split(" ")[-1][:8]
            rows.append({"sym": sym, "side": side, "qty": qty,
                         "px": px, "dt": dt, "date": date, "time": tm})
    rows.sort(key=lambda x: x["dt"] or x["date"])
    return rows


def fifo_pairs(fills):
    """FIFO 配對。回 list of round-trip dict。"""
    book = defaultdict(deque)     # sym -> deque[(qty, px, dt, side)]
    trips = []
    for f in fills:
        s = f["sym"]
        q = book[s]
        # 沖銷相反方向
        opp = "SELL" if f["side"] == "BUY" else "BUY"
        remain = f["qty"]
        while remain > 1e-9 and q and q[0][3] == opp:
            oq, op, odt, _ = q[0]
            take = min(remain, oq)
            # 判斷方向：先買後賣 = 做多
            if f["side"] == "SELL":
                entry_px, entry_dt = op, odt
                exit_px, exit_dt = f["px"], f["dt"]
                direction = "LONG"
            else:
                entry_px, entry_dt = op, odt
                exit_px, exit_dt = f["px"], f["dt"]
                direction = "SHORT"
            pnl = (exit_px - entry_px) * take * (1 if direction == "LONG" else -1)
            trips.append({
                "sym": s, "dir": direction, "qty": take,
                "entry": entry_px, "exit": exit_px,
                "entry_dt": entry_dt, "exit_dt": exit_dt,
                "entry_date": (entry_dt or "")[:10],
                "exit_date": (exit_dt or "")[:10],
                "entry_time": (entry_dt.split(" ")[-1][:8] if entry_dt and " " in entry_dt else ""),
                "pnl": pnl,
                "ret_pct": ((exit_px / entry_px - 1) * 100
                            * (1 if direction == "LONG" else -1)),
                "lev": is_lev(s),
                "inv": is_inverse(s),
                "bias": ("BEAR" if is_inverse(s) else "BULL"),
            })
            remain -= take
            if take >= oq - 1e-9:
                q.popleft()
            else:
                q[0] = (oq - take, op, odt, opp)
        if remain > 1e-9:
            q.append((remain, f["px"], f["dt"], f["side"]))
    return trips


def hold_minutes(t):
    """持倉分鐘數。解析唔到 → None。"""
    import datetime as _dt
    a, b = t.get("entry_dt"), t.get("exit_dt")
    if not a or not b:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            da = _dt.datetime.strptime(a[:19], fmt)
            db = _dt.datetime.strptime(b[:19], fmt)
            return (db - da).total_seconds() / 60.0
        except Exception:                                    # noqa: BLE001
            continue
    return None


def bucket_hold(m):
    if m is None:
        return "未知"
    if m < 30:
        return "① <30 分鐘"
    if m < 1440:
        return "② 30分–1日"
    if m <= 7200:
        return "③ 1–5 日"
    return "④ >5 日"


def seg_stats(trips):
    """一組 round-trip 嘅統計。"""
    if not trips:
        return None
    pnls = [t["pnl"] for t in trips]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    n = len(pnls)
    return {
        "n": n,
        "total": sum(pnls),
        "ev": sum(pnls) / n,
        "win_rate": len(wins) / n,
        "avg_win": st.mean(wins) if wins else 0.0,
        "avg_loss": st.mean(losses) if losses else 0.0,
        "payoff": (st.mean(wins) / abs(st.mean(losses))
                   if wins and losses else 0.0),
        "proven": n >= MIN_N,
    }


def build():
    fills = load_fills()
    if not fills:
        return ("Edge", '<div class="warn">⛔ 搵唔到成交記錄</div>')
    trips = fifo_pairs(fills)
    for t in trips:
        t["hold"] = hold_minutes(t)
        t["hold_b"] = bucket_hold(t["hold"])

    S = seg_stats(trips)
    L = ["""<style>
.eh-k{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 14px}
.eh-k>div{flex:1 1 108px;padding:11px 13px;border-radius:11px;
  border:1px solid rgba(128,128,128,.26);background:rgba(128,128,128,.05)}
.eh-k .n{font-size:20px;font-weight:800;line-height:1.15}
.eh-k .l{font-size:10.5px;opacity:.6;margin-top:2px}
.eh-t{width:100%;border-collapse:collapse;font-size:12px;margin:0 0 4px}
.eh-t th{text-align:left;font-size:10.5px;letter-spacing:.05em;
  text-transform:uppercase;opacity:.55;padding:6px 8px;font-weight:700;
  border-bottom:1px solid rgba(128,128,128,.28)}
.eh-t td{padding:6px 8px;border-bottom:1px solid rgba(128,128,128,.1);
  text-align:left!important}
.eh-t tr.good td:first-child{border-left:3px solid #16a34a;padding-left:9px}
.eh-t tr.bad td:first-child{border-left:3px solid #dc2626;padding-left:9px}
.eh-t tr.mid td:first-child{border-left:3px solid #94a3b8;padding-left:9px}
.pos{color:#16a34a;font-weight:700}.neg{color:#dc2626;font-weight:700}
.eh-hero{border-radius:13px;padding:15px 17px;margin:0 0 15px;
  font-size:13px;line-height:1.9;font-weight:600}
.eh-s{border:1px solid rgba(22,163,74,.45);background:rgba(22,163,74,.08)}
.eh-w{border:1px solid rgba(220,38,38,.5);background:rgba(220,38,38,.08)}
@media(max-width:700px){
  .eh-t thead{display:none}
  .eh-t,.eh-t tbody,.eh-t tr{display:block;width:100%}
  .eh-t tr{padding:8px 0;border-bottom:1px solid rgba(128,128,128,.16)}
  .eh-t td{display:inline;border:0;padding:1px 5px 1px 0;font-size:11.5px}
  .eh-t td:first-child{display:block;font-weight:800;font-size:13px}
}
</style>"""]

    L.append("<h2>Edge Improving <small>針對實盤交易記錄</small></h2>")
    L.append(f'<p class="crumb">{len(fills)} 張成交單 → '
             f'{len(trips)} 個 round-trip｜'
             f'{trips[0]["entry_date"] if trips else "—"} → '
             f'{trips[-1]["exit_date"] if trips else "—"}</p>')

    # ── 總覽 ──
    L.append('<div class="eh-k">')
    for v, lab, col in (
            (f"${S['total']:,.0f}", "總盈虧",
             "#16a34a" if S["total"] > 0 else "#dc2626"),
            (f"{S['win_rate']*100:.1f}%", "勝率", ""),
            (f"{S['payoff']:.2f}:1", "贏輸比",
             "#16a34a" if S["payoff"] >= 3 else "#dc2626"),
            (f"${S['ev']:,.0f}", "每單期望",
             "#16a34a" if S["ev"] > 0 else "#dc2626"),
            (str(S["n"]), "交易數", "")):
        c = f' style="color:{col}"' if col else ""
        L.append(f'<div><div class="n"{c}>{v}</div>'
                 f'<div class="l">{lab}</div></div>')
    L.append("</div>")

    # ── 六大維度 ──
    dims = [
        ("① 持倉時間", lambda t: t["hold_b"],
         "持倉越短 = 越似手勢；越長 = 越似持倉。"),
        ("② 方向 × 工具",
         lambda t: ("槓桿" if t["lev"] else "真股")
         + ("・睇跌" if t["bias"] == "BEAR" else "・睇升"),
         "反向 ETF 買入 = 睇跌。呢個係你近期主要收入來源。"),
        ("③ 每日單數", None,
         "單數越多 = 越可能報復交易 / 亂做。"),
        ("④ 入場時段", None, "開市頭 30 分鐘雜訊最多。"),
        ("⑤ 同一隻股次數", None, "同一隻做太多次 = 冇新資訊。"),
        ("⑥ 睇升 vs 睇跌", lambda t: "看漲" if t["bias"] == "BULL" else "看跌",
         "兩種係唔同技能，勝率同賠率都唔應該混埋計。"),
    ]

    # 預先算每日單數 / 每股票次數 / 時段
    per_day = defaultdict(int)
    for t in trips:
        per_day[t["entry_date"]] += 1
    for t in trips:
        d = per_day[t["entry_date"]]
        t["day_b"] = ("1–3 單" if d <= 3 else "4–9 單"
                      if d <= 9 else "10–19 單" if d <= 19 else "20+ 單")
    # 每隻股累計次數（按時間順序）
    seen = defaultdict(int)
    for t in sorted(trips, key=lambda x: x["entry_dt"] or ""):
        seen[t["sym"]] += 1
        n = seen[t["sym"]]
        t["sym_b"] = ("第 1 次" if n == 1 else "第 2–3 次"
                      if n <= 3 else "第 4+ 次")
    for t in trips:
        hh = (t.get("entry_time") or "")[:5]
        try:
            mins = int(hh[:2]) * 60 + int(hh[3:5])
        except Exception:                                    # noqa: BLE001
            t["time_b"] = "未知"
            continue
        t["time_b"] = "開市 0–30 分" if mins <= 570 else "其餘時間"

    getters = {
        "③ 每日單數": lambda t: t["day_b"],
        "④ 入場時段": lambda t: t["time_b"],
        "⑤ 同一隻股次數": lambda t: t["sym_b"],
    }

    strengths, weaknesses = [], []
    for title, getter, note in dims:
        g = getter or getters[title]
        groups = defaultdict(list)
        for t in trips:
            groups[g(t)].append(t)
        rows = []
        for k, v in groups.items():
            s = seg_stats(v)
            if s:
                rows.append((k, s))
        rows.sort(key=lambda kv: -kv[1]["ev"])
        if not rows:
            continue
        L.append(f'<div class="card"><h2>{title} '
                 f'<small>{note}</small></h2><div class="body">'
                 '<table class="eh-t"><thead><tr><th>分組</th><th>n</th>'
                 '<th>總盈虧</th><th>每單</th><th>勝率</th><th>贏輸比</th>'
                 '<th>判定</th></tr></thead><tbody>')
        for k, s in rows:
            if not s["proven"]:
                cls, verdict = "mid", "⚪ 樣本不足"
            elif s["ev"] > 0:
                cls, verdict = "good", "✅ 強處"
                strengths.append((title, k, s))
            else:
                cls, verdict = "bad", "❌ 弱點"
                weaknesses.append((title, k, s))
            pc = "pos" if s["total"] > 0 else "neg"
            L.append(
                f'<tr class="{cls}"><td><b>{k}</b></td><td>{s["n"]}</td>'
                f'<td class="{pc}">${s["total"]:,.0f}</td>'
                f'<td class="{pc}">${s["ev"]:,.0f}</td>'
                f'<td>{s["win_rate"]*100:.0f}%</td>'
                f'<td>{s["payoff"]:.2f}:1</td>'
                f'<td>{verdict}</td></tr>')
        L.append('</tbody></table></div></div>')

    # ── 強處摘要 ──
    strengths.sort(key=lambda x: -x[2]["ev"])
    weaknesses.sort(key=lambda x: x[2]["ev"])
    if strengths:
        top = strengths[0]
        L.append(f'<div class="eh-hero eh-s">💪 <b>最強嘅一項</b>：'
                 f'{top[0]} → <b>{top[1]}</b><br>'
                 f'n={top[2]["n"]}｜每單 <b>${top[2]["ev"]:,.0f}</b>｜'
                 f'勝率 {top[2]["win_rate"]*100:.0f}%｜'
                 f'贏輸比 {top[2]["payoff"]:.2f}:1<br>'
                 f'<b>行動：加大比重。</b>呢個係你嘅 edge，唔應該同其他嘢平分倉位。'
                 '</div>')
    if weaknesses:
        bot = weaknesses[0]
        L.append(f'<div class="eh-hero eh-w">🩸 <b>最傷嘅一項</b>：'
                 f'{bot[0]} → <b>{bot[1]}</b><br>'
                 f'n={bot[2]["n"]}｜每單 <b>${bot[2]["ev"]:,.0f}</b>｜'
                 f'勝率 {bot[2]["win_rate"]*100:.0f}%｜'
                 f'總共蝕 <b>${bot[2]["total"]:,.0f}</b><br>'
                 f'<b>行動：直接停止。</b>呢個分組冇 edge，做幾多次都係蝕。'
                 '</div>')

    # ── 每日 / 每週 改善清單 ──
    bear = [t for t in trips if t["bias"] == "BEAR"]
    bull = [t for t in trips if t["bias"] == "BULL"]
    s_bear = seg_stats(bear) if bear else None
    s_bull = seg_stats(bull) if bull else None

    # 每日單數分組統計（搵「做太多」嘅代價）
    dayg = defaultdict(list)
    for t in trips:
        dayg[t["day_b"]].append(t)
    day_stats = {k: seg_stats(v) for k, v in dayg.items() if len(v) >= MIN_N}

    # 持倉時間分組
    holdg = defaultdict(list)
    for t in trips:
        holdg[t["hold_b"]].append(t)
    hold_stats = {k: seg_stats(v) for k, v in holdg.items() if len(v) >= MIN_N}

    L.append('<div class="card"><h2>每日 / 每週 改善 '
             '<small>做完即刻可以改嘅行為</small></h2><div class="body">')

    # 每日三條
    L.append('<div style="font-size:13px;font-weight:800;margin:0 0 8px;'
             'color:#c2410c">📅 每日（收市後 5 分鐘檢視）</div>')
    daily = []
    if s_bull and s_bull["ev"] < 0 and s_bull["proven"]:
        daily.append(
            f'<b>① 今日有冇做「看漲」單？</b>　呢類單平均每單 '
            f'<span class="neg">${s_bull["ev"]:,.0f}</span>'
            f'（n={s_bull["n"]}，勝率 {s_bull["win_rate"]*100:.0f}%）。'
            f'如果大盤 GMI ≤ 2，<b>今日唔應該做任何看漲單</b>。')
    if "20+ 單" in day_stats and day_stats["20+ 單"]["ev"] < 0:
        d = day_stats["20+ 單"]
        daily.append(
            f'<b>② 今日做咗幾多單？</b>　超過 20 單嘅日子平均每單 '
            f'<span class="neg">${d["ev"]:,.0f}</span>'
            f'（n={d["n"]}）。<b>目標：每日 ≤ 3 單</b>，只做最好嘅。')
    if "① <30 分鐘" in hold_stats and hold_stats["① <30 分鐘"]["ev"] < 0:
        h = hold_stats["① <30 分鐘"]
        daily.append(
            f'<b>③ 有冇單喺 30 分鐘內平倉？</b>　呢類單平均每單 '
            f'<span class="neg">${h["ev"]:,.0f}</span>'
            f'（n={h["n"]}）。<b>入場前寫低出場條件，唔好中途改。</b>')
    if not daily:
        daily.append('（樣本未夠，暫時唔出建議）')
    L.append('<div style="font-size:12.5px;line-height:2">'
             + "<br><br>".join(daily) + '</div>')

    # 每週三條
    L.append('<div style="font-size:13px;font-weight:800;margin:18px 0 8px;'
             'color:#c2410c">📆 每週（週末 15 分鐘檢視）</div>')
    weekly = []
    if s_bear and s_bull:
        diff = s_bear["ev"] - s_bull["ev"]
        weekly.append(
            f'<b>① 比較兩個方向</b>　看跌每單 '
            f'<span class="pos">${s_bear["ev"]:,.0f}</span>｜'
            f'看漲每單 <span class="neg">${s_bull["ev"]:,.0f}</span>'
            f'　差距 <b>${diff:,.0f}</b>。<br>'
            f'→ 本週如果做咗看漲單，計一計損失咗幾多。')
    # 最大單一股票損失
    bysym = defaultdict(list)
    for t in trips:
        bysym[t["sym"]].append(t)
    worst = sorted(((k, seg_stats(v)) for k, v in bysym.items()
                    if len(v) >= 5), key=lambda kv: kv[1]["total"])[:3]
    if worst:
        txt = "｜".join(f'{k} ${v["total"]:,.0f}（{v["n"]} 單）'
                        for k, v in worst)
        weekly.append(
            f'<b>② 邊隻股食咗你最多錢</b>　{txt}<br>'
            f'→ 呢幾隻列入下週黑名單，唔准再做。')
    # 贏輸比
    weekly.append(
        f'<b>③ 贏輸比</b>　現時 <b>{S["payoff"]:.2f}:1</b>'
        f'（目標 3.0:1）。<br>'
        f'→ 平均贏 ${S["avg_win"]:,.0f}｜平均輸 ${abs(S["avg_loss"]):,.0f}。'
        f'要提升贏輸比，<b>唔係贏多啲，係輸少啲</b>：'
        f'止蝕再收窄，贏單再拖長。')
    L.append('<div style="font-size:12.5px;line-height:2">'
             + "<br><br>".join(weekly) + '</div>')
    L.append('</div></div>')

    # ── 誠實聲明 ──
    L.append('<div class="note" style="margin-top:14px;font-size:11.5px;'
             'line-height:1.85">'
             f'<b>數據</b>：{len(fills)} 張成交單，FIFO 配對成 {len(trips)} 個 '
             'round-trip。配對規則：先買後賣 = 做多，先賣後買 = 做空。<br>'
             f'<b>樣本門檻</b>：少於 {MIN_N} 個 round-trip 標「樣本不足」，'
             '唔會叫你改。<br>'
             '<b>限制</b>：未計手續費、佣金、滑價。'
             '真實盈虧會比呢度顯示嘅差少少。'
             '</div>')
    return ("Edge Improving", "".join(L))


if __name__ == "__main__":
    t, b = build()
    print(t, len(b) // 1024, "KB")
