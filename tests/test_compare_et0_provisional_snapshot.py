import unittest

import pandas as pd

from src.analysis.compare_et0_provisional_snapshot import compare_frames


class CompareEt0SnapshotTests(unittest.TestCase):
    def test_detects_revisions_and_new_dates(self):
        original = pd.DataFrame(
            {"date": ["2026-10-27"], "et0_mm": [2.0], "precipitation_mm": [0.0]}
        )
        current = pd.DataFrame(
            {
                "date": ["2026-10-27", "2026-10-28"],
                "et0_mm": [2.2, 2.1],
                "precipitation_mm": [0.0, 0.0],
            }
        )
        result = compare_frames(original, current)
        self.assertEqual(result["common_dates"], 1)
        self.assertEqual(result["only_requery_dates"], 1)
        self.assertEqual(result["changed_cells"], 1)
        self.assertAlmostEqual(
            result["columns"]["et0_mm"]["max_absolute_change"], 0.2
        )

    def test_identical_snapshots_have_no_changes(self):
        frame = pd.DataFrame({"date": ["2026-10-27"], "et0_mm": [2.0]})
        result = compare_frames(frame, frame.copy())
        self.assertEqual(result["changed_cells"], 0)


if __name__ == "__main__":
    unittest.main()
