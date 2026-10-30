"""Avisos de disponibilidad que deben verse antes de consultar una dosis."""
from datetime import date, timedelta
import pandas as pd


def availability_notice(history, metadata, *, issue: date, today: date,
                        planning: bool, live_case: bool, horizon: int = 1) -> str | None:
    first = history["date"].min().date()
    last = history["date"].max().date()
    span = f"{first:%d/%m/%Y}–{last:%d/%m/%Y}"
    selected = history.loc[history["date"].eq(pd.Timestamp(issue))]
    if planning and not selected.empty and (
        pd.isna(selected["kc"].iat[0]) or selected["kc"].iat[0] <= 0
    ):
        return (f"Fecha fuera del ciclo del cultivo: {issue:%d/%m/%Y}. "
                "No hay dosis para esta fecha. Elige un día con Kc positivo o cambia de cultivo.")
    if planning and not live_case:
        active_months = metadata.get("active_months", [])
        reason = (
            "El cultivo está fuera de su ciclo actual."
            if today.month not in active_months or history["kc"].iloc[-1] <= 0
            else "Faltan datos SiAR recientes y completos; actualiza las fuentes."
        )
        return f"No hay recomendación actual. {reason} Solo se muestra un ejemplo histórico. Datos guardados: {span}."
    if planning and issue not in {today, today + timedelta(days=1)}:
        return f"Consulta histórica del {issue:%d/%m/%Y}: esta cifra no es para regar hoy. Datos guardados: {span}."
    end = issue + timedelta(days=horizon - 1)
    if planning and live_case and end > last and (
        end.month != last.month or end.month not in metadata.get("active_months", [])
    ):
        return ("El horizonte supera el mes o ciclo publicado por SiAR. "
                "Solo se calcularán los días con calendario de cultivo disponible; los demás quedarán sin dosis.")
    return None
