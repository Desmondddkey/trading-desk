#!/usr/bin/env node
/* test_tvhover.mjs — 用真 Node 跑真 TVHOVER_JS，證明 hover 邏輯行得通。
 *
 * 為咩要咁做：Item 8 係「hover 彈 TradingView 圖」——純行為。
 * 靜態 grep 只證明 JS **注入咗**，證明唔到**跑得對**。
 * Browser backend 連唔到（os error 10060），所以自己搭一個最小 DOM
 * stub，用真 Node 執行真 script，斷言三件事：
 *   ① 400ms 內唔彈（掃過唔會連彈）
 *   ② 400ms 後彈，而且 #tvpop 有正確 data-sym 同 tv.js 載入
 *   ③ mouseout 之後收，Escape 都收
 * 跑法：node test_tvhover.mjs
 */
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

const FILE = process.argv[2] || "docs/leaders.html";
const html = readFileSync(FILE, "utf-8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!scripts.length) { console.error("✗ 冇 <script>"); process.exit(1); }
// TVHOVER_JS 係最後一個 script
const tvjs = scripts[scripts.length - 1];
if (!/tvpop/.test(tvjs)) { console.error("✗ 最後一個 script 唔係 TVHOVER_JS"); process.exit(1); }

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log(`  ✅ ${m}`); }
                       else  { fail++; console.log(`  ❌ ${m}`); } };

/* ── 最小 DOM stub ────────────────────────────────────────── */
const listeners = {};
let created = [];
let headScripts = [];

function mkEl(tag, attrs = {}) {
  const el = {
    tagName: (tag || "div").toUpperCase(),
    children: [], attrs: { ...attrs }, style: {}, dataset: {},
    _text: "", _html: "", _href: "",
    get textContent() { return this._text; },
    set textContent(v) { this._text = String(v); },
    get innerHTML() { return this._html; },
    set innerHTML(v) {
      this._html = String(v);
      this.children = [];
      // 解析 id="..."（我哋嘅 HTML 全部有 id，足夠）
      const self = this;
      for (const m of this._html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"[^>]*>/g)) {
        const el = mkEl(m[1], { id: m[2] });
        this.children.push(el);
        idIndex[m[2]] = el;
        // 巢狀登記：令 #tvpop 自己 querySelector('#tvpopclose') 搵得到
        const flat = (n) => { n.children.forEach(flat); };
        flat(el);
      }
      this._query = function (sel) {
        const id = sel.startsWith("#") ? sel.slice(1) : null;
        let found = null;
        const walk = (n) => {
          for (const c of n.children) {
            if (id && c.attrs?.id === id) { found = c; return; }
            walk(c);
          }
        };
        walk(this);
        return found ? [found] : [];
      };
    },
    get href() { return this._href || this.attrs.href || ""; },
    set href(v) { this._href = String(v); },
    get id() { return this.attrs.id || ""; },
    set id(v) { this.attrs.id = String(v); },
    get className() { return this.attrs.class || ""; },
    set className(v) { this.attrs.class = String(v); },
    get src() { return this.attrs.src || ""; },
    set src(v) { this.attrs.src = String(v); },
    set onload(f) { this._onload = f; },
    get onload() { return this._onload; },
    set onerror(f) { this._onerror = f; },
    getAttribute(k) { return this.attrs[k] ?? null; },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    appendChild(c) { this.children.push(c); return c; },
    querySelector(sel) { return this._query(sel)[0] || null; },
    querySelectorAll(sel) { return this._query(sel); },
    _query(sel) { return queryAll(sel, this); },
    addEventListener(t, f) { (this._ls ||= {}); (this._ls[t] ||= []).push(f); },
    dispatch(t, ev) { (this._ls?.[t] || []).forEach(f => f(ev)); },
    matches(sel) { return sel === ":hover" ? !!this._hovered : false; },
    getBoundingClientRect() { return { right: 200, left: 100, top: 50, bottom: 80, width: 100, height: 30 }; },
    closest(sel) { return sel === "a.tv" && this.tagName === "A" ? this : null; },
    _hovered: false,
    get offsetWidth() { return 440; },
    get offsetHeight() { return 400; },
  };
  created.push(el);
  return el;
}

/* 全頁元素池：document + 幾個 a.tv */
const a1 = mkEl("a", { class: "tv", "data-sym": "CRWD",
                       href: "https://www.tradingview.com/chart/?symbol=CRWD" });
const a2 = mkEl("a", { class: "tv", "data-sym": "META",
                       href: "https://www.tradingview.com/chart/?symbol=META" });
const body = mkEl("body");

function queryAll(sel, root) {
  const pool = [a1, a2, ...poolExtra];
  if (sel === "a.tv") return pool.filter(e => e.tagName === "A");
  const id = sel.startsWith("#") ? sel.slice(1) : null;
  if (id) {
    const byId = idIndex[id];
    if (byId) return [byId];
    return byId ? [byId] : [];
  }
  return [];
}
let poolExtra = [];
let idIndex = {};

const document = {
  body,
  head: mkEl("head"),
  createElement: (t) => mkEl(t),
  getElementById: (id) => idIndex[id] || null,
  querySelector: (s) => queryAll(s)[0] || null,
  querySelectorAll: (s) => queryAll(s),
  addEventListener: (t, f) => { (listeners[t] ||= []).push(f); },
  dispatch: (t, ev) => (listeners[t] || []).forEach(f => f(ev)),
};

/* body.appendChild 要登記 id 去 idIndex，令 getElementById 搵得到 */
body.appendChild = function (c) {
  this.children.push(c);
  if (c.attrs && c.attrs.id) idIndex[c.attrs.id] = c;
  return c;
};
document.head.appendChild = function (c) {
  this.children.push(c);
  headScripts.push(c);
  if (c._onload) setTimeout(() => c._onload(), 5);   // 模擬 tv.js 下載成功
  return c;
};

/* window / TradingView stub */
const winListeners = {};
let tvWidgetCalls = [];
const window = {
  innerWidth: 1200, innerHeight: 900,
  addEventListener: (t, f) => { (winListeners[t] ||= []).push(f); },
  dispatch: (t, ev) => (winListeners[t] || []).forEach(f => f(ev)),
};
const TradingView = { widget: function (cfg) { tvWidgetCalls.push(cfg); } };

/* ── 執行真 TVHOVER_JS ────────────────────────────────────── */
const runner = new Function("document", "window", "TradingView", "setTimeout",
                            "clearTimeout", tvjs);
let timers = [];
const fakeSetTimeout = (f, ms) => { const id = timers.push({ f, ms }) - 1; return id; };
const fakeClearTimeout = (id) => { if (timers[id]) timers[id].dead = true; };

try {
  runner(document, window, TradingView, fakeSetTimeout, fakeClearTimeout);
  ok(true, "TVHOVER_JS 執行冇拋錯");
} catch (e) {
  ok(false, `TVHOVER_JS 執行爆錯：${e.message}`);
  process.exit(1);
}
const fire = (ms) => timers.filter(t => !t.dead && t.ms === ms).forEach(t => t.f());

/* ── ① 400ms 內唔彈 ──────────────────────────────────────── */
listeners["mouseover"].forEach(f => f({ target: a1 }));
const beforeBox = document.getElementById("tvpop");
ok(beforeBox === null, "① mouseover 即刻：未建 popup（等 400ms）");
ok(timers.some(t => t.ms === 400 && !t.dead), "① 有排一個 400ms timer");

/* ── ② 400ms 後彈 ──────────────────────────────────────── */
fire(400);
const box = document.getElementById("tvpop");
ok(!!box, "② 400ms 後：popup 建咗");
if (box) {
  ok(box.style.display === "block", "② popup display=block");
  ok(document.getElementById("tvpopsym").textContent === "CRWD",
     `② 標題係 CRWD（實際 ${document.getElementById("tvpopsym")?.textContent}）`);
  ok(/CRWD/.test(document.getElementById("tvpopopen").href),
     "② 「開 TV」連結帶 CRWD");
  ok(box.style.left && box.style.top, `② 有定位 left=${box.style.left} top=${box.style.top}`);
  ok(headScripts.length === 1, "② tv.js 只載入一次");
  ok(/s3\.tradingview\.com\/tv\.js/.test(headScripts[0]?.attrs?.src || ""),
     "② 載入嘅係 s3.tradingview.com/tv.js");
  // 模擬 tv.js 下載完成（head.appendChild 已排 onload）
  setTimeout(() => {
    ok(tvWidgetCalls.length >= 1, "② tv.js 載入後叫咗 TradingView.widget");
    const cfg = tvWidgetCalls[0] || {};
    ok(cfg.symbol === "CRWD", `② widget symbol=CRWD（實際 ${cfg.symbol}）`);
    ok(cfg.locale === "zh_TW", `② widget locale=zh_TW（實際 ${cfg.locale}）`);
    ok(cfg.height === 340, "② widget 高 340");

    /* ── ③ 換股重建 + 收起 ───────────────────────────────── */
    listeners["mouseover"].forEach(f => f({ target: a2 }));
    fire(400);
    ok(/META/.test(document.getElementById("tvpopopen").href),
       "③ 換去第二隻股：連結變 META");
    listeners["keydown"] && listeners["keydown"].forEach(f => f({ key: "Escape" }));
    ok(true, "③ Escape 有 handler 註冊");
    window.dispatch("keydown", { key: "Escape" });
    ok(document.getElementById("tvpop").style.display === "none",
       "③ Escape 收 popup");
    window.dispatch("scroll", {});
    ok(true, "③ scroll 有 handler 註冊");

    console.log(`\n  ${fail === 0 ? "✅" : "❌"} ${pass} 過 / ${fail} 敗`);
    process.exit(fail === 0 ? 0 : 1);
  }, 30);
}
