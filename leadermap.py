# -*- coding: utf-8 -*-
"""leadermap.py — RS Leader 位置圖頁（Desmond 2026-10-19）

需求：「更新返落個WEB到就得　新增日期選項，默認今日」

做法：
  ① 掃 trading-os-lab/output/leader_map_YYYY-MM-DD.{png,json}
  ② PNG 複製去 docs/img/lm/（GitHub Pages 要靜態檔）
  ③ 生成 leadermap.html：日期下拉（默認最新）→ 切換圖片，唔 reload
  ④ 圖下面列出當日 🔴 疊加 同 🔵 候選（由 JSON 讀，唔靠 OCR）

★ Missing ≠ Zero：冇 PNG = 顯示 DATA_UNAVAILABLE，唔准扮有圖。
"""
import datetime
import glob
import html as _h
import io
import json
import os
import shutil
import sys

LAB = r"C:\Users\rain0\trading-os-lab\output"
HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")
IMGDIR = os.path.join(DOCS, "img", "lm")


def _esc(v):
    return _h.escape(str(v)) if v is not None else ""


def _num(v, d=2):
    try:
        return f"{float(v):,.{d}f}"
    except (TypeError, ValueError):
        return "—"


def collect():
    """→ [(date, png_path, json_path_or_None)]，新→舊。"""
    out = []
    for png in glob.glob(os.path.join(LAB, "leader_map_*.png")):
        base = os.path.basename(png)[len("leader_map_"):-len(".png")]
        if len(base) != 10:
            continue
        js = os.path.join(LAB, f"leader_map_{base}.json")
        out.append((base, png, js if os.path.exists(js) else None))
    out.sort(key=lambda x: x[0], reverse=True)
    return out


def copy_images(items):
    os.makedirs(IMGDIR, exist_ok=True)
    ok = []
    for d, png, js in items:
        dst = os.path.join(IMGDIR, f"{d}.png")
        try:
            if (not os.path.exists(dst)
                    or os.path.getmtime(png) > os.path.getmtime(dst)):
                shutil.copy2(png, dst)
            ok.append((d, f"img/lm/{d}.png", js))
        except OSError as e:
            sys.stderr.write(f"⚠ copy {d} 失敗：{e}\n")
    return ok


CSS = """
.lm-bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;
  margin:0 0 14px;padding:12px 14px;border-radius:12px;
  border:1px solid rgba(128,128,128,.28);background:rgba(128,128,128,.05)}
.lm-bar label{font-size:12.5px;opacity:.72}
.lm-bar select{padding:8px 12px;border-radius:9px;font-size:14px;font-weight:600;
  border:1px solid rgba(128,128,128,.4);background:rgba(128,128,128,.1);
  color:inherit;font-family:inherit;cursor:pointer}
.lm-bar .lm-n{margin-left:auto;font-size:12px;opacity:.6}
.lm-img{width:100%;border-radius:12px;border:1px solid rgba(128,128,128,.28);
  background:#fff;display:block}
.lm-wrap{overflow-x:auto}
.lm-legend{display:flex;gap:16px;flex-wrap:wrap;margin:12px 0 0;font-size:13px}
.lm-red{color:#c0262b;font-weight:700}
.lm-blue{color:#1d4ed8;font-weight:700}
[data-theme="dark"] .lm-red{color:#ff9a9d}
[data-theme="dark"] .lm-blue{color:#7caeff}
.lm-empty{padding:20px;border-radius:12px;border:1px dashed rgba(128,128,128,.4);
  opacity:.7;font-size:13.5px;line-height:1.8}
.lm-asof{border-radius:10px;padding:10px 14px;font-size:12.5px;
  margin:0 0 12px;line-height:1.65}
.lm-asof.ok{background:rgba(47,191,113,.12);border:1px solid rgba(47,191,113,.45);
  color:#1a7f4b}
.lm-asof.warn{background:rgba(224,168,0,.12);border:1px solid rgba(224,168,0,.5);
  color:#8a6100}
[data-theme="dark"] .lm-asof.ok{color:#7ce0a8}
[data-theme="dark"] .lm-asof.warn{color:#fbc06a}
"""

JS = """
function lmPick(sel){
  var d = sel.value;
  var img = document.getElementById('lmimg');
  if(img) img.src = 'img/lm/' + d + '.png?v=' + Date.now();
  document.querySelectorAll('[data-lmdate]').forEach(function(el){
    el.style.display = (el.getAttribute('data-lmdate') === d) ? '' : 'none';
  });
  var lab = document.getElementById('lmlab');
  if(lab) lab.textContent = d;
}
"""


def _detail(js_path, date):
    """由 JSON 生成當日 🔴 / 🔵 名單。"""
    if not js_path:
        return '<div class="dim">（冇 JSON，只有圖）</div>'
    try:
        d = json.load(io.open(js_path, encoding="utf-8"))
    except (OSError, ValueError):
        return '<div class="dim">（JSON 讀唔到）</div>'

    def row(x, cls):
        return (f'<tr><td class="l"><b class="{cls}">{_esc(x.get("ticker"))}</b></td>'
                f'<td>{_num(x.get("close"))}</td>'
                f'<td>{_num(x.get("adr_pct"))}%</td>'
                f'<td>{_num(x.get("x"))}</td>'
                f'<td>{_num(x.get("y"))}</td>'
                f'<td>{_num(x.get("stack"), 0)}/6</td>'
                f'<td>{_num(x.get("dist_hi_pct"))}%</td>'
                f'<td>{_num(x.get("rs_1m_pct"))}%</td></tr>')

    head = ('<tr><th class="l">代號</th><th>收市</th><th>ADR%</th>'
            '<th>X（日）</th><th>Y（週 ATRX）</th><th>疊加</th>'
            '<th>距新高</th><th>1M 超額</th></tr>')
    red = d.get("red") or {}
    blues = d.get("blues") or []
    body = ""
    if red:
        body += row(red, "lm-red")
    for b in blues:
        body += row(b, "lm-blue")
    if not body:
        return '<div class="dim">當日冇候選</div>'
    return (f'<table><thead>{head}</thead><tbody>{body}</tbody></table>')


def _expected_last_trading_day():
    """美股最後一個應該有完整數據嘅交易日（香港時間計）。

    ★ 第一性原理：美股交易日 D 收市 = HKT (D+1) 04:00–05:30。
      → HKT 星期一 17:00 時，最新完整交易日一定係上星期五。
      → 唔可以用「日曆日差」判斷 stale（會永遠誤報）。
    """
    import datetime as _dt
    now = _dt.datetime.now()
    d = now.date() - _dt.timedelta(days=1)
    if now.hour < 6:
        d -= _dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= _dt.timedelta(days=1)
    return d.isoformat()


def _gap_days(a, b):
    """兩個 ISO 日期相差幾多日（a 較早）。"""
    try:
        import datetime as _dt
        return (_dt.date.fromisoformat(b) - _dt.date.fromisoformat(a)).days
    except (ValueError, TypeError):
        return "?"


def _price_asof():
    """讀 pkl 嘅最後交易日 —— 唔可以靠生成日扮數據日期。"""
    try:
        import pickle
        p = pickle.load(open(os.path.join(
            r"C:\Users\rain0\trading-os-lab", "cache", "daily_2y.pkl"), "rb"))
        return str(p.index[-1].date())
    except Exception:                                        # noqa: BLE001
        return ""


def build():
    items = collect()
    pa = _price_asof()
    if not items:
        body = ('<div class="lm-empty">⛔ <b>DATA_UNAVAILABLE</b><br>'
                '搵唔到 <code>trading-os-lab/output/leader_map_*.png</code>。<br>'
                '★ Missing ≠ Zero —— 冇圖唔等於冇候選。</div>')
        return ("RS Leader 位置圖", body)

    ready = copy_images(items)
    latest = ready[0][0]
    dates = [d for d, _, _ in ready]

    parts = [f'<style>{CSS}</style><script>{JS}</script>']
    parts.append('<h2>📍 RS Leader 位置圖 '
                 '<small>邊隻領導股有交易機會？</small></h2>')
    parts.append(
        '<p class="crumb">X 軸 =（收市 − 21日EMA）／ATR14（每日維度）｜'
        'Y 軸 =（收市 − 50日SMA）／ATR14 ＝ ATRX（週線維度）｜'
        '綠框買入區：−0.5 ≤ X ≤ +1 且 0 ≤ Y ≤ +4｜'
        '唯讀研究用途，<b>非買入指令</b></p>')

    # 日期選擇器
    opts = "".join(
        f'<option value="{d}"{" selected" if d == latest else ""}>{d}'
        f'{"（最新）" if d == latest else ""}</option>' for d in dates)
    parts.append('<div class="lm-bar">'
                 '<label for="lmsel">日期</label>'
                 f'<select id="lmsel" onchange="lmPick(this)">{opts}</select>'
                 f'<span class="lm-n">共 {len(dates)} 日'
                 f'｜最新 <b id="lmlab">{latest}</b></span>'
                 '</div>')

    # ★ 2026-10-19：圖上面嘅日期係【生成日】，唔一定等於【價格最後交易日】。
    #   兩個都要印，唔准扮同一日（SOUL §8.16）。
    #   ★★ 判斷 stale 要用「應該有嘅最後交易日」，唔係圖生成日。
    _exp = _expected_last_trading_day()
    if pa:
        if pa >= _exp:
            parts.append(f'<div class="lm-asof ok">✅ <b>已最新</b>：'
                         f'價格截至 <b>{pa}</b> ＝ 美股最新完整交易日'
                         f'（圖生成日 {latest}）。下一交易日數據要等 HKT 明早 05:30 後。</div>')
        else:
            parts.append(f'<div class="lm-asof warn">⚠️ 價格落後：最新 <b>{pa}</b>，'
                         f'應該有 <b>{_exp}</b>。→ 跑 <code>desk-refresh-daily</code>。'
                         f'（圖生成日 {latest}）</div>')

    # 圖
    parts.append('<div class="lm-wrap card" style="padding:10px">'
                 f'<img id="lmimg" class="lm-img" alt="RS Leader 位置圖 {latest}" '
                 f'src="img/lm/{latest}.png">'
                 '</div>')

    # 當日名單（跟日期切換）
    for d, rel, js in ready:
        style = "" if d == latest else ' style="display:none"'
        parts.append(f'<div class="card" data-lmdate="{d}"{style}>'
                     f'<h2>當日候選 <small>{d}</small></h2>'
                     f'<div class="body"><div class="scroll">'
                     f'{_detail(js, d)}</div>'
                     '<div class="lm-legend">'
                     '<span><b class="lm-red">● 紅</b>＝多重概率疊加（6 條件最高分）</span>'
                     '<span><b class="lm-blue">● 藍</b>＝候選（3 隻）</span>'
                     '</div>'
                     '<div class="note">★ X 同 Y 都係 ATR 單位，唔係 %。'
                     'Y 就係系統嘅 <code>ATRX</code>（EDGE-009 / EDGE-036 同一條公式），'
                     '硬刪門檻 4.0。</div>'
                     '</div></div>')

    return ("RS Leader 位置圖", "".join(parts))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    title, body = build()
    out = os.path.join(HERE, "leadermap_body.html")
    io.open(out, "w", encoding="utf-8").write(body)
    print(f"✓ leadermap body {len(body):,} 字 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
