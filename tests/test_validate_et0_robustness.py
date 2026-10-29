import unittest

import numpy as np
import pandas as pd

from src.analysis.validate_et0_robustness import (
    _seasonally_adjusted_persistence,
    build_summary,
    evaluate_station,
)


class Et0RobustnessTests(unittest.TestCase):
    def test_seasonal_persistence_uses_only_supplied_training_history(self):
        history = pd.DataFrame(
            {
                "date": pd.to_datetime(["2021-01-01", "2021-01-02", "2022-01-01", "2022-01-02"]),
                "et0_mm": [1.0, 2.0, 3.0, 6.0],
            }
        )
        test = pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-01-01"]),
                "prediction_date": pd.to_datetime(["2023-01-02"]),
                "baseline_persistence": [4.0],
            }
        )
        result = _seasonally_adjusted_persistence(history, test)
        # Climatologia 01-01=2, 01-02=4; 4 + (4 - 2) = 6.
        self.assertAlmostEqual(float(result.iloc[0]), 6.0)

    def test_rolling_origin_never_trains_on_test_year(self):
        dates = pd.date_range("2021-01-01", "2025-12-31", freq="D")
        day = dates.dayofyear.to_numpy()
        et0 = 3 + np.sin(2 * np.pi * day / 365.25)
        history = pd.DataFrame(
            {
                "date": dates,
                "station_code": "TEST",
                "et0_mm": et0,
                "temperature_mean_c": et0 + 10,
            }
        )
        results = evaluate_station(history, "TEST", test_years=(2024, 2025))
        self.assertEqual(set(results["test_year"]), {2024, 2025})
        self.assertEqual(
            results.groupby("test_year")["n"].first().to_dict(),
            {2024: 366, 2025: 365},
        )

    def test_february_29_climatology_is_interpolated(self):
        history = pd.DataFrame(
            {
                "date": pd.to_datetime(["2021-02-28", "2021-03-01"]),
                "et0_mm": [2.0, 4.0],
            }
        )
        test = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-02-28"]),
                "prediction_date": pd.to_datetime(["2024-02-29"]),
                "baseline_persistence": [5.0],
            }
        )
        result = _seasonally_adjusted_persistence(history, test)
        self.assertAlmostEqual(float(result.iloc[0]), 6.0)

    def test_summary_counts_all_station_year_comparisons(self):
        rows = []
        for station in ("A", "B"):
            for method, mae in {
                "Ridge completo": 0.5,
                "Ridge ET0 + estacionalidad": 0.6,
                "Media movil 7 dias": 0.7,
                "Persistencia ajustada estacionalmente": 0.8,
            }.items():
                rows.append(
                    {
                        "station_code": station,
                        "test_year": 2025,
                        "horizon_days": 1,
                        "method": method,
                        "mae_mm_day": mae,
                    }
                )
        summary = build_summary(pd.DataFrame(rows))
        self.assertEqual(summary["total_station_years"], 2)
        self.assertEqual(summary["ridge_full_wins_vs_mean_7d"], 2)


if __name__ == "__main__":
    unittest.main()
