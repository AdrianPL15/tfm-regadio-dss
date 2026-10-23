"""Contratos de las campañas SiAR 2026 y de la proyección de mañana."""

from datetime import date
import unittest

import pandas as pd

from src.dss.config import DEMO_CASES, RecommendationRequest
from src.dss.data_access import load_case
from src.dss.engine import recommend
from src.dss.live_calendar import extend_recent_kc


class Campaign2026Tests(unittest.TestCase):
    def test_all_four_official_series_are_present_and_stop_at_last_published_day(self):
        cases = [case for case in DEMO_CASES if case.campaign_year == 2026]
        self.assertEqual(len(cases), 4)
        counts = {"Pimiento": 175, "Coliflor": 144, "Maíz": 205, "Algodón": 205}
        for case in cases:
            with self.subTest(case=case.crop):
                history, metadata = load_case(case)
                self.assertEqual(len(history), counts[case.crop])
                self.assertEqual(metadata["record_count"], len(history))
                self.assertEqual(history["date"].max().date(), date(2026, 10, 22))
                self.assertEqual(metadata["last_returned_date"], "2026-10-22")
                self.assertFalse(history["date"].duplicated().any())

    def test_october_maize_and_cotton_are_not_projected_as_active_crops(self):
        for case in (case for case in DEMO_CASES if case.campaign_year == 2026 and case.crop in {"Maíz", "Algodón", "Pimiento"}):
            with self.subTest(case=case.crop):
                history, metadata = load_case(case)
                with self.assertRaises(ValueError):
                    extend_recent_kc(history, metadata, target_day=date(2026, 10, 24), as_of=date(2026, 10, 23))

    def test_coliflor_tomorrow_uses_projected_kc_and_forecast_rain(self):
        case = next(case for case in DEMO_CASES if case.campaign_year == 2026 and case.crop == "Coliflor")
        history, metadata = load_case(case)
        extended = extend_recent_kc(history, metadata, target_day=date(2026, 10, 24), as_of=date(2026, 10, 23))
        self.assertEqual(extended.iloc[-1]["record_status"], "kc_proyectado_mes")
        self.assertTrue(pd.isna(extended.iloc[-1]["et0_mm"]))
        request = RecommendationRequest(issue_date=date(2026, 10, 24), horizon_days=1, rain_effective_fraction=0.5, case=case)
        dry = recommend(request, history=extended, metadata=metadata)
        rain = pd.DataFrame({"date": ["2026-10-24"], "issued_at": ["2026-10-23T10:00:00"], "precipitation_mm": [4.0]})
        wet = recommend(request, history=extended, metadata=metadata, forecast=rain)
        self.assertAlmostEqual(dry.daily["net_need_mm"].iat[0] - wet.daily["net_need_mm"].iat[0], 2.0)
        self.assertIn("Kc futuro", wet.daily["warnings"].iat[0])


if __name__ == "__main__":
    unittest.main()
