import unittest

import numpy as np
import pandas as pd

from src.analysis.evaluate_et0_multiyear import irrigation_impact, statistical_comparisons


class EvaluateEt0MultiyearTests(unittest.TestCase):
    def test_bootstrap_is_reproducible(self):
        frame = pd.DataFrame(
            {
                "target_et0_mm": np.linspace(1, 3, 40),
                "Persistencia": np.linspace(1, 3, 40) + 0.5,
                "Ridge": np.linspace(1, 3, 40) + 0.1,
                "Random Forest": np.linspace(1, 3, 40) + 0.2,
                "HistGradientBoosting": np.linspace(1, 3, 40) + 0.3,
                "XGBoost": np.linspace(1, 3, 40) + 0.4,
            }
        )
        first = statistical_comparisons(frame)
        second = statistical_comparisons(frame)
        pd.testing.assert_frame_equal(first, second)

    def test_irrigation_impact_applies_kc_and_precipitation_once(self):
        predictions = pd.DataFrame(
            {
                "prediction_date": pd.to_datetime(["2025-05-01"]),
                "target_et0_mm": [4.0],
                "Persistencia": [3.0],
                "Ridge": [4.0],
                "Random Forest": [4.0],
                "HistGradientBoosting": [4.0],
                "XGBoost": [4.0],
            }
        )
        crop = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-05-01"]),
                "kc": [0.5],
                "siar_etc_mm": [2.0],
                "effective_precipitation_mm": [0.5],
                "siar_net_need_mm": [1.5],
            }
        )
        _, detail = irrigation_impact(predictions, crop)
        self.assertAlmostEqual(detail.loc[0, "etc_Ridge_mm"], 2.0)
        self.assertAlmostEqual(detail.loc[0, "net_need_Ridge_mm"], 1.5)


if __name__ == "__main__":
    unittest.main()
