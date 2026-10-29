"""Proyección limitada del Kc SiAR para hoy o mañana.

El CSV puede no incluir el día de consulta. Solo se prolonga el último Kc publicado
dentro del mismo mes y ciclo declarado por SiAR, con dato reciente y aviso
explícito. No se fabrican ET0, lluvia ni necesidad observadas.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd


MAX_KC_STALENESS_DAYS = 7


def extend_recent_kc(
    history: pd.DataFrame,
    metadata: dict[str, Any],
    *,
    target_day: date,
    as_of: date,
    horizon_days: int = 1,
) -> pd.DataFrame:
    """Añade Kc para hoy o mañana si la serie y el ciclo lo sostienen."""
    if target_day not in {as_of, as_of + timedelta(days=1)}:
        raise ValueError("La proyección SiAR solo se permite para hoy o mañana.")
    if not 1 <= horizon_days <= 7:
        raise ValueError("El horizonte debe estar entre uno y siete días.")
    active_months = {int(month) for month in metadata.get("active_months", [])}
    if not active_months:
        raise ValueError("Falta el calendario de meses activos de SiAR.")
    if history.empty or history["date"].isna().any():
        raise ValueError("No hay una serie SiAR válida para proyectar Kc.")

    # Una consulta retrospectiva solo puede utilizar observaciones que ya
    # existían en su fecha de emisión. El CSV versionado puede haberse ampliado
    # después; ignorar esas filas evita fuga temporal y mantiene reproducibles
    # las simulaciones históricas.
    available_history = history.copy()
    available_history["date"] = pd.to_datetime(
        available_history["date"], errors="raise"
    ).dt.normalize()
    available_history = available_history.loc[
        available_history["date"].dt.date <= as_of
    ].copy()
    if available_history.empty:
        raise ValueError("SiAR no dispone de observaciones anteriores a la consulta.")

    last = available_history.sort_values("date").iloc[-1]
    last_day = pd.Timestamp(last["date"]).date()
    if not as_of - timedelta(days=MAX_KC_STALENESS_DAYS) <= last_day <= as_of:
        raise ValueError(
            "SiAR no dispone de un Kc publicado en los últimos "
            f"{MAX_KC_STALENESS_DAYS} días para esta campaña."
        )
    if last["record_status"] != "completo" or pd.isna(last["kc"]):
        raise ValueError("El último Kc SiAR no está completo.")
    if float(last["kc"]) <= 0:
        raise ValueError("El cultivo figura fuera de ciclo: Kc SiAR es cero.")
    future = []
    for offset in range(horizon_days):
        day = target_day + timedelta(days=offset)
        if day <= last_day:
            continue
        if day.month != last_day.month or day.month not in active_months:
            break
        row = last.copy()
        row["date"] = pd.Timestamp(day)
        row["kc"] = float(last["kc"])
        row["kc_imputed"] = True
        row["record_status"] = "kc_proyectado_mes"
        for column in ("et0_mm", "etc_mm", "pe_mm", "net_need_mm"):
            row[column] = float("nan")
        future.append(row)
    if not future:
        if target_day <= last_day:
            return available_history.reset_index(drop=True)
        raise ValueError("La fecha solicitada queda fuera del mes y ciclo SiAR publicados.")
    return pd.concat(
        [available_history, pd.DataFrame(future)], ignore_index=True
    )
