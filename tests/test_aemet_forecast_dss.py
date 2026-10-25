"""Contrato entre los productos municipales AEMET y el DSS."""

from datetime import date, datetime
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.dss.aemet_forecast import (
    forecast_from_payloads, prepare_live_forecast, require_current_forecast,
)
from src.data.archive_aemet_forecast import archive_forecast


def sample_payloads():
    daily = [{
        "id": "id04013", "elaborado": "2025-06-20T07:00:00",
        "prediccion": {"dia": [{
            "fecha": "2025-06-20T00:00:00",
            "probPrecipitacion": [{"periodo": "00-24", "value": 80}],
        }, {
            "fecha": "2025-06-21T00:00:00",
            "probPrecipitacion": [{"periodo": "00-24", "value": 60}],
        }]},
    }]
    hourly = [{
        "id": "04013", "elaborado": "2025-06-20T07:00:00",
        "prediccion": {"dia": [{
            "fecha": "2025-06-20T00:00:00",
            "precipitacion": [
                {"periodo": "06", "value": "10"},
                {"periodo": "08", "value": "5"},
                {"periodo": "09", "value": "7"},
            ],
        }]},
    }]
    return daily, hourly


class AemetForecastDssTests(unittest.TestCase):
    def test_sums_future_hours_and_never_treats_probability_as_mm(self):
        daily, hourly = sample_payloads()
        table = forecast_from_payloads(daily, hourly)
        self.assertEqual(table.loc[0, "precipitation_mm"], 12.0)
        self.assertEqual(table.loc[0, "precipitation_probability_pct"], 80)
        self.assertEqual(table.loc[0, "precipitation_hours_covered"], 2)
        self.assertTrue(pd.isna(table.loc[1, "precipitation_mm"]))
        self.assertEqual(table.loc[1, "precipitation_amount_status"], "solo_probabilidad_diaria")
        require_current_forecast(table, date(2025, 6, 20))
        with self.assertRaises(ValueError):
            require_current_forecast(table, date(2026, 10, 23))

    def test_rejects_mismatched_municipalities(self):
        daily, hourly = sample_payloads()
        hourly[0]["id"] = "50095"
        with self.assertRaisesRegex(ValueError, "mismo municipio"):
            forecast_from_payloads(daily, hourly)

    def test_missing_hour_does_not_become_zero_rain(self):
        daily, hourly = sample_payloads()
        hourly[0]["prediccion"]["dia"][0]["precipitacion"][1]["value"] = ""
        table = forecast_from_payloads(daily, hourly)
        self.assertTrue(pd.isna(table.loc[0, "precipitation_mm"]))
        self.assertEqual(table.loc[0, "precipitation_amount_status"], "horas_incompletas")

    def test_daily_probability_remains_available_without_hourly_product(self):
        daily, _ = sample_payloads()
        table = forecast_from_payloads(daily, [])
        self.assertEqual(len(table), 2)
        self.assertTrue(table["precipitation_mm"].isna().all())
        self.assertEqual(table["precipitation_probability_pct"].iat[0], 80)

    def test_today_only_uses_hours_remaining_at_consultation(self):
        daily, hourly = sample_payloads()
        hourly[0]["prediccion"]["dia"][0]["precipitacion"].insert(
            0, {"periodo": "07", "value": "4"}
        )
        consulted_at = datetime(2025, 6, 20, 7, 30)
        table = forecast_from_payloads(daily, hourly, consulted_at=consulted_at)
        prepared = prepare_live_forecast(
            table, target_day=date(2025, 6, 20), consulted_at=consulted_at,
        )
        self.assertEqual(prepared.loc[0, "precipitation_mm"], 12.0)
        self.assertEqual(prepared.loc[0, "precipitation_hours_covered"], 2)
        self.assertTrue(pd.isna(prepared.loc[1, "precipitation_mm"]))

    def test_live_forecast_rejects_stale_issue(self):
        daily, hourly = sample_payloads()
        table = forecast_from_payloads(daily, hourly)
        with self.assertRaisesRegex(ValueError, "no es reciente"):
            prepare_live_forecast(
                table, target_day=date(2025, 6, 21),
                consulted_at=datetime(2025, 6, 21, 8, 0),
            )

    def test_today_accepts_recent_previous_day_issue_with_future_hours(self):
        table = pd.DataFrame({
            "date": [pd.Timestamp("2026-10-25")],
            "issued_at": ["2026-10-24T20:00:00"],
            "precipitation_mm": [2.5],
            "precipitation_hours_covered": [7],
            "precipitation_amount_status": ["horas_disponibles"],
        })
        prepared = prepare_live_forecast(
            table, target_day=date(2026, 10, 25),
            consulted_at=datetime(2026, 10, 25, 10),
        )
        self.assertEqual(prepared["precipitation_mm"].iat[0], 2.5)

    def test_tomorrow_requires_complete_hourly_amount(self):
        table = pd.DataFrame({
            "date": [pd.Timestamp("2025-06-21")],
            "issued_at": ["2025-06-20T20:00:00"],
            "precipitation_mm": [3.0],
            "precipitation_hours_covered": [23],
            "precipitation_amount_status": ["horas_disponibles"],
        })
        prepared = prepare_live_forecast(
            table, target_day=date(2025, 6, 21),
            consulted_at=datetime(2025, 6, 20, 21, 0),
        )
        self.assertTrue(pd.isna(prepared["precipitation_mm"].iat[0]))
        table.loc[0, "precipitation_hours_covered"] = 24
        prepared = prepare_live_forecast(
            table, target_day=date(2025, 6, 21),
            consulted_at=datetime(2025, 6, 20, 21, 0),
        )
        self.assertEqual(prepared["precipitation_mm"].iat[0], 3.0)

    def test_ejea_daily_uses_internal_negative_id_but_hourly_confirms_requested_code(self):
        daily, hourly = sample_payloads()
        daily[0].update({"id": -15441, "nombre": "Ejea de los Caballeros"})
        hourly[0].update({"id": "50095", "nombre": "Ejea de los Caballeros"})
        table = forecast_from_payloads(daily, hourly, municipality_code="50095")
        self.assertEqual(table["municipality_code"].iat[0], "50095")
        hourly[0]["nombre"] = "Otro municipio"
        with self.assertRaisesRegex(ValueError, "mismo municipio"):
            forecast_from_payloads(daily, hourly, municipality_code="50095")

    def test_archives_issued_snapshot_without_overwriting(self):
        daily, hourly = sample_payloads()

        class Provider:
            def get_daily_municipality_forecast(self, code):
                return daily

            def get_hourly_municipality_forecast(self, code):
                return hourly

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            kwargs = {"client": Provider(), "raw_root": root / "raw", "interim_root": root / "interim"}
            paths = archive_forecast("04013", **kwargs)
            self.assertEqual(set(paths), {"daily_raw", "hourly_raw", "daily_normalized"})
            self.assertTrue(all(path.exists() for path in paths.values()))
            self.assertEqual(paths, archive_forecast("04013", **kwargs))
            daily[0]["nombre"] = "Cambio tras la emisión"
            with self.assertRaises(FileExistsError):
                archive_forecast("04013", **kwargs)


if __name__ == "__main__":
    unittest.main()
