from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor

from src.dss.predict_et0 import predict_et0_with_fallback


class PredictEt0Tests(unittest.TestCase):
    def _history(self):
        return pd.DataFrame(
            {
                "date": pd.date_range("2025-01-01", periods=20, freq="D"),
                "et0_mm": np.linspace(1.0, 3.0, 20),
                "temperature_mean_c": np.linspace(10.0, 15.0, 20),
            }
        )

    def test_missing_artifact_falls_back_to_last_observation(self):
        result = predict_et0_with_fallback(
            "AL01",
            self._history(),
            date(2025, 1, 21),
            manifest_path=Path("does-not-exist.json"),
        )
        self.assertEqual(result["method"], "persistence_fallback")
        self.assertAlmostEqual(result["et0_mm"], 3.0)

    def test_stale_history_does_not_invoke_model(self):
        with TemporaryDirectory(dir=".test_tmp") as folder:
            root = Path(folder)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"stations": {"AL01": {}}}), encoding="utf-8")
            result = predict_et0_with_fallback(
                "AL01", self._history().iloc[:-1], date(2025, 1, 21),
                manifest_path=manifest, model_dir=root,
            )
            self.assertEqual(result["method"], "persistence_fallback")

    def test_valid_artifact_returns_ridge_method(self):
        with TemporaryDirectory(dir=".test_tmp") as folder:
            root = Path(folder)
            history = self._history()
            from src.models.train_et0_multiyear import build_feature_table

            table, features = build_feature_table(history)
            model = DummyRegressor(strategy="constant", constant=2.5)
            model.fit(table.iloc[:-1][features], table.iloc[:-1]["target_et0_mm"])
            artifact = root / "model.joblib"
            joblib.dump(model, artifact)
            import hashlib

            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps({"stations": {"AL01": {
                    "artifact": artifact.name,
                    "sha256": digest,
                    "feature_columns": features,
                }}}),
                encoding="utf-8",
            )
            result = predict_et0_with_fallback(
                "AL01", history, date(2025, 1, 21),
                manifest_path=manifest, model_dir=root,
            )
            self.assertEqual(result["method"], "ridge_et0_multiyear")
            self.assertAlmostEqual(result["et0_mm"], 2.5)


if __name__ == "__main__":
    unittest.main()
