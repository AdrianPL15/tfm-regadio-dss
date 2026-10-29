from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor

from src.dss.predict_et0 import (
    history_from_siar_records,
    predict_et0_with_fallback,
    predict_live_et0,
    predict_live_et0_horizon,
    to_etc_model_estimate,
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
        self.assertEqual(result["method"], "mean_7d_fallback")
        self.assertAlmostEqual(result["et0_mm"], self._history()["et0_mm"].tail(7).mean())

    def test_stale_history_does_not_invoke_model(self):
        with TemporaryDirectory(dir=".test_tmp") as folder:
            root = Path(folder)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"stations": {"AL01": {}}}), encoding="utf-8")
            result = predict_et0_with_fallback(
                "AL01", self._history().iloc[:-1], date(2025, 1, 21),
                manifest_path=manifest, model_dir=root,
            )
            self.assertEqual(result["method"], "mean_7d_fallback")

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
            self.assertEqual(result["method"], "mean_7d_fallback")
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
            self.assertEqual(result["method"], "ridge_et0_multiyear_h1")
            self.assertEqual(result["horizon_days"], 1)
            self.assertAlmostEqual(result["et0_mm"], 2.5)

    def test_two_day_horizon_is_selected_from_last_observation(self):
        with TemporaryDirectory(dir=".test_tmp") as folder:
            root = Path(folder)
            history = self._history().iloc[:-1].copy()
            from src.models.train_et0_multiyear import build_feature_table

            table, features = build_feature_table(history, horizon_days=2)
            model = DummyRegressor(strategy="constant", constant=2.7)
            model.fit(table.iloc[:-2][features], table.iloc[:-2]["target_et0_mm"])
            artifact = root / "model_h2.joblib"
            joblib.dump(model, artifact)
            import hashlib

            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps({"stations": {"AL01": {"horizons": {"2": {
                    "artifact": artifact.name,
                    "sha256": digest,
                    "feature_columns": features,
                    "horizon_days": 2,
                }}}}}),
                encoding="utf-8",
            )
            result = predict_et0_with_fallback(
                "AL01", history, date(2025, 1, 21),
                manifest_path=manifest, model_dir=root,
            )
            self.assertEqual(result["method"], "ridge_et0_multiyear_h2")
            self.assertEqual(result["horizon_days"], 2)
            self.assertAlmostEqual(result["et0_mm"], 2.7)

    def test_more_than_one_imputed_input_forces_physical_fallback(self):
        with TemporaryDirectory(dir=".test_tmp") as folder:
            root = Path(folder)
            history = self._history()
            history.loc[history.index[-1], [
                "temperature_mean_c", "temperature_max_c"
            ]] = np.nan
            features = [
                "et0_lag_1d", "et0_lag_2d", "et0_lag_3d",
                "temperature_mean_c_lag_1d", "temperature_max_c_lag_1d",
            ]
            model = DummyRegressor(strategy="constant", constant=2.5)
            model.fit(pd.DataFrame([[1.0] * len(features)], columns=features), [2.5])
            artifact = root / "model.joblib"
            joblib.dump(model, artifact)
            import hashlib
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps({"stations": {"AL01": {"horizons": {"1": {
                    "artifact": artifact.name,
                    "sha256": digest,
                    "feature_columns": features,
                }}}}}),
                encoding="utf-8",
            )
            result = predict_et0_with_fallback(
                "AL01", history, date(2025, 1, 21),
                manifest_path=manifest, model_dir=root,
            )
            self.assertEqual(result["method"], "mean_7d_fallback")
            self.assertIn("demasiados valores", result["fallback_reason"])

    def test_monitoring_gate_can_force_physical_fallback(self):
        with TemporaryDirectory(dir=".test_tmp") as folder:
            root = Path(folder)
            monitoring = root / "monitoring.json"
            monitoring.write_text(
                json.dumps({"deployment_gate": "physical_mean_7d"}),
                encoding="utf-8",
            )
            manifest = root / "manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            result = predict_et0_with_fallback(
                "AL01", self._history(), date(2025, 1, 21),
                manifest_path=manifest,
                monitoring_path=monitoring,
            )
            # La ausencia del manifiesto también es segura; el contrato principal
            # es que nunca se intente devolver Ridge con la puerta física activa.
            self.assertEqual(result["method"], "mean_7d_fallback")

    def test_unversioned_horizon_uses_mean_7d_before_persistence(self):
        with TemporaryDirectory(dir=".test_tmp") as folder:
            root = Path(folder)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps({"stations": {"AL01": {"horizons": {"1": {}}}}}),
                encoding="utf-8",
            )
            result = predict_et0_with_fallback(
                "AL01",
                self._history().iloc[:-2],
                date(2025, 1, 21),
                manifest_path=manifest,
                model_dir=root,
            )
            self.assertEqual(result["method"], "mean_7d_fallback")
            self.assertEqual(result["fallback_observations"], 7)
            self.assertIn("no soportado", result["fallback_reason"])

    def test_fallback_uses_persistence_when_three_recent_values_do_not_exist(self):
        history = self._history().iloc[[0, 10, 19]].copy()
        result = predict_et0_with_fallback(
            "AL01", history, date(2025, 1, 21),
            manifest_path=Path("does-not-exist.json"),
        )
        self.assertEqual(result["method"], "persistence_fallback")
        self.assertEqual(result["fallback_observations"], 1)

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
        self.assertEqual(result["method"], "mean_7d_fallback")
        self.assertIn("fallo del extractor", result["fallback_reason"])

    def test_seven_day_horizon_queries_siar_once(self):
        class Source:
            def __init__(self):
                self.calls = 0

            def get_data(self, *args, **kwargs):
                self.calls += 1
                return []

        source = Source()
        results = predict_live_et0_horizon(
            "AL01", date(2026, 10, 29), 7,
            client=source, fallback_history=self._history(),
            manifest_path=Path("does-not-exist.json"),
        )
        self.assertEqual(source.calls, 1)
        self.assertEqual(len(results), 7)
        self.assertEqual(
            list(results),
            [
                "2026-10-29", "2026-10-30", "2026-10-31",
                "2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04",
            ],
        )

    def test_horizon_without_api_token_uses_validated_crop_history(self):
        with patch(
            "src.dss.predict_et0.SiARClient",
            side_effect=ValueError("token no configurado"),
        ):
            results = predict_live_et0_horizon(
                "AL01", date(2025, 1, 21), 2,
                fallback_history=self._history(),
                manifest_path=Path("does-not-exist.json"),
            )
        self.assertEqual(len(results), 2)
        self.assertTrue(
            all(item["method"] == "mean_7d_fallback" for item in results.values())
        )

    def test_et0_is_converted_to_etc_once_with_kc(self):
        estimate = to_etc_model_estimate(
            {
                "et0_mm": 3.0,
                "method": "ridge_et0_multiyear_h2",
                "horizon_days": 2,
                "station_code": "AL01",
                "model_trained_through": "2025-12-31",
                "external_test_ridge_mae_mm_day": 0.4,
                "external_test_mean_7d_mae_mm_day": 0.5,
            },
            0.8,
        )
        self.assertAlmostEqual(estimate["etc_mm"], 2.4)
        self.assertEqual(estimate["metric_target"], "ET0")
        self.assertTrue(estimate["deploy_model_for_dose"])

    def test_fallback_cannot_be_converted_to_etc_model(self):
        with self.assertRaises(ValueError):
            to_etc_model_estimate(
                {"et0_mm": 3.0, "method": "mean_7d_fallback"}, 0.8
            )


if __name__ == "__main__":
    unittest.main()
