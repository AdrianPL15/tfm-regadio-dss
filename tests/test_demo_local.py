"""El entregable visual debe usar exactamente el motor del piloto."""

import unittest

from scripts.demo_local import calculate


class LocalDemoTests(unittest.TestCase):
    def test_example_matches_chapter_five(self):
        result = calculate({
            "fecha": ["2025-06-28"], "horizonte": ["7"],
            "sistema": ["goteo"], "eficiencia": ["0.90"],
            "superficie": ["1.5"],
        })
        self.assertEqual(result["summary"]["net_need_total_mm"], 38.96)
        self.assertEqual(result["summary"]["gross_dose_total_mm"], 43.29)
        self.assertEqual(len(result["daily"]), 7)

    def test_invalid_date_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "fecha"):
            calculate({"fecha": ["2026-06-28"]})


if __name__ == "__main__":
    unittest.main()
