"""La demo distingue la dosis diaria de la suma orientativa del horizonte."""

from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


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


if __name__ == "__main__":
    unittest.main()
