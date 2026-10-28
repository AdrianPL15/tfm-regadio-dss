from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor

from src.dss.predict_et0 import (
    history_from_siar_records,
    predict_et0_with_fallback,
    predict_live_et0,
)
from src.models.train_et0_multiyear import WEATHER_CURRENT


class PredictEt0Tests(unittest.TestCase):
    def _history(self):
        data = {
            "date": pd.date_range("2025-01-01", periods=20, freq="D"),
            "et0_mm": np.linspace(1.0, 3.0, 20),
        }
        for index, column in enumerate(WEATHER_CURRENT):
            data[column] = np.linspace(10.0 + index, 15.0 + index, 20)
        return pd.DataFrame(data)

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

    def test_missing_operational_columns_force_fallback(self):
        history = self._history()[["date", "et0_mm"]]
        with TemporaryDirectory(dir=".test_tmp") as folder:
            root = Path(folder)
            artifact = root / "model.joblib"
            joblib.dump(DummyRegressor(strategy="mean"), artifact)
            import hashlib
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"stations": {"AL01": {
                "artifact": artifact.name, "sha256": digest,
                "feature_columns": [
                    "et0_lag_1d", "et0_lag_2d", "et0_lag_3d",
                    "temperature_mean_c_lag_1d",
                ],
            }}}), encoding="utf-8")
            result = predict_et0_with_fallback(
                "AL01", history, date(2025, 1, 21),
                manifest_path=manifest, model_dir=root,
            )
            self.assertEqual(result["method"], "persistence_fallback")
            self.assertIn("faltan columnas", result["fallback_reason"])

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

    def test_siar_adapter_produces_training_schema(self):
        record = {
            "Fecha": "2026-10-28T00:00:00", "Estacion": "AL01",
            "TempMedia": 20, "TempMax": 25, "TempMin": 15,
            "HumedadMedia": 60, "HumedadMax": 80, "humedadMin": 40,
            "VelViento": 1.2, "VelVientoMax": 4.0, "Radiacion": 18,
            "Precipitacion": 0, "EtPMon": 3.2, "PePMon": 0,
        }
        history = history_from_siar_records([record], "AL01")
        self.assertEqual(history.loc[0, "station_code"], "AL01")
        self.assertAlmostEqual(history.loc[0, "et0_mm"], 3.2)
        self.assertIn("solar_radiation_mj_m2", history.columns)

    def test_live_extractor_failure_uses_crop_history_persistence(self):
        class FailingSource:
            def get_data(self, *args, **kwargs):
                raise ValueError("servicio no disponible")

        result = predict_live_et0(
            "AL01", date(2025, 1, 21), client=FailingSource(),
            fallback_history=self._history(),
        )
        self.assertEqual(result["method"], "persistence_fallback")
        self.assertIn("fallo del extractor", result["fallback_reason"])


if __name__ == "__main__":
    unittest.main()
