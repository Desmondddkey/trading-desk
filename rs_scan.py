# -*- coding: utf-8 -*-
"""rs_scan.py — RS Daily Scan 頁（Desmond 2026-10-24）

放喺 Daily Scan 下面（側欄「選股」組）。

數據來源：trading-os/output/rs_select_<YYYY-MM-DD>.json（rs-select-v1.1）
內容：61 隻 RS 宇宙 → gate 過濾 → 買入區
欄位全部有出處（唔准自己发明）：
  X      距 21EMA，ATR 單位（買入區通常 0-1）
  Y      距 50MA，ATR 單位（= ATRX，Jeff Sun 上限 4）
  距52高  同 52 週高距離（%）
  ADR%   平均日波幅
  RS1M/3M 相對 SPY 超額回報

冇數據時顯示 DATA_UNAVAILABLE，唔准用舊檔扮今日（零假更新鐵律）。
"""
import glob
import html as _h
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = r"C:/Users/rain0/trading-os/output"


def _latest(pattern):
    fs = sorted(glob.glob(os.path.join(DATA, pattern)))
    return fs[-1] if fs else None


def _esc(v):
    return _h.escape(str(v)) if v is not None else ""


def _f(v, d=2, plus=False):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "—"
    return (f"{x:+,.{d}f}" if plus else f"{x:,.{d}f}")


CSS = """
.rs-h{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:0 0 6px}
.rs-h h2{margin:0;font-size:19px}
.rs-sub{font-size:11.5px;opacity:.66}
.rs-f{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
.rs-f button{font:inherit;font-size:11.5px;padding:5px 11px;border-radius:999px;
  border:1px solid rgba(128,128,128,.35);background:transparent;color:inherit;
  cursor:pointer}
.rs-f button.on{background:#f97316;border-color:#f97316;color:#fff;font-weight:700}
.rs-wrap{overflow-x:auto}
.rs-tbl{width:100%;border-collapse:collapse;font-size:12px;
  font-variant-numeric:tabular-nums}
.rs-tbl th{position:sticky;top:0;background:var(--card,#1b1b19);text-align:right;
  padding:8px 7px;font-size:10.5px;font-weight:700;letter-spacing:.03em;
  border-bottom:1px solid rgba(128,128,128,.3);white-space:nowrap;opacity:.8}
.rs-tbl th.l,.rs-tbl td.l{text-align:left}
.rs-tbl th.sortable{cursor:pointer;user-select:none}
.rs-tbl th.sortable:hover{color:#f97316;opacity:1}
.rs-tbl th .arr{display:inline-block;margin-left:3px;font-size:8px;opacity:.4}
.rs-tbl th[data-dir="asc"] .arr{transform:rotate(180deg);opacity:1;color:#f97316}
.rs-tbl th[data-dir="desc"] .arr{opacity:1;color:#f97316}
.rs-tbl td{padding:7px;border-bottom:1px solid rgba(128,128,128,.12)}
.rs-tbl tr:hover td{background:rgba(249,115,22,.06)}
.rs-tk{font-weight:800;font-size:12.5px}
.rs-tk a{color:inherit;text-decoration:none;border-bottom:1px dotted rgba(128,128,128,.5)}
.rs-dot{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:5px}
.rs-in{background:#22c55e}
.rs-out{background:#6b7280}
.rs-pos{color:#15803d;font-weight:700}
.rs-neg{color:#dc2626;font-weight:700}
html[data-theme="dark"] .rs-pos{color:#7ce0a8}
html[data-theme="dark"] .rs-neg{color:#ff8f8f}
.rs-tag{font-size:9.5px;padding:1px 6px;border-radius:999px;
  border:1px solid rgba(128,128,128,.35);font-weight:700}
.rs-tag.buy{background:#f97316;border-color:#f97316;color:#fff}
.rs-tag.fail{border-color:#dc2626;color:#dc2626}
.rs-note{font-size:11px;opacity:.6;margin-top:10px;line-height:1.7}
.rs-meta{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;opacity:.75;
  margin:4px 0 10px}
.rs-meta b{font-weight:800;opacity:1}
"""

JS = """
function rsFilter(mode,btn){
  document.querySelectorAll('.rs-f button').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  document.querySelectorAll('#rsbody tr').forEach(r=>{
    var ok = mode==='all' ? true
      : mode==='buy' ? r.dataset.buy==='1'
      : mode==='pass' ? r.dataset.pass==='1'
      : mode==='focus' ? r.dataset.bucket==='focus'
      : true;
    r.style.display = ok ? '' : 'none';
  });
}
function rsSort(btn, idx){
  var tb=document.getElementById('rsbody');
  if(!tb) return;
  var rows=Array.from(tb.querySelectorAll('tr'));
  var dir = btn.dataset.dir==='desc' ? 'asc' : 'desc';
  document.querySelectorAll('.rs-tbl th').forEach(function(t){ if(t!==btn) t.dataset.dir=''; });
  btn.dataset.dir = dir;
  var sign = dir==='asc' ? 1 : -1;
  rows.sort(function(a,b){
    var x=a.children[idx].dataset.v, y=b.children[idx].dataset.v;
    var nx=parseFloat(x), ny=parseFloat(y);
    var vx=isNaN(nx)?x:nx, vy=isNaN(ny)?y:ny;
    if(typeof vx==='number' && typeof vy==='number') return (vx-vy)*sign;
    return String(vx).localeCompare(String(vy))*sign;
  });
  rows.forEach(function(r){tb.appendChild(r);});
}
"""

COLS = [
    ("代號", "ticker", "l", None),
    ("收市", "close", "", 2),
    ("RS 1M", "r1m", "", 1),
    ("RS 3M", "r3m", "", 1),
    ("EX 1M", "ex1m", "", 1),
    ("ADR%", "adr", "", 1),
    ("ATR%", "atr_pct", "", 1),
    ("X 距21EMA", "x", "", 2),
    ("Y 距50MA", "y", "", 2),
    ("距 52 高", "dist52w", "", 1),
    ("財報", "days_to_earn", "", 0),
    ("狀態", None, "l", None),
]


def build():
    p = _latest("rs_select_*.json")
    if not p:
        return ("RS Daily Scan",
                f'<style>{CSS}</style><div class="rs-h"><h2>RS Daily Scan</h2></div>'
                '<div class="dim">DATA_UNAVAILABLE（冇 rs_select_*.json）</div>')
    d = json.load(io.open(p, encoding="utf-8"))
    rows = d.get("rows") or []
    as_of = (d.get("as_of") or "")[:10]
    gates = d.get("gates") or {}
    n_univ = d.get("n_universe")
    n_pass = d.get("n_gate_pass")
    n_box = d.get("n_buy_box_all")

    parts = [f"<style>{CSS}</style><script>{JS}</script>"]
    parts.append('<div class="rs-h"><h2>RS Daily Scan</h2>'
                 f'<span class="rs-sub">{_esc(as_of)}｜rs-select-v1.1</span></div>')
    parts.append(
        '<div class="rs-meta">'
        f'<span>宇宙 <b>{_esc(n_univ)}</b></span>'
        f'<span>過閘 <b>{_esc(n_pass)}</b></span>'
        f'<span>買入區 <b>{_esc(n_box)}</b></span>'
        f'<span>價 ≥{_esc(gates.get("min_price"))}</span>'
        f'<span>成交額 ≥{_f((gates.get("min_dollar_vol") or 0)/1e6,0)}M</span>'
        f'<span>ADR ≥{_esc(gates.get("min_adr"))}%</span>'
        f'<span>ATRX ≤{_esc(gates.get("max_atrx"))}</span>'
        f'<span>距52高 ≥{_esc(gates.get("min_dist52w"))}%</span>'
        '</div>')

    parts.append('<div class="rs-f">'
                 '<button class="on" onclick="rsFilter(\'all\',this)">'
                 f'全部 {len(rows)}</button>'
                 f'<button onclick="rsFilter(\'buy\',this)">買入區 {n_box or 0}</button>'
                 f'<button onclick="rsFilter(\'pass\',this)">過閘 {n_pass or 0}</button>'
                 '<button onclick="rsFilter(\'focus\',this)">FOCUS</button></div>')

    th = []
    for i, (label, _k, cls, _dp) in enumerate(COLS):
        if i == len(COLS) - 1:
            th.append(f'<th class="l">{label}</th>')
        else:
            th.append(f'<th class="sortable {cls}" onclick="rsSort(this,{i})" '
                      f'data-dir="">{label}<span class="arr">▼</span></th>')
    parts.append('<div class="rs-wrap card" style="padding:0"><table class="rs-tbl">'
                 '<thead><tr>' + "".join(th) + '</tr></thead><tbody id="rsbody">')

    for r in rows:
        t = r.get("ticker") or ""
        in_box = bool(r.get("in_buy_box"))
        passed = bool(r.get("gate_pass"))
        fails = r.get("gate_fail") or []
        if in_box:
            status = '<span class="rs-tag buy">買入區</span>'
        elif not passed:
            status = ('<span class="rs-tag fail">閘：'
                      + _esc("、".join(str(x) for x in fails[:2])) + '</span>')
        else:
            status = '<span class="rs-tag">過閘</span>'
        dte = r.get("days_to_earn")
        dte_s = (f"{int(dte)}D" if isinstance(dte, (int, float))
                 and dte == dte else "—")   # NaN 檢查（dte != dte）
        note = r.get("watch_price") or ""
        inval = r.get("invalidation") or ""
        tip = f'{note}｜{inval}' if (note or inval) else ""

        parts.append(
            f'<tr data-buy="{1 if in_box else 0}" data-pass="{1 if passed else 0}" '
            f'data-bucket="{_esc(r.get("bucket") or "")}">'
            f'<td class="l"><span class="rs-dot {"rs-in" if in_box else "rs-out"}">'
            f'</span><span class="rs-tk"><a href="https://www.tradingview.com/chart/'
            f'?symbol={_esc(t)}" target="_blank" rel="noopener">{_esc(t)}</a></span>'
            + (f'<div class="dim" style="font-size:10px">{_esc(tip[:90])}</div>'
               if tip else "")
            + '</td>'
            f'<td data-v="{_esc(r.get("close"))}">{_f(r.get("close"), 2)}</td>'
            f'<td data-v="{_esc(r.get("r1m"))}" class="rs-pos">'
            f'{_f(r.get("r1m"), 1, True)}%</td>'
            f'<td data-v="{_esc(r.get("r3m"))}" class="rs-pos">'
            f'{_f(r.get("r3m"), 1, True)}%</td>'
            f'<td data-v="{_esc(r.get("ex1m"))}">{_f(r.get("ex1m"), 1, True)}</td>'
            f'<td data-v="{_esc(r.get("adr"))}">{_f(r.get("adr"), 1)}</td>'
            f'<td data-v="{_esc(r.get("atr_pct"))}">{_f(r.get("atr_pct"), 1)}</td>'
            f'<td data-v="{_esc(r.get("x"))}">{_f(r.get("x"), 2)}</td>'
            f'<td data-v="{_esc(r.get("y"))}" class="'
            f'{"rs-neg" if (r.get("y") or 0) > 4 else ""}">{_f(r.get("y"), 2)}</td>'
            f'<td data-v="{_esc(r.get("dist52w"))}">{_f(r.get("dist52w"), 1)}%</td>'
            f'<td data-v="{_esc(dte)}">{dte_s}</td>'
            f'<td class="l">{status}</td></tr>')

    parts.append('</tbody></table></div>')
    parts.append(
        '<div class="rs-note">'
        'X = 距 21EMA（ATR 單位）；Y = 距 50MA（= ATRX，>4 紅字代表過度延伸）。'
        '買入區 = 同時符合 6 個條件（價、成交額、ADR、ATRX、距 52 高、財報黑名單）。'
        '<br>★ 呢頁係「今日邊隻有資格」嘅清單，唔係買入訊號；'
        '實際入場價／止蝕／股數睇 Daily Scan 同盤前卡。</div>')
    return ("RS Daily Scan", "".join(parts))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    t, b = build()
    print(f"{t} — {len(b):,} chars")
    for probe in ("rsbody", "rsSort", "買入區", "ATR"):
        print(("OK  " if probe in b else "MISS") + f" {probe}")
