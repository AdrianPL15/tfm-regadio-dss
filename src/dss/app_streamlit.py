"""Interfaz de demostración del sistema de apoyo a la decisión.

Se ejecuta desde la raíz del repositorio con:

    streamlit run src/dss/app_streamlit.py
"""

from __future__ import annotations

from datetime import date, timedelta
import os
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dss.config import (  # noqa: E402
    DEMO_CASES,
    IRRIGATION_EFFICIENCY,
    MAX_HORIZON_DAYS,
    CropCase,
    RecommendationRequest,
)
from src.dss.data_access import load_case  # noqa: E402
from src.dss.aemet_forecast import fetch_live_forecast, require_current_forecast  # noqa: E402
from src.data.aemet_client import AEMETClient, AEMETError  # noqa: E402
from src.dss.engine import METHOD_LABELS, fmt_es, recommend  # noqa: E402
from src.dss.live_calendar import extend_recent_kc  # noqa: E402


st.set_page_config(page_title="DSS de riego", layout="wide")


@st.cache_data
def _load(source: str, metadata: str):
    case = CropCase(source_file=Path(source), metadata_file=Path(metadata))
    return load_case(case)


def _absolute(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


params = st.query_params
try:
    default_issue = date.fromisoformat(params.get("fecha", "2025-06-28"))
except ValueError:
    default_issue = date(2025, 6, 28)

st.title("Sistema de apoyo a la decisión para el riego")
st.caption(
    "Prototipo del TFM. La recomendación es orientativa y debe contrastarse con "
    "el estado real de la parcela y el criterio técnico."
)
st.caption(
    "Conservamos las campañas SiAR de 2025 para evaluación y añadimos datos "
    "observados de 2026. Para un cultivo activo, se puede estimar mañana con "
    "ET0 reciente, Kc proyectado y la predicción AEMET emitida hoy."
)

with st.sidebar:
    st.header("Caso analizado")
    community = st.selectbox(
        "Comunidad autónoma", list(dict.fromkeys(item.community for item in DEMO_CASES))
    )
    community_cases = [item for item in DEMO_CASES if item.community == community]
    province = st.selectbox(
        "Provincia", list(dict.fromkeys(item.province for item in community_cases))
    )
    province_cases = [item for item in community_cases if item.province == province]
    crop_options = list(dict.fromkeys(item.crop for item in province_cases))
    preferred_crop = "Coliflor" if date.today().month == 10 and "Coliflor" in crop_options else crop_options[0]
    crop = st.selectbox("Cultivo", crop_options, index=crop_options.index(preferred_crop))
    crop_cases = [item for item in province_cases if item.crop == crop]
    station_codes = [item.station_code for item in crop_cases]
    station_code = st.selectbox(
        "Estación SiAR",
        station_codes,
        format_func=lambda code: next(
            f"{item.station_code} - {item.station_name}"
            for item in crop_cases if item.station_code == code
        ),
    )
    station_cases = [item for item in crop_cases if item.station_code == station_code]
    years = sorted({item.campaign_year for item in station_cases}, reverse=True)
    campaign_year = st.selectbox("Campaña SiAR", years)
    case = next(item for item in station_cases if item.campaign_year == campaign_year)
    st.caption(
        "Solo aparecen combinaciones con CSV local verificado. La demo no extrae "
        "automáticamente todas las zonas y cultivos de SiAR."
    )

    history, metadata = _load(
        str(_absolute(case.source_file)), str(_absolute(case.metadata_file))
    )
    first_day = history["date"].min().date()
    last_day = history["date"].max().date()
    tomorrow = date.today() + timedelta(days=1)
    live_case = (
        case.campaign_year == date.today().year
        and tomorrow.month in metadata.get("active_months", [])
        and 0 <= (date.today() - last_day).days <= 2
        and float(history["kc"].iloc[-1]) > 0
    )
    active_dates = history.loc[history["kc"].gt(0), "date"]
    historical_example = active_dates.max().date() if not active_dates.empty else last_day

    st.header("Consulta")
    mode_label = st.radio(
        "Modo",
        ["Planificación (solo datos anteriores)", "Seguimiento (días ya cerrados)"],
    )
    mode = "planificacion" if mode_label.startswith("Planificación") else "seguimiento"
    issue = st.date_input(
        "Primer día a recomendar",
        value=(tomorrow if live_case else historical_example if case.campaign_year == date.today().year
               else min(max(default_issue, first_day), last_day)),
        min_value=first_day,
        max_value=last_day + timedelta(days=MAX_HORIZON_DAYS),
        format="DD/MM/YYYY",
        key=f"fecha_{case.station_code}_{case.crop}_{case.campaign_year}",
    )
    horizon = st.slider(
        "Horizonte orientativo (días)", 1, MAX_HORIZON_DAYS,
        MAX_HORIZON_DAYS if live_case else 7,
    )
    if live_case and issue == tomorrow:
        st.caption(
            "El primer día es la recomendación principal. Los siguientes son una "
            "previsión provisional, que conviene recalcular con nuevos datos SiAR y AEMET."
        )
    if case.campaign_year == date.today().year and not live_case:
        st.caption(
            "La campaña de este cultivo no está activa mañana según SiAR; "
            "mostramos un día histórico con Kc positivo, sin aplicar AEMET actual."
        )

    st.header("Parcela")
    system = st.selectbox("Sistema de riego", list(IRRIGATION_EFFICIENCY), index=0)
    efficiency = st.slider(
        "Eficiencia de aplicación", 0.50, 1.00, IRRIGATION_EFFICIENCY[system], 0.01
    )
    area = st.number_input("Superficie (ha)", min_value=0.0, value=1.5, step=0.1)
    use_allocation = st.checkbox("Limitar por dotación semanal")
    allocation = (
        st.number_input("Dotación semanal (mm)", min_value=0.0, value=30.0, step=1.0)
        if use_allocation
        else None
    )
    show_reference = st.checkbox(
        "Comparar con la referencia SiAR posterior",
        value=params.get("referencia") == "1",
    )

    st.header("Lluvia prevista")
    use_scenario = st.checkbox("Explorar un escenario de lluvia", value=False)
    scenario_amount = 0.0
    scenario_date = issue
    rain_fraction = None
    if use_scenario:
        st.caption("Introducción manual hipotética; no se atribuye a AEMET.")
        scenario_date = st.selectbox(
            "Día con lluvia hipotética",
            [issue + timedelta(days=offset) for offset in range(horizon)],
            format_func=lambda value: value.strftime("%d/%m/%Y"),
        )
        scenario_amount = st.number_input("Lluvia hipotética (mm)", min_value=0.0, value=8.0, step=0.5)
        rain_fraction = st.slider(
            "Fracción aprovechable hipotética (%)", 0, 100, 50, 5
        ) / 100
        st.caption("Este porcentaje es un supuesto editable, no una calibración de la parcela.")
    elif live_case:
        rain_fraction = st.slider(
            "Lluvia prevista aprovechable, supuesto (%)", 0, 100, 50, 5
        ) / 100
        st.caption("La fracción es orientativa. Solo se descuenta si AEMET cubre las 24 horas de mañana con mm numéricos.")

st.subheader("Predicción municipal AEMET actual")
st.caption(
    "La predicción corresponde al municipio, no a la estación SiAR ni a la parcela. "
    "Solo se aplica al horizonte futuro de un cultivo en ciclo con SiAR 2026 reciente. "
    "AEMET se renueva al pulsar el botón; los CSV SiAR de esta demo no se actualizan solos."
)
if st.button("Consultar AEMET ahora"):
    try:
        try:
            cloud_key = st.secrets.get("AEMET_API_KEY")
        except (FileNotFoundError, KeyError):
            cloud_key = None
        provider = AEMETClient(api_key=cloud_key or os.getenv("AEMET_API_KEY"))
        st.session_state[f"aemet_{case.station_code}"] = fetch_live_forecast(
            case.aemet_municipality_code, client=provider
        )
    except (AEMETError, ValueError) as error:
        st.session_state.pop(f"aemet_{case.station_code}", None)
        st.error(f"No se pudo obtener la predicción: {error}")

live_forecast = st.session_state.get(f"aemet_{case.station_code}")
forecast_input = None
if live_forecast is not None:
    visible = live_forecast[[
        "date", "precipitation_probability_pct", "precipitation_mm",
        "precipitation_hours_covered", "precipitation_amount_status",
    ]].copy()
    visible["date"] = visible["date"].dt.strftime("%d/%m/%Y")
    st.dataframe(visible, hide_index=True, width="stretch")
    st.caption(f"Emisión AEMET: {live_forecast['issued_at'].iat[0]}; municipio {case.aemet_municipality_code}.")
    if issue == tomorrow and live_case and not use_scenario:
        try:
            require_current_forecast(live_forecast, date.today())
            forecast_input = live_forecast.copy()
            incomplete = (
                forecast_input["precipitation_hours_covered"].fillna(0) < 24
            ) | (forecast_input["precipitation_amount_status"] != "horas_disponibles")
            forecast_input.loc[incomplete, "precipitation_mm"] = float("nan")
        except ValueError as error:
            st.warning(str(error))
    else:
        st.info("Esta fecha no es mañana dentro de un ciclo SiAR vigente: AEMET se muestra, pero no se aplica al cálculo histórico.")
elif live_case and issue == tomorrow and not use_scenario:
    st.info("Pulsa «Consultar AEMET ahora» para considerar la previsión de lluvia de mañana; mientras tanto se muestra la dosis base.")

if use_scenario:
    forecast_input = pd.DataFrame({
        "date": [pd.Timestamp(scenario_date)],
        "precipitation_mm": [scenario_amount],
        "source": ["Escenario manual hipotético"],
    })

request = RecommendationRequest(
    issue_date=issue,
    horizon_days=horizon,
    irrigation_system=system,
    efficiency=efficiency,
    area_ha=area if area > 0 else None,
    weekly_allocation_mm=allocation,
    mode=mode,
    rain_effective_fraction=(rain_fraction if (use_scenario or forecast_input is not None) and mode == "planificacion" else None),
    case=case,
)

st.info(
    f"Caso seleccionado: **{case.crop} · {case.station_code} {case.station_name} "
    f"({case.province}, {case.community})**. Serie diaria del "
    f"{first_day:%d/%m/%Y} al {last_day:%d/%m/%Y} "
    f"({metadata.get('record_count', len(history))} registros descargados)."
)
if case.campaign_year == 2025 and case.crop in {"Maíz", "Algodón"}:
    st.caption(
        "Este caso dispone de una evaluación temporal predictiva adicional, "
        "independiente por cultivo; no acredita ahorro ni precisión en campo."
    )
st.caption(
    "El CSV SiAR identifica cultivo y estación, pero no acredita el sistema de "
    "producción concreto (por ejemplo, aire libre o invernadero)."
)

try:
    calculation_history = (
        extend_recent_kc(history, metadata, target_day=issue, as_of=date.today(), horizon_days=horizon)
        if live_case and issue == tomorrow else history
    )
    result = recommend(request, history=calculation_history, metadata=metadata, forecast=forecast_input)
except ValueError as error:
    st.error(str(error))
    st.stop()

summary = result.summary
daily = result.daily.copy()

for warning in result.warnings:
    st.warning(warning)

first = daily.iloc[0]
st.subheader(f"Riego propuesto para el {first['date']:%d/%m/%Y}")
if pd.notna(first["gross_dose_mm"]):
    dose = float(first["gross_dose_mm"])
    first_volume = first["volume_m3"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Dosis a aplicar", f"{fmt_es(dose)} mm")
    col2.metric("Equivale a", f"{fmt_es(dose)} L/m²")
    col3.metric("Por hectárea", f"{fmt_es(dose * 10, 0)} m³/ha")
    col4.metric(
        f"Para tu parcela ({fmt_es(area, 2)} ha)",
        f"{fmt_es(first_volume, 0)} m³" if pd.notna(first_volume) else "indica superficie",
    )
    st.caption(
        f"La necesidad neta del cultivo es {fmt_es(first['net_need_mm'])} mm. "
        "La dosis bruta incorpora la eficiencia del sistema; si limitas la dotación, "
        "la cantidad propuesta puede quedar por debajo y se advierte del déficit. "
        "1 mm de riego = 1 litro por m² = 10 m³ por hectárea."
    )
else:
    st.warning("No hay datos suficientes para proponer una dosis para el primer día.")

if horizon > 1:
    st.subheader(f"Panorama provisional de {horizon} días")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Necesidad neta acumulada", f"{fmt_es(summary['net_need_total_mm'])} mm")
    col2.metric("Riego acumulado estimado", f"{fmt_es(summary['gross_dose_total_mm'])} mm")
    col3.metric(
        "Volumen para tu parcela",
        f"{fmt_es(summary['volume_total_m3'], 0)} m³"
        if summary["volume_total_m3"] is not None else "indica superficie",
    )
    col4.metric(
        "Días calculables",
        f"{summary['days_with_recommendation']} de {summary['days_requested']}",
    )
    if live_case and issue == tomorrow:
        st.warning(
            "Los días posteriores a mañana son orientativos: se mantiene temporalmente "
            "el último Kc SiAR dentro del mismo mes, la ET0 se estima con observaciones "
            "recientes y la lluvia solo se descuenta cuando AEMET aporta mm horarios "
            "completos. Una lluvia sin cantidad disponible no significa lluvia cero. "
            "Recalcula antes de regar cada día."
        )
    if summary["days_with_recommendation"] < summary["days_requested"]:
        st.warning(
            "El acumulado solo suma los días calculables; no representa una dosis "
            "para todo el horizonte seleccionado."
        )

left, right = st.columns([3, 2])
with left:
    st.subheader("Recomendación diaria")
    fig, axis = plt.subplots(figsize=(7.5, 3.2))
    labels = daily["date"].dt.strftime("%d/%m")
    axis.bar(labels, daily["gross_dose_mm"], color="#5FA8D3", label="Dosis bruta")
    axis.plot(labels, daily["net_need_mm"], color="#E07A1F", marker="o", label="Necesidad neta")
    if show_reference:
        reference = daily["date"].map(history.set_index("date")["net_need_mm"])
        axis.plot(labels, reference, color="#1B4965", marker="s", ls="--",
                  label="Referencia SiAR")
    axis.set_ylabel("mm/día")
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False, fontsize=8)
    st.pyplot(fig)
    plt.close(fig)

with right:
    st.subheader("Fundamento")
    method = summary["main_method"]
    st.markdown(f"**Método principal:** {METHOD_LABELS.get(method, 'sin método')}")
    st.markdown(f"**Eficiencia aplicada:** {fmt_es(summary['efficiency'] * 100, 0)} %")
    if summary["allocation_factor"] < 1:
        st.markdown(
            f"**Reducción por dotación:** se aplica el "
            f"{fmt_es(summary['allocation_factor'] * 100, 0)} % de la dosis planificada"
        )
    st.markdown(
        f"**Fuente:** {metadata.get('source', 'SiAR')}, descargada el "
        f"{metadata.get('retrieved_at', 'sin fecha')}"
    )
    st.markdown(f"**Último dato observado:** {daily['data_last_observed'].iat[0] or 'ninguno'}")

st.subheader("Detalle por día")
table = pd.DataFrame(
    {
        "Fecha": daily["date"].dt.strftime("%d/%m/%Y"),
        "Kc": daily["kc"].map(lambda v: fmt_es(v, 2)),
        "ET0 usada (mm)": daily["et0_used_mm"].map(lambda v: fmt_es(v, 2)),
        "Necesidad neta (mm)": daily["net_need_mm"].map(lambda v: fmt_es(v, 2)),
        "Necesidad sin lluvia hipotética (mm)": daily["base_need_before_rain_mm"].map(lambda v: fmt_es(v, 2)),
        "Lluvia prevista/hipotética (mm)": daily["precipitation_forecast_mm"].map(lambda v: fmt_es(v, 2)),
        "Dosis a aplicar (mm = L/m²)": daily["gross_dose_mm"].map(lambda v: fmt_es(v, 2)),
        "Por hectárea (m³/ha)": daily["gross_dose_mm"].map(
            lambda v: fmt_es(v * 10, 1) if pd.notna(v) else "sin dato"
        ),
        "Volumen (m³)": daily["volume_m3"].map(lambda v: fmt_es(v, 0)),
        "Confianza": daily["confidence"],
        "Avisos": daily["warnings"],
    }
)
st.dataframe(table, hide_index=True, width="stretch")

with st.expander("Explicación de cada recomendación y reglas aplicadas"):
    for _, row in daily.iterrows():
        st.markdown(f"- {row['explanation']}  \n  *Reglas:* {row['rules_applied']}")

st.download_button(
    "Descargar recomendación (CSV)",
    daily.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8"),
    file_name=f"recomendacion_{case.crop.lower()}_{case.station_code}_{issue:%Y%m%d}.csv",
    mime="text/csv",
)
