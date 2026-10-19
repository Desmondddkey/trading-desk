# -*- coding: utf-8 -*-
"""freshness.py — 數據新鮮度唯一真相來源（Single Source of Truth）

Desmond 2026-10-20：「我唔想佢有任何假野 / 假更新既情況出現會影響我既判斷」

━━━ 為什麼要有呢個檔 ━━━
舊做法嘅致命問題（實測證據）：
  · build_site.py:293 「搵唔到今日 rs_select → 用 newest()」，
    而 rs_select_2026-10-11.json 係唯一一個檔（8 日前），
    但頁面標題照寫「今日圖表隊列」→ **假更新**。
  · layer5_campaign 停在 2026-10-06（13 日前），冇任何警示。

正確做法（第一性原理）：
  ① 每個數據源**事先聲明**期望更新頻率（cadence）
  ② 每次讀取都經同一個函數，回傳 (data, status)
  ③ status ∈ FRESH / STALE / MISSING
  ④ UI **必須**標示真實日期；STALE 一定要有警告
  ⑤ 永遠唔可以靜靜用舊檔扮新

狀態定義：
  FRESH   檔案存在，age ≤ max_age（以日曆日計，已考慮週末）
  STALE   檔案存在，但 age > max_age
  MISSING 完全搵唔到檔案

★ max_age 用「日曆日」而唔係「交易日」的原因：
  交易日判斷需要市假日曆，容易出錯；用日曆日 + 寬鬆門檻更安全。
  週末會出現 STALE（週五數據在週日 age=2），所以 max_age 已預留。
"""
import datetime as dt
import glob
import io
import json
import os
import sys

TO = r"C:\Users\rain0\trading-os\output"
LAB = r"C:\Users\rain0\trading-os-lab\output"

# ── 數據源登記表（唯一權威）──────────────────────────────────────
# key = 穩定標識；pattern = glob；max_age = 容許最大日曆日差
# producer = 邊個 cron / 腳本負責更新（方便追）
SOURCES = [
    dict(k="l1_scans",   label="Jeff Sun Daily Scan（盤前）",
         pattern="My_Scans_*.xlsx", base=TO, max_age=1,
         producer="jeffsun_scan（盤後）", used="Daily Scan、機會"),
    dict(k="l2_focus",   label="Focus&Stalking List",
         pattern="layer2_*.json", base=TO, max_age=1,
         producer="layer2_focus_stalk", used="Daily Scan、領導股"),
    dict(k="breadth",    label="廣度（40MA/ADL）",
         pattern="breadth_*.json", base=TO, max_age=1,
         producer="layer4_breadth", used="市場簡報、Breadth"),
    dict(k="insight",    label="市場洞察",
         pattern="market_insight_*.json", base=TO, max_age=1,
         producer="layer3b insight", used="市場簡報"),
    dict(k="rs_select",  label="RS 選股（圖表隊列）",
         pattern="rs_select_*.json", base=TO, max_age=1,
         producer="rs_select ⚠️ 未見對應 cron", used="市場簡報 · 圖表隊列"),
    dict(k="layer5",     label="競賽 campaign",
         pattern="layer5_campaign_*.json", base=TO, max_age=3,
         producer="layer5_campaign ⚠️ 未見對應 cron", used="Review / Positioning"),
    dict(k="plan",       label="每日計劃",
         pattern="daily_plan_*.json", base=TO, max_age=1,
         producer="daily_plan", used="機會（總表）"),
    dict(k="setup_hist", label="Setup 警報歷史",
         pattern="setup_alerts_history.csv", base=TO, max_age=1,
         producer="setup_alerts（盤中）", used="警報總覽"),
    dict(k="orh_hist",   label="ORH 警報歷史",
         pattern="orh_alert_history.csv", base=TO, max_age=1,
         producer="orh_alert（盤中）", used="警報總覽"),
    dict(k="prices",     label="價格快取（實驗室）",
         pattern="daily_2y.pkl", base=os.path.join(
             r"C:\Users\rain0\trading-os-lab", "cache"), max_age=3,
         producer="pkl_refresh（08:00）", used="位置圖、回測"),
    dict(k="dash",       label="交易台圖（dashboard）",
         pattern="dashboard_*.html", base=LAB, max_age=1,
         producer="dashboard", used="機會（總表）"),
]


def _age_days(path):
    try:
        m = os.path.getmtime(path)
    except OSError:
        return None
    return (dt.datetime.now() - dt.datetime.fromtimestamp(m)).days


def _pick(pattern, base):
    fs = glob.glob(os.path.join(base, pattern))
    if not fs:
        return None
    return max(fs, key=os.path.getmtime)


def status(k):
    """→ dict(status, path, age, mtime, ...)"""
    for s in SOURCES:
        if s["k"] != k:
            continue
        p = _pick(s["pattern"], s["base"])
        if not p:
            return dict(s, status="MISSING", path=None, age=None, mtime=None)
        age = _age_days(p)
        st = "FRESH" if (age is not None and age <= s["max_age"]) else "STALE"
        return dict(s, status=st, path=p, age=age,
                    mtime=dt.datetime.fromtimestamp(
                        os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M"))
    return dict(k=k, label=k, status="MISSING", path=None, age=None,
                mtime=None, max_age=None, producer="?", used="?")


def all_status():
    return [status(s["k"]) for s in SOURCES]


def load(k):
    """讀數據 + 附帶真實狀態。呼叫方**必須**使用回傳嘅 status。"""
    st = status(k)
    if not st["path"]:
        return None, st
    try:
        if st["path"].lower().endswith(".json"):
            with io.open(st["path"], encoding="utf-8") as f:
                return json.load(f), st
        return st["path"], st
    except (OSError, ValueError):
        st["status"] = "MISSING"
        return None, st


def badge(st):
    """HTML 徽章：永遠顯示真實日期，STALE/MISSING 明顯警告。"""
    s = st["status"]
    if s == "MISSING":
        return ('<span class="fr-b fr-miss">⛔ 冇數據</span>')
    if s == "STALE":
        return (f'<span class="fr-b fr-stale">⚠️ 過期 {st["age"]} 日'
                f'（{st["mtime"]}）</span>')
    return f'<span class="fr-b fr-fresh">✓ {st["mtime"][5:16]}</span>'


def summary():
    rs = all_status()
    return {
        "fresh": sum(1 for r in rs if r["status"] == "FRESH"),
        "stale": sum(1 for r in rs if r["status"] == "STALE"),
        "missing": sum(1 for r in rs if r["status"] == "MISSING"),
        "total": len(rs),
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    rs = all_status()
    for r in rs:
        icon = {"FRESH": "✓", "STALE": "⚠️", "MISSING": "⛔"}[r["status"]]
        age = f'{r["age"]}d' if r["age"] is not None else "—"
        print(f'{icon} {r["label"]:<24}{r["status"]:<8}{age:<5}'
              f'{r.get("mtime") or "—"}')
    sm = summary()
    print(f'\n  合計 {sm["total"]}｜即時 {sm["fresh"]}｜'
          f'過期 {sm["stale"]}｜缺失 {sm["missing"]}')
