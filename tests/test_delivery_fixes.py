"""Regresiones de abstención, separación temporal y avisos de disponibilidad."""
from datetime import date
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from src.dss.config import RecommendationRequest
from src.dss.engine import recommend
from src.dss.predict_et0 import predict_et0_with_fallback
from src.analysis.build_validation_5_3 import TEST_START, horizon_errors, window_selection
from src.dss.data_access import load_case
from src.dss.config import CropCase
from src.dss.consultation_status import availability_notice


class DeliveryFixTests(unittest.TestCase):
    def history(self):
        return pd.DataFrame({
            "date": pd.date_range("2026-10-01", "2026-10-21"),
            "et0_mm": [5.] + [np.nan] * 20, "kc": 1.,
            "net_need_mm": [5.] + [np.nan] * 20, "pe_mm": 0.,
        })

    def test_old_et0_cannot_produce_a_dose(self):
        result = recommend(RecommendationRequest(issue_date=date(2026, 10, 20)),
                           history=self.history(), expected_errors={})
        self.assertEqual(result.daily["method"].iat[0], "sin_recomendacion")
        self.assertTrue(pd.isna(result.daily["gross_dose_mm"].iat[0]))

    def test_selector_abstention_survives_to_the_final_dose(self):
        h = self.history()
        h.loc[18, "et0_mm"] = 9.  # otra fuente local no debe reemplazar al selector
        selector = predict_et0_with_fallback(
            "AL01", self.history().iloc[:1], date(2026, 10, 20),
            manifest_path=Path("missing-manifest.json"), monitoring_path=None,
        )
        result = recommend(RecommendationRequest(issue_date=date(2026, 10, 20)),
                           history=h, expected_errors={},
                           et0_predictions={"2026-10-20": selector})
        self.assertTrue(pd.isna(result.daily["gross_dose_mm"].iat[0]))

    def test_fallback_value_and_missing_horizon_are_preserved(self):
        h = self.history()
        h.loc[18, "et0_mm"] = 9.
        result = recommend(RecommendationRequest(issue_date=date(2026, 10, 20), horizon_days=2),
            history=h, expected_errors={}, et0_predictions={"2026-10-20": {
                "method": "mean_7d_fallback", "et0_mm": 2., "fallback_reason": "faltan entradas",
            }})
        self.assertEqual(result.daily["net_need_mm"].iat[0], 2.)
        self.assertEqual(result.daily["et0_origin"].iat[0], "mean_7d_fallback")
        self.assertTrue(pd.isna(result.daily["gross_dose_mm"].iat[1]))

    def test_zero_kc_is_not_presented_as_a_zero_irrigation_dose(self):
        h = self.history()
        h.loc[18, "et0_mm"] = 5.
        h.loc[19, "kc"] = 0.
        result = recommend(RecommendationRequest(issue_date=date(2026, 10, 20)),
                           history=h, expected_errors={})
        self.assertEqual(result.daily["method"].iat[0], "sin_recomendacion")

    def test_window_selection_ignores_test_targets_from_earlier_issues(self):
        h, _ = load_case(CropCase())
        altered = h.copy()
        altered.loc[altered["date"].ge(TEST_START), "net_need_mm"] = 1000.
        pd.testing.assert_series_equal(window_selection(h)["desarrollo"],
                                       window_selection(altered)["desarrollo"])

    def test_out_of_cycle_notice_names_the_selected_day(self):
        h = self.history()
        h.loc[19, "kc"] = 0.
        notice = availability_notice(h, {"active_months": [10]},
            issue=date(2026, 10, 20), today=date(2026, 10, 20), planning=True, live_case=True)
        self.assertIn("20/10/2026", notice)
        self.assertIn("No hay dosis", notice)

    def test_partial_horizon_is_announced(self):
        notice = availability_notice(self.history(), {"active_months": [10]},
            issue=date(2026, 10, 30), today=date(2026, 10, 30),
            planning=True, live_case=True, horizon=7)
        self.assertIn("los demás quedarán sin dosis", notice)
