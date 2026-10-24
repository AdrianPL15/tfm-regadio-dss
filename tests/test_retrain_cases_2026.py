"""Controles del reentrenamiento con campañas SiAR 2025 y 2026."""

import unittest

import pandas as pd

from src.models.retrain_cases_2026 import grouped_cases, prepare_group, source_for_case
from src.models.train_evaluate import EXCLUDED_SAME_DAY_FEATURES, FEATURE_COLUMNS, TARGET


class RetrainCases2026Tests(unittest.TestCase):
    def test_six_groups_and_campaigns_remain_separate(self):
        groups = grouped_cases()
        self.assertEqual(len(groups), 6)
        self.assertEqual([item.campaign_year for item in groups["pimiento_AL01"]], [2025, 2026])
        self.assertEqual([item.campaign_year for item in groups["coliflor_AL01"]], [2026])

    def test_missing_meteorology_is_not_relabelled_as_zero(self):
        case = grouped_cases()["algodon_BA08"][-1]
        source, quality = source_for_case(case)
        self.assertEqual(quality["csv_rows"], 205)
        self.assertEqual(quality["excluded_incomplete_rows"], 1)
        self.assertEqual(source[TARGET].isna().sum(), 1)

    def test_all_available_active_days_and_safe_lags(self):
        groups = grouped_cases()
        expected = {
            "pimiento_AL01": 300,
            "coliflor_AL01": 144,
            "maiz_Z06": 366,
            "algodon_BA08": 365,
            "alfalfa_Z06": 236,
            "alcachofa_BA08": 173,
        }
        for key, campaigns in groups.items():
            active, _ = prepare_group(campaigns)
            self.assertEqual(len(active), expected[key])
            self.assertTrue(active["crop_coefficient_kc"].gt(0).all())
            self.assertTrue(active[TARGET].notna().all())
            self.assertTrue(set(FEATURE_COLUMNS).issubset(active.columns))
            self.assertTrue(set(EXCLUDED_SAME_DAY_FEATURES).isdisjoint(active.columns))
            if len(campaigns) > 1:
                first_new_year = active.loc[active["campaign_year"].eq(2026)].iloc[0]
                self.assertTrue(pd.isna(first_new_year["net_irrigation_need_mm_lag_1d"]))


if __name__ == "__main__":
    unittest.main()
