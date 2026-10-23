"""Adaptador de la predicción municipal AEMET al calendario del DSS.

La predicción diaria aporta probabilidad, no milímetros. Solo se suma la
precipitación horaria futura cuando todas las horas disponibles tienen un
valor numérico; la cobertura se conserva para no llamar «total diario» a una
predicción parcial. No se inventa ET0 a partir de temperatura o UV.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from src.data.aemet_client import AEMETClient, AEMETError
from src.data.transform_interim import normalize_aemet_daily, normalize_aemet_hourly


def forecast_from_payloads(
    daily_payload: list[dict[str, Any]],
    hourly_payload: list[dict[str, Any]],
) -> pd.DataFrame:
    """Une dos productos del mismo municipio, sin confundir probabilidad y mm."""
    if not daily_payload:
        raise ValueError("Falta la predicción diaria de AEMET.")
    daily_root = daily_payload[0]
    daily_code = str(daily_root.get("id", "")).removeprefix("id").zfill(5)
    if not daily_code.isdigit():
        raise ValueError("El municipio AEMET no es válido.")
    daily_issued = pd.Timestamp(daily_root["elaborado"])
    hourly_issued = pd.NaT
    if hourly_payload:
        hourly_root = hourly_payload[0]
        hourly_code = str(hourly_root.get("id", "")).removeprefix("id").zfill(5)
        if daily_code != hourly_code:
            raise ValueError("Las predicciones AEMET no corresponden al mismo municipio.")
        hourly_issued = pd.Timestamp(hourly_root["elaborado"])
        if abs((daily_issued - hourly_issued).total_seconds()) > 24 * 3600:
            raise ValueError("Las predicciones AEMET tienen fechas de emisión incompatibles.")

    daily_rows = normalize_aemet_daily(daily_payload, ingested_at="", source_file="AEMET")
    hourly_rows = normalize_aemet_hourly(hourly_payload, ingested_at="", source_file="AEMET")
    if not daily_rows:
        raise ValueError("AEMET no devolvió días de predicción.")
    daily = pd.DataFrame(daily_rows)
    daily["date"] = pd.to_datetime(daily["valid_date"]).dt.normalize()
    if daily["date"].duplicated().any():
        raise ValueError("AEMET devolvió fechas diarias duplicadas.")
    daily = daily.rename(columns={"precipitation_probability_max_pct": "precipitation_probability_pct"})

    aggregates: dict[pd.Timestamp, dict[str, Any]] = {}
    hourly = pd.DataFrame(hourly_rows)
    if not hourly.empty:
        hourly = hourly.loc[hourly["is_future_at_issue"]].copy()
        hourly["date"] = pd.to_datetime(hourly["valid_time_local"]).dt.normalize()
        if hourly["valid_time_local"].duplicated().any():
            raise ValueError("AEMET devolvió horas duplicadas.")
        for valid_date, group in hourly.groupby("date"):
            amounts = pd.to_numeric(group["precipitation_mm"], errors="coerce")
            complete = bool(amounts.notna().all())
            if (amounts.dropna() < 0).any():
                raise ValueError("AEMET devolvió precipitación negativa.")
            aggregates[valid_date] = {
                "precipitation_mm": float(amounts.sum()) if complete else float("nan"),
                "precipitation_hours_covered": int(len(group)),
                "precipitation_amount_status": "horas_disponibles" if complete else "horas_incompletas",
            }

    rows: list[dict[str, Any]] = []
    for _, day in daily.iterrows():
        valid_date = day["date"]
        amount = aggregates.get(valid_date, {
            "precipitation_mm": float("nan"),
            "precipitation_hours_covered": 0,
            "precipitation_amount_status": "solo_probabilidad_diaria",
        })
        probability = day["precipitation_probability_pct"]
        if pd.notna(probability) and not 0 <= float(probability) <= 100:
            raise ValueError("AEMET devolvió probabilidad fuera de 0–100 %.")
        rows.append({
            "date": valid_date,
            "precipitation_probability_pct": probability,
            **amount,
            "issued_at": daily_issued.isoformat(),
            "hourly_issued_at": hourly_issued.isoformat() if pd.notna(hourly_issued) else None,
            "municipality_code": daily_code,
            "source": "AEMET OpenData",
        })
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def fetch_live_forecast(municipality_code: str, *, client: AEMETClient | None = None) -> pd.DataFrame:
    """Descarga la predicción actual; el llamante decide si su fecha es válida."""
    provider = client or AEMETClient()
    daily = provider.get_daily_municipality_forecast(municipality_code)
    try:
        hourly = provider.get_hourly_municipality_forecast(municipality_code)
    except AEMETError:
        hourly = []
    if not isinstance(daily, list) or not isinstance(hourly, list):
        raise ValueError("La respuesta municipal AEMET no tiene el formato esperado.")
    return forecast_from_payloads(daily, hourly)


def require_current_forecast(forecast: pd.DataFrame, issue_date: date) -> None:
    """Impide combinar una predicción actual con el piloto histórico de 2025."""
    if not (pd.to_datetime(forecast["issued_at"]).dt.date == issue_date).all():
        raise ValueError("La emisión AEMET no corresponde a la fecha de consulta; no se mezcla con SiAR histórico.")
