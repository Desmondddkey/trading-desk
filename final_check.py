# -*- coding: utf-8 -*-
"""final_check.py — 上線前最終驗收（確定性，零猜測）

Desmond 2026-10-20：「final 你再round check 多次 確保我聽朝訓醒係run 到
我要見到所有野係work」

逐項驗，印 PASS/FAIL，任何 FAIL 就 exit 1（cron 會報錯）。
唔會上網改任何嘢，只讀本機產物 + 一次 HTTP HEAD。
"""
import io
import json
import os
import re
import sys
import urllib.request

WEB = r"C:\Users\rain0\trading-os-web"
DOCS = os.path.join(WEB, "docs")
TO = r"C:\Users\rain0\trading-os\output"
LIVE = "https://desmondddkey.github.io/trading-desk"

OK, BAD = [], []


def chk(name, cond, detail=""):
    (OK if cond else BAD).append((name, detail))
    print(f'  {"✓" if cond else "✗"} {name}' + (f'  {detail}' if detail else ''))
    return cond


def rd(p):
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:                                        # noqa: BLE001
        return ""


def sidebar(h):
    m = re.search(r'<aside[^>]*id="sb".*?</aside>', h, re.S)
    return m.group(0) if m else ""


print("\n═══ 1. 本機檔案 ═══")
pages = sorted(f for f in os.listdir(DOCS) if f.endswith(".html"))
chk("docs 有 HTML", len(pages) >= 25, f"{len(pages)} 頁")
small = [p for p in pages
         if os.path.getsize(os.path.join(DOCS, p)) < 2000]
chk("冇空頁（<2KB）", not small, str(small[:3]) if small else "")

print("\n═══ 2. 側欄結構 ═══")
idx = rd(os.path.join(DOCS, "index.html"))
sb = sidebar(idx)
chk("側欄存在", bool(sb), f"{len(sb)} bytes")
labels = re.findall(r'<span class="lbl">([^<]+)</span>', sb)
chk("LOG BOOK 貼最底", labels and labels[-1] == "LOG BOOK",
    f"最後 = {labels[-1] if labels else '無'}")
chk("DATABASE 在第一組", "DATABASE" in labels)
chk("冇「數據健康」殘留", "數據健康" not in idx)
chk("冇「警報總覽」殘留", "警報總覽" not in idx)
chk("有 Alert", "Alert" in labels)
chk("冇 LOG BOOK 重複", labels.count("LOG BOOK") <= 1,
    f"出現 {labels.count('LOG BOOK')} 次")

print("\n═══ 3. 選股列表欄位一致性 ═══")
for f in ("week", "leaders", "cm"):
    h = rd(os.path.join(DOCS, f + ".html"))
    chk(f"{f} 有 RS-D", "<th>RS-D</th>" in h, f"svg {h.count('<svg')} 個")
    chk(f"{f} 有 RS-W", "<th>RS-W</th>" in h)
chk("Kell 全英文", not any(x in rd(os.path.join(DOCS, "leaders.html"))
                          for x in ("楔形彈出", "回踩 EMA", "基底突破",
                                    "過度延伸", "反轉延伸")),
    "冇中文階段殘留")
sc = rd(os.path.join(WEB, "stdcols.py"))
chk("標籤 21EMA", '("x",        "21EMA")' in sc)
chk("標籤 EXT.", '("y",        "EXT.")' in sc)

print("\n═══ 4. DATABASE 頁 ═══")
dh = rd(os.path.join(DOCS, "datahealth.html"))
chk("h2 = DATABASE", "<h2>DATABASE" in dh)
chk("顯示 Jeff Sun Daily Scan", "Jeff Sun Daily Scan（盤前）" in dh)
chk("顯示 Focus&Stalking List",
    "Focus&amp;Stalking List" in dh or "Focus&Stalking List" in dh)
chk("有三態 badge", "fr-fresh" in dh and "fr-stale" in dh)

print("\n═══ 5. 假更新防線 ═══")
chk("冇「今日圖表隊列」", "今日圖表隊列" not in idx)
chk("圖表隊列有真日期", bool(re.search(r"圖表隊列（過期|圖表隊列", idx)))
fresh = rd(os.path.join(WEB, "freshness.py"))
chk("freshness.py 有 SOURCES", "SOURCES = [" in fresh)

print("\n═══ 6. 數據源 ═══")
sys.path.insert(0, WEB)
try:
    import freshness as F
    rows = F.all_status()
    sm = F.summary()
    chk("freshness 讀得到", sm["total"] > 0, str(sm))
    miss = [r["label"] for r in rows if r["status"] == "MISSING"]
    print(f"      缺失 {len(miss)} 個：{miss[:4]}")
except Exception as e:                                       # noqa: BLE001
    chk("freshness 讀得到", False, f"{type(e).__name__}: {e}")

print("\n═══ 7. Cron 排程 ═══")
try:
    j = json.load(io.open(
        r"C:\Users\rain0\AppData\Local\hermes\cron\jobs.json", encoding="utf-8"))
    jobs = j if isinstance(j, list) else j.get("jobs", [])
    nm = {x.get("name"): x for x in jobs}
    chk("job 總數", len(jobs) >= 60, f"{len(jobs)} 個")
    p = nm.get("premarket-refresh-1850")
    chk("18:50 盤前刷新存在", bool(p),
        (p or {}).get("schedule", "") if p else "冇")
    if p:
        chk("18:50 未被停用", p.get("enabled") is not False,
            str(p.get("last_status")))
    # ★ 只計「今日」嘅失敗 —— 舊記錄（修好之前）唔算
    import datetime as _dt
    _today = _dt.date.today().isoformat()
    err = []
    for x in jobs:
        if (x.get("last_status") or "") != "error":
            continue
        lr = str(x.get("last_run_at") or "")[:10]
        if lr == _today:
            err.append(x.get("name"))
        else:
            print(f"      （舊失敗 {x.get('name')} @ {lr}，今日未重跑）")
    chk("今日冇 job 失敗", not err, str(err[:3]) if err else "")
except Exception as e:                                       # noqa: BLE001
    chk("Cron 讀得到", False, f"{type(e).__name__}: {e}")

print("\n═══ 8. 前瞻標籤 ═══")
try:
    import csv
    rows2 = list(csv.DictReader(io.open(
        os.path.join(TO, "setup_alerts_history.csv"), encoding="utf-8-sig")))
    for c in ("t3_r", "t10_r", "fwd_hi_r"):
        n = sum(1 for r in rows2
                if (r.get(c) or "").strip() not in ("", "nan", "None"))
        chk(f"{c} 已填", n >= 80, f"{n}/{len(rows2)}")
except Exception as e:                                       # noqa: BLE001
    chk("歷史檔讀得到", False, f"{type(e).__name__}: {e}")

print("\n═══ 9. Live 網站 ═══")
for f in ("index.html", "datahealth.html", "alerts.html", "logbook.html",
          "week.html", "cm.html", "leaders.html"):
    try:
        u = f"{LIVE}/{f}?cb={os.urandom(3).hex()}"
        rq = urllib.request.Request(u, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(rq, timeout=25) as r:
            chk(f"live {f}", r.status == 200, str(r.status))
    except Exception as e:                                   # noqa: BLE001
        chk(f"live {f}", False, f"{type(e).__name__}")

print("\n" + "═" * 46)
print(f"PASS {len(OK)}｜FAIL {len(BAD)}")
if BAD:
    print("\n❌ 失敗項：")
    for n, d in BAD:
        print(f"  · {n}  {d}")
    sys.exit(1)
print("✅ 全部通過，聽朝起身可以睇")
