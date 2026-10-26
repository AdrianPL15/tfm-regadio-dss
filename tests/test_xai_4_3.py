import numpy as np
import unittest

from src.analysis.build_xai_4_3 import FEATURE_COLUMNS, summarize_importance


class XaiSummaryTests(unittest.TestCase):
    def test_summarize_importance_orders_features_and_normalizes_share(self):
        values = np.zeros((4, len(FEATURE_COLUMNS)), dtype=float)
        values[:, 0] = [1.0, -1.0, 1.0, -1.0]
        values[:, 1] = [0.5, -0.5, 0.5, -0.5]

        summary = summarize_importance("random_forest", values)

        self.assertEqual(summary.iloc[0]["feature"], FEATURE_COLUMNS[0])
        self.assertEqual(summary.iloc[1]["feature"], FEATURE_COLUMNS[1])
        self.assertAlmostEqual(summary["importance_share_pct"].sum(), 100.0)
        self.assertEqual(summary.iloc[0]["mean_signed_shap_mm"], 0.0)


if __name__ == "__main__":
    unittest.main()
