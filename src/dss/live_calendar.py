"""Proyección limitada del Kc SiAR para una recomendación próxima.

El CSV histórico no incluye mañana. Solo se prolonga el último Kc publicado
dentro del mismo mes y ciclo declarado por SiAR, con dato reciente y aviso
explícito. No se fabrican ET0, lluvia ni necesidad observadas.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd


def extend_recent_kc(
    history: pd.DataFrame,
    metadata: dict[str, Any],
    *,
    target_day: date,
    as_of: date,
    horizon_days: int = 1,
) -> pd.DataFrame:
    """Añade Kc futuro solo si la serie y el ciclo sostienen la proyección."""
    if target_day != as_of + timedelta(days=1):
        raise ValueError("La proyección SiAR solo se permite para empezar mañana.")
    if not 1 <= horizon_days <= 7:
        raise ValueError("El horizonte debe estar entre uno y siete días.")
    active_months = {int(month) for month in metadata.get("active_months", [])}
    if not active_months:
        raise ValueError("Falta el calendario de meses activos de SiAR.")
    if history.empty or history["date"].isna().any():
        raise ValueError("No hay una serie SiAR válida para proyectar Kc.")

    last = history.sort_values("date").iloc[-1]
    last_day = pd.Timestamp(last["date"]).date()
    if not as_of - timedelta(days=2) <= last_day <= as_of:
        raise ValueError("SiAR no dispone de un Kc reciente para esta campaña.")
    if last["record_status"] != "completo" or pd.isna(last["kc"]):
        raise ValueError("El último Kc SiAR no está completo.")
    if float(last["kc"]) <= 0:
        raise ValueError("El cultivo figura fuera de ciclo: Kc SiAR es cero.")

    future = []
    for offset in range(horizon_days):
        day = target_day + timedelta(days=offset)
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
        raise ValueError("Mañana queda fuera del mes y ciclo SiAR publicados.")
    return pd.concat([history, pd.DataFrame(future)], ignore_index=True)
