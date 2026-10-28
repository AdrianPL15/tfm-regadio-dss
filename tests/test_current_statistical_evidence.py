"""Pruebas de la ampliación estadística de los capítulos 4 y 5."""

import unittest

import numpy as np

from src.analysis.build_current_statistical_evidence import paired_block_bootstrap


class CurrentStatisticalEvidenceTests(unittest.TestCase):
    def test_bootstrap_is_reproducible(self):
        reference = np.array([0.5, 0.4, 0.6, 0.7, 0.3, 0.4, 0.5, 0.6])
        candidate = np.array([0.4, 0.3, 0.5, 0.5, 0.2, 0.3, 0.4, 0.4])
        first = paired_block_bootstrap(reference, candidate, replicates=200, seed=42)
        second = paired_block_bootstrap(reference, candidate, replicates=200, seed=42)
        self.assertEqual(first, second)

    def test_positive_difference_favours_candidate(self):
        result = paired_block_bootstrap(
            [1.0] * 10, [0.5] * 10, replicates=200, block_days=3, seed=42
        )
        self.assertEqual(result["observed_difference_mm_day"], 0.5)
        self.assertGreater(result["ci_95_lower_mm_day"], 0)

    def test_requires_paired_valid_values(self):
        with self.assertRaises(ValueError):
            paired_block_bootstrap([np.nan], [np.nan], replicates=10)


if __name__ == "__main__":
    unittest.main()
