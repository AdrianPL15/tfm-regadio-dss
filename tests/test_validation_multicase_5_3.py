"""Pruebas del protocolo cronológico multicaso del apartado 5.3.10."""

import math
import unittest

import pandas as pd

from src.analysis.build_validation_multicase_5_3 import (
    BOOTSTRAP_SEED,
    TEST_FRACTION,
    _active_cases,
    _paired_block_bootstrap,
    evaluate_case,
)


class ValidationMulticaseTests(unittest.TestCase):
    def test_only_active_days_are_evaluated(self):
        _, comparable = evaluate_case(_active_cases()[0])
        self.assertTrue(comparable["kc"].gt(0).all())
        self.assertTrue(comparable["reference_need_mm"].notna().all())

    def test_final_fifteen_percent_is_reserved_in_order(self):
        report, comparable = evaluate_case(_active_cases()[0])
        expected_development = math.floor(len(comparable) * (1 - TEST_FRACTION))
        self.assertEqual(report["development_days"], expected_development)
        self.assertEqual(report["test_days"], len(comparable) - expected_development)
        development = comparable.loc[comparable["period"].eq("desarrollo"), "date"]
        test = comparable.loc[comparable["period"].eq("prueba"), "date"]
        self.assertLess(development.max(), test.min())

    def test_block_bootstrap_is_reproducible(self):
        frame = pd.DataFrame(
            {
                "case_id": ["caso"] * 12,
                "error_dss_mm": [0.2, -0.1, 0.3, -0.2] * 3,
                "error_persistence_mm": [0.4, -0.3, 0.5, -0.4] * 3,
            }
        )
        first = _paired_block_bootstrap(frame, replicates=250)
        second = _paired_block_bootstrap(frame, replicates=250)
        self.assertEqual(BOOTSTRAP_SEED, 42)
        self.assertEqual(first, second)
        self.assertGreater(first["observed_difference_mm_day"], 0)


if __name__ == "__main__":
    unittest.main()
