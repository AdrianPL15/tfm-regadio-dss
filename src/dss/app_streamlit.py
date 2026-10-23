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
from src.dss.data_access import load_case, load_crop_needs_bytes  # noqa: E402
from src.dss.aemet_forecast import fetch_live_forecast, require_current_forecast  # noqa: E402
from src.data.aemet_client import AEMETClient, AEMETError  # noqa: E402
from src.data.refresh_siar_crop_needs import SiARRefreshError, fetch_validated_case  # noqa: E402
from src.dss.engine import METHOD_LABELS, fmt_es, recommend  # noqa: E402
from src.dss.live_calendar import extend_recent_kc  # noqa: E402


st.set_page_config(page_title="DSS de riego", layout="wide")


@st.cache_data(ttl=900)
def _load(source: str, metadata: str):
    case = CropCase(source_file=Path(source), metadata_file=Path(metadata))
    return load_case(case)


def _absolute(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _active_for_tomorrow(item: CropCase) -> bool:
    """Selecciona un ejemplo vigente; el dato real se verifica otra vez al cargarlo."""
    today = date.today()
    if item.campaign_year != today.year:
        return False
    history, metadata = _load(str(_absolute(item.source_file)), str(_absolute(item.metadata_file)))
    last = history.iloc[-1]
    return (
        (today + timedelta(days=1)).month in metadata.get("active_months", [])
        and last["record_status"] == "completo"
        and float(last["kc"]) > 0
    )


params = st.query_params
try:
    default_issue = date.fromisoformat(params.get("fecha", "2025-06-28"))
except ValueError:
    default_issue = date(2025, 6, 28)

st.title("¿Cuánto regar?")
st.caption(
    "Elige cultivo y zona a la izquierda. Verás una dosis orientativa para tu parcela; "
    "confírmala con el estado real del cultivo y el criterio técnico."
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
    preferred_crop = next(
        (item.crop for item in province_cases if _active_for_tomorrow(item)),
        crop_options[0],
    )
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

    snapshot_key = f"siar_{case.station_code}_{case.crop}_{case.campaign_year}"
    aemet_key = f"aemet_{case.station_code}"
    generate = st.button("Actualizar fuentes y generar recomendación", type="primary")
    if generate:
        st.session_state.pop(snapshot_key, None)
        st.session_state.pop(aemet_key, None)

    history, metadata = _load(
        str(_absolute(case.source_file)), str(_absolute(case.metadata_file))
    )
    if generate and case.campaign_year == date.today().year:
        try:
            with st.spinner("Consultando necesidades hídricas en SiAR…"):
                content, fresh_metadata, additions = fetch_validated_case(
                    metadata, _absolute(case.source_file).read_bytes(), date.today()
                )
                fresh_history = load_crop_needs_bytes(
                    content, f"SiAR web: {case.crop} {case.station_code}"
                )
            st.session_state[snapshot_key] = (fresh_history, fresh_metadata)
            st.success(
                f"SiAR consultado: {len(additions)} jornadas nuevas; "
                f"última observación {fresh_metadata['last_returned_date']}."
            )
        except (SiARRefreshError, OSError, ValueError) as error:
            st.warning(
                "No se pudo validar la descarga de SiAR. Se utilizará la "
                f"instantánea guardada: {error}"
            )
    if snapshot_key in st.session_state:
        history, metadata = st.session_state[snapshot_key]

    first_day = history["date"].min().date()
    last_day = history["date"].max().date()
    tomorrow = date.today() + timedelta(days=1)
    live_case = (
        case.campaign_year == date.today().year
        and tomorrow.month in metadata.get("active_months", [])
        and 0 <= (date.today() - last_day).days <= 2
        and history["record_status"].iloc[-1] == "completo"
        and float(history["kc"].iloc[-1]) > 0
    )
    issue_key = f"fecha_{case.station_code}_{case.crop}_{case.campaign_year}"
    if generate and live_case:
        st.session_state[issue_key] = tomorrow
    if generate and case.campaign_year == date.today().year and tomorrow.month in metadata.get("active_months", []):
        try:
            with st.spinner("Consultando la previsión municipal de AEMET…"):
                try:
                    cloud_key = st.secrets.get("AEMET_API_KEY")
                except (FileNotFoundError, KeyError):
                    cloud_key = None
                provider = AEMETClient(api_key=cloud_key or os.getenv("AEMET_API_KEY"))
                st.session_state[aemet_key] = fetch_live_forecast(
                    case.aemet_municipality_code, client=provider
                )
            st.success("Previsión AEMET recibida.")
        except (AEMETError, ValueError) as error:
            st.warning(f"AEMET no está disponible; se mostrará la dosis base: {error}")
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
        key=issue_key,
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
        if tomorrow.month not in metadata.get("active_months", []) or float(history["kc"].iloc[-1]) <= 0:
            st.warning(
                "No hay predicción actual: este cultivo figura fuera de su periodo "
                "de ciclo en SiAR (Kc nulo o mes no activo). Hay datos históricos, "
                "pero no se aplicará la previsión AEMET de hoy."
            )
        else:
            st.warning(
                "No hay predicción actual: falta una observación SiAR reciente y "
                "completa. Prueba a actualizar las fuentes."
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

live_forecast = st.session_state.get(aemet_key)
forecast_input = None
if live_forecast is not None:
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

st.caption(
    f"{case.crop} · {case.station_name} ({case.province}) · "
    f"Parcela de {fmt_es(area, 2)} ha"
)
for warning in result.warnings:
    st.warning(warning)

first = daily.iloc[0]
historical_view = case.campaign_year != date.today().year or not live_case or issue != tomorrow
st.subheader(
    f"{'Ejemplo histórico' if historical_view else 'Riego recomendado'} "
    f"· {first['date']:%d/%m/%Y}"
)
if historical_view:
    st.warning("Esta cifra es de un día pasado. No es una dosis para regar mañana.")
if pd.notna(first["gross_dose_mm"]):
    dose = float(first["gross_dose_mm"])
    first_volume = first["volume_m3"]
    col1, col2, col3 = st.columns([2, 1, 1])
    col1.metric("Agua por metro cuadrado", f"{fmt_es(dose)} L/m²")
    col2.metric("Para tu parcela",
        f"{fmt_es(first_volume, 0)} m³" if pd.notna(first_volume) else "indica superficie",
    )
    col3.metric("Por hectárea", f"{fmt_es(dose * 10, 0)} m³/ha")
    st.caption(
        f"Equivale a {fmt_es(dose)} mm de lámina de agua. "
        f"Necesidad neta del cultivo: {fmt_es(first['net_need_mm'])} mm. "
        "La dosis indicada considera la eficiencia del riego."
    )
    if live_case and issue == tomorrow and not use_scenario:
        if forecast_input is None:
            st.info(
                "Esta dosis todavía no descuenta lluvia prevista. Pulsa «Actualizar fuentes y "
                "generar recomendación» para incorporar los datos de AEMET."
            )
        elif pd.isna(first["precipitation_forecast_mm"]):
            st.info("AEMET no aporta una cantidad de lluvia completa para mañana; no se descuenta lluvia.")
        else:
            st.caption(
                f"Lluvia prevista para mañana: {fmt_es(first['precipitation_forecast_mm'])} mm "
                f"(fracción aprovechable supuesta: {fmt_es(rain_fraction * 100, 0)} %)."
            )
else:
    st.warning("No hay datos suficientes para proponer una dosis para el primer día.")

if horizon > 1:
    st.subheader(
        f"{'Periodo histórico de' if historical_view else 'Próximos'} "
        f"{horizon} días · orientación"
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Riego total estimado", f"{fmt_es(summary['gross_dose_total_mm'])} L/m²")
    col2.metric(
        "Para tu parcela en total",
        f"{fmt_es(summary['volume_total_m3'], 0)} m³"
        if summary["volume_total_m3"] is not None else "indica superficie",
    )
    col3.metric(
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

st.subheader("Riego día a día")
fig, axis = plt.subplots(figsize=(7.5, 3.2))
labels = daily["date"].dt.strftime("%d/%m")
axis.bar(labels, daily["gross_dose_mm"], color="#5FA8D3", label="Dosis propuesta")
axis.plot(labels, daily["net_need_mm"], color="#E07A1F", marker="o", label="Necesidad neta")
if show_reference:
    reference = daily["date"].map(history.set_index("date")["net_need_mm"])
    axis.plot(labels, reference, color="#1B4965", marker="s", ls="--",
              label="Referencia SiAR")
axis.set_ylabel("L/m² al día (equivale a mm)")
axis.spines[["top", "right"]].set_visible(False)
axis.legend(frameon=False, fontsize=8)
st.pyplot(fig)
plt.close(fig)

with st.expander("¿De dónde sale esta recomendación?"):
    st.write(
        f"Caso SiAR: {case.crop} · {case.station_code} {case.station_name} "
        f"({case.province}, {case.community}). Datos del {first_day:%d/%m/%Y} "
        f"al {last_day:%d/%m/%Y} "
        f"({metadata.get('record_count', len(history))} registros)."
    )
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
    if case.campaign_year == 2025 and case.crop in {"Maíz", "Algodón"}:
        st.caption(
            "Este caso tiene una evaluación temporal predictiva adicional, independiente "
            "por cultivo; no acredita ahorro ni precisión en campo."
        )
    st.caption(
        "El CSV SiAR identifica cultivo y estación, pero no acredita el sistema de "
        "producción concreto (por ejemplo, aire libre o invernadero)."
    )
    st.caption(
        "Para cultivos activos, el botón consulta SiAR y AEMET. SiAR se usa en memoria "
        "y no altera el CSV de GitHub. La previsión AEMET corresponde al municipio, "
        "no a la parcela, y solo se aplica a fechas futuras compatibles."
    )

if live_forecast is not None:
    with st.expander("Ver previsión recibida de AEMET"):
        if issue != tomorrow or not live_case or use_scenario:
            st.info("Esta previsión se muestra como referencia, pero no se aplica al cálculo histórico o al escenario manual.")
        visible = live_forecast[[
            "date", "precipitation_probability_pct", "precipitation_mm",
            "precipitation_hours_covered", "precipitation_amount_status",
        ]].copy()
        visible["date"] = visible["date"].dt.strftime("%d/%m/%Y")
        st.dataframe(visible, hide_index=True, width="stretch")
        st.caption(
            f"Emisión AEMET: {live_forecast['issued_at'].iat[0]}; "
            f"municipio {case.aemet_municipality_code}."
        )

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
with st.expander("Ver tabla detallada y reglas de cálculo"):
    st.dataframe(table, hide_index=True, width="stretch")
    for _, row in daily.iterrows():
        st.markdown(f"- {row['explanation']}  \n  *Reglas:* {row['rules_applied']}")

st.download_button(
    "Descargar recomendación (CSV)",
    daily.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8"),
    file_name=f"recomendacion_{case.crop.lower()}_{case.station_code}_{issue:%Y%m%d}.csv",
    mime="text/csv",
)
