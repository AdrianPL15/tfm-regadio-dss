"""Pruebas de normalización de las tablas interim."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.data.transform_interim import (
    _calendar_gaps,
    _select_crop_needs_file,
    _load_siar_weather,
    _validate_case_alignment,
    normalize_aemet_daily,
    normalize_aemet_hourly,
    normalize_siar_crop_needs,
    normalize_siar_daily,
)


class TransformInterimTests(unittest.TestCase):
    def test_rejects_incompatible_station_or_campaign(self):
        weather = [{"station_code": "AL01", "observed_date": "2025-05-01"}]
        crop = [{"station_code": "AL02", "observed_date": "2025-05-01"}]
        with self.assertRaisesRegex(ValueError, "estación"):
            _validate_case_alignment(weather, crop)
        crop[0]["station_code"] = "AL01"
        crop[0]["observed_date"] = "2024-05-01"
        with self.assertRaisesRegex(ValueError, "fechas"):
            _validate_case_alignment(weather, crop)

    def test_siar_raw_selection_requires_explicit_choice_when_ambiguous(self):
        with TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            root = Path(folder)
            first = root / "siar/weather/daily/station=AL01/first.json"
            second = root / "siar/weather/daily/station=AL02/second.json"
            for path in (first, second):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{"data": []}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "--siar-weather-file"):
                _load_siar_weather(root, None)
            document, selected = _load_siar_weather(root, first)
            self.assertEqual(document["data"], [])
            self.assertEqual(selected, first)

    def test_crop_csv_selection_requires_explicit_choice_when_ambiguous(self):
        with TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            root = Path(folder)
            first = root / "siar_necesidades_pimiento_AL01_2025.csv"
            second = root / "siar_necesidades_tomate_AL01_2025.csv"
            for path in (first, second):
                path.write_text("Fecha;Kc\n", encoding="utf-8")
                path.with_suffix(".metadata.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "varios CSV"):
                _select_crop_needs_file(root, None)
            self.assertEqual(_select_crop_needs_file(root, first), first)

    def test_crop_csv_selection_checks_metadata(self):
        with TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            path = Path(folder) / "siar_necesidades_pimiento_AL01_2025.csv"
            path.write_text("Fecha;Kc\n", encoding="utf-8")
            with self.assertRaisesRegex(FileNotFoundError, "metadatos"):
                _select_crop_needs_file(path.parent, path)

    def test_detects_missing_calendar_dates(self):
        rows = [
            {"observed_date": "2025-07-17"},
            {"observed_date": "2025-07-21"},
        ]
        self.assertEqual(
            _calendar_gaps(rows),
            ["2025-07-18", "2025-07-19", "2025-07-20"],
        )

    def test_normalizes_crop_water_needs_and_flags_missing_weather(self):
        rows = normalize_siar_crop_needs(
            [
                {
                    "Fecha": "01/05/2025",
                    "Kc": "0,50",
                    "ET0 (mm)": "4,72",
                    "ETc (mm)": "2,36",
                    "Pe (mm)": "0,00",
                    "ETc - Pe (mm)": "2,36",
                },
                {
                    "Fecha": "21/07/2025",
                    "Kc": "0,90",
                    "ET0 (mm)": "",
                    "ETc (mm)": "",
                    "Pe (mm)": "",
                    "ETc - Pe (mm)": "",
                },
            ],
            metadata={
                "station_code": "AL01",
                "station_name": "La Mojonera",
                "region": "Dalias",
                "crop": "Pimiento",
                "retrieved_at": "2026-09-24",
            },
            source_file="needs.csv",
        )

        self.assertEqual(rows[0]["observed_date"], "2025-05-01")
        self.assertEqual(rows[0]["quality_status"], "PASS")
        self.assertEqual(rows[0]["net_irrigation_need_mm"], 2.36)
        self.assertEqual(rows[1]["quality_status"], "WARN")
        self.assertIn("missing:et0_mm", rows[1]["quality_issues"])

    def test_normalizes_siar_and_checks_temperature_order(self):
        rows = normalize_siar_daily(
            [
                {
                    "Fecha": "2026-09-23T00:00:00",
                    "Estacion": "AL01",
                    "TempMedia": 21.1,
                    "TempMax": 26.3,
                    "TempMin": 17.3,
                    "HumedadMedia": 62.4,
                    "HumedadMax": 90,
                    "humedadMin": 40,
                    "VelViento": 0.6,
                    "VelVientoMax": 3.2,
                    "Radiacion": 21.7,
                    "Precipitacion": 0,
                    "EtPMon": 3.47,
                    "PePMon": 0,
                }
            ],
            ingested_at="2026-09-24T08:00:00+00:00",
            source_file="raw.json",
        )
        self.assertEqual(rows[0]["observed_date"], "2026-09-23")
        self.assertEqual(rows[0]["et0_pm_mm"], 3.47)
        self.assertEqual(rows[0]["quality_status"], "PASS")

    def test_normalizes_daily_code_and_horizon(self):
        payload = [
            {
                "id": "4013",
                "nombre": "Almería",
                "elaborado": "2026-09-24T07:19:08",
                "prediccion": {
                    "dia": [
                        {
                            "fecha": "2026-09-25T00:00:00",
                            "temperatura": {"minima": 20, "maxima": 29},
                            "humedadRelativa": {"minima": 40, "maxima": 90},
                            "probPrecipitacion": [{"periodo": "00-24", "value": 25}],
                            "estadoCielo": [{"periodo": "00-24", "value": "12", "descripcion": "Poco nuboso"}],
                            "viento": [{"periodo": "00-24", "direccion": "S", "velocidad": 15}],
                            "rachaMax": [{"periodo": "00-24", "value": 30}],
                        }
                    ]
                },
            }
        ]
        rows = normalize_aemet_daily(
            payload, ingested_at="2026-09-24T08:00:00+00:00", source_file="raw.json"
        )
        self.assertEqual(rows[0]["municipality_code"], "04013")
        self.assertEqual(rows[0]["horizon_days"], 1)
        self.assertEqual(rows[0]["precipitation_probability_max_pct"], 25)
        self.assertEqual(rows[0]["quality_status"], "PASS")

    def test_flattens_hourly_wind_gust_and_probabilities(self):
        payload = [
            {
                "id": "04013",
                "nombre": "Almería",
                "elaborado": "2026-09-24T07:00:00",
                "prediccion": {
                    "dia": [
                        {
                            "fecha": "2026-09-24T00:00:00",
                            "precipitacion": [{"periodo": "08", "value": "0"}],
                            "temperatura": [{"periodo": "08", "value": "22"}],
                            "humedadRelativa": [{"periodo": "08", "value": "47"}],
                            "probPrecipitacion": [{"periodo": "0814", "value": "10"}],
                            "probTormenta": [{"periodo": "0814", "value": "0"}],
                            "estadoCielo": [{"periodo": "08", "value": "12", "descripcion": "Poco nuboso"}],
                            "vientoAndRachaMax": [
                                {"periodo": "08", "direccion": ["N"], "velocidad": ["5"]},
                                {"periodo": "08", "value": "7"},
                            ],
                        }
                    ]
                },
            }
        ]
        rows = normalize_aemet_hourly(
            payload, ingested_at="2026-09-24T08:00:00+00:00", source_file="raw.json"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["precipitation_probability_pct"], 10)
        self.assertEqual(rows[0]["wind_direction"], "N")
        self.assertEqual(rows[0]["gust_kmh"], 7)
        self.assertEqual(rows[0]["quality_status"], "PASS")


if __name__ == "__main__":
    unittest.main()
