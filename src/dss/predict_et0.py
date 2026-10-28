"""Inferencia experimental de ET0 con respaldo explícito a persistencia."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.models.train_et0_multiyear import build_feature_table


ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models/experimental_et0_multiyear"
MANIFEST = MODEL_DIR / "manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _persistence(history: pd.DataFrame, target_day: date, reason: str) -> dict:
    known = history.loc[pd.to_datetime(history["date"]).dt.date < target_day].copy()
    values = pd.to_numeric(known.get("et0_mm"), errors="coerce").dropna()
    if values.empty:
        return {"et0_mm": None, "method": "unavailable", "fallback_reason": reason}
    return {
        "et0_mm": float(max(0.0, values.iloc[-1])),
        "method": "persistence_fallback",
        "fallback_reason": reason,
    }


def predict_et0_with_fallback(
    station_code: str,
    history: pd.DataFrame,
    target_day: date,
    *,
    manifest_path: Path = MANIFEST,
    model_dir: Path = MODEL_DIR,
) -> dict:
    """Predice ET0 para mañana o devuelve persistencia con causa trazable."""

    station_code = station_code.upper()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = manifest["stations"][station_code]
        artifact = model_dir / entry["artifact"]
        if artifact.parent.resolve() != model_dir.resolve() or not artifact.is_file():
            raise ValueError("artefacto ausente o ruta no válida")
        if _sha256(artifact) != entry["sha256"]:
            raise ValueError("la huella del artefacto no coincide")

        data = history.copy()
        data["date"] = pd.to_datetime(data["date"], errors="raise")
        data = data.loc[data["date"].dt.date < target_day].sort_values("date")
        if data.empty or data["date"].max().date() != target_day - timedelta(days=1):
            raise ValueError("no existe observación del día inmediatamente anterior")
        table, available_features = build_feature_table(data)
        row = table.loc[table["prediction_date"].dt.date.eq(target_day)]
        if len(row) != 1:
            raise ValueError("no se pudo construir una única fila de inferencia")
        features = list(entry["feature_columns"])
        feature_frame = row.reindex(columns=features)
        et0_lags = [name for name in features if name.startswith("et0_lag_")]
        if feature_frame[et0_lags].notna().sum(axis=1).iat[0] < 3:
            raise ValueError("histórico ET0 insuficiente para el modelo")
        missing_columns = sorted(set(features).difference(available_features))
        model = joblib.load(artifact)
        prediction = float(model.predict(feature_frame)[0])
        if not np.isfinite(prediction) or prediction < 0:
            raise ValueError("predicción no válida")
        return {
            "et0_mm": prediction,
            "method": "ridge_et0_multiyear",
            "station_code": station_code,
            "target_date": target_day.isoformat(),
            "artifact": entry["artifact"],
            "artifact_sha256": entry["sha256"],
            "missing_feature_columns_imputed": missing_columns,
            "fallback_reason": None,
        }
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        result = _persistence(history, target_day, str(exc))
        result.update({"station_code": station_code, "target_date": target_day.isoformat()})
        return result
