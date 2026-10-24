# -*- coding: utf-8 -*-
"""test_process_page_tv.py — 守護：每日流程候選 chips 必須可觸發 TV 預覽

為咩要有呢個測試（SOUL §8.5：防錯做進物理環境）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2026-10-24 真實事故：chips 有 `data-sym` 但冇 `tv` class，
而 tvhover.js 用 `el.closest('a.tv')` 搵目標 → 永遠 null → hover 唔彈。
呢個 bug 靜默、唔會 crash、頁面照出 —— 只有人手試先發現。

所以呢度把「觸發憑證」寫成斷言：
  每個 .pf-cand 必須同時有 ① `tv` class ② `data-sym` ③ 可點嘅 href。
任何一項缺失 = 測試紅 = 唔准上線。
"""
import os
import re
import sys

WEB = r"C:/Users/rain0/trading-os-web"
if WEB not in sys.path:
    sys.path.insert(0, WEB)


def _body():
    import process_page
    _title, body = process_page.build()
    return body


def test_chips_exist():
    body = _body()
    chips = re.findall(r'<a class="pf-cand[^"]*"[^>]*>', body)
    assert chips, "每日流程 ④ 候選：一個 chip 都冇（買入區可能係空，但唔應該冇 markup）"
    assert len(chips) >= 3, f"chip 太少（{len(chips)}），檢查 rs_select 買入區"


def test_every_chip_has_tv_class():
    body = _body()
    chips = re.findall(r'<a class="pf-cand[^"]*"[^>]*>', body)
    for c in chips:
        assert re.search(r'class="[^"]*\btv\b', c), \
            f"chip 缺 tv class（tvhover.js 用 closest('a.tv')）: {c}"


def test_every_chip_has_data_sym():
    body = _body()
    chips = re.findall(r'<a class="pf-cand[^"]*"[^>]*>', body)
    for c in chips:
        assert "data-sym=" in c, f"chip 缺 data-sym: {c}"


def test_every_chip_has_href():
    body = _body()
    chips = re.findall(r'<a class="pf-cand[^"]*"[^>]*>', body)
    for c in chips:
        assert "href=" in c and "tradingview.com" in c, \
            f"chip 缺 TradingView 連結: {c}"


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok   {name}")
            except AssertionError as e:
                fails += 1
                print(f"  FAIL {name}: {e}")
    print("FAILED" if fails else "ALL OK")
    raise SystemExit(1 if fails else 0)
