# -*- coding: utf-8 -*-
"""hermesdir_page.py — Hermes 目錄（指令、工具、文件、站內入口）

一個地方睇齊 Hermes 做得到咩：CLI、內建工具、文件章節、同站內相關頁。
純靜態清單（唔上網、唔跑 CLI），所以 build 唔會慢或者卡死。
"""
from __future__ import annotations

import html as _h

CLI = [
    ("hermes", "開互動 session", "hermes"),
    ("hermes chat", "一次性對話（唔留 session）", "hermes chat -q \"QQQ 今日狀態\""),
    ("hermes model", "揀／切換模型", "hermes model"),
    ("hermes config", "讀寫設定", "hermes config get model"),
    ("hermes skills", "列出／安裝技能", "hermes skills list"),
    ("hermes hooks", "工具掛鈎（risk-guard 等）", "hermes hooks doctor"),
    ("hermes cron", "排程 job", "hermes cron list"),
    ("hermes profile", "多 profile（default / propfirm）", "hermes profile list"),
    ("hermes gateway", "長駐 gateway（Telegram 等）", "hermes gateway status"),
    ("hermes sessions", "歷史 session", "hermes sessions list"),
]

TOOLS = [
    ("terminal", "跑 shell（bash／MSYS）", "抓數、build、測試"),
    ("read_file / write_file / patch", "讀寫檔（patch 做定點改）", "改頁面、改代碼"),
    ("search_files", "全文／檔名搜尋（ripgrep）", "搵 rule、搵舊實作"),
    ("browser_exec", "真瀏覽器（CDP）", "截圖驗收、登入頁、JS 頁"),
    ("vision_analyze", "睇圖", "睇圖表、讀 screenshot"),
    ("delegate_task", "開子代理（隔離 context）", "大批量研究、獨立驗證"),
    ("cronjob_manage", "排程管理", "每日 collector、watchdog"),
    ("skill_manage / skill_view", "技能讀寫", "把流程封成 skill"),
    ("memory", "長期記憶", "偏好、環境事實"),
]

DOCS = [
    ("總覽", "https://hermes-agent.nousresearch.com/docs"),
    ("Hooks（工具前後掛鈎）", "https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks"),
    ("Skills（技能）", "https://hermes-agent.nousresearch.com/docs/user-guide/features/skills"),
    ("Cron（排程）", "https://hermes-agent.nousresearch.com/docs/user-guide/features/cron"),
    ("Tools（工具）", "https://hermes-agent.nousresearch.com/docs/user-guide/features/tools"),
]

SITE = [
    ("技能庫", "skills.html", "已安裝嘅 skill 全文（可搜尋）"),
    ("系統地圖", "sysmap.html", "96 個 cron job 做咩、幾時跑"),
    ("廚房看板", "jobboard.html", "job 狀態、失敗、新鮮度"),
    ("每日流程", "process.html", "由掃描到下注前檢查"),
    ("資料健康", "datahealth.html", "每個數據源幾時更新"),
]

CSS = """
.hd-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
.hd-tbl th{text-align:left;font-size:10px;letter-spacing:.05em;opacity:.55;font-weight:800;
  padding:5px 7px;border-bottom:1px solid rgba(148,163,184,.25)}
.hd-tbl td{padding:5px 7px;border-bottom:1px solid rgba(148,163,184,.1);vertical-align:top}
.hd-tbl code{font-size:12px}
.hd-note{font-size:10.5px;opacity:.55;line-height:1.7;margin-top:8px}
.hd-links{display:flex;flex-wrap:wrap;gap:8px}
.hd-links a{font-size:12px;padding:5px 9px;border:1px solid rgba(148,163,184,.3);
  border-radius:6px;text-decoration:none}
"""


def _esc(x):
    return _h.escape(str(x))


def build():
    L = [f"<style>{CSS}</style>"]
    L.append('<div class="card"><h2>Hermes 目錄 '
             '<small>呢個 agent 做得到咩、去邊度睇</small></h2><div class="body">')
    L.append('<div class="hd-links">')
    for name, href, _ in SITE:
        L.append(f'<a href="{href}">{_esc(name)}</a>')
    L.append('</div>')
    L.append('<div class="hd-note">站內五個入口；下面係 CLI、內建工具同官方文件。</div>')
    L.append('</div></div>')

    L.append('<div class="card"><h2>CLI 指令 <small>以 <code>hermes --help</code> 為準</small></h2>'
             '<div class="body"><div class="tscroll"><table class="hd-tbl"><thead><tr>'
             '<th>指令</th><th>做咩</th><th>例子</th></tr></thead><tbody>')
    for a, b, c in CLI:
        L.append(f'<tr><td><code>{_esc(a)}</code></td><td>{_esc(b)}</td>'
                 f'<td><code style="opacity:.7">{_esc(c)}</code></td></tr>')
    L.append('</tbody></table></div></div></div>')

    L.append('<div class="card"><h2>內建工具 <small>我實際用嘅</small></h2>'
             '<div class="body"><table class="hd-tbl"><thead><tr>'
             '<th>工具</th><th>做咩</th><th>我點用</th></tr></thead><tbody>')
    for a, b, c in TOOLS:
        L.append(f'<tr><td><code>{_esc(a)}</code></td><td>{_esc(b)}</td>'
                 f'<td style="opacity:.7">{_esc(c)}</td></tr>')
    L.append('</tbody></table></div></div>')

    L.append('<div class="card"><h2>官方文件</h2><div class="body">')
    L.append('<div class="hd-links">')
    for name, href in DOCS:
        L.append(f'<a href="{href}" target="_blank" rel="noopener">{_esc(name)}</a>')
    L.append('</div>')
    L.append('<div class="hd-note">文件永遠係最新；本頁只係索引，唔會取代文件。</div>')
    L.append('</div></div>')

    return ("Hermes 目錄", "".join(L))


if __name__ == "__main__":
    print(build()[0])
