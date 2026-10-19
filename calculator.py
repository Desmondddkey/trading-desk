# -*- coding: utf-8 -*-
"""calculator.py — 倉位計算機（Position Sizing Tool）

Desmond 2026-10-19：參考 lonestocktrader position-sizing，但要跟
【我哋自己嘅常數】（SOUL §4），唔盲目抄人。

═══════════════════════════════════════════════════════════════════
數學（透明，全部寫死）
═══════════════════════════════════════════════════════════════════
1R（風險額）    = 淨值 × 風險%
每股風險        = |入場價 − 止蝕價|
股數            = floor(1R / 每股風險)
倉位金額        = 股數 × 入場價
倉位 % 淨值     = 倉位金額 / 淨值

★ 3 Stops（Jeff Sun）：把倉位分 3 注，每注獨立止蝕
   · Stop 1 = 用戶輸入（最遠）
   · Stop 2、Stop 3 逐級收緊
   · 如果 3 注全部止蝕 → 總損失 ≈ 0.67R（Jeff Sun 原文目標）
   · 反推：股數 = (0.67 × 1R) / 平均每股風險

═══════════════════════════════════════════════════════════════════
硬規則（同 SOUL §4 / discipline_gate 一致）
═══════════════════════════════════════════════════════════════════
· 單筆風險 0.5% 淨值（預設）
· 止蝕距離 ≤ 3%（超過 = 紅字警告）
· 單一倉位 ≤ 33% 淨值（超過 = 紅字警告）
· 目標 3:1

═══════════════════════════════════════════════════════════════════
實測 EV 提示（1,336 單 FIFO 配對）
═══════════════════════════════════════════════════════════════════
· 持倉 ≥1 日：EV +2.795%/單（t=2.76，顯著）
· 持倉 <1 日：EV +0.271%/單（t=1.16，唔顯著）
· 真股短倉：  EV −0.48%/單（最大虧損源）
· 槓桿長倉：  EV +7.78%/單（但只 35 單，樣本細）
"""

RISK_DEFAULT = 0.5        # % 淨值（SOUL §4）
STOP_MAX_PCT = 3.0        # 止蝕上限 %
POS_MAX_PCT = 33.0        # 單一倉位上限 %
RR_TARGET = 3.0           # 目標賺輸比
JEFF_TOTAL_R = 0.67       # 3 注全部止蝕 = 0.67R

EV_HOLD_1D = 2.795        # % 每單（≥1 日，顯著）
EV_HOLD_INTRADAY = 0.271  # % 每單（<1 日，唔顯著）
EV_TRUESTOCK_SHORT = -0.48
EV_LEV_LONG = 7.78


def calc(capital, entry, stop, risk_pct=RISK_DEFAULT, mode="1", side="BUY"):
    """回傳完整計算結果 dict。

    mode="1" → 單一止蝕
    mode="3" → Jeff Sun 3 注階梯
    """
    out = dict(ok=False, errors=[], warns=[],
               capital=capital, entry=entry, stop=stop,
               risk_pct=risk_pct, mode=mode, side=side)

    if not (capital > 0):
        out["errors"].append("淨值必須 > 0")
        return out
    if not (entry > 0):
        out["errors"].append("入場價必須 > 0")
        return out
    if not (stop > 0):
        out["errors"].append("止蝕價必須 > 0")
        return out

    r1 = capital * risk_pct / 100.0

    # 方向檢查
    if side == "BUY" and stop >= entry:
        out["errors"].append("BUY：止蝕必須低於入場價")
        return out
    if side == "SELL" and stop <= entry:
        out["errors"].append("SELL：止蝕必須高於入場價")
        return out

    sign = 1 if side == "BUY" else -1
    per_share = abs(entry - stop)
    stop_pct = per_share / entry * 100

    # ── 3 Stops：階梯止蝕
    if mode == "3":
        # 由 entry 到 stop（最遠）之間，分 3 級
        # Stop 3 = 最緊（最接近 entry），Stop 1 = 最遠
        step = per_share / 3.0
        stops = [entry - sign * per_share,          # Stop 1（最遠）
                 entry - sign * per_share * 2 / 3,  # Stop 2
                 entry - sign * per_share * 1 / 3]  # Stop 3（最緊）
        avg_stop = sum(stops) / 3.0
        avg_per_share = abs(entry - avg_stop)
        # 目標：3 注全中 = 0.67R
        target_total = JEFF_TOTAL_R * r1
        shares_total = int(target_total / avg_per_share) if avg_per_share > 0 else 0
        per_tranche = shares_total // 3
        shares_total = per_tranche * 3
        tranche_shares = [per_tranche] * 3
        risk_if_all = shares_total * avg_per_share
        out["stops"] = stops
        out["avg_stop"] = avg_stop
        out["tranche_shares"] = tranche_shares
        out["risk_if_all"] = risk_if_all
        out["risk_if_all_pct"] = risk_if_all / capital * 100
        out["risk_if_all_r"] = risk_if_all / r1 if r1 else 0
    else:
        shares_total = int(r1 / per_share) if per_share > 0 else 0
        risk_if_all = shares_total * per_share
        out["stops"] = [stop]
        out["avg_stop"] = stop
        out["tranche_shares"] = [shares_total]
        out["risk_if_all"] = risk_if_all
        out["risk_if_all_pct"] = risk_if_all / capital * 100
        out["risk_if_all_r"] = risk_if_all / r1 if r1 else 0

    notional = shares_total * entry
    pos_pct = notional / capital * 100

    out.update(
        ok=True,
        r1=r1,
        per_share=per_share,
        stop_pct=stop_pct,
        shares=shares_total,
        notional=notional,
        pos_pct=pos_pct,
        # 目標價
        t1=entry + sign * per_share * 1,
        t2=entry + sign * per_share * 2,
        t3=entry + sign * per_share * 3,
        t4=entry + sign * per_share * 4,
        # 2R 減 33%（SOUL §4 分批）
        trim_2r_shares=int(shares_total * 0.33),
    )

    # ── 警告
    if stop_pct > STOP_MAX_PCT:
        out["warns"].append(
            f"⛔ 止蝕距離 {stop_pct:.2f}% > {STOP_MAX_PCT}% 上限 → 收緊止蝕")
    if pos_pct > POS_MAX_PCT:
        out["warns"].append(
            f"⛔ 倉位 {pos_pct:.1f}% > {POS_MAX_PCT}% 上限 → 減股數")
    elif pos_pct > POS_MAX_PCT * 0.8:
        out["warns"].append(f"🟡 倉位 {pos_pct:.1f}% 接近 {POS_MAX_PCT}% 上限")
    if risk_pct > 1.0:
        out["warns"].append(f"🟡 風險 {risk_pct}% > 1% 上限（SOUL §4）")
    if shares_total == 0:
        out["warns"].append("⛔ 股數 0 —— 止蝕太遠，1R 買唔到 1 股")
    return out


def calc_page():
    """回傳 calculator.html 嘅 body HTML（圖表 + 輸入 + 即時計算）。"""
    import html as _h

    def opt(v, label, sel=False):
        return (f'<option value="{v}"{" selected" if sel else ""}>'
                f'{_h.escape(label)}</option>')

    # ★ 2026-10-19 Desmond：「唔好用列表揀 RISK，用方格比我揀」
    RISKS = [("0.25", "0.25%", ""), ("0.35", "0.35%", ""),
             ("0.5", "0.50%", "SOUL 預設"),
             ("0.75", "0.75%", ""), ("1.0", "1.00%", "上限"),
             ("2.0", "2.00%", "超上限")]
    risk_opts = "".join(
        f'<button data-v="{v}"{" class=\"on\"" if v == "0.5" else ""}>'
        f'<span class="rv">{lbl}</span>'
        + (f'<span class="rn">{note}</span>' if note else '')
        + '</button>'
        for v, lbl, note in RISKS)

    return f"""
<style>
/* ★ 主題無關：唔用 CSS 變數（網站冇定義），面板透明 + 邊框，
   文字繼承 body 色 → 淺色／深色主題都讀得到 */
.calcbox{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:18px 0}}
@media(max-width:800px){{.calcbox{{grid-template-columns:1fr}}}}
.calc-panel{{background:rgba(128,128,128,.06);border:1px solid rgba(128,128,128,.32);
  border-radius:14px;padding:18px}}
.calc-panel h3{{margin:0 0 14px;font-size:15px;letter-spacing:.06em;
  text-transform:uppercase;opacity:.75}}
.frow{{margin-bottom:14px}}
.frow label{{display:block;font-size:12px;letter-spacing:.05em;
  text-transform:uppercase;opacity:.7;margin-bottom:6px}}
.frow input,.frow select{{width:100%;background:rgba(128,128,128,.10);
  border:1px solid rgba(128,128,128,.38);border-radius:9px;padding:11px 12px;
  color:inherit;font-size:15px;font-family:inherit}}
.frow input:focus,.frow select:focus{{outline:none;border-color:#4c8dff}}
.seg-risk{display:grid!important;grid-template-columns:repeat(3,1fr);gap:8px}
.seg-risk button{flex-direction:column;gap:2px;padding:11px 6px;
  line-height:1.25}
.seg-risk .rv{font-size:14.5px;font-weight:800}
.seg-risk .rn{font-size:9.5px;opacity:.62;font-weight:600;letter-spacing:.02em}
.seg-risk button.on .rn{opacity:.85}
@media(min-width:560px){.seg-risk{grid-template-columns:repeat(6,1fr)}}
.seg{{display:flex;gap:8px}}
.seg button{{flex:1;background:rgba(128,128,128,.10);
  border:1px solid rgba(128,128,128,.38);
  border-radius:9px;padding:11px;color:inherit;font-size:14px;
  cursor:pointer;font-family:inherit}}
.seg button.on{{background:#2fbf71;border-color:#2fbf71;color:#04140b;font-weight:700}}
.seg button.on.sell{{background:#e5484d;border-color:#e5484d;color:#fff}}
.res-item{{margin-bottom:16px}}
.res-item .k{{font-size:11px;letter-spacing:.06em;text-transform:uppercase;
  opacity:.65;margin-bottom:4px}}
.res-item .v{{font-size:19px;font-weight:700;color:inherit}}
.res-item .v small{{font-size:12px;font-weight:400;opacity:.65;margin-left:8px}}
.stop-row{{display:flex;justify-content:space-between;padding:6px 0;
  border-bottom:1px dashed rgba(128,128,128,.28);font-size:14px}}
.stop-row:last-child{{border-bottom:none}}
.stop-row .lbl{{opacity:.65}}
.warnbox{{margin-top:14px;padding:12px 14px;border-radius:10px;font-size:13px;
  line-height:1.6;display:none}}
.warnbox.show{{display:block}}
.warnbox.err{{background:rgba(229,72,77,.14);border:1px solid rgba(229,72,77,.5);
  color:#c0262b}}
.warnbox.ok{{background:rgba(47,191,113,.12);border:1px solid rgba(47,191,113,.45);
  color:#1a7f4b}}
.evnote{{font-size:12px;line-height:1.7;opacity:.85;
  margin-top:16px;padding:12px;border-radius:10px;
  background:rgba(128,128,128,.06);border:1px solid rgba(128,128,128,.3)}}
.evnote b{{color:#b8860b}}
/* 數值顏色（主題感知） */
.c-red{{color:#c0262b;font-weight:700}}
.c-green{{color:#1a7f4b;font-weight:700}}
.c-strong{{font-weight:700}}
/* 深色主題：提高對比 */
[data-theme="dark"] .warnbox.err{{color:#ff9a9d}}
[data-theme="dark"] .warnbox.ok{{color:#7ce0a8}}
[data-theme="dark"] .evnote b{{color:#ffd166}}
[data-theme="dark"] .c-red{{color:#ff9a9d}}
[data-theme="dark"] .c-green{{color:#7ce0a8}}
</style>

<h2>🧮 倉位計算機 <small>Position Sizing</small></h2>
<p class="crumb">按 SOUL §4 常數：風險 0.5% 淨值｜止蝕 ≤3%｜倉位 ≤33%｜目標 3R。
3 注模式跟 Jeff Sun（3 注全止蝕 = 0.67R）。</p>

<div class="calcbox">
  <div class="calc-panel">
    <h3>輸入</h3>
    <div class="frow">
      <label>淨值 Net Liquidation</label>
      <input id="c_cap" type="number" value="27400" step="100" min="1">
    </div>
    <div class="frow">
      <label>方向 Direction</label>
      <div class="seg" id="c_side">
        <button data-v="BUY" class="on">BUY 買</button>
        <button data-v="SELL">SELL 沽</button>
      </div>
    </div>
    <div class="frow">
      <label>風險 Risk (1R)</label>
      <div class="seg seg-risk" id="c_risk">{risk_opts}</div>
    </div>
    <div class="frow">
      <label>入場價 Entry</label>
      <input id="c_entry" type="number" value="100" step="0.01" min="0.01">
    </div>
    <div class="frow">
      <label>止蝕 Stop Loss</label>
      <input id="c_stop" type="number" value="97" step="0.01" min="0.01">
    </div>
    <div class="frow">
      <label>止蝕模式 Stop Mode</label>
      <div class="seg" id="c_mode">
        <button data-v="1" class="on">1 Stop</button>
        <button data-v="3">3 Stops（Jeff Sun）</button>
      </div>
    </div>
  </div>

  <div class="calc-panel">
    <h3>結果</h3>
    <div class="res-item"><div class="k">1R 風險額</div>
      <div class="v" id="r_r1">—</div></div>
    <div class="res-item"><div class="k">總股數</div>
      <div class="v" id="r_shares">—</div></div>
    <div class="res-item"><div class="k">倉位金額 / 佔淨值</div>
      <div class="v" id="r_pos">—</div></div>
    <div class="res-item"><div class="k">止蝕距離</div>
      <div class="v" id="r_stop">—</div></div>
    <div id="r_stops_wrap"></div>
    <div id="r_targets_wrap"></div>
    <div class="warnbox" id="r_warn"></div>
  </div>
</div>

<div class="evnote">
<b>★ 實測 EV（1,336 單 FIFO 配對，剔拆股污染）</b><br>
· 持倉 <b>≥1 日</b>：EV <b>+2.795%</b>/單（t=2.76，統計顯著）<br>
· 持倉 <b>&lt;1 日</b>：EV <b>+0.271%</b>/單（t=1.16，唔顯著）<br>
· <b>真股做日內</b>：EV <b>−0.48%</b>/單 ← 最大虧損源（717 單）<br>
· 槓桿 ETF 揸過夜：EV +7.78%/單（但只 35 單，樣本細 + 衰減風險）<br>
<br>
<b>★ 大贏家全部揸 ≥1 日</b>：最大 20 單中位持倉 191 小時（8 日），95% 揸 ≥24 小時。
</div>

<script>
(function(){{
  const $ = id => document.getElementById(id);
  let side = "BUY", mode = "1";

  document.querySelectorAll("#c_side button").forEach(b => {{
    b.onclick = () => {{
      side = b.dataset.v;
      document.querySelectorAll("#c_side button").forEach(x =>
        x.classList.toggle("on", x === b));
      document.querySelectorAll("#c_side button").forEach(x =>
        x.classList.toggle("sell", x === b && side === "SELL"));
      run();
    }};
  }});
  document.querySelectorAll("#c_mode button").forEach(b => {{
    b.onclick = () => {{
      mode = b.dataset.v;
      document.querySelectorAll("#c_mode button").forEach(x =>
        x.classList.toggle("on", x === b));
      run();
    }};
  }});
  ["c_cap","c_entry","c_stop"].forEach(id => $(id).oninput = run);
  let riskVal = "0.5";
  document.querySelectorAll("#c_risk button").forEach(b => {{
    b.onclick = () => {{
      riskVal = b.dataset.v;
      document.querySelectorAll("#c_risk button").forEach(x =>
        x.classList.toggle("on", x === b));
      run();
    }};
  }});

  const money = v => "$" + v.toLocaleString("en-US", {{maximumFractionDigits:2, minimumFractionDigits:2}});
  const num = (v,d=2) => v.toLocaleString("en-US", {{maximumFractionDigits:d}});

  function run(){{
    const cap = +$("c_cap").value, entry = +$("c_entry").value,
          stop = +$("c_stop").value, risk = +riskVal;
    const warn = $("r_warn");
    const fail = m => {{ warn.className = "warnbox err show"; warn.innerHTML = "⛔ " + m;
      ["r_r1","r_shares","r_pos","r_stop"].forEach(i => $(i).textContent = "—");
      $("r_stops_wrap").innerHTML = ""; $("r_targets_wrap").innerHTML = ""; }};

    if(!(cap>0)) return fail("淨值必須 > 0");
    if(!(entry>0)) return fail("入場價必須 > 0");
    if(!(stop>0)) return fail("止蝕價必須 > 0");
    if(side==="BUY" && stop>=entry) return fail("BUY：止蝕必須低於入場價");
    if(side==="SELL" && stop<=entry) return fail("SELL：止蝕必須高於入場價");

    const sign = side==="BUY" ? 1 : -1;
    const r1 = cap * risk / 100;
    const perShare = Math.abs(entry-stop);
    const stopPct = perShare/entry*100;

    let stops, avgStop, shares, tranche, riskAll;
    if(mode==="3"){{
      const step = perShare/3;
      stops = [entry-sign*perShare, entry-sign*perShare*2/3, entry-sign*perShare/3];
      avgStop = (stops[0]+stops[1]+stops[2])/3;
      const aps = Math.abs(entry-avgStop);
      const target = 0.67*r1;
      shares = aps>0 ? Math.floor(target/aps) : 0;
      const pt = Math.floor(shares/3);
      shares = pt*3;
      tranche = [pt,pt,pt];
      riskAll = shares*aps;
    }} else {{
      stops=[stop]; avgStop=stop;
      shares = perShare>0 ? Math.floor(r1/perShare) : 0;
      tranche=[shares];
      riskAll = shares*perShare;
    }}

    const notional = shares*entry;
    const posPct = notional/cap*100;

    $("r_r1").innerHTML = money(r1);
    $("r_shares").innerHTML = num(shares,0) +
      "<small>" + money(notional) + "</small>";
    $("r_pos").innerHTML = num(posPct,2) + "%" +
      "<small>" + money(notional) + "</small>";
    $("r_stop").innerHTML = num(stopPct,2) + "%" +
      "<small>" + money(perShare) + " / 股</small>";

    let ws = '<div class="res-item"><div class="k">止蝕階梯 Stop Levels</div>';
    stops.forEach((s,i) => {{
      const sh = tranche[i] !== undefined ? tranche[i] : 0;
      ws += '<div class="stop-row"><span class="lbl">Stop ' + (i+1) + '</span>' +
            '<span class="c-red">' + money(s) +
            '</span><span class="lbl">' + num(sh,0) + ' 股</span></div>';
    }});
    ws += '<div class="stop-row"><span class="lbl">全部止蝕</span>' +
          '<span class="c-strong">' + money(riskAll) +
          '（' + num(riskAll/r1,2) + 'R · ' + num(riskAll/cap*100,3) + '%）</span></div>';
    ws += '</div>';
    $("r_stops_wrap").innerHTML = ws;

    let ts = '<div class="res-item"><div class="k">目標價 Profit Targets</div>';
    [1,2,3,4].forEach(n => {{
      const p = entry + sign*perShare*n;
      ts += '<div class="stop-row"><span class="lbl">' + n + 'R</span>' +
            '<span class="c-green">' + money(p) +
            '</span><span class="lbl">+' + num(perShare*n*shares,0) + '</span></div>';
    }});
    ts += '</div>';
    $("r_targets_wrap").innerHTML = ts;

    let msgs = [];
    if(stopPct > 3) msgs.push("⛔ 止蝕距離 " + num(stopPct,2) + "% > 3% 上限 → 收緊止蝕");
    if(posPct > 33) msgs.push("⛔ 倉位 " + num(posPct,1) + "% > 33% 上限 → 減股數");
    else if(posPct > 26.4) msgs.push("🟡 倉位 " + num(posPct,1) + "% 接近 33% 上限");
    if(risk > 1) msgs.push("🟡 風險 " + risk + "% > 1% 上限（SOUL §4）");
    if(shares===0) msgs.push("⛔ 股數 0 —— 止蝕太遠，1R 買唔到 1 股");

    if(msgs.length){{
      warn.className = "warnbox err show";
      warn.innerHTML = msgs.join("<br>");
    }} else {{
      warn.className = "warnbox ok show";
      warn.innerHTML = "✅ 符合 SOUL §4：風險 " + num(riskAll/cap*100,3) +
        "%｜倉位 " + num(posPct,1) + "%｜止蝕 " + num(stopPct,2) + "%";
    }}
  }}
  run();
}})();
</script>
"""
