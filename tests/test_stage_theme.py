# -*- coding: utf-8 -*-
"""test_stage_theme.py — 契約測試（唔係數字測試）：四階段頁嘅內部一致性。

唔會寫死「今日 S2 幾多 %」（嗰個係 state，會日日變）。只驗：
  1. 四個階段家數加起來 = covered（唔可以有一隻跌落裂縫）
  2. 百分比加起來 ≈ 100
  3. 每個行業 row 嘅健康標籤可以由 s2 − s4 重算出來（讀者可以自己覆核）
  4. row 成員數 ≥ MIN_N，而且四欄加起來 = n
  5. 走勢線每一點四欄加起來 ≈ 100
  6. 兩份輸出（panel 用 / stage_page 用）講同一件事
"""
import io
import json
import os
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TH = os.path.join(HERE, "data", "stage_theme.json")
PG = os.path.join(HERE, "data", "stage_for_page.json")


def _j(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


@unittest.skipUnless(os.path.exists(TH), "未跑過 stage_theme.py")
class TestStageTheme(unittest.TestCase):
    def setUp(self):
        self.d = _j(TH)

    def test_counts_sum_to_covered(self):
        d = self.d
        self.assertEqual(d["status"], "OK")
        self.assertEqual(sum(d["counts"].values()), d["covered"])
        self.assertLessEqual(d["covered"], d["universe"])

    def test_pct_sums_100(self):
        self.assertAlmostEqual(sum(self.d["pct"].values()), 100.0, delta=0.3)

    def test_health_recomputable(self):
        for r in self.d["rows"]:
            score = r["s2"] - r["s4"]
            want = ("Strong" if score >= 5 else "Healthy" if score >= -15
                    else "Neutral" if score >= -35 else "Weak")
            self.assertEqual(r["health"], want, r["group"])

    def test_rows_valid(self):
        mn = self.d["def"]["min_n"]
        for r in self.d["rows"]:
            self.assertGreaterEqual(r["n"], mn, r["group"])
            self.assertEqual(r["s1"] + r["s2"] + r["s3"] + r["s4"], 100,
                             f'{r["group"]} 四欄加起來唔係 100')

    def test_history_rows_sane(self):
        h = self.d["history"]
        self.assertGreaterEqual(len(h), 20)
        for row in h:
            self.assertAlmostEqual(row["s1"] + row["s2"] + row["s3"] + row["s4"],
                                   100.0, delta=0.5, msg=row["d"])
            self.assertGreaterEqual(row["n"], 50)

    def test_two_outputs_agree(self):
        if not os.path.exists(PG):
            self.skipTest("stage_for_page.json 未有")
        p = _j(PG)
        self.assertEqual(p["asof"], self.d["as_of"])
        self.assertEqual(p["n"], self.d["covered"])
        self.assertEqual(p["agg"], self.d["counts"])
        self.assertEqual(len(p["groups"]), len(self.d["rows"]))
        self.assertEqual(len(p["history"]), len(self.d["history"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
