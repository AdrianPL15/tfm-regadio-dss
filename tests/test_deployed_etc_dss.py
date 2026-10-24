"""Comprueba la conexión modelo ETc → lluvia prevista → dosis."""

from datetime import timedelta
import json
import unittest

import pandas as pd

from src.dss.config import DEMO_CASES, RecommendationRequest
from src.dss.data_access import load_case
from src.dss.engine import recommend
from src.dss.live_calendar import extend_recent_kc
from src.dss.predict_etc import REPORT, ModelUnavailable, predict_tomorrow_etc


class DeployedEtcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = next(case for case in DEMO_CASES if case.crop == "Coliflor")
        history, cls.metadata = load_case(cls.case)
        cls.target_day = history["date"].max().date() + timedelta(days=1)
        cls.history = extend_recent_kc(
            history, cls.metadata, target_day=cls.target_day,
            as_of=cls.target_day - timedelta(days=1),
        )

    def test_model_predicts_etc_before_rain(self):
        estimate = predict_tomorrow_etc(self.case, self.history, self.target_day)
        self.assertEqual(estimate["model"], "Ridge")
        self.assertGreater(estimate["etc_mm"], 0)
        self.assertEqual(estimate["trained_through"], "2026-10-22")
        self.assertFalse(estimate["deploy_model_for_dose"])
        self.assertEqual(estimate["steps_ahead"], 1)

    def test_missing_intermediate_days_are_comparison_only(self):
        future = self.target_day + timedelta(days=2)
        original, metadata = load_case(self.case)
        extended = extend_recent_kc(
            original, metadata, target_day=future,
            as_of=future - timedelta(days=1),
        )
        estimate = predict_tomorrow_etc(self.case, extended, future)
        self.assertEqual(estimate["steps_ahead"], 3)
        self.assertFalse(estimate["deploy_model_for_dose"])
        self.assertGreaterEqual(estimate["etc_mm"], 0)

    def test_operational_choice_uses_comparative_holdout(self):
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        for entry in report["cases"].values():
            self.assertEqual(
                entry["deploy_model_for_dose"],
                entry["test_mae_mm_day"] < entry["physical_baseline_test_mae_mm_day"],
            )
        self.assertTrue(report["cases"]["algodon_BA08"]["deploy_model_for_dose"])

    def test_aemet_rain_is_subtracted_once_after_model(self):
        estimate = predict_tomorrow_etc(self.case, self.history, self.target_day)
        forecast = pd.DataFrame({
            "date": [pd.Timestamp(self.target_day)],
            "precipitation_mm": [2.0],
            "issued_at": [pd.Timestamp(self.target_day - timedelta(days=1))],
        })
        request = RecommendationRequest(
            issue_date=self.target_day, horizon_days=1,
            rain_effective_fraction=0.5, case=self.case,
        )
        result = recommend(
            request, history=self.history, metadata=self.metadata,
            forecast=forecast, expected_errors={}, model_estimate=estimate,
        )
        row = result.daily.iloc[0]
        self.assertEqual(row["method"], "modelo_etc")
        self.assertAlmostEqual(row["base_need_before_rain_mm"], estimate["etc_mm"])
        self.assertAlmostEqual(row["effective_rain_scenario_mm"], 1.0)
        self.assertAlmostEqual(row["net_need_mm"], max(0, estimate["etc_mm"] - 1.0), places=3)
        self.assertAlmostEqual(row["gross_dose_mm"], row["net_need_mm"] / 0.9, places=3)

    def test_model_cannot_recommend_a_date_inside_its_training(self):
        with self.assertRaises(ModelUnavailable):
            predict_tomorrow_etc(
                self.case, self.history, self.target_day - timedelta(days=1)
            )


if __name__ == "__main__":
    unittest.main()
