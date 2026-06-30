import unittest

import pandas as pd

from src.quality_model import (
    ScreeningWeights,
    build_risk_flags,
    build_screening_memo,
    build_sector_summary,
    count_risk_flags,
    load_company_universe,
    normalize_company_universe,
    recommend_company,
    score_company_universe,
    score_market_position,
)


class QualityModelTests(unittest.TestCase):
    def setUp(self):
        self.universe = pd.DataFrame(
            {
                "Company": ["A", "B", "C"],
                "Sector": ["Software", "Software", "Services"],
                "Revenue": [100.0, 120.0, 80.0],
                "Revenue_Growth": [0.20, 0.05, 0.02],
                "EBITDA_Margin": [0.25, 0.10, 0.08],
                "FCF_Conversion": [0.85, 0.40, 0.35],
                "ROIC": [0.20, 0.08, 0.07],
                "Net_Debt_EBITDA": [0.5, 3.0, 3.6],
                "Customer_Concentration": [0.12, 0.35, 0.41],
                "Recurring_Revenue": [0.88, 0.45, 0.30],
                "Rule_Of_40": [0.45, 0.15, 0.10],
                "Market_Position": ["Leader", "Challenger", "Niche"],
            }
        )
        self.weights = ScreeningWeights()

    def test_normalize_requires_expected_columns(self):
        normalized = normalize_company_universe(self.universe)

        self.assertEqual(len(normalized), 3)
        self.assertIn("Revenue_Growth", normalized.columns)

    def test_score_company_universe_ranks_strong_company_first(self):
        scored = score_company_universe(self.universe, self.weights)

        self.assertEqual(scored.iloc[0]["Company"], "A")
        self.assertGreater(scored.iloc[0]["Quality_Score"], scored.iloc[-1]["Quality_Score"])

    def test_quality_score_is_bounded(self):
        scored = score_company_universe(self.universe, self.weights)

        self.assertGreaterEqual(scored["Quality_Score"].min(), 0)
        self.assertLessEqual(scored["Quality_Score"].max(), 100)
        self.assertIn("Rule_Of_40_Score", scored.columns)
        self.assertIn("Market_Position_Score", scored.columns)

    def test_risk_flags_detect_weak_company(self):
        flags = build_risk_flags(self.universe.iloc[-1])

        self.assertIn("High leverage", flags)
        self.assertIn("Customer concentration", flags)
        self.assertIn("Below Rule of 40", flags)

    def test_recommendation_uses_score_and_flags(self):
        scored = score_company_universe(self.universe, self.weights)

        self.assertIn(scored.iloc[0]["Recommendation"], {"Attractive", "Watchlist"})
        self.assertEqual(scored.iloc[-1]["Recommendation"], "Avoid")

    def test_flag_count_is_explicit(self):
        self.assertEqual(count_risk_flags("None"), 0)
        self.assertEqual(count_risk_flags("High leverage, Thin margin"), 2)

    def test_market_position_scores_are_used(self):
        self.assertEqual(score_market_position("Leader"), 100.0)
        self.assertEqual(score_market_position("Challenger"), 65.0)
        self.assertEqual(score_market_position("Unknown"), 50.0)

    def test_sector_summary_aggregates_scores(self):
        scored = score_company_universe(self.universe, self.weights)
        summary = build_sector_summary(scored)

        self.assertIn("Avg_Quality_Score", summary.columns)
        self.assertEqual(summary["Companies"].sum(), 3)

    def test_memo_contains_top_company_and_screening_view(self):
        scored = score_company_universe(self.universe, self.weights)
        summary = build_sector_summary(scored)
        memo = build_screening_memo(scored, summary)

        self.assertIn("Investment & Business Quality Screening Memo", memo)
        self.assertIn("Top-ranked company", memo)

    def test_loader_reads_sample_universe(self):
        loaded = load_company_universe("data/company_universe.csv")

        self.assertFalse(loaded.empty)
        self.assertIn("Company", loaded.columns)
        self.assertNotIn("Quality_Score", loaded.columns)


if __name__ == "__main__":
    unittest.main()
