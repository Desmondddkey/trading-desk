/* sortable.js — 全站唯一排序實作（2026-10-29 Desmond：「以後所有列表都要應用呢個」）
 *
 * 問題：頁面各有自己一份 tsSort / pfSort / rtSort / rsSort / dsSort，
 *       拆表或改 id 之後就會靜靜失效 → 三角係假嘅（按落去冇反應）。
 *
 * 做法：一個 SORT() 處理所有表；載入時覆蓋所有舊排序函數名，
 *       舊 onclick 唔需要改，行為統一。
 *
 * 規則：
 *   1. 喺「被撳嘅嗰張表」內排序（逐個 tbody 排，唔會把 FOCUS 同 STALK 混埋）
 *   2. 數值用 data-v；冇就用 textContent 抽數字；仍然唔係數字 → 字串比較
 *   3. 同一張表其他欄頭會清走箭咀
 *   4. 第一次撳 = desc（大→細），再撳 = asc
 */
(function () {
  function val(cell) {
    if (!cell) return '';
    var raw = (cell.dataset && cell.dataset.v !== undefined) ? cell.dataset.v
                                                             : cell.textContent;
    var s = String(raw).trim();
    var n = parseFloat(s.replace(/[^0-9.+-]/g, ''));
    return isNaN(n) ? s : n;
  }

  function SORT(btn, col) {
    var table = btn.closest ? btn.closest('table') : null;
    if (!table) return false;
    var dir = btn.dataset.dir === 'desc' ? 'asc' : 'desc';
    table.querySelectorAll('th').forEach(function (b) {
      if (b !== btn) b.dataset.dir = '';
    });
    btn.dataset.dir = dir;
    var idx = parseInt(col, 10);
    if (isNaN(idx)) idx = Array.prototype.indexOf.call(btn.parentNode.children, btn);

    table.querySelectorAll('tbody').forEach(function (tb) {
      var rows = Array.prototype.slice.call(tb.querySelectorAll(':scope > tr'));
      if (rows.length < 2) return;
      rows.sort(function (a, b) {
        var x = val(a.children[idx]), y = val(b.children[idx]);
        if (typeof x === 'number' && typeof y === 'number') {
          return dir === 'asc' ? x - y : y - x;
        }
        var sx = String(x), sy = String(y);
        return dir === 'asc' ? (sx > sy ? 1 : sx < sy ? -1 : 0)
                             : (sx < sy ? 1 : sx > sy ? -1 : 0);
      });
      rows.forEach(function (r) { tb.appendChild(r); });
    });
    return false;
  }

  window.SORT = SORT;

  // 覆蓋所有舊函數名（inline onclick 仍然有效，但行為統一）
  // ★ 一定要喺頁面自己嘅 <script> 之後做，否則會被覆蓋返轉頭
  var NAMES = ['tsSort', 'pfSort', 'rtSort', 'rsSort', 'dsSort', 'jbSort',
               'topSort', 'sortTable', 'tblSort'];
  function takeOver() {
    NAMES.forEach(function (n) { window[n] = SORT; });
  }
  takeOver();
  document.addEventListener('DOMContentLoaded', takeOver);
  window.addEventListener('load', function () { takeOver(); autoEnable(); });
  // ── 2026-10-29：所有表自動可排序（Desmond：「以後所有列表都要應用呢個」）
  //   規則：有 thead、≥2 個 th、≥3 行資料 → 自動加三角 + click。
  //   已經有 onclick 嘅唔重複加。想排除某欄：加 data-no-sort。
  function autoEnable() {
    document.querySelectorAll('table').forEach(function (t) {
      var thead = t.querySelector('thead');
      if (!thead) return;
      var ths = Array.prototype.slice.call(thead.querySelectorAll('th'));
      if (ths.length < 2) return;
      var rows = t.querySelectorAll('tbody tr');
      if (rows.length < 3) return;
      ths.forEach(function (th, i) {
        if (th.hasAttribute('onclick')) return;
        if (th.hasAttribute('data-no-sort')) return;
        if (th.dataset.autoSort === '1') return;
        th.dataset.autoSort = '1';
        th.dataset.dir = th.dataset.dir || '';
        th.style.cursor = 'pointer';
        th.addEventListener('click', function () { SORT(th, i); });
        if (!th.querySelector('.arr')) {
          var sp = document.createElement('span');
          sp.className = 'arr';
          sp.textContent = '▼';
          th.appendChild(sp);
        }
      });
    });
  }
  document.addEventListener('DOMContentLoaded', function () {
    takeOver();
    autoEnable();
  });


  // 箭咀提示：任何有 data-dir 嘅欄頭都顯示
  var css = document.createElement('style');
  css.textContent =
    'th[data-dir]{cursor:pointer;user-select:none}' +
    'th[data-dir] .arr{opacity:.35;margin-left:3px}' +
    'th[data-dir="asc"] .arr{opacity:1;transform:rotate(180deg);display:inline-block}' +
    'th[data-dir="desc"] .arr{opacity:1}';
  document.head.appendChild(css);
})();
