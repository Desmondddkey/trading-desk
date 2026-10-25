# -*- coding: utf-8 -*-
"""wishingwealth.py — Dr. Wish（Gil Morales / Chris Kacher 系）GMI 數據

Desmond 2026-10-20：「https://wishingwealthblog.com/ 加入外部數據」

━━━ 為什麼呢個對賺錢關鍵 ━━━

GMI（General Market Index）= 6 個多頭條件之中有幾個成立。
  GMI 6/6 + GREEN  → 大盤健康，做多
  GMI 3-5/6        → 中性，減倉
  GMI ≤ 2/6 + RED  → 危險，現金為王（或做空）

實測對照（Desmond 2026-10-19）：
  GMI = 1/6，RED
  我哋回測：做空 EV +4.27R｜做多 EV +0.02R

  → GMI 低 = 做空有效，做多無效。呢個係 regime 過濾器。

另外兩個指標：
  GMI-2  9 個條件（更嚴格版本）
  T2108  % 股票喺 40 日 MA 之上（30% 以下 = 超賣）

━━━ 抓邊度 ━━━
RSS feed：https://wishingwealthblog.com/feed/
每篇文章嘅 <content:encoded> 有：
  <strong>GMI:</strong> 1/6
  <strong>GMI-2:</strong> 1/9
  <strong>T2108:</strong> 30%
標題有 "Day N of $QQQ short term (up|down)-trend" 同 "GREEN|YELLOW|RED"

━━━ 誠實規則 ━━━
  · 抓唔到 = 寫 MISSING，唔會用舊值扮新（EDGE-016）
  · 快取 30 分鐘（避免每次 build 都打人哋個站）
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache", "wishingwealth.json")
FEED = "https://wishingwealthblog.com/feed/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
TTL = 1800          # 30 分鐘


def _get(url, timeout=25):
    rq = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml,application/xml,text/xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(rq, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _parse(xml):
    """由 RSS 抽最新一篇嘅 GMI 數據。"""
    items = re.findall(r"<item>(.*?)</item>", xml, re.S)
    out = {"status": "MISSING", "source": FEED}
    for it in items[:6]:                      # 睇最近 6 篇，搵第一個有數嘅
        t = re.search(r"<title>(.*?)</title>", it, re.S)
        title = re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1)).strip() if t else ""
        body = re.sub(r"<!\[CDATA\[|\]\]>", "", it)
        g = re.search(r"GMI:\s*(\d)\s*/\s*(\d)", body)
        g2 = re.search(r"GMI-2:\s*(\d)\s*/\s*(\d)", body)
        t2 = re.search(r"T2108[:\s]*([\d.]+)\s*%", body)
        if not g:
            continue
        d = re.search(r"Day\s+(\d+)\s+of\s+\$?QQQ[^\n]{0,40}?"
                      r"(up|down)[- ]trend", title, re.I)
        col = "RED" if re.search(r"\bRED\b", title) else (
            "GREEN" if re.search(r"\bGREEN\b", title) else (
                "YELLOW" if re.search(r"\bYELLOW\b", title) else None))
        pd_ = re.search(r"<pubDate>(.*?)</pubDate>", it)
        out = {
            "status": "OK",
            "gmi": int(g.group(1)), "gmi_max": int(g.group(2)),
            "gmi2": int(g2.group(1)) if g2 else None,
            "gmi2_max": int(g2.group(2)) if g2 else None,
            "t2108": float(t2.group(1)) if t2 else None,
            "color": col,
            "qqq_day": int(d.group(1)) if d else None,
            "qqq_dir": d.group(2).lower() if d else None,
            "title": title[:160],
            "published": pd_.group(1) if pd_ else None,
            "source": FEED,
        }
        break
    return out


def fetch(force=False):
    """攞 GMI。有 30 分鐘快取。失敗回 MISSING（唔會用舊值扮新）。"""
    now = time.time()
    if not force and os.path.exists(CACHE):
        try:
            with io.open(CACHE, encoding="utf-8") as f:
                c = json.load(f)
            if now - c.get("_ts", 0) < TTL:
                return c
        except Exception:                                    # noqa: BLE001
            pass
    try:
        d = _parse(_get(FEED))
    except Exception as e:                                   # noqa: BLE001
        return {"status": "MISSING", "error": f"{type(e).__name__}: {e}",
                "source": FEED}
    d["_ts"] = now
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    try:
        with io.open(CACHE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except Exception:                                        # noqa: BLE001
        pass
    return d


def regime_bias(d=None):
    """由 GMI 推導方向偏好。回 'SHORT' / 'LONG' / 'NEUTRAL'。

    ★ 呢個係 YOYO alert 嘅過濾器：
      GMI ≤ 2 或 RED → 只出做空
      GMI ≥ 5 或 GREEN → 只出做多
      中間 → 兩個都出（但標「中性」）
    """
    d = d or fetch()
    if d.get("status") != "OK":
        return "NEUTRAL", "GMI 讀唔到，唔加方向限制"
    g = d.get("gmi")
    c = (d.get("color") or "").upper()
    if (g is not None and g <= 2) or c == "RED":
        return "SHORT", f"GMI {g}/{d.get('gmi_max')} {c} → 大盤弱，做空優先"
    if (g is not None and g >= 5) or c == "GREEN":
        return "LONG", f"GMI {g}/{d.get('gmi_max')} {c} → 大盤強，做多優先"
    return "NEUTRAL", f"GMI {g}/{d.get('gmi_max')} {c or '—'} → 中性，兩個方向都睇"


def card_html():
    """網站卡片 HTML。"""
    d = fetch()
    if d.get("status") != "OK":
        return ('<div class="warn">⛔ Wishing Wealth GMI 讀唔到：'
                f'{d.get("error") or "unknown"}</div>')
    g, gm = d.get("gmi"), d.get("gmi_max")
    c = d.get("color") or "—"
    col = {"RED": "#dc2626", "GREEN": "#16a34a",
           "YELLOW": "#ea580c"}.get(c, "#64748b")
    bias, why = regime_bias(d)
    bcol = {"SHORT": "#dc2626", "LONG": "#16a34a"}.get(bias, "#64748b")
    return (
        '<div class="card"><h2>Wishing Wealth GMI <small>Dr. Wish</small></h2>'
        '<div class="body">'
        f'<div style="font-size:34px;font-weight:800;color:{col};'
        f'line-height:1.1">{g}/{gm}</div>'
        f'<div style="font-size:12.5px;font-weight:700;color:{col};'
        f'margin-bottom:10px">{c}</div>'
        f'<div style="font-size:12.5px;line-height:1.9">'
        f'GMI-2　<b>{d.get("gmi2")}/{d.get("gmi2_max")}</b><br>'
        f'T2108　<b>{d.get("t2108")}%</b>'
        f'（{"超賣" if (d.get("t2108") or 99) < 30 else "正常"}）<br>'
        f'QQQ　<b>{d.get("qqq_dir") or "—"}</b> trend 第 '
        f'<b>{d.get("qqq_day") or "—"}</b> 日</div>'
        f'<div style="margin-top:11px;padding:9px 12px;border-radius:8px;'
        f'border:1px solid {bcol};color:{bcol};font-size:12.5px;'
        f'font-weight:700">{why}</div>'
        f'<div style="margin-top:9px;font-size:11.5px;opacity:.6;'
        f'line-height:1.7">'
        f'發布 {d.get("published") or "—"}<br>'
        f'{d.get("title") or ""}</div>'
        '</div></div>')


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    d = fetch(force="--force" in sys.argv)
    print(json.dumps(d, ensure_ascii=False, indent=1))
    bias, why = regime_bias(d)
    print(f"\n方向偏好：{bias} — {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
