"""Predicción de ETc para mañana a partir de modelos SiAR versionados.

Los artefactos fueron generados dentro de este repositorio. No se cargan
modelos proporcionados por el usuario.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.dss.config import CropCase


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs/data_samples/etc_model_deployment_2026.json"
MODEL_DIR = ROOT / "models/deployed_etc_2026"
MAX_MODEL_AGE_DAYS = 45


class ModelUnavailable(ValueError):
    """El caso o las observaciones no permiten una predicción válida."""


def case_key(case: CropCase) -> str:
    slug = case.crop.lower().translate(str.maketrans("áéíóúüñ", "aeiouun"))
    return f"{slug}_{case.station_code}"


def predict_tomorrow_etc(
    case: CropCase, history: pd.DataFrame, target_day: date
) -> dict:
    """Devuelve ETc previa a lluvia, usando solo observaciones anteriores."""

    manifest = json.loads(REPORT.read_text(encoding="utf-8"))
    entry = manifest["cases"].get(case_key(case))
    if entry is None or entry["crop"] != case.crop or entry["station_code"] != case.station_code:
        raise ModelUnavailable("No hay modelo entrenado para este cultivo y estación.")
    trained_through = date.fromisoformat(entry["trained_through"])
    if not trained_through < target_day:
        raise ModelUnavailable("El modelo contiene datos posteriores a la fecha solicitada.")
    if (target_day - trained_through).days > MAX_MODEL_AGE_DAYS:
        raise ModelUnavailable("El modelo necesita reentrenamiento para esta fecha.")

    target_timestamp = pd.Timestamp(target_day)
    target = history.loc[history["date"].eq(target_timestamp)]
    if len(target) != 1 or pd.isna(target["kc"].iat[0]) or target["kc"].iat[0] <= 0:
        raise ModelUnavailable("No hay Kc activo para mañana.")
    if pd.notna(target["etc_mm"].iat[0]):
        raise ModelUnavailable("La fecha solicitada ya tiene una ETc observada.")

    previous = history.loc[history["date"].lt(target_timestamp), ["date", "etc_mm"]].copy()
    if previous.empty or previous["date"].duplicated().any():
        raise ModelUnavailable("Falta una serie histórica SiAR válida.")
    etc = previous.set_index("date")["etc_mm"].astype(float)
    observed_dates = etc.dropna().index
    if observed_dates.empty:
        raise ModelUnavailable("No hay ETc SiAR observada antes de mañana.")
    last_observed = observed_dates.max()
    steps = (target_timestamp - last_observed).days
    if not 1 <= steps <= 3 or last_observed.month != target_timestamp.month:
        raise ModelUnavailable("El último dato de ETc no permite proyectar este ciclo.")

    artifact = entry["artifact"]
    if Path(artifact).name != artifact:
        raise ModelUnavailable("La ruta del modelo no es válida.")
    model_path = MODEL_DIR / artifact
    if not model_path.is_file():
        raise ModelUnavailable("Falta el modelo versionado para este caso.")
    model = joblib.load(model_path)
    prediction = np.nan
    for day in pd.date_range(last_observed + pd.Timedelta(days=1), target_timestamp):
        calendar = pd.date_range(day - pd.Timedelta(days=14),
                                 day - pd.Timedelta(days=1), freq="D")
        window = etc.reindex(calendar)
        if pd.isna(window.iloc[-1]):
            raise ModelUnavailable("Falta la ETc necesaria para avanzar el modelo.")
        row = history.loc[history["date"].eq(day)]
        kc = float(row["kc"].iat[0]) if len(row) == 1 and pd.notna(row["kc"].iat[0]) else float(target["kc"].iat[0])
        doy = day.dayofyear
        values = {
            "crop_coefficient_kc": kc,
            "day_of_year_sin": np.sin(2 * np.pi * doy / 365.25),
            "day_of_year_cos": np.cos(2 * np.pi * doy / 365.25),
        }
        # El esquema heredado se llama net_irrigation_need; aquí los valores
        # son retardos y acumulados de ETc antes de lluvia.
        for lag in (1, 3, 7):
            values[f"net_irrigation_need_mm_lag_{lag}d"] = window.iloc[-lag]
        for days in (3, 7, 14):
            values[f"net_irrigation_need_mm_sum_{days}d"] = window.iloc[-days:].sum(min_count=1)
        features = pd.DataFrame([values], columns=manifest["feature_columns"])
        prediction = float(model.predict(features)[0])
        if not np.isfinite(prediction):
            raise ModelUnavailable("El modelo produjo una estimación no válida.")
        etc.loc[day] = max(0.0, prediction)
    return {
        "etc_mm": max(0.0, prediction),
        "model": entry["selected_model_label"],
        "case": case_key(case),
        "trained_through": entry["trained_through"],
        "test_mae_mm_day": entry["test_mae_mm_day"],
        "physical_baseline_test_mae_mm_day": entry["physical_baseline_test_mae_mm_day"],
        "steps_ahead": steps,
        "deploy_model_for_dose": entry["deploy_model_for_dose"] and steps == 1,
    }
