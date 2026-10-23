"""La tabla AEMET–SiAR solo utiliza previsiones anteriores a la etiqueta."""

import unittest

import pandas as pd

from src.dss.config import DEMO_CASES
from src.features.build_aemet_model_table import join_forecasts_to_siar


class AemetModelTableTests(unittest.TestCase):
    def test_selects_latest_prior_emission_and_ignores_other_municipality(self):
        forecasts = pd.DataFrame({
            "date": ["2025-06-21"] * 4,
            "issued_at": [
                "2025-06-19T07:00:00", "2025-06-20T07:00:00",
                "2025-06-21T12:00:00", "2025-06-20T08:00:00",
            ],
            "municipality_code": ["04013", "04013", "04013", "50095"],
            "precipitation_mm": [1.0, 2.0, 99.0, 50.0],
            "precipitation_probability_pct": [20, 40, 100, 80],
            "precipitation_amount_status": ["horas_disponibles"] * 4,
        })
        table = join_forecasts_to_siar(DEMO_CASES[0], forecasts)
        self.assertEqual(len(table), 1)
        self.assertEqual(table["forecast_precipitation_mm"].iat[0], 2.0)
        self.assertEqual(table["forecast_horizon_days"].iat[0], 1)
        self.assertLess(table["forecast_issued_at"].iat[0], table["observed_date"].iat[0])

    def test_current_forecast_cannot_train_on_2025_siar(self):
        forecasts = pd.DataFrame({
            "date": ["2026-10-24"], "issued_at": ["2026-10-23T12:00:00"],
            "municipality_code": ["04013"], "precipitation_mm": [5.0],
            "precipitation_probability_pct": [80],
            "precipitation_amount_status": ["horas_disponibles"],
        })
        self.assertTrue(join_forecasts_to_siar(DEMO_CASES[0], forecasts).empty)


if __name__ == "__main__":
    unittest.main()
