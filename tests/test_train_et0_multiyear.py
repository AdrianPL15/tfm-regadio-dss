import unittest

import numpy as np
import pandas as pd

from src.models.train_et0_multiyear import build_feature_table


class TrainEt0MultiyearTests(unittest.TestCase):
    def test_target_is_next_day_and_features_are_past_only(self):
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        history = pd.DataFrame(
            {
                "date": dates,
                "et0_mm": np.arange(20, dtype=float),
                "temperature_mean_c": np.arange(20, dtype=float) + 10,
            }
        )
        table, _ = build_feature_table(history)
        self.assertEqual(float(table.iloc[5]["target_et0_mm"]), 6.0)
        self.assertEqual(float(table.iloc[5]["et0_lag_1d"]), 5.0)
        self.assertEqual(float(table.iloc[5]["et0_lag_2d"]), 4.0)

    def test_future_change_does_not_modify_earlier_features(self):
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        history = pd.DataFrame({"date": dates, "et0_mm": np.arange(20, dtype=float)})
        before, features = build_feature_table(history)
        changed = history.copy()
        changed.loc[15:, "et0_mm"] = 999.0
        after, _ = build_feature_table(changed)
        pd.testing.assert_series_equal(before.loc[10, features], after.loc[10, features])

    def test_two_day_horizon_uses_current_and_past_only(self):
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        history = pd.DataFrame({"date": dates, "et0_mm": np.arange(20, dtype=float)})
        table, _ = build_feature_table(history, horizon_days=2)
        self.assertEqual(float(table.iloc[5]["target_et0_mm"]), 7.0)
        self.assertEqual(float(table.iloc[5]["et0_lag_1d"]), 5.0)
        self.assertEqual(table.iloc[5]["prediction_date"], pd.Timestamp("2024-01-08"))

    def test_horizon_must_be_positive(self):
        history = pd.DataFrame({"date": ["2024-01-01"], "et0_mm": [1.0]})
        with self.assertRaises(ValueError):
            build_feature_table(history, horizon_days=0)

    def test_fourteen_day_mean_requires_complete_window(self):
        history = pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=14, freq="D"),
            "et0_mm": np.arange(1.0, 15.0),
        })
        table, _ = build_feature_table(history)
        self.assertTrue(table["et0_mean_14d"].iloc[:13].isna().all())
        self.assertAlmostEqual(table["et0_mean_14d"].iloc[13], 7.5)

    def test_lags_follow_calendar_days_when_history_has_a_gap(self):
        history = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-03", "2024-01-04"]),
                "et0_mm": [1.0, 3.0, 4.0],
            }
        )
        table, _ = build_feature_table(history)
        row = table.loc[table["date"].eq(pd.Timestamp("2024-01-03"))].iloc[0]
        self.assertEqual(float(row["et0_lag_1d"]), 3.0)
        self.assertTrue(pd.isna(row["et0_lag_2d"]))


if __name__ == "__main__":
    unittest.main()
