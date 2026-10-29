from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from src.dss.et0_prospective import record_prediction, validate_log


class Et0ProspectiveTests(unittest.TestCase):
    def _prediction(self):
        return {
            "station_code": "AL01",
            "target_date": "2026-10-29",
            "horizon_days": 2,
            "et0_mm": 2.5,
            "method": "ridge_et0_multiyear_h2",
            "baseline_mean_7d_mm": 2.2,
            "baseline_persistence_mm": 2.1,
            "artifact": "ridge.joblib",
            "artifact_sha256": "abc",
        }

    def test_record_is_idempotent_and_validation_closes_it(self):
        with TemporaryDirectory(dir=".test_tmp") as folder:
            root = Path(folder)
            log = root / "predictions.csv"
            summary = root / "summary.json"
            stamp = datetime(2026, 10, 27, tzinfo=timezone.utc)
            self.assertTrue(record_prediction(self._prediction(), log_path=log, issued_at=stamp))
            self.assertFalse(record_prediction(self._prediction(), log_path=log, issued_at=stamp))
            actuals = pd.DataFrame({
                "date": ["2026-10-29"], "station_code": ["AL01"], "et0_mm": [2.4]
            })
            result = validate_log(actuals, log_path=log, summary_path=summary)
            self.assertEqual(result["validated"], 1)
            self.assertAlmostEqual(result["ridge_mae_mm_day"], 0.1)

    def test_fallback_is_not_recorded(self):
        with TemporaryDirectory(dir=".test_tmp") as folder:
            log = Path(folder) / "predictions.csv"
            self.assertFalse(record_prediction(
                {"method": "mean_7d_fallback"}, log_path=log
            ))
            self.assertFalse(log.exists())


if __name__ == "__main__":
    unittest.main()
