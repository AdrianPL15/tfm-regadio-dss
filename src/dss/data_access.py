"""Lectura de la referencia agronómica y de la predicción meteorológica.

El motor trabaja con un calendario diario completo. Las fechas que la fuente no
devuelve se conservan como filas sin dato y con una marca explícita, de modo que
una ausencia nunca se confunde con una necesidad nula.
"""

from __future__ import annotations

import json
import io
from pathlib import Path
from typing import Any

import pandas as pd

from src.dss.config import CropCase


CROP_NEEDS_COLUMNS = {
    "Fecha": "date",
    "Kc": "kc",
    "ET0 (mm)": "et0_mm",
    "ETc (mm)": "etc_mm",
    "Pe (mm)": "pe_mm",
    "ETc - Pe (mm)": "net_need_mm",
}

# La descarga CSV directa de la web SiAR usa cabeceras sin la unidad; la
# instantánea inicial de pimiento conserva las cabeceras de la tabla web.
OFFICIAL_CSV_COLUMNS = {
    "ET0": "ET0 (mm)",
    "ETc": "ETc (mm)",
    "Pe": "Pe (mm)",
    "ETc - Pe": "ETc - Pe (mm)",
}

FORECAST_COLUMNS = {"date", "et0_mm", "precipitation_mm", "precipitation_probability_pct"}
FORECAST_TRACE_COLUMNS = (
    "issued_at", "hourly_issued_at", "municipality_code", "source",
    "precipitation_hours_covered", "precipitation_amount_status",
)


def load_crop_needs(path: Path) -> pd.DataFrame:
    """Carga el CSV oficial de SiAR y devuelve un calendario diario completo."""

    if not Path(path).exists():
        raise FileNotFoundError(f"No se encuentra la referencia agronómica: {path}")

    raw = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig")
    return _normalize_crop_needs(raw, Path(path).as_posix())


def load_crop_needs_bytes(content: bytes, source_label: str) -> pd.DataFrame:
    """Aplica la misma normalización a un CSV obtenido en vivo, sin escribirlo."""
    raw = pd.read_csv(io.BytesIO(content), sep=";", decimal=",", encoding="utf-8-sig")
    return _normalize_crop_needs(raw, source_label)


def _normalize_crop_needs(raw: pd.DataFrame, source_label: str) -> pd.DataFrame:
    raw = raw.rename(columns=OFFICIAL_CSV_COLUMNS)
    missing = set(CROP_NEEDS_COLUMNS).difference(raw.columns)
    if missing:
        raise ValueError(f"Faltan columnas en la referencia SiAR: {sorted(missing)}")

    data = raw.rename(columns=CROP_NEEDS_COLUMNS)[list(CROP_NEEDS_COLUMNS.values())]
    data["date"] = pd.to_datetime(data["date"], dayfirst=True, errors="raise")
    for column in ("kc", "et0_mm", "etc_mm", "pe_mm", "net_need_mm"):
        data[column] = pd.to_numeric(data[column], errors="coerce")

    if data["date"].duplicated().any():
        raise ValueError("La referencia SiAR contiene fechas duplicadas.")

    calendar = pd.date_range(data["date"].min(), data["date"].max(), freq="D")
    data = data.set_index("date").reindex(calendar)
    data.index.name = "date"
    data["record_status"] = "completo"
    data.loc[data["kc"].isna(), "record_status"] = "fecha_no_devuelta"
    data.loc[
        data["kc"].notna() & data["et0_mm"].isna(), "record_status"
    ] = "meteorologia_ausente"
    # El Kc procede del calendario del cultivo y se conoce de antemano. Si falta
    # una fecha, se toma el último valor publicado y se deja constancia.
    data["kc_imputed"] = data["kc"].isna()
    data["kc"] = data["kc"].ffill()
    data["source_file"] = source_label
    return data.reset_index()


def load_metadata(path: Path) -> dict[str, Any]:
    if not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_case(case: CropCase) -> tuple[pd.DataFrame, dict[str, Any]]:
    return load_crop_needs(case.source_file), load_metadata(case.metadata_file)


def load_forecast(path: Path | None) -> pd.DataFrame | None:
    """Carga una predicción diaria opcional.

    Se espera un CSV con ``date`` y, al menos, una de las columnas ``et0_mm``,
    ``precipitation_mm`` o ``precipitation_probability_pct``. Puede proceder de
    la predicción municipal de AEMET normalizada en ``data/interim`` o del
    producto de ET0 prevista de SiAR.
    """

    if path is None:
        return None
    forecast = pd.read_csv(path)
    if "date" not in forecast.columns:
        for alias in ("valid_date", "forecast_date", "fecha"):
            if alias in forecast.columns:
                forecast = forecast.rename(columns={alias: "date"})
                break
    if "date" not in forecast.columns:
        raise ValueError("La predicción debe incluir una columna de fecha.")
    if not FORECAST_COLUMNS.difference({"date"}).intersection(forecast.columns):
        raise ValueError("La predicción no contiene ninguna variable utilizable.")
    forecast["date"] = pd.to_datetime(forecast["date"]).dt.normalize()
    return normalise_forecast(forecast)


def normalise_forecast(forecast: pd.DataFrame | None) -> pd.DataFrame | None:
    if forecast is None:
        return None
    result = forecast.copy()
    result["date"] = pd.to_datetime(result["date"]).dt.normalize()
    if result["date"].isna().any() or result["date"].duplicated().any():
        raise ValueError("La predicción contiene fechas inválidas o duplicadas.")
    for column in FORECAST_COLUMNS.difference({"date"}):
        if column not in result.columns:
            result[column] = pd.NA
        result[column] = pd.to_numeric(result[column], errors="coerce")
    for column in ("et0_mm", "precipitation_mm"):
        if (result[column].dropna() < 0).any():
            raise ValueError(f"La predicción contiene valores negativos en {column}.")
    probability = result["precipitation_probability_pct"].dropna()
    if ((probability < 0) | (probability > 100)).any():
        raise ValueError("La probabilidad prevista debe estar entre 0 y 100 %.")
    if "issued_at" in result:
        result["issued_at"] = pd.to_datetime(result["issued_at"], errors="raise")
        if (result["issued_at"].dt.normalize() > result["date"]).any():
            raise ValueError("La predicción se emitió después de su fecha válida.")
    columns = sorted(FORECAST_COLUMNS) + [name for name in FORECAST_TRACE_COLUMNS if name in result]
    return result[columns].sort_values("date").reset_index(drop=True)
