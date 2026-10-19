# -*- coding: utf-8 -*-
"""jobboard.py — 廚房看板：所有 cron job 狀態 + 最新輸出（Desmond 2026-10-19）

★ 目的：Desmond 要「所有 active 常駐 job 都可以係網站讀取，自動更新」。

資料來源（全部本機，零上網）：
  ① ~/AppData/Local/hermes/cron/jobs.json      → 57 個 job 定義
  ② ~/AppData/Local/hermes/cron/executions.db  → 執行記錄 + incidents
  ③ ~/AppData/Local/hermes/cron/output/<id>/   → 每次執行嘅 stdout .md

★ Missing ≠ Zero：讀唔到某個源 = 該區顯示 DATA_UNAVAILABLE，唔當 0。

用法：
    python jobboard.py            # 生成 docs/jobboard.html
    python jobboard.py --json     # 只印統計 JSON
"""
import datetime
import html as _h
import io
import json
import os
import sqlite3
import sys

try:
    from job_purpose import purpose as _purpose
except Exception:                                    # noqa: BLE001
    def _purpose(n):
        return '', ''

HERMES = os.path.expanduser("~/AppData/Local/hermes")
JOBS = os.path.join(HERMES, "cron", "jobs.json")
EXECDB = os.path.join(HERMES, "cron", "executions.db")
OUTROOT = os.path.join(HERMES, "cron", "output")

# ★ 只顯示最新 1 個輸出，最多幾多字
MAX_OUT_CHARS = 2600
# ★ 最近幾多次執行
RECENT_N = 5


# ══════════════════════════════════════════════════════════════
def _esc(v):
    return _h.escape(str(v)) if v is not None else ""


def _ago(iso):
    """ISO 時間 → 幾耐之前（廣東話）。"""
    if not iso:
        return "從未"
    try:
        t = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        s = (now - t).total_seconds()
    except (ValueError, TypeError):
        return str(iso)[:16]
    if s < 0:
        return "未來"
    if s < 3600:
        return f"{int(s/60)} 分鐘前"
    if s < 86400:
        return f"{int(s/3600)} 小時前"
    d = int(s / 86400)
    return f"{d} 日前" if d < 30 else f"{d//30} 個月前"


def _sched(j):
    """schedule dict → 人話。"""
    sd = j.get("schedule") or {}
    if isinstance(sd, str):
        return sd
    kind = sd.get("kind")
    if kind == "cron":
        return sd.get("expr") or sd.get("display") or "cron"
    for k in ("display", "expr", "description", "value", "at"):
        if sd.get(k):
            return str(sd[k])
    return kind or "—"


# ══════════════════════════════════════════════════════════════
def load_jobs():
    """讀 jobs.json → list[dict]。"""
    try:
        raw = json.load(io.open(JOBS, encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, f"jobs.json 讀唔到：{type(e).__name__}"
    jobs = raw.get("jobs") if isinstance(raw, dict) else raw
    if not jobs:
        return None, "jobs.json 冇 jobs"
    return jobs, None


def load_exec():
    """讀 executions.db → dict[job_id] = dict(recent=[...], last=...) 。"""
    out = {}
    if not os.path.exists(EXECDB):
        return out
    try:
        con = sqlite3.connect(f"file:{EXECDB}?mode=ro", uri=True, timeout=8)
        cur = con.cursor()
        cols = [c[1] for c in cur.execute("PRAGMA table_info(executions)")]
        tcol = ("finished_at" if "finished_at" in cols else
                "ended_at" if "ended_at" in cols else
                "started_at" if "started_at" in cols else
                "claimed_at" if "claimed_at" in cols else "id")
        _extra = ", ".join(
            c if c in cols else f"NULL AS {c}"
            for c in ("started_at", "finished_at", "error"))
        rows = cur.execute(
            f"SELECT job_id, status, {tcol}, {_extra} FROM executions "
            f"ORDER BY id DESC LIMIT 1200").fetchall()
        for jid, st, ts, s_at, f_at, err in rows:
            d = out.setdefault(jid, {"recent": [], "last": None})
            if len(d["recent"]) < RECENT_N:
                _dur = None
                try:
                    _a = datetime.datetime.fromisoformat(
                        str(s_at).replace("Z", "+00:00"))
                    _b = datetime.datetime.fromisoformat(
                        str(f_at).replace("Z", "+00:00"))
                    _dur = max(0.0, (_b - _a).total_seconds())
                except (TypeError, ValueError):
                    pass
                d["recent"].append({"status": st, "at": ts,
                                    "dur": _dur, "err": err})
            if d["last"] is None:
                d["last"] = {"status": st, "at": ts}
        con.close()
    except (sqlite3.Error, OSError):
        pass
    return out


def load_incidents():
    """未關閉 incident。"""
    out = {}
    if not os.path.exists(EXECDB):
        return out
    try:
        con = sqlite3.connect(f"file:{EXECDB}?mode=ro", uri=True, timeout=8)
        cur = con.cursor()
        rows = cur.execute(
            "SELECT job_id, error_sig, failure_type, last_seen_at "
            "FROM cron_incidents WHERE closed_at IS NULL "
            "ORDER BY last_seen_at DESC").fetchall()
        for jid, sig, ft, seen in rows:
            out.setdefault(jid, []).append(
                {"sig": sig, "type": ft, "seen": seen})
        con.close()
    except (sqlite3.Error, OSError):
        pass
    return out


def latest_output(job_id):
    """cron/output/<job_id>/ 最新一個 .md → (text, mtime, filename)。"""
    p = os.path.join(OUTROOT, job_id)
    if not os.path.isdir(p):
        return None, None, None
    try:
        fs = [f for f in os.listdir(p) if f.endswith((".md", ".txt", ".log"))]
    except OSError:
        return None, None, None
    if not fs:
        return None, None, None
    fs.sort(key=lambda f: os.path.getmtime(os.path.join(p, f)), reverse=True)
    fp = os.path.join(p, fs[0])
    try:
        txt = io.open(fp, encoding="utf-8", errors="replace").read()
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(fp))
    except OSError:
        return None, None, None
    return txt, mt, fs[0]


# ══════════════════════════════════════════════════════════════
CSS = """
.jb-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
  gap:12px;margin:0 0 18px}
.jb-stat{padding:14px 16px;border-radius:12px;
  border:1px solid rgba(128,128,128,.28);background:rgba(128,128,128,.05)}
.jb-stat .v{font-size:26px;font-weight:800;line-height:1.1}
.jb-stat .k{font-size:11px;letter-spacing:.07em;text-transform:uppercase;
  opacity:.62;margin-top:5px}
.jb-ok{color:#1a7f4b}.jb-err{color:#c0262b}.jb-none{color:#8b8b8b}
[data-theme="dark"] .jb-ok{color:#7ce0a8}
[data-theme="dark"] .jb-err{color:#ff9a9d}
[data-theme="dark"] .jb-none{color:#8d9bb0}

.jb-grid{display:grid;gap:12px}
.jb-group{border:1px solid rgba(128,128,128,.28);border-radius:14px;
  margin:0 0 12px;background:rgba(128,128,128,.03);overflow:hidden}
.jb-group>summary{padding:13px 16px;cursor:pointer;font-size:14px;
  list-style:none;display:flex;align-items:center;gap:9px;
  background:rgba(128,128,128,.07);user-select:none}
.jb-group>summary::-webkit-details-marker{display:none}
.jb-group>summary::before{content:"▸";font-size:12px;opacity:.55;
  transition:transform .15s}
.jb-group[open]>summary::before{transform:rotate(90deg)}
.jb-group>summary:hover{background:rgba(128,128,128,.13)}
.jb-group>.jb-grid{padding:12px}
.jb-g-n{margin-left:auto;font-size:12px;opacity:.62;font-weight:400}
.jb-g-err{font-size:12px;color:#c0262b;font-weight:700}
.jb-g-none{font-size:12px;opacity:.6;font-weight:400}
[data-theme="dark"] .jb-g-err{color:#ff9a9d}
.jb-card{border:1px solid rgba(128,128,128,.26);border-radius:12px;
  overflow:hidden;background:rgba(128,128,128,.035)}
.jb-card.err{border-color:rgba(192,38,43,.5);
  background:rgba(192,38,43,.055)}
.jb-hd{display:flex;gap:10px;align-items:flex-start;padding:12px 14px;
  cursor:pointer;user-select:none}
.jb-hd:hover{background:rgba(128,128,128,.08)}
.jb-dot{width:10px;height:10px;border-radius:50%;flex:0 0 auto;margin-top:5px}
.d-ok{background:#2fbf71}.d-err{background:#e5484d}.d-none{background:#8b93a3}
.jb-nm{font-weight:700;font-size:14px;line-height:1.3}

.jb-log{margin:8px 0 4px;border:1px solid rgba(128,128,128,.2);
  border-radius:8px;overflow:hidden}
.jb-log-h{font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;
  opacity:.55;padding:5px 8px;background:rgba(128,128,128,.09);font-weight:700}
.jb-log-r{display:grid;grid-template-columns:20px 1fr auto auto;gap:8px;
  padding:4px 8px;font-size:11.5px;font-family:ui-monospace,monospace;
  border-top:1px solid rgba(128,128,128,.1);align-items:center}
.jb-log-r.e{color:#e5484d}
.jb-log-s{opacity:.7;font-size:10.5px}
.jb-cat{font-size:10px;font-weight:700;padding:1px 6px;border-radius:999px;
  border:1px solid rgba(128,128,128,.35);margin-left:6px;opacity:.75;
  white-space:nowrap;vertical-align:middle}
.jb-purpose{font-size:12.5px;line-height:1.6;margin-top:5px;
  opacity:.9;color:inherit}
.jb-meta{font-size:11.5px;opacity:.68;margin-top:3px;line-height:1.55}
.jb-meta code{font-size:11px;padding:1px 5px;border-radius:4px;
  background:rgba(128,128,128,.16)}
.jb-body{padding:0 14px 14px;display:none}
.jb-card.open .jb-body{display:block}
.jb-pre{white-space:pre-wrap;word-break:break-word;font-size:12.5px;
  line-height:1.65;padding:12px;border-radius:9px;
  background:rgba(128,128,128,.075);border:1px solid rgba(128,128,128,.18);
  max-height:420px;overflow:auto;font-family:ui-monospace,Menlo,Consolas,monospace}
.jb-chips{display:flex;gap:5px;flex-wrap:wrap;margin:0 0 9px}
.jb-chip{font-size:10.5px;padding:2px 7px;border-radius:999px;
  border:1px solid rgba(128,128,128,.34);opacity:.86}
.jb-empty{opacity:.5;font-size:12px;padding:8px 0}
.jb-filters{display:flex;gap:7px;flex-wrap:wrap;margin:0 0 16px}
.jb-filters button{padding:7px 13px;border-radius:999px;font-size:12.5px;
  border:1px solid rgba(128,128,128,.34);background:rgba(128,128,128,.07);
  color:inherit;cursor:pointer;font-family:inherit}
.jb-filters button.on{background:#2563eb;border-color:#2563eb;color:#fff}
.jb-sched{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px}
@media(max-width:700px){.jb-pre{max-height:300px;font-size:12px}}
"""

JS = """
function jbToggle(el){el.parentElement.classList.toggle('open')}

function jbCat(cat,btn){
  document.querySelectorAll('.jb-filters button').forEach(b=>b.classList.remove('on'));
  if(btn) btn.classList.add('on');
  document.querySelectorAll('.jb-group').forEach(g=>{
    var on = (g.dataset.cat===cat);
    g.style.display = on ? '' : 'none';
    if(on) g.open = true;
  });
}

function jbFilter(mode,btn){
  document.querySelectorAll('.jb-filters button').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  document.querySelectorAll('.jb-card').forEach(c=>{
    const ok = mode==='all' ? true
      : mode==='err' ? c.classList.contains('err')
      : mode==='never' ? c.dataset.state==='never'
      : mode==='on' ? c.dataset.state!=='never'
      : mode==='must' ? c.dataset.pri==='📌'
      : mode==='eye' ? (c.dataset.pri==='📌'||c.dataset.pri==='👀')
      : true;
    c.style.display = ok ? '' : 'none';
  });
  // 篩選時自動展開有可見卡嘅組
  document.querySelectorAll('.jb-group').forEach(g=>{
    const vis = Array.from(g.querySelectorAll('.jb-card'))
      .some(c=>c.style.display!=='none');
    g.style.display = vis ? '' : 'none';
    if(mode!=='all') g.open = vis;
  });
}
"""


def build(jobs, execs, incs):
    today = datetime.date.today().isoformat()
    parts = [f'<style>{CSS}</style><script>{JS}</script>']
    parts.append(f'<h2>🍳 廚房看板 <small>所有常駐 job 狀態</small></h2>')
    parts.append(
        f'<p class="crumb">本機讀取 <code>~/AppData/Local/hermes/cron/</code>'
        f'｜生成 {_esc(today)}｜'
        f'<b>{len(jobs)}</b> 個 job 註冊｜'
        f'<a href="https://desmondddkey.github.io/trading-desk/index.html">回主頁</a></p>')

    # ── 分類 ──
    rows = []
    for j in jobs:
        jid = j.get("id") or j.get("job_id")
        name = j.get("name") or jid
        enabled = j.get("enabled", True)
        st = j.get("last_status") or (execs.get(jid, {}).get("last") or {}).get("status")
        last_at = j.get("last_run_at") or (execs.get(jid, {}).get("last") or {}).get("at")
        nxt = j.get("next_run_at")
        txt, mt, fn = latest_output(jid)
        err = j.get("last_error") or ""
        inc = incs.get(jid) or []
        rows.append(dict(
            jid=jid, name=name, enabled=enabled, status=st,
            last_at=last_at, next_at=nxt, out=txt, out_name=fn,
            out_mt=mt, err=err, inc=inc,
            sched=_sched(j), script=j.get("script") or "",
            no_agent=bool(j.get("no_agent")),
            deliver=str(j.get("deliver") or ""),
            purpose=_purpose(name)[0],
            picon=_purpose(name)[1],
        ))

    def state(r):
        if not r["enabled"]:
            return "off"
        if not r["status"] and not r["last_at"]:
            return "never"
        if r["status"] == "ok":
            return "ok"
        return "err"

    for r in rows:
        r["state"] = state(r)

    n_ok = sum(1 for r in rows if r["state"] == "ok")
    n_err = sum(1 for r in rows if r["state"] == "err")
    n_never = sum(1 for r in rows if r["state"] == "never")
    n_off = sum(1 for r in rows if r["state"] == "off")

    # ── 統計卡 ──
    parts.append('<div class="jb-stats">')
    for k, v, cls in (("正常", n_ok, "jb-ok"), ("失敗", n_err, "jb-err"),
                      ("從未跑過", n_never, "jb-none"),
                      ("已停用", n_off, "jb-none"),
                      ("未關閉事故", len(incs), "jb-err")):
        parts.append(f'<div class="jb-stat"><div class="v {cls}">{v}</div>'
                     f'<div class="k">{k}</div></div>')
    parts.append('</div>')

    # ── 失敗優先顯示 ──
    errs = sorted([r for r in rows if r["state"] == "err"],
                  key=lambda r: str(r["last_at"] or ""), reverse=True)
    if errs:
        parts.append('<div class="card"><h2>🚨 需要處理 '
                     f'<small>{len(errs)} 個 job 失敗</small></h2>'
                     '<div style="padding:12px 16px">')
        for r in errs:
            e = (r["err"] or "").strip().splitlines()
            msg = e[-1][:220] if e else "（冇錯誤訊息）"
            parts.append(
                f'<div style="padding:9px 0;border-bottom:1px solid '
                f'rgba(128,128,128,.16);font-size:13px">'
                f'<b>{_esc(r["name"])}</b> '
                f'<code style="font-size:11px">{_esc(r["jid"])}</code><br>'
                f'<span class="jb-err" style="font-size:12px">'
                f'{_esc(_ago(r["last_at"]))}｜{_esc(msg)}</span></div>')
        parts.append('</div></div>')

    # ── 篩選 ──
    parts.append('<div class="jb-filters">')
    parts.append('<button class="on" onclick="jbFilter(\'all\',this)">'
                 f'全部 {len(rows)}</button>')
    parts.append('<button onclick="jbFilter(\'err\',this)">'
                 f'🚨 失敗 {n_err}</button>')
    parts.append('<button onclick="jbFilter(\'on\',this)">'
                 f'✅ 運作中 {n_ok + n_err}</button>')
    parts.append('<button onclick="jbFilter(\'never\',this)">'
                 f'⚪ 從未跑 {n_never}</button>')
    n_must = sum(1 for r in rows if r.get("picon") == "📌")
    n_eye = sum(1 for r in rows if r.get("picon") == "👀")
    parts.append('<button onclick="jbFilter(\'must\',this)">'
                 f'📌 一定要睇 {n_must}</button>')
    parts.append('<button onclick="jbFilter(\'eye\',this)">'
                 f'👀 有時間睇 {n_must + n_eye}</button>')
    parts.append('</div>')

    # ── Job 卡：分組 + 摺疊（Desmond 2026-10-19「做返好個格式」）──
    # 58 張卡平鋪 = 睇唔到。改成 6 個時段組，每組預設摺疊，
    # 有失敗嘅組自動打開。
    order = {"err": 0, "ok": 1, "never": 2, "off": 3}
    rows.sort(key=lambda r: (order.get(r["state"], 4),
                             -(datetime.datetime.fromisoformat(
                                 str(r["last_at"]).replace("Z", "+00:00")
                             ).timestamp() if r["last_at"] else 0)))

    def _hour(r):
        """由 cron expr 抽 hour；非標準 → -1。"""
        try:
            p = str(r["sched"]).split()
            return int(p[1])
        except (ValueError, IndexError):
            return -1

    # ★ 2026-10-19 Desmond：「廚房看板 將setup分類返出黎」
    #   由「按時間」改成「按你做咩決定」分 6 類。
    try:
        import job_purpose as _jp
        CATS = _jp.CATS
        CAT = _jp.CAT
    except Exception:                                        # noqa: BLE001
        CATS, CAT = [], {}

    ICON = {"act": "📌", "scan": "🔍", "mkt": "🌍",
            "perf": "📊", "rec": "📓", "sys": "⚙️"}

    def _bucket(r):
        return CAT.get(r.get("name"), "other")

    order_cat = [c[0] for c in CATS] + ["other"]
    buckets = {}
    for r in rows:
        buckets.setdefault(_bucket(r), []).append(r)

    # 失敗一律排最前
    for _k in buckets:
        buckets[_k].sort(key=lambda r: 0 if r["state"] == "err" else 1)

    labels = {c[0]: (c[1], c[2]) for c in CATS}
    labels["other"] = ("未分類", "")

    for ck in order_cat:
        grp = buckets.get(ck) or []
        if not grp:
            continue
        g_err = sum(1 for r in grp if r["state"] == "err")
        g_never = sum(1 for r in grp if r["state"] == "never")
        badge = (f' <span class="jb-g-err">🚨 {g_err}</span>' if g_err else "")
        badge += (f' <span class="jb-g-none">⚪ {g_never}</span>' if g_never else "")
        nm, desc = labels.get(ck, ("未分類", ""))
        parts.append(
            f'<details class="jb-group" data-cat="{ck}"'
            f'{" open" if g_err or ck == "act" else ""}>'
            f'<summary><b>{ICON.get(ck, "·")} {nm}</b>'
            f'{" · " + desc if desc else ""}'
            f'<span class="jb-g-n">{len(grp)} 個</span>{badge}</summary>'
            '<div class="jb-grid">')

        for r in grp:
            st = r["state"]
            dot = {"ok": "d-ok", "err": "d-err", "never": "d-none",
                   "off": "d-none"}[st]
            cls = " err" if st == "err" else ""
            parts.append(f'<div class="jb-card{cls}" data-state="{st}" '
                         f'data-cat="{_esc(_bucket(r))}" '
                         f'data-pri="{_esc(r["picon"])}">')
            parts.append('<div class="jb-hd" onclick="jbToggle(this)">'
                         f'<span class="jb-dot {dot}"></span>'
                         '<div style="flex:1;min-width:0">'
                         f'<div class="jb-nm">{_esc(r["picon"])} {_esc(r["name"])}'
                         f'<span class="jb-cat">{ICON.get(_bucket(r), "")} '
                         f'{_esc(labels.get(_bucket(r), ("未分類", ""))[0])}</span>'
                         '</div>'
                         + (f'<div class="jb-purpose">{_esc(r["purpose"])}</div>'
                            if r["purpose"] else '')
                         + '<div class="jb-meta">'
                         f'<span class="jb-sched">{_esc(r["sched"])}</span>'
                         f'｜{_esc(_ago(r["last_at"]))}'
                         f'｜下次 {_esc(str(r["next_at"] or "—")[5:16])}'
                         '</div></div></div>')

            parts.append('<div class="jb-body">')
            chips = []
            if r["no_agent"]:
                chips.append("零 token")
            if r["script"]:
                chips.append(r["script"])
            if r["deliver"]:
                chips.append("→ " + r["deliver"][:30])
            if r["out_mt"]:
                chips.append("輸出 " + r["out_mt"].strftime("%m-%d %H:%M"))
            if r["inc"]:
                chips.append(f"⚠ {len(r['inc'])} 事故")
            chips.append(r["jid"])
            parts.append('<div class="jb-chips">' +
                         "".join(f'<span class="jb-chip">{_esc(c)}</span>'
                                 for c in chips) + '</div>')

            # ★ 2026-10-19 Desmond：「加個log 記錄」
            #   每次跑嘅時間 / 狀態 / 耗時（最新在上）
            rec = r.get("recent") or []
            if rec:
                okl = {"ok": "✅", "success": "✅", "done": "✅",
                       "error": "❌", "failed": "❌", "timeout": "⏱",
                       "skipped": "⏭", "running": "▶"}
                parts.append('<div class="jb-log"><div class="jb-log-h">'
                             '執行記錄（最新在上）</div>')
                for e in rec:
                    stt = str(e.get("status") or "?")
                    ic = okl.get(stt, "·")
                    at = str(e.get("at") or "")[:16].replace("T", " ")
                    du = e.get("dur")
                    du_s = (f"{du:.1f}s" if isinstance(du, (int, float))
                            and du < 60 else
                            f"{du/60:.1f}m" if isinstance(du, (int, float))
                            else "—")
                    parts.append(
                        f'<div class="jb-log-r{" e" if "err" in stt or "fail" in stt else ""}">'
                        f'<span>{ic}</span><span>{_esc(at)}</span>'
                        f'<span class="jb-log-s">{_esc(stt)}</span>'
                        f'<span>{_esc(du_s)}</span></div>')
                parts.append('</div>')

            if r["err"]:
                parts.append('<div class="jb-pre" style="color:#e5484d;'
                             'border-color:rgba(229,72,77,.4)">'
                             f'{_esc(r["err"][-1200:])}</div>')

            if r["out"]:
                t = r["out"].strip()
                if len(t) > MAX_OUT_CHARS:
                    t = t[:MAX_OUT_CHARS] + "\n\n…（截斷）"
                parts.append(f'<div class="jb-pre">{_esc(t)}</div>')
            elif not r["err"]:
                parts.append('<div class="jb-empty">'
                             '（成功但冇報告 = 沉默合約，空白即正常）'
                             '</div>')
            parts.append('</div></div>')

        parts.append('</div></details>')

    return "".join(parts)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    jobs, err = load_jobs()
    if err:
        sys.stderr.write(f"✗ {err}\n")
        print(json.dumps({"ok": False, "error": err}, ensure_ascii=False))
        return 1
    execs = load_exec()
    incs = load_incidents()

    if "--json" in sys.argv:
        rows = []
        for j in jobs:
            jid = j.get("id")
            st = j.get("last_status")
            txt, mt, fn = latest_output(jid)
            rows.append(dict(id=jid, name=j.get("name"),
                             status=st, last=j.get("last_run_at"),
                             next=j.get("next_run_at"),
                             sched=_sched(j),
                             has_out=bool(txt)))
        print(json.dumps(dict(n=len(rows), jobs=rows), ensure_ascii=False,
                         indent=1))
        return 0

    body = build(jobs, execs, incs)
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "jobboard_body.html")
    io.open(out, "w", encoding="utf-8").write(body)
    print(f"✓ jobboard body {len(body):,} 字 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
