# -*- coding: utf-8 -*-
"""rs_before_price.py — RS 先創新高，價未跟上

來源：1ChartMaster（Elite Swing Traders）2026-10-20
  「當一隻股票嘅週線上 RS 先創出新高，而股價未跟上之前，
    你應該對呢隻股票格外留神。呢個代表機構性累積喺表面下進行緊。」

━━━ 第一性原理 ━━━
RS = 收市價 ÷ SPY 收市價
  · RS 上升 = 股票跑贏大市 = 有資金流入
  · RS 創新高 但 價格未破頂 = 買盤累積，未反映喺絕對價

━━━ ★ 判準（2026-10-20 實測修正）━━━
初版用「RS 距 52 週高 ≤2%」→ 命中 0 隻。根因：
  RS 嘅 52 週最高點幾乎必然同價格最高點同時出現（數學上必然）
  → 要求「RS 52 週新高 + 價唔係新高」= 邏輯矛盾

正確判準（實測 4 隻命中，符合 Tweet 原意）：
  ① RS 創 20 日新高（rs_now >= max(rs[-20:]) × 0.999）
  ② 價格距 52 週高 2%–25%（近高位但未破頂）
     · 距高 >25% = 跌殘股反彈，唔係「高位吸納」
     · 距高 <2% = 已破頂，唔算「價未跟上」

━━━ 分級（按價距高）━━━
  🔥 A：價距 52 週高 ≥10%
  🟠 B：價距高 ≥5%
  🟡 C：價距高 2%–5%

━━━ 額外確認 ━━━
  量比 = 近 10 日均量 ÷ 近 50 日均量（≥1.2 = 有資金）
  ADR  = 近 20 日平均日波幅 %
  RS 新高距今 / 52 週高距今 = 幾多個交易日
"""
import pickle

PKL = r"C:\Users\rain0\trading-os-web\data\charts_ohlc.pkl"
BENCH = "SPY"
RS_N = 20          # RS 新高視窗
PX_MIN = -25.0     # 價距 52 週高最少 -25%
PX_MAX = -2.0      # 價距 52 週高最多 -2%

CSS = """
.rp-k{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 14px}
.rp-k>div{flex:1 1 105px;padding:11px 13px;border-radius:10px;
  border:1px solid rgba(128,128,128,.26);background:rgba(128,128,128,.05)}
.rp-k .n{font-size:20px;font-weight:800;line-height:1.15}
.rp-k .l{font-size:10.5px;opacity:.6;margin-top:2px}
.rp-lvl{display:inline-block;padding:1px 7px;border-radius:999px;
  font-size:10px;font-weight:800}
.lv-a{background:#fef3c7;color:#92400e;border:1px solid #f59e0b}
.lv-b{background:#fed7aa;color:#9a3412;border:1px solid #fb923c}
.lv-c{background:#e2e8f0;color:#475569;border:1px solid #94a3b8}
.rp-t td,.rp-t th{font-size:11.5px;padding:5px 6px;white-space:nowrap}
.rp-t .pos{color:#16a34a;font-weight:700}
.rp-t .big{color:#b45309;font-weight:800}
.rp-warn{border-left:3px solid #f59e0b;background:rgba(245,158,11,.09);
  padding:10px 13px;border-radius:8px;margin:0 0 12px;font-size:11.5px;
  line-height:1.85}
.rp-step{border:1px solid rgba(128,128,128,.24);border-radius:10px;
  padding:11px 14px;margin:0 0 9px;font-size:12.5px;line-height:1.9}
.rp-step b{color:#c2410c}
@media(max-width:700px){
  .rp-t thead{display:none}
  .rp-t tr{display:block;border:1px solid rgba(128,128,128,.25);
    border-radius:10px;margin-bottom:8px;padding:8px 10px}
  .rp-t td{display:flex;justify-content:space-between;border:0;
    padding:2px 0;white-space:normal}
  .rp-t td::before{content:attr(data-l);opacity:.55;font-weight:600}
}
"""


def load():
    try:
        with open(PKL, "rb") as f:
            return pickle.load(f)
    except Exception:                                        # noqa: BLE001
        return None


def _close(df, t):
    """兼容兩種 yfinance 欄位次序：('SPY','Close') 同 ('Close','SPY')。"""
    for key in ((t, "Close"), ("Close", t)):
        if key in df.columns:
            return df[key]
    raise KeyError(t)


def compute(df):
    import numpy as np
    bench = _close(df, BENCH).astype(float)
    out = []
    for t in sorted({c[0] for c in df.columns}):
        if t == BENCH:
            continue
        try:
            px = _close(df, t).astype(float).dropna().reindex(bench.index).dropna()
            if len(px) < 120:
                continue
            rs = (px / bench.reindex(px.index)).dropna()
            if len(rs) < RS_N + 5:
                continue

            rs_now = float(rs.iloc[-1])
            rs_max20 = float(rs.iloc[-RS_N:].max())
            if rs_now < rs_max20 * 0.999:        # RS 未創 20 日新高
                continue

            px_now = float(px.iloc[-1])
            px_hi = float(px.iloc[-252:].max())
            if not px_hi:
                continue
            px_off = (px_now / px_hi - 1) * 100
            if not (PX_MIN <= px_off <= PX_MAX):
                continue

            arr = rs.iloc[-RS_N:].values
            d_rs = RS_N - 1 - int(np.argmax(arr))
            parr = px.iloc[-252:].values
            d_px = min(252, len(px)) - 1 - int(np.argmax(parr))

            vol = df[(t, "Volume")].astype(float).reindex(px.index).dropna()
            v10 = float(vol.iloc[-10:].mean()) if len(vol) >= 10 else 0
            v50 = float(vol.iloc[-50:].mean()) if len(vol) >= 50 else 0
            vr = (v10 / v50) if v50 else 0.0

            hi20 = df[(t, "High")].astype(float).reindex(px.index).dropna().iloc[-20:]
            lo20 = df[(t, "Low")].astype(float).reindex(px.index).dropna().iloc[-20:]
            c20 = px.iloc[-20:]
            m = min(len(hi20), len(lo20), len(c20))
            adr = (float(((hi20.iloc[-m:] - lo20.iloc[-m:]) / c20.iloc[-m:]).mean() * 100)
                   if m >= 5 else 0.0)

            if px_off <= -10:
                lvl = "A"
            elif px_off <= -5:
                lvl = "B"
            else:
                lvl = "C"

            out.append({
                "t": t, "px": px_now, "px_off": px_off, "lead": -px_off,
                "d_rs": d_rs, "d_px": d_px, "vr": vr, "adr": adr,
                "lvl": lvl, "px_hi": px_hi,
            })
        except Exception:                                    # noqa: BLE001
            continue
    out.sort(key=lambda x: -x["lead"])
    return out


def build():
    df = load()
    if df is None:
        return ("RS Before Price",
                '<div class="warn">⛔ 讀唔到 charts_ohlc.pkl</div>')
    rows = compute(df)
    last = df.index[-1]
    n_all = len({c[0] for c in df.columns})

    L = [f"<style>{CSS}</style>",
         "<h2>RS Before Price <small>RS 先創新高，價未跟上</small></h2>",
         f'<p class="crumb">數據日 {last.date()}｜基準 {BENCH}｜'
         f'掃 {n_all} 隻｜命中 <b>{len(rows)}</b> 隻</p>']

    L.append('<div class="rp-warn">'
             '<b>呢個訊號講咩</b>　RS（股票 ÷ SPY）創 20 日新高 = '
             '呢隻股跑贏大市；但價格仲距 52 週高 2–25% = 未破頂。<br>'
             '<b>機構解讀</b>　大戶喺大眾未留意之前靜悄悄吸納 —— '
             '表面價格橫行，相對強度已經先跑。<br>'
             '<b>⚠ 唔係買入訊號</b>　呢個係「加入觀察名單」嘅理由，'
             '唔係「現在買」嘅理由。要等價格真突破 + 量確認。</div>')

    a = [r for r in rows if r["lvl"] == "A"]
    b = [r for r in rows if r["lvl"] == "B"]
    c = [r for r in rows if r["lvl"] == "C"]
    L.append('<div class="rp-k">')
    for v, lab, col in ((len(rows), "命中總數", ""),
                        (len(a), "🔥 A 級 ≥10%", "#b45309"),
                        (len(b), "🟠 B 級 ≥5%", "#c2410c"),
                        (len(c), "🟡 C 級 2–5%", "#64748b")):
        cc = f' style="color:{col}"' if col else ""
        L.append(f'<div><div class="n"{cc}>{v}</div>'
                 f'<div class="l">{lab}</div></div>')
    L.append('</div>')

    if not rows:
        L.append('<div class="card"><div class="body" '
                 'style="font-size:12.5px;line-height:1.9">'
                 '⚪ <b>今日冇任何股票符合條件。</b><br>'
                 '呢個訊號本身罕見 —— 要求 RS 創 20 日新高 '
                 '<b>同時</b>價格距 52 週高 2–25%。<br>'
                 '大市急跌時通常冇；大市橫行或溫和上升時最多。</div></div>')
        return ("RS Before Price", "".join(L))

    L.append('<div class="card"><h2>命中名單 '
             '<small>按「價落後」排序</small></h2>'
             '<div class="body"><div style="overflow-x:auto">'
             '<table class="rp-t"><thead><tr>'
             '<th>#</th><th>股票</th><th>級</th><th>現價</th>'
             '<th>52週高</th><th>價距高</th>'
             '<th>RS 新高距今</th><th>52週高距今</th>'
             '<th>量比</th><th>ADR</th></tr></thead><tbody>')
    for i, r in enumerate(rows, 1):
        lv = {"A": "lv-a", "B": "lv-b", "C": "lv-c"}[r["lvl"]]
        L.append(
            f'<tr><td data-l="#">{i}</td>'
            f'<td data-l="股票"><b>{r["t"]}</b></td>'
            f'<td data-l="級"><span class="rp-lvl {lv}">{r["lvl"]}</span></td>'
            f'<td data-l="現價">${r["px"]:,.2f}</td>'
            f'<td data-l="52週高">${r["px_hi"]:,.2f}</td>'
            f'<td data-l="價距高" class="big">{r["px_off"]:+.1f}%</td>'
            f'<td data-l="RS新高距今" class="pos">{r["d_rs"]} 日</td>'
            f'<td data-l="52週高距今">{r["d_px"]} 日</td>'
            f'<td data-l="量比">{r["vr"]:.2f}</td>'
            f'<td data-l="ADR">{r["adr"]:.1f}%</td></tr>')
    L.append('</tbody></table></div></div></div>')

    L.append('<div class="card"><h2>點用呢個表</h2><div class="body">')
    for b1, b2 in (
        ("① 「價距高」越大 = 落後越多",
         "RS 已經新高，但價格仲差 10-25% → 相對強度已破頂，"
         "絕對價有空間追上。呢個就係 Tweet 講嘅「格外留神」。"),
        ("② 「52 週高距今」越遠越好",
         "價格距上次高位 60-120 日 = 長期橫行整理，RS 慢慢爬升。"
         "如果只係 5 日前高位，只係正常回調。"),
        ("③ 「量比」≥1.2 = 有資金流入",
         "近 10 日均量 ÷ 近 50 日均量。量比低但 RS 高 = "
         "可能只係跟大市，唔係真吸納。"),
        ("④ 入場時機：等價格真突破",
         "呢頁淨係話你「留意」，唔係「買」。真入場 = "
         "價格破 52 週高 + 量放大 ≥1.5x + 大市唔逆風。"),
        ("⑤ 止蝕用 LOD，唔用固定 %",
         "Jeff Sun 原則：止蝕 = 當日低位，距離 ≤0.60 ATR。"
         "呢個 setup 尤其重要 —— 你買嘅係「未破頂」嘅股，"
         "破頂失敗要走得快。"),
    ):
        L.append(f'<div class="rp-step"><b>{b1}</b><br>{b2}</div>')
    L.append('</div></div>')

    L.append('<div class="note" style="margin-top:14px;font-size:11.5px;'
             f'line-height:1.85"><b>RS 定義</b>　收市價 ÷ {BENCH} 收市價'
             '（自算相對強度線，唔係 IBD 官方 RS Rating）。<br>'
             f'<b>判準</b>　RS 創 {RS_N} 日新高 且 價距 52 週高 '
             f'{PX_MIN:.0f}% ~ {PX_MAX:.0f}%。<br>'
             f'<b>掃描範圍</b>　圖表快取 {n_all} 隻（你嘅掃描名單），'
             '唔係全美股。<br>'
             '<b>★ 未回測</b>　呢個訊號嘅 forward return 未量化。'
             '樣本夠我會用 forward_label.py 量 t3/t10 R。</div>')
    return ("RS Before Price", "".join(L))


if __name__ == "__main__":
    t, b = build()
    print(t, len(b) // 1024, "KB")
