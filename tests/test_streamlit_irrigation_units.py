"""La demo distingue la dosis diaria de la suma orientativa del horizonte."""

from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from src.data.aemet_client import AEMETError


class IrrigationUnitsUiTests(unittest.TestCase):
    def test_daily_depth_volume_and_weekly_outlook_are_visible(self):
        app = AppTest.from_file(
            str(Path("src/dss/app_streamlit.py")), default_timeout=30
        ).run()
        self.assertEqual(len(app.exception), 0)
        metrics = {item.label: item.value for item in app.metric}
        self.assertIn("Dosis a aplicar", metrics)
        self.assertIn("Equivale a", metrics)
        self.assertIn("Por hectárea", metrics)
        self.assertIn("Riego acumulado estimado", metrics)
        self.assertEqual(app.slider[0].value, 7)
        self.assertTrue(metrics["Dosis a aplicar"].endswith(" mm"))
        self.assertTrue(metrics["Equivale a"].endswith(" L/m²"))
        self.assertTrue(metrics["Por hectárea"].endswith(" m³/ha"))

    def test_one_button_refreshes_siar_and_survives_aemet_failure(self):
        source = Path("data/external/siar_necesidades_coliflor_AL01_2026.csv").read_bytes()
        app = AppTest.from_file(str(Path("src/dss/app_streamlit.py")), default_timeout=30).run()
        self.assertEqual(app.button[0].label, "Actualizar fuentes y generar recomendación")
        with (
            patch("src.data.refresh_siar_crop_needs.download_csv", return_value=source),
            patch("src.data.aemet_client.AEMETClient"),
            patch("src.dss.aemet_forecast.fetch_live_forecast", side_effect=AEMETError("prueba")),
        ):
            app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("SiAR consultado" in item.value for item in app.success))
        self.assertTrue(any("AEMET no está disponible" in item.value for item in app.warning))


if __name__ == "__main__":
    unittest.main()
