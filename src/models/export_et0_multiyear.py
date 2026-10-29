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
        "status": "operational_controlled_with_fallback",
        "model_family": "Ridge",
        "target": "ET0 de uno a nueve días (mm/día)",
        "training_policy": "reajuste final con 2021-2025 tras evaluación externa congelada en 2025",
        "retraining_policy": (
            "reentrenamiento anual tras cerrar y auditar la campaña; no sustituir "
            "artefactos si empeoran frente a media 7 días en rolling-origin"
        ),
        "retraining_schedule": {
            "frequency": "annual",
            "trigger": "official_campaign_closed_and_audited",
            "promotion_rule": (
                "superar media 7 días en rolling-origin y conservar la puerta "
                "prospectiva de 30 casos, ventana 60 y mejora mínima del 5 %"
            ),
        },
        "prospective_gate_policy": {
            "minimum_paired_consolidated_cases": 30,
            "recent_window_cases": 60,
            "minimum_relative_mae_improvement_pct": 5.0,
            "fallback": "physical_mean_7d",
        },
        "fallback": "media de ET0 de los últimos 7 días con al menos 3 observaciones; en último término, persistencia",
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
    robustness = pd.read_csv(metrics_root / "et0_multiyear_robustness.csv")
    prediction_evidence = pd.read_csv(
        metrics_root / "et0_multiyear_robustness_predictions.csv"
    )
    comparison = robustness.pivot_table(
        index=["station_code", "test_year", "horizon_days"],
        columns="method",
        values="mae_mm_day",
        aggfunc="first",
    ).reset_index()
    comparison["approved"] = (
        comparison["Ridge completo"] < comparison["Media movil 7 dias"]
    )
    horizon_approval = comparison.groupby("horizon_days")["approved"].agg(["all", "sum", "count"])
    approved_horizons = [
        int(horizon)
        for horizon, row in horizon_approval.iterrows()
        if bool(row["all"])
    ]
    manifest["selection_policy"] = (
        "se serializa un horizonte solo si Ridge completo supera a la media móvil de 7 días "
        "en todas las combinaciones estación-año de la validación rolling-origin"
    )
    manifest["approved_horizons_days"] = approved_horizons
    manifest["selection_evidence"] = {
        str(int(horizon)): {
            "wins_vs_mean_7d": int(row["sum"]),
            "comparisons": int(row["count"]),
            "approved": bool(row["all"]),
        }
        for horizon, row in horizon_approval.iterrows()
    }
    for station in STATIONS:
        history_path = data_root / f"et0_history_{station}_2021_2025.csv"
        history = pd.read_csv(history_path)
        station_horizons: dict[str, object] = {}
        for horizon_days in approved_horizons:
            table, features = build_feature_table(history, horizon_days=horizon_days)
            training = table.dropna(subset=["target_et0_mm"]).copy()
            model = _models()["Ridge"]
            model.fit(training[features], training["target_et0_mm"])
            suffix = "" if horizon_days == 1 else f"_h{horizon_days}"
            artifact = model_dir / f"ridge_et0_{station}{suffix}.joblib"
            joblib.dump(model, artifact, compress=3)
            robustness_test = robustness[
                (robustness["station_code"] == station)
                & (robustness["test_year"] == 2025)
                & (robustness["horizon_days"] == horizon_days)
            ].set_index("method")
            ridge_mae = float(robustness_test.loc["Ridge completo", "mae_mm_day"])
            persistence_mae = float(robustness_test.loc["Persistencia", "mae_mm_day"])
            mean_7d_mae = float(
                robustness_test.loc["Media movil 7 dias", "mae_mm_day"]
            )
            residual_sample = prediction_evidence[
                (prediction_evidence["station_code"] == station)
                & (prediction_evidence["test_year"] == 2025)
                & (prediction_evidence["horizon_days"] == horizon_days)
            ].copy()
            residual = (
                residual_sample["target_et0_mm"]
                - residual_sample["ridge_full_prediction_mm"]
            )
            residual_q10, residual_q90 = residual.quantile([0.10, 0.90])
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
                "external_test_residual_interval_80_pct_mm_day": [
                    float(residual_q10), float(residual_q90)
                ],
                "external_test_residual_interval_sample_size": int(
                    residual.notna().sum()
                ),
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
