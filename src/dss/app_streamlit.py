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
    "Demostración retrospectiva con tres combinaciones reales de SiAR de 2025. "
    "Las dosis históricas usan CSV versionados. La consulta AEMET actual es "
    "opcional y no se mezcla con fechas de 2025."
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
    crop = st.selectbox("Cultivo", list(dict.fromkeys(item.crop for item in province_cases)))
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
    case = next(item for item in crop_cases if item.station_code == station_code)
    st.caption(
        "Solo aparecen combinaciones con CSV local verificado. La demo no extrae "
        "automáticamente todas las zonas y cultivos de SiAR."
    )

    history, metadata = _load(
        str(_absolute(case.source_file)), str(_absolute(case.metadata_file))
    )
    first_day = history["date"].min().date()
    last_day = history["date"].max().date()

    st.header("Consulta")
    mode_label = st.radio(
        "Modo",
        ["Planificación (solo datos anteriores)", "Seguimiento (días ya cerrados)"],
    )
    mode = "planificacion" if mode_label.startswith("Planificación") else "seguimiento"
    issue = st.date_input(
        "Fecha de emisión",
        value=min(max(default_issue, first_day), last_day),
        min_value=first_day,
        max_value=last_day + timedelta(days=MAX_HORIZON_DAYS),
        format="DD/MM/YYYY",
        key=f"fecha_{case.station_code}_{case.crop}",
    )
    horizon = st.slider("Horizonte (días)", 1, MAX_HORIZON_DAYS, 7)

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
        st.caption("Introducción manual para la campaña de 2025; no es una predicción AEMET histórica.")
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

st.subheader("Predicción municipal AEMET actual")
st.caption(
    "La predicción corresponde al municipio, no a la estación SiAR ni a la parcela. "
    "No se mezcla con las series retrospectivas de 2025."
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
    if issue == date.today() and first_day <= issue <= last_day and not use_scenario:
        try:
            require_current_forecast(live_forecast, issue)
            forecast_input = live_forecast
        except ValueError as error:
            st.warning(str(error))
    else:
        st.info("La fecha elegida no coincide con una campaña SiAR vigente: se muestra AEMET, pero no se usa para calcular la dosis histórica.")

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
    rain_effective_fraction=rain_fraction if mode == "planificacion" else None,
    case=case,
)

st.info(
    f"Caso seleccionado: **{case.crop} · {case.station_code} {case.station_name} "
    f"({case.province}, {case.community})**. Serie diaria del "
    f"{first_day:%d/%m/%Y} al {last_day:%d/%m/%Y} "
    f"({metadata.get('record_count', len(history))} registros descargados)."
)
if case != DEMO_CASES[0]:
    st.caption(
        "Este caso dispone de una evaluación temporal predictiva adicional, "
        "independiente por cultivo; no acredita ahorro ni precisión en campo."
    )
st.caption(
    "El CSV SiAR identifica cultivo y estación, pero no acredita el sistema de "
    "producción concreto (por ejemplo, aire libre o invernadero)."
)

try:
    result = recommend(request, history=history, metadata=metadata, forecast=forecast_input)
except ValueError as error:
    st.error(str(error))
    st.stop()

summary = result.summary
daily = result.daily.copy()

for warning in result.warnings:
    st.warning(warning)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Necesidad neta", f"{fmt_es(summary['net_need_total_mm'])} mm")
col2.metric(
    "Dosis bruta condicionada" if use_scenario else "Dosis bruta propuesta",
    f"{fmt_es(summary['gross_dose_total_mm'])} mm",
)
col3.metric(
    "Volumen estimado",
    f"{fmt_es(summary['volume_total_m3'], 0)} m³" if summary["volume_total_m3"] else "sin superficie",
)
col4.metric(
    "Días con recomendación",
    f"{summary['days_with_recommendation']} de {summary['days_requested']}",
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
        "Dosis bruta (mm)": daily["gross_dose_mm"].map(lambda v: fmt_es(v, 2)),
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
