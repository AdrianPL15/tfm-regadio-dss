"""Reentrena y versiona Ridge ET0 después de la evaluación externa de 2025.

Los artefactos permanecen aislados del DSS estable hasta que se apruebe su
integración. Se ajustan con 2021-2025 completos; las métricas declaradas en el
manifiesto proceden exclusivamente de la prueba externa previa de 2025.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd

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
        "target": "ET0 del día siguiente (mm/día)",
        "training_policy": "reajuste final con 2021-2025 tras evaluación externa congelada en 2025",
        "fallback": "persistencia de la última ET0 observada",
        "stations": {},
    }
    for station in STATIONS:
        history_path = data_root / f"et0_history_{station}_2021_2025.csv"
        metrics_name = "et0_multiyear_metrics.csv" if station == "AL01" else f"et0_multiyear_metrics_{station}.csv"
        metrics = pd.read_csv(metrics_root / metrics_name)
        history = pd.read_csv(history_path)
        table, features = build_feature_table(history)
        training = table.dropna(subset=["target_et0_mm"]).copy()
        model = _models()["Ridge"]
        model.fit(training[features], training["target_et0_mm"])
        artifact = model_dir / f"ridge_et0_{station}.joblib"
        joblib.dump(model, artifact, compress=3)
        test = metrics[(metrics["phase"] == "test_2025") & metrics["model"].isin(["Ridge", "Persistencia"])].set_index("model")
        manifest["stations"][station] = {
            "artifact": artifact.name,
            "sha256": _sha256(artifact),
            "feature_columns": features,
            "trained_from": pd.to_datetime(training["prediction_date"]).min().date().isoformat(),
            "trained_through": pd.to_datetime(training["prediction_date"]).max().date().isoformat(),
            "training_rows": int(len(training)),
            "external_test_year": 2025,
            "external_test_ridge_mae_mm_day": float(test.loc["Ridge", "mae_mm"]),
            "external_test_persistence_mae_mm_day": float(test.loc["Persistencia", "mae_mm"]),
        }
    manifest_path = model_dir / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = export_models()
    for station, entry in result["stations"].items():
        print(f"{station}: {entry['artifact']} ({entry['training_rows']} filas)")
