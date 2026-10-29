from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from src.analysis.audit_et0_availability import build_inventory


class AuditEt0AvailabilityTests(unittest.TestCase):
    def test_station_weather_requires_three_years(self):
        with TemporaryDirectory(dir=".test_tmp") as folder:
            path = Path(folder) / "weather.csv"
            pd.DataFrame(
                {
                    "station_code": ["AL01"] * 3,
                    "observed_date": ["2023-01-01", "2024-01-01", "2025-01-01"],
                    "et0_pm_mm": [1.0, 1.1, 1.2],
                }
            ).to_csv(path, index=False)
            result = build_inventory(path, Path(folder) / "missing")
            self.assertEqual(int(result.iloc[0]["year_count"]), 3)
            self.assertTrue(bool(result.iloc[0]["multiyear_full_weather_candidate"]))

    def test_current_single_year_weather_is_not_eligible(self):
        result = build_inventory(
            Path("data/interim/siar_weather_daily.csv"), Path("data/external")
        )
        weather = result[result["source_type"] == "station_weather"].iloc[0]
        self.assertEqual(weather["station_code"], "AL01")
        self.assertEqual(int(weather["year_count"]), 1)
        self.assertFalse(bool(weather["multiyear_full_weather_candidate"]))


if __name__ == "__main__":
    unittest.main()
