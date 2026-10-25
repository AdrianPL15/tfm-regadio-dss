"""Interfaz de demostración del sistema de apoyo a la decisión.

Se ejecuta desde la raíz del repositorio con:

    streamlit run src/dss/app_streamlit.py
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

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
from src.dss.aemet_forecast import fetch_live_forecast, prepare_live_forecast  # noqa: E402
from src.data.aemet_client import AEMETClient, AEMETError  # noqa: E402
from src.data.refresh_siar_crop_needs import SiARRefreshError, fetch_validated_case  # noqa: E402
from src.dss.engine import METHOD_LABELS, fmt_es, recommend  # noqa: E402
from src.dss.live_calendar import extend_recent_kc  # noqa: E402
from src.dss.predict_etc import ModelUnavailable, predict_tomorrow_etc  # noqa: E402


st.set_page_config(page_title="DSS de riego", layout="wide")
consulted_at = datetime.now(ZoneInfo("Europe/Madrid")).replace(tzinfo=None)
today = consulted_at.date()
tomorrow = today + timedelta(days=1)


@st.cache_data(ttl=900)
def _load(source: str, metadata: str):
    case = CropCase(source_file=Path(source), metadata_file=Path(metadata))
    return load_case(case)


def _absolute(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _active_for_today(item: CropCase) -> bool:
    """Selecciona un ejemplo vigente; el dato real se verifica otra vez al cargarlo."""
    if item.campaign_year != today.year:
        return False
    history, metadata = _load(str(_absolute(item.source_file)), str(_absolute(item.metadata_file)))
    last = history.iloc[-1]
    return (
        today.month in metadata.get("active_months", [])
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
        (item.crop for item in province_cases if _active_for_today(item)),
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
    aemet_time_key = f"aemet_consulta_{case.station_code}"
    generate = st.button("Actualizar fuentes y generar recomendación", type="primary")
    if generate:
        st.session_state.pop(snapshot_key, None)
        st.session_state.pop(aemet_key, None)
        st.session_state.pop(aemet_time_key, None)

    history, metadata = _load(
        str(_absolute(case.source_file)), str(_absolute(case.metadata_file))
    )
    if generate and case.campaign_year == today.year:
        try:
            with st.spinner("Consultando necesidades hídricas en SiAR…"):
                content, fresh_metadata, additions = fetch_validated_case(
                    metadata, _absolute(case.source_file).read_bytes(), today
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
    live_case = (
        case.campaign_year == today.year
        and today.month in metadata.get("active_months", [])
        and 0 <= (today - last_day).days <= 2
        and history["record_status"].iloc[-1] == "completo"
        and float(history["kc"].iloc[-1]) > 0
    )
    active_dates = history.loc[history["kc"].gt(0), "date"]
    historical_example = active_dates.max().date() if not active_dates.empty else last_day
    if generate and case.campaign_year == today.year and today.month in metadata.get("active_months", []):
        try:
            with st.spinner("Consultando la previsión municipal de AEMET…"):
                try:
                    cloud_key = st.secrets.get("AEMET_API_KEY")
                except (FileNotFoundError, KeyError):
                    cloud_key = None
                provider = AEMETClient(api_key=cloud_key or os.getenv("AEMET_API_KEY"))
                st.session_state[aemet_key] = fetch_live_forecast(
                    case.aemet_municipality_code, client=provider,
                    consulted_at=consulted_at,
                )
                st.session_state[aemet_time_key] = consulted_at
            st.success("Respuesta AEMET recibida; se comprobará su vigencia antes de usarla.")
        except (AEMETError, ValueError) as error:
            st.warning(f"AEMET no está disponible; se mostrará la dosis base: {error}")
    st.header("Consulta")
    mode_label = st.radio(
        "Modo",
        ["Recomendación (hoy o mañana)", "Revisión histórica (día cerrado)"],
    )
    mode = "planificacion" if mode_label.startswith("Recomendación") else "seguimiento"
    issue_key = f"fecha_{case.station_code}_{case.crop}_{case.campaign_year}_{mode}"
    if issue_key not in st.session_state:
        st.session_state[issue_key] = (
            today if mode == "planificacion" and live_case
            else historical_example if case.campaign_year == today.year
            else min(max(default_issue, first_day), last_day)
        )
    if generate and live_case and mode == "planificacion":
        st.session_state[issue_key] = today
    latest_selectable = (
        tomorrow if mode == "planificacion" and live_case
        and tomorrow.month in metadata.get("active_months", [])
        else today if mode == "planificacion" and live_case else last_day
    )
    if not first_day <= st.session_state[issue_key] <= latest_selectable:
        st.session_state[issue_key] = min(
            max(st.session_state[issue_key], first_day), latest_selectable
        )
    issue = st.date_input(
        "Primer día a recomendar",
        min_value=first_day,
        max_value=latest_selectable,
        format="DD/MM/YYYY",
        key=issue_key,
    )
    operational_view = (
        mode == "planificacion" and live_case and issue in {today, tomorrow}
        and issue.month in metadata.get("active_months", [])
    )
    horizon = st.slider(
        "Horizonte orientativo (días)", 1, MAX_HORIZON_DAYS,
        MAX_HORIZON_DAYS if live_case else 7,
    )
    if operational_view:
        st.caption(
            "El primer día es la recomendación principal para la fecha elegida. "
            "Los siguientes son una "
            "previsión provisional, que conviene recalcular con nuevos datos SiAR y AEMET."
        )
    if case.campaign_year == today.year and not live_case:
        if today.month not in metadata.get("active_months", []) or float(history["kc"].iloc[-1]) <= 0:
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
    elif operational_view:
        rain_fraction = st.slider(
            "Lluvia prevista aprovechable, supuesto (%)", 0, 100, 50, 5
        ) / 100
        st.caption(
            "La fracción es orientativa. Para hoy solo se consideran las horas "
            "que quedan; para mañana se exige el día completo con mm numéricos."
        )

live_forecast = st.session_state.get(aemet_key)
forecast_input = None
if live_forecast is not None:
    if operational_view and not use_scenario:
        try:
            if issue == today and (
                consulted_at - st.session_state.get(aemet_time_key, consulted_at)
            ) > timedelta(minutes=15):
                raise ValueError(
                    "La consulta AEMET para hoy tiene más de 15 minutos; actualiza las fuentes."
                )
            forecast_input = prepare_live_forecast(
                live_forecast, target_day=issue, consulted_at=consulted_at,
            )
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
        extend_recent_kc(history, metadata, target_day=issue, as_of=today, horizon_days=horizon)
        if operational_view else history
    )
    model_estimate = None
    if operational_view:
        try:
            model_estimate = predict_tomorrow_etc(case, calculation_history, issue)
        except (ModelUnavailable, OSError, ImportError) as error:
            st.warning(f"Modelo no disponible; se usa el cálculo físico SiAR: {error}")
    result = recommend(
        request, history=calculation_history, metadata=metadata,
        forecast=forecast_input,
        model_estimate=(
            model_estimate if model_estimate and model_estimate["deploy_model_for_dose"]
            else None
        ),
    )
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
historical_view = not operational_view
st.subheader(
    f"{'Ejemplo histórico' if historical_view else 'Riego recomendado'} "
    f"· {first['date']:%d/%m/%Y}"
)
if historical_view:
    st.warning("Esta cifra es de un día ya cerrado. No es una dosis para regar hoy.")
elif issue == today:
    st.info(
        "La dosis representa la necesidad orientativa de todo el día. "
        "Se descuenta solo la lluvia prevista para las horas restantes; "
        "la aplicación no conoce el riego ni la lluvia ya ocurridos hoy. "
        "Si ya has regado, ajusta la cantidad antes de aplicarla."
    )
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
    if first["method"] == "modelo_etc":
        st.caption(
            f"Demanda antes de lluvia estimada con {first['predictive_model']} "
            f"({fmt_es(first['base_need_before_rain_mm'])} mm de ETc). "
            "Después se aplica la lluvia prevista disponible y la eficiencia del riego."
        )
    elif model_estimate is not None:
        st.caption(
            f"Modelo {model_estimate['model']} comprobado: "
            f"{fmt_es(model_estimate['etc_mm'])} mm de ETc. Se mantiene la "
            "estimación física para la dosis porque tuvo menos error en la "
            "prueba histórica de este caso o porque faltan observaciones de "
            "algún día intermedio."
        )
    if operational_view and not use_scenario:
        if forecast_input is None:
            if live_forecast is None:
                st.info(
                    "Esta dosis todavía no descuenta lluvia prevista. Pulsa «Actualizar fuentes y "
                    "generar recomendación» para consultar AEMET."
                )
            else:
                st.info(
                    "La previsión recibida no es utilizable para esta consulta; "
                    "no se descuenta lluvia. Actualiza las fuentes cuando haya "
                    "una emisión vigente o una consulta reciente para hoy."
                )
        elif pd.isna(first["precipitation_forecast_mm"]):
            st.info(
                "AEMET no aporta una cantidad de lluvia utilizable para la fecha "
                "elegida; no se descuenta lluvia."
            )
        else:
            st.caption(
                f"Lluvia prevista para {'hoy (horas restantes)' if issue == today else 'mañana'}: "
                f"{fmt_es(first['precipitation_forecast_mm'])} mm "
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
    if operational_view:
        st.warning(
            "Los días posteriores al primero son orientativos: se mantiene temporalmente "
            "el último Kc SiAR dentro del mismo mes, la ET0 se estima con observaciones "
            "recientes y la lluvia solo se descuenta cuando AEMET aporta mm horarios "
            "utilizables. Una lluvia sin cantidad disponible no significa lluvia cero. "
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
    method = first["method"]
    st.markdown(f"**Método del primer día:** {METHOD_LABELS.get(method, 'sin método')}")
    if summary["main_method"] != method:
        st.markdown(
            f"**Método principal del periodo:** "
            f"{METHOD_LABELS.get(summary['main_method'], 'sin método')}"
        )
    if method == "modelo_etc":
        st.caption(
            f"Modelo entrenado con SiAR hasta {first['model_trained_through']}; "
            "predice ETc para el primer día. La lluvia AEMET se descuenta después, "
            "solo cuando hay cantidad horaria utilizable y según la fracción supuesta."
        )
    if model_estimate is not None:
        st.markdown(
            f"**Comparación ETc:** modelo {fmt_es(model_estimate['etc_mm'])} mm; "
            f"método usado {fmt_es(first['base_need_before_rain_mm'])} mm. "
            f"MAE de prueba: modelo {fmt_es(model_estimate['test_mae_mm_day'], 2)} "
            "mm/día; físico "
            f"{fmt_es(model_estimate['physical_baseline_test_mae_mm_day'], 2)} mm/día."
        )
        st.caption(
            "La elección operativa utiliza este tramo de prueba como control de "
            "calidad; esas métricas no son una evaluación independiente del sistema "
            "completo desplegado."
        )
        if model_estimate["steps_ahead"] > 1:
            st.warning(
                f"La predicción comparativa avanzó {model_estimate['steps_ahead']} "
                "días desde la última ETc observada. Esta extrapolación no se "
                "evaluó y nunca modifica la dosis principal."
            )
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
        "no a la parcela, y solo se aplica al día seleccionado si es utilizable."
    )

if live_forecast is not None:
    with st.expander("Ver previsión recibida de AEMET"):
        if not operational_view or use_scenario:
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
        "Modelo del primer día": daily["predictive_model"].fillna("cálculo físico"),
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
