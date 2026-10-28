"""Reentrena y versiona Ridge ET0 después de la evaluación externa de 2025.

Los artefactos permanecen aislados del DSS estable hasta que se apruebe su
integración. Se ajustan con 2021-2025 completos; las métricas declaradas en el
manifiesto proceden exclusivamente de la prueba externa previa de 2025.
"""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from src.models.train_et0_multiyear import _models, build_feature_table


ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models/experimental_et0_multiyear"
MANIFEST = MODEL_DIR / "manifest.json"
STATIONS = ("AL01", "Z06", "BA08")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_models(
    data_root: Path = ROOT / "data/interim",
    metrics_root: Path = ROOT / "docs/data_samples",
    model_dir: Path = MODEL_DIR,
) -> dict:
    model_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "status": "experimental_not_deployed",
        "model_family": "Ridge",
        "target": "ET0 a uno o dos días (mm/día)",
        "training_policy": "reajuste final con 2021-2025 tras evaluación externa congelada en 2025",
        "fallback": "persistencia de la última ET0 observada",
        "exported_at": date.today().isoformat(),
        "runtime_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
        "stations": {},
    }
    for station in STATIONS:
        history_path = data_root / f"et0_history_{station}_2021_2025.csv"
        metrics_name = "et0_multiyear_metrics.csv" if station == "AL01" else f"et0_multiyear_metrics_{station}.csv"
        metrics = pd.read_csv(metrics_root / metrics_name)
        history = pd.read_csv(history_path)
        robustness = pd.read_csv(metrics_root / "et0_multiyear_robustness.csv")
        station_horizons: dict[str, object] = {}
        for horizon_days in (1, 2):
            table, features = build_feature_table(history, horizon_days=horizon_days)
            training = table.dropna(subset=["target_et0_mm"]).copy()
            model = _models()["Ridge"]
            model.fit(training[features], training["target_et0_mm"])
            suffix = "" if horizon_days == 1 else f"_h{horizon_days}"
            artifact = model_dir / f"ridge_et0_{station}{suffix}.joblib"
            joblib.dump(model, artifact, compress=3)
            if horizon_days == 1:
                test = metrics[
                    (metrics["phase"] == "test_2025")
                    & metrics["model"].isin(["Ridge", "Persistencia"])
                ].set_index("model")
                ridge_mae = float(test.loc["Ridge", "mae_mm"])
                persistence_mae = float(test.loc["Persistencia", "mae_mm"])
            else:
                test = robustness[
                    (robustness["station_code"] == station)
                    & (robustness["test_year"] == 2025)
                    & (robustness["horizon_days"] == horizon_days)
                ].set_index("method")
                ridge_mae = float(test.loc["Ridge completo", "mae_mm_day"])
                persistence_mae = float(test.loc["Persistencia", "mae_mm_day"])
            robustness_test = robustness[
                (robustness["station_code"] == station)
                & (robustness["test_year"] == 2025)
                & (robustness["horizon_days"] == horizon_days)
            ].set_index("method")
            mean_7d_mae = float(
                robustness_test.loc["Media movil 7 dias", "mae_mm_day"]
            )
            station_horizons[str(horizon_days)] = {
                "artifact": artifact.name,
                "sha256": _sha256(artifact),
                "feature_columns": features,
                "horizon_days": horizon_days,
                "trained_from": pd.to_datetime(training["prediction_date"]).min().date().isoformat(),
                "trained_through": pd.to_datetime(training["prediction_date"]).max().date().isoformat(),
                "training_rows": int(len(training)),
                "external_test_year": 2025,
                "external_test_ridge_mae_mm_day": ridge_mae,
                "external_test_persistence_mae_mm_day": persistence_mae,
                "external_test_mean_7d_mae_mm_day": mean_7d_mae,
            }
        manifest["stations"][station] = {"horizons": station_horizons}
    manifest_path = model_dir / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = export_models()
    for station, entry in result["stations"].items():
        artifacts = ", ".join(
            f"h={horizon}: {details['artifact']}"
            for horizon, details in entry["horizons"].items()
        )
        print(f"{station}: {artifacts}")
