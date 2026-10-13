#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_site_build.py — 守住網站兩個「全站爆」級 bug。

★ 為咩要測試守住（第一性原理，SOUL §8.5）
   呢兩個 bug 都唔係外觀問題 —— 佢哋令【14 頁全部唔出】或者
   【導覽靜靜地被切斷而冇人知】。

   ② 類最危險：`extras.py:108` 嘅 pandas 對比會直接 raise →
      build_site 中止 → docs/ 唔更新 → 但 git 上仍然係舊版 →
      網站睇落「正常」，其實係三日前的資料。冇測試 = 睇唔到。

   ① nav 被切斷更陰險：build 成功、頁面「正常」，
      只係最後 1-2 個 link 消失（Chrome 隱藏 scrollbar = 零提示）。

用法：
    PY=~/trading-os/.venv/Scripts/python.exe
    $PY -X utf8 -m unittest discover -s tests -p 'test_*.py'
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


class TestNoIndexMisalignment(unittest.TestCase):
    """★ bug ②：ETF 同 SPY 兩條 Series index 唔同 → pandas 強制 align
    → `ValueError: Can only compare identically-labeled Series objects`
    → build_site 全爆。

    守護方式：源碼一定要有 index 對齊（intersection/reindex），
    唔准再直接 `r.iloc[-n:] > s.iloc[-n:]`。
    """

    def setUp(self):
        self.src = io.open(os.path.join(HERE, "extras.py"),
                           encoding="utf-8").read()

    def test_aligns_before_compare(self):
        self.assertIn("intersection", self.src,
                      "extras.py 冇 index 對齊 —— 兩條 Series 直接比會爆")
        self.assertIn(".reindex(", self.src, "冇 reindex 對齊")

    def test_no_bare_cross_series_compare(self):
        """唔准再寫 `rX.iloc[..] > sY.iloc[..]`（唔同來源直接比）。"""
        bad = re.findall(r"r\d+\.iloc\[[^\]]*\]\s*>\s*s\d+\.iloc", self.src)
        self.assertEqual(bad, [],
                         f"又出現跨 index 直接比：{bad}")

    def test_imports_math(self):
        self.assertIn("import math", self.src, "spark 用 math.isfinite")


class TestNavWrapsOnDesktop(unittest.TestCase):
    """★ bug ①：14 個 link 喺桌面塞唔落（1433px vs 1213px 容器）
    → 默認 nowrap → 最後 1-2 個被切斷，而 scrollbar 被隱藏。

    守護方式：桌面 nav 規則一定要有 flex-wrap:wrap。
    """

    def setUp(self):
        self.src = io.open(os.path.join(HERE, "build_site.py"),
                           encoding="utf-8").read()

    def test_desktop_nav_has_flex_wrap(self):
        """base `nav{...}` 規則要有 flex-wrap:wrap（唔可以靠 media query）。"""
        # 搵唔喺 @media 入面嘅第一個 nav{...}
        m = re.search(r"\nnav\{([^}]*)\}", self.src)
        self.assertIsNotNone(m, "搵唔到 base nav 規則")
        body = m.group(1)
        self.assertIn("flex-wrap:wrap", body.replace(" ", ""),
                      f"base nav 冇 flex-wrap:wrap → 導覽會被切斷\n{body}")
        self.assertNotIn("overflow-x:auto", body,
                         "base nav 仍然靠橫向 scroll（桌面應該 wrap）")

    def test_mobile_keeps_scroll(self):
        """手機斷點（@media(max-width:700px)）應該維持 nowrap + 滑動。

        ★ 呢條測試第一次寫錯：我以為係 768px（Bootstrap 慣例），
          但呢個站用 700px。教訓：斷點值唔可以靠慣例估 —— 要查。
        """
        m = re.search(r"@media\(max-width:700px\)\{(.*?)\n\}",
                      self.src, re.S)
        self.assertIsNotNone(m, "搵唔到 700px 斷點")
        seg = m.group(1).replace(" ", "")
        self.assertIn("flex-wrap:nowrap", seg,
                      "手機規則冇 nowrap —— 會 wrap 成多行，好難睇")

    def test_nav_links_count_frozen(self):
        """★ 14 個 link 係已知數量。加 link 之前要重算寬度。

        呢條測試嘅作用：有人加 link 時被迫睇一眼導覽夠唔夠位。
        """
        m = re.search(r"SITENAV_LINKS\s*=\s*\[(.*?)\n\]", self.src, re.S)
        self.assertIsNotNone(m, "搵唔到 SITENAV_LINKS")
        n = len(re.findall(r'\(\s*"', m.group(1)))
        self.assertGreaterEqual(n, 10,
                                f"link 只剩 {n} 個？可能係 regex 壞咗")
        self.assertLessEqual(n, 18,
                             f"而家有 {n} 個 link —— 14 個已經要 wrap，"
                             f"{n} 個可能唔夠位。檢查 mobile/desktop 佈局。")


class TestBuildProducesAllPages(unittest.TestCase):
    """★ build 成功 = docs/ 全部頁面都比源碼新（唔可以靜靜地唔更新）。"""

    def test_docs_fresh(self):
        d = os.path.join(HERE, "docs")
        if not os.path.isdir(d):
            self.skipTest("docs/ 未生成")
        names = sorted(f for f in os.listdir(d) if f.endswith(".html"))
        self.assertGreaterEqual(len(names), 10,
                                f"docs/ 只有 {len(names)} 頁 —— 可能 build 中途爆")
        for f in names:
            self.assertGreater(os.path.getsize(os.path.join(d, f)), 1000,
                               f"{f} 太細（build 冇寫完）")


if __name__ == "__main__":
    unittest.main(verbosity=2)
