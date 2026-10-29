"""Inferencia experimental de ET0 con respaldos físicos explícitos."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

import joblib
import numpy as np
import pandas as pd

from src.models.train_et0_multiyear import build_feature_table
from src.data.siar_client import SiARClient, SiARError
from src.data.transform_interim import normalize_siar_daily


ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models/experimental_et0_multiyear"
MANIFEST = MODEL_DIR / "manifest.json"
MAX_IMPUTED_FEATURE_VALUES = 1


class SiARDailySource(Protocol):
    def get_data(self, data_type, scope, identifiers, start_date, end_date, *, calculated=False): ...


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _physical_fallback(history: pd.DataFrame, target_day: date, reason: str) -> dict:
    if "date" not in history.columns or "et0_mm" not in history.columns:
        return {"et0_mm": None, "method": "unavailable", "fallback_reason": reason}
    known = history.loc[pd.to_datetime(history["date"]).dt.date < target_day].copy()
    known["date"] = pd.to_datetime(known["date"], errors="coerce")
    known["et0_mm"] = pd.to_numeric(known.get("et0_mm"), errors="coerce")
    known = known.dropna(subset=["date", "et0_mm"]).sort_values("date")
    values = known["et0_mm"]
    if values.empty:
        return {"et0_mm": None, "method": "unavailable", "fallback_reason": reason}
    last_day = known["date"].max()
    recent = known.loc[known["date"].ge(last_day - pd.Timedelta(days=6)), "et0_mm"]
    if len(recent) >= 3:
        return {
            "et0_mm": float(max(0.0, recent.mean())),
            "method": "mean_7d_fallback",
            "fallback_observations": int(len(recent)),
            "fallback_reason": reason,
        }
    return {
        "et0_mm": float(max(0.0, values.iloc[-1])),
        "method": "persistence_fallback",
        "fallback_observations": 1,
        "fallback_reason": reason,
    }


def _baseline_values(history: pd.DataFrame, target_day: date) -> dict[str, float | None]:
    """Devuelve referencias físicas calculadas únicamente con datos disponibles."""

    fallback = _physical_fallback(history, target_day, "referencia física")
    known = history.copy()
    if "date" not in known.columns or "et0_mm" not in known.columns:
        return {"baseline_mean_7d_mm": None, "baseline_persistence_mm": None}
    known["date"] = pd.to_datetime(known["date"], errors="coerce")
    known["et0_mm"] = pd.to_numeric(known["et0_mm"], errors="coerce")
    known = known.loc[known["date"].dt.date < target_day].dropna(
        subset=["date", "et0_mm"]
    ).sort_values("date")
    persistence = float(known["et0_mm"].iloc[-1]) if not known.empty else None
    mean_7d = (
        float(fallback["et0_mm"])
        if fallback.get("method") == "mean_7d_fallback"
        else None
    )
    return {
        "baseline_mean_7d_mm": mean_7d,
        "baseline_persistence_mm": persistence,
    }


def predict_et0_with_fallback(
    station_code: str,
    history: pd.DataFrame,
    target_day: date,
    *,
    manifest_path: Path = MANIFEST,
    model_dir: Path = MODEL_DIR,
) -> dict:
    """Predice ET0 para un horizonte versionado o devuelve respaldo trazable."""

    station_code = station_code.upper()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        station_entry = manifest["stations"][station_code]
        data = history.copy()
        data["date"] = pd.to_datetime(data["date"], errors="raise")
        data = data.loc[data["date"].dt.date < target_day].sort_values("date")
        if data.empty:
            raise ValueError("no existen observaciones anteriores a la fecha objetivo")
        horizon_days = (target_day - data["date"].max().date()).days
        horizons = station_entry.get("horizons")
        if horizons is None:
            if horizon_days != 1:
                raise ValueError("el manifiesto legado solo contiene el horizonte de un día")
            entry = station_entry
        else:
            if str(horizon_days) not in horizons:
                raise ValueError(
                    f"horizonte operativo no soportado: {horizon_days} días desde el último dato"
                )
            entry = horizons[str(horizon_days)]
        artifact = model_dir / entry["artifact"]
        if artifact.parent.resolve() != model_dir.resolve() or not artifact.is_file():
            raise ValueError("artefacto ausente o ruta no válida")
        if _sha256(artifact) != entry["sha256"]:
            raise ValueError("la huella del artefacto no coincide")

        table, available_features = build_feature_table(data, horizon_days=horizon_days)
        row = table.loc[table["prediction_date"].dt.date.eq(target_day)]
        if len(row) != 1:
            raise ValueError("no se pudo construir una única fila de inferencia")
        features = list(entry["feature_columns"])
        feature_frame = row.reindex(columns=features)
        et0_lags = [name for name in features if name.startswith("et0_lag_")]
        if feature_frame[et0_lags].notna().sum(axis=1).iat[0] < 3:
            raise ValueError("histórico ET0 insuficiente para el modelo")
        missing_columns = sorted(set(features).difference(available_features))
        if missing_columns:
            raise ValueError(
                "faltan columnas operativas completas: " + ", ".join(missing_columns)
            )
        imputed_values = feature_frame.columns[feature_frame.isna().iloc[0]].tolist()
        if len(imputed_values) > MAX_IMPUTED_FEATURE_VALUES:
            raise ValueError(
                "demasiados valores de entrada requieren imputación: "
                f"{len(imputed_values)} > {MAX_IMPUTED_FEATURE_VALUES}"
            )
        model = joblib.load(artifact)
        prediction = float(model.predict(feature_frame)[0])
        if not np.isfinite(prediction) or prediction < 0:
            raise ValueError("predicción no válida")
        result = {
            "et0_mm": prediction,
            "method": f"ridge_et0_multiyear_h{horizon_days}",
            "horizon_days": horizon_days,
            "station_code": station_code,
            "target_date": target_day.isoformat(),
            "artifact": entry["artifact"],
            "artifact_sha256": entry["sha256"],
            "model_trained_through": entry.get("trained_through"),
            "external_test_ridge_mae_mm_day": entry.get(
                "external_test_ridge_mae_mm_day"
            ),
            "external_test_persistence_mae_mm_day": entry.get(
                "external_test_persistence_mae_mm_day"
            ),
            "external_test_mean_7d_mae_mm_day": entry.get(
                "external_test_mean_7d_mae_mm_day"
            ),
            "missing_feature_columns_imputed": [],
            "missing_feature_values_imputed": imputed_values,
            "fallback_reason": None,
        }
        result.update(_baseline_values(data, target_day))
        return result
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        result = _physical_fallback(history, target_day, str(exc))
        result.update({"station_code": station_code, "target_date": target_day.isoformat()})
        result.update(_baseline_values(history, target_day))
        return result


def history_from_siar_records(records: list[dict], station_code: str) -> pd.DataFrame:
    """Adapta la respuesta diaria oficial al mismo esquema del entrenamiento."""

    rows = normalize_siar_daily(records, ingested_at="live", source_file="SiAR API")
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=["date", "station_code", "et0_mm"])
    station_values = frame["station_code"].dropna().astype(str).str.upper().unique()
    if len(station_values) != 1 or station_values[0] != station_code.upper():
        raise ValueError("La respuesta SiAR no corresponde a la estación solicitada.")
    renamed = frame.rename(
        columns={
            "observed_date": "date",
            "solar_radiation_raw": "solar_radiation_mj_m2",
            "et0_pm_mm": "et0_mm",
        }
    )
    columns = [
        "date", "station_code", "et0_mm", "temperature_mean_c",
        "temperature_max_c", "temperature_min_c", "humidity_mean_pct",
        "humidity_max_pct", "humidity_min_pct", "wind_speed_mean_ms",
        "wind_speed_max_ms", "solar_radiation_mj_m2", "precipitation_mm",
        "quality_status", "quality_issues",
    ]
    renamed["date"] = pd.to_datetime(renamed["date"], errors="raise")
    return renamed[columns].sort_values("date").reset_index(drop=True)


def to_etc_model_estimate(prediction: dict, kc: float) -> dict:
    """Convierte una ET0 Ridge válida en el contrato ETc que consume el DSS."""

    method = str(prediction.get("method", ""))
    if not method.startswith("ridge_et0_multiyear_h"):
        raise ValueError("La predicción ET0 no procede de un artefacto Ridge válido.")
    et0_mm = float(prediction["et0_mm"])
    kc = float(kc)
    if not np.isfinite(et0_mm) or et0_mm < 0 or not np.isfinite(kc) or kc <= 0:
        raise ValueError("ET0 o Kc no válidos para calcular ETc.")
    return {
        "etc_mm": et0_mm * kc,
        "model": f"Ridge ET0 h={prediction['horizon_days']} × Kc",
        "case": prediction.get("station_code"),
        "trained_through": prediction.get("model_trained_through", "2025"),
        "test_mae_mm_day": prediction.get("external_test_ridge_mae_mm_day"),
        "physical_baseline_test_mae_mm_day": prediction.get(
            "external_test_mean_7d_mae_mm_day"
        ),
        "steps_ahead": int(prediction["horizon_days"]),
        "deploy_model_for_dose": True,
        "metric_target": "ET0",
    }


def predict_live_et0(
    station_code: str,
    target_day: date,
    *,
    client: SiARDailySource | None = None,
    lookback_days: int = 30,
    fallback_history: pd.DataFrame | None = None,
    manifest_path: Path = MANIFEST,
    model_dir: Path = MODEL_DIR,
) -> dict:
    """Consulta SiAR hasta t-1 y elige un horizonte validado entre h=1 y h=7."""

    if lookback_days < 14:
        raise ValueError("El periodo operativo debe cubrir al menos 14 días.")
    source = client or SiARClient()
    start = target_day - timedelta(days=lookback_days)
    end = target_day - timedelta(days=1)
    try:
        records = source.get_data(
            "Diarios", "ESTACION", station_code.upper(), start, end, calculated=True
        )
        history = history_from_siar_records(records, station_code)
    except (SiARError, ValueError, KeyError, TypeError) as exc:
        fallback = fallback_history if fallback_history is not None else pd.DataFrame(
            columns=["date", "et0_mm"]
        )
        result = _physical_fallback(
            fallback, target_day, f"fallo del extractor SiAR: {exc}"
        )
        result.update({"station_code": station_code.upper(), "target_date": target_day.isoformat()})
        return result
    return predict_et0_with_fallback(
        station_code,
        history,
        target_day,
        manifest_path=manifest_path,
        model_dir=model_dir,
    )
