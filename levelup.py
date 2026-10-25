# -*- coding: utf-8 -*-
"""levelup.py — LevelUp Tools Market Pulse（外部數據）

Desmond 2026-10-20：「加外部數據
http://leveluptools.net/pulse/2026-10-20-close/#futures」

━━━ 呢個源提供咩 ━━━
① Growth risk gauge（6 個信號 → +/−/0）
   1. NQ futures / QQQ
   2. ES futures / SPY
   3. VIX futures（盤前）或 Up volume %（收市）
   4. Growth > 20-day %
   5. Growth > 50-day %
   6. 新高 vs 新低
   → 加總 = Gauge 分數（−6 至 +6）

② 每日敘事（例如「Small caps rotate in, tech sits out」）

③ What I'm watching tomorrow（作者關注點）

━━━ ★ 為何有價值 ━━━
佢嘅 Growth > 20MA / 50MA 係用 **98 隻成長股** 計，
唔同我哋三把尺：
  MMTW  = 全美股 % above 20MA
  MMFI  = NYSE+NASDAQ+AMEX % above 50MA
  LevelUp = 98 隻成長股（更貼近你實際交易嘅股票池）

━━━ 實作 ━━━
· iframe 嵌入原頁（冇 X-Frame-Options，200 OK）
· 另外自己 fetch + regex 抽關鍵數字做卡片
· 快取 30 分鐘；fetch 失敗 → DATA_UNAVAILABLE（EDGE-016）
"""
import io
import json
import os
import re
import time
import urllib.request

CACHE = r"C:\Users\rain0\trading-os-web\cache"
BASE = "https://leveluptools.net/pulse/"
TTL = 30 * 60          # 30 分鐘

CSS = """
.lu-k{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px}
.lu-k>div{flex:1 1 88px;padding:10px 11px;border-radius:10px;
  border:1px solid rgba(128,128,128,.26);background:rgba(128,128,128,.05)}
.lu-k .n{font-size:17px;font-weight:800;line-height:1.15}
.lu-k .l{font-size:10px;opacity:.6;margin-top:2px}
.lu-g{border-radius:10px;padding:12px 14px;margin:0 0 12px;
  font-size:12.5px;line-height:1.8}
.lu-g.on{background:rgba(22,163,74,.10);border:1px solid rgba(22,163,74,.35)}
.lu-g.mix{background:rgba(245,158,11,.10);border:1px solid rgba(245,158,11,.35)}
.lu-g.off{background:rgba(220,38,38,.10);border:1px solid rgba(220,38,38,.35)}
.lu-row{display:flex;justify-content:space-between;padding:4px 0;
  border-bottom:1px solid rgba(128,128,128,.12);font-size:11.5px}
.lu-row b{font-weight:700}
.lu-narr{font-size:12.5px;line-height:1.95}
.lu-narr b{color:#c2410c}
@media(max-width:700px){.lu-k>div{flex:1 1 70px;padding:8px 9px}
  .lu-k .n{font-size:17px}}
"""


def _cache_path():
    return os.path.join(CACHE, "levelup.json")


def fetch(force=False):
    """→ dict(ok, date, title, gauge, gauge_n, lines, narr, ts) """
    os.makedirs(CACHE, exist_ok=True)
    p = _cache_path()
    if not force and os.path.exists(p):
        try:
            d = json.load(io.open(p, encoding="utf-8"))
            if time.time() - d.get("ts", 0) < TTL:
                return d
        except (OSError, ValueError):
            pass
    try:
        req = urllib.request.Request(
            BASE, headers={"User-Agent": "Mozilla/5.0 (Hermes)"})
        html = urllib.request.urlopen(req, timeout=25).read().decode(
            "utf-8", "replace")
    except Exception as e:                                   # noqa: BLE001
        try:
            d = json.load(io.open(p, encoding="utf-8"))
            d["stale"] = True
            d["err"] = f"{type(e).__name__}"
            return d
        except (OSError, ValueError):
            return dict(ok=False, err=f"{type(e).__name__}: {e}")

    txt = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    txt = re.sub(r"<style.*?</style>", " ", txt, flags=re.S)
    txt = re.sub(r"<[^>]+>", "\n", txt)
    # ★ 2026-10-20：HTML entity 要先解碼，否則 `Growth > 20-day` 抓唔到
    import html as _html
    txt = _html.unescape(txt)
    txt = re.sub(r"\n{2,}", "\n", txt)
    lines = [x.strip() for x in txt.split("\n") if x.strip()]

    def grab(pat):
        m = re.search(pat, " ".join(lines))
        return m.group(1).strip() if m else None

    title = grab(r"Market Pulse[^:]*:\s*([^.]+)\.")
    qqq = grab(r"QQQ\s*([−\-+]\d+\.?\d*)%")
    spy = grab(r"SPY\s*([−\-+]\d+\.?\d*)%")
    upv = grab(r"Up volume\s*(\d+)%")
    g20 = grab(r"Growth\s*>\s*20-day\s*(\d+)%")
    g50 = grab(r"Growth\s*>\s*50-day\s*(\d+)%")
    hl = grab(r"Highs vs lows\s*(\d+\s*highs\s*/\s*\d+\s*lows)")
    gs = re.search(r"leaning risk-off\s*\(([−\-+]?\d+)\s*of\s*6\)|"
                   r"leaning risk-on\s*\(([−\-+]?\d+)\s*of\s*6\)",
                   " ".join(lines))
    gauge = gs.group(1) or gs.group(2) if gs else None

    d = dict(ok=True, ts=time.time(), title=title, qqq=qqq, spy=spy,
             upv=upv, g20=g20, g50=g50, hl=hl, gauge=gauge,
             url=BASE, stale=False)
    io.open(p, "w", encoding="utf-8").write(
        json.dumps(d, ensure_ascii=False))
    return d


def build():
    d = fetch()
    L = [f"<style>{CSS}</style>",
         "<h2>Market Pulse <small>LevelUp Tools · 外部</small></h2>"]

    if not d.get("ok"):
        L.append('<div class="warn">⛔ DATA_UNAVAILABLE：'
                 f'抓唔到 leveluptools.net（{d.get("err", "unknown")}）'
                 '<br>下面仍然有原頁連結。</div>')
    else:
        stale = d.get("stale")
        L.append(f'<p class="crumb">'
                 f'{"⚠️ 用舊快取（" + str(d.get("err","")) + "）" if stale else "即時抓取"}'
                 f'｜{time.strftime("%m-%d %H:%M", time.localtime(d["ts"]))}</p>')

        L.append('<div class="lu-k">')
        for v, lab in ((d.get("qqq"), "QQQ"), (d.get("spy"), "SPY"),
                       (d.get("upv"), "Up vol %"),
                       (d.get("g20"), "Growth>20MA"),
                       (d.get("g50"), "Growth>50MA")):
            if not v:
                continue
            try:
                fv = float(str(v).replace("−", "-").replace("+", ""))
            except ValueError:
                fv = None
            col = ""
            if fv is not None:
                if "vol" in lab or "Growth" in lab:
                    col = ("#16a34a" if fv >= 60 else
                           "#dc2626" if fv < 40 else "#f59e0b")
                elif lab in ("QQQ", "SPY"):
                    col = "#16a34a" if fv > 0 else "#dc2626"
            cc = f' style="color:{col}"' if col else ""
            unit = "%" if lab not in ("QQQ", "SPY") else "%"
            L.append(f'<div><div class="n"{cc}>{v}{unit}</div>'
                     f'<div class="l">{lab}</div></div>')
        L.append('</div>')

        g = d.get("gauge")
        if g:
            try:
                gv = int(str(g).replace("−", "-"))
            except ValueError:
                gv = 0
            cls = "on" if gv >= 2 else ("off" if gv <= -2 else "mix")
            lab = ("Risk-On" if gv >= 2 else
                   "Risk-Off" if gv <= -2 else "Mixed")
            L.append(f'<div class="lu-g {cls}">'
                     f'<b>Growth risk gauge：{lab}</b>'
                     f'（{g} of 6）<br>'
                     '6 個信號：QQQ／SPY 期貨或收市、VIX 期貨或 Up volume、'
                     'Growth > 20MA、Growth > 50MA、新高vs新低</div>')

        if d.get("title"):
            L.append(f'<div class="card"><div class="body lu-narr">'
                     f'<b>今日主題</b>：{d["title"]}</div></div>')

        if d.get("hl"):
            L.append(f'<div class="note" style="font-size:11.5px">'
                     f'新高 / 新低：{d["hl"]}</div>')

    # iframe 原頁
    L.append(
        '<div class="card" style="padding:0;overflow:hidden;margin-top:12px">'
        '<div style="padding:9px 14px;background:rgba(128,128,128,.08);'
        'display:flex;align-items:center;gap:9px;flex-wrap:wrap">'
        '<b style="font-size:12.5px">完整 Market Pulse</b>'
        '<span style="font-size:11.5px;opacity:.6">leveluptools.net</span>'
        '<span style="margin-left:auto;font-size:11.5px">'
        '<a href="https://leveluptools.net/pulse/" target="_blank" '
        'rel="noopener noreferrer">↗ 開新視窗</a></span></div>'
        '<iframe src="https://leveluptools.net/pulse/" '
        'style="width:100%;height:1400px;border:0;display:block" '
        'loading="lazy" referrerpolicy="no-referrer-when-downgrade">'
        '</iframe></div>')

    L.append('<div class="note" style="margin-top:14px;font-size:11.5px;'
             'line-height:1.85">'
             '<b>數據來源</b>　leveluptools.net（John Muchow）· 外部，只讀<br>'
             '<b>★ 呢把尺有咩唔同</b>　佢嘅 Growth &gt; 20MA / 50MA 用 '
             '<b>98 隻成長股</b> 計，比我哋嘅 MMTW（全美股）同 '
             'MMFI（NYSE+NASDAQ+AMEX）更貼近你實際交易嘅股票池。<br>'
             '<b>判讀</b>　Growth &gt; 20MA ≥60% = 綠（accumulation）；'
             '&lt;40% = 紅（distribution）；中間 = 黃。<br>'
             '<b>限制</b>　99 隻樣本細，抽樣誤差大；作者自己嘅方法論，'
             '唔係官方指數。</div>')
    return ("Market Pulse", "".join(L))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    d = fetch(force=True)
    print(json.dumps(d, ensure_ascii=False, indent=1))
