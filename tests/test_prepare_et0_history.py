from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from src.data.prepare_et0_history import prepare_history, quality_by_year


HEADER = (
    "Fecha;Temp Media (ºC);Temp Max (ºC);Temp Mín (ºC);Hum Media (%);"
    "Vel Viento (m/s);Rad (MJ/m2);Precip (mm);ET0 (mm)\n"
)


class PrepareEt0HistoryTests(unittest.TestCase):
    def test_normalises_public_siar_csv(self):
        with TemporaryDirectory(dir=".test_tmp") as folder:
            path = Path(folder) / "sample.csv"
            path.write_text(
                HEADER + "01/01/2023;12,0;18,0;7,0;60,0;1,2;10,5;0,0;2,3\n",
                encoding="cp1252",
            )
            result = prepare_history(Path(folder))
            self.assertEqual(len(result), 1)
            self.assertAlmostEqual(float(result.iloc[0]["et0_mm"]), 2.3)
            self.assertEqual(result.iloc[0]["station_code"], "AL01")

    def test_quality_reports_missing_calendar_day(self):
        data = pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-01-01", "2023-01-03"]),
                "et0_mm": [1.0, 1.2],
                "temperature_mean_c": [10.0, 11.0],
                "humidity_mean_pct": [60.0, 61.0],
                "solar_radiation_mj_m2": [8.0, 9.0],
                "wind_speed_mean_ms": [1.0, 1.1],
                "precipitation_mm": [0.0, 0.0],
            }
        )
        quality = quality_by_year(data)
        self.assertEqual(int(quality.iloc[0]["observed_days"]), 2)
        self.assertEqual(int(quality.iloc[0]["missing_calendar_days"]), 363)

    def test_station_code_is_parameterised(self):
        with TemporaryDirectory(dir=".test_tmp") as folder:
            path = Path(folder) / "sample.csv"
            path.write_text(
                HEADER + "01/01/2023;12,0;18,0;7,0;60,0;1,2;10,5;0,0;2,3\n",
                encoding="cp1252",
            )
            result = prepare_history(Path(folder), "Z06")
            self.assertEqual(result.iloc[0]["station_code"], "Z06")


if __name__ == "__main__":
    unittest.main()
