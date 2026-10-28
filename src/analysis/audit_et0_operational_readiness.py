"""Audita si las fuentes operativas actuales satisfacen el contrato de Ridge ET0."""

from __future__ import annotations

import json
from pathlib import Path

from src.dss.config import DEMO_CASES
from src.dss.data_access import load_case
from src.models.train_et0_multiyear import WEATHER_CURRENT


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "models/experimental_et0_multiyear/manifest.json"
OUTPUT = ROOT / "docs/data_samples/et0_operational_readiness.json"


def build() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    model_required_sources = ["et0_mm", *WEATHER_CURRENT]
    model_required_sources = list(dict.fromkeys(model_required_sources))
    # La app estable carga el mismo esquema de necesidades para todos los casos.
    operational, _ = load_case(next(case for case in DEMO_CASES if case.campaign_year == 2026))
    operational_columns = sorted(operational.columns.tolist())
    missing = sorted(set(model_required_sources).difference(operational_columns))
    # Contrato real del adaptador AEMET municipal utilizado por el DSS.
    aemet_columns = [
        "date", "precipitation_probability_pct", "precipitation_mm",
        "precipitation_hours_covered", "precipitation_amount_status",
        "issued_at", "hourly_issued_at", "municipality_code", "source",
    ]
    report = {
        "model_status": manifest["status"],
        "stations_with_artifact": sorted(manifest["stations"]),
        "required_daily_observation_columns": model_required_sources,
        "streamlit_siar_crop_needs_columns": operational_columns,
        "missing_from_current_streamlit_input": missing,
        "aemet_live_forecast_columns": aemet_columns,
        "aemet_role": (
            "AEMET aporta lluvia prevista para descontarla después de ET0 × Kc; "
            "no sustituye las observaciones SiAR del día anterior usadas por Ridge."
        ),
        "siar_live_adapter": "implemented_and_unit_tested",
        "ridge_integration_gate": "blocked_siar_publication_lag_for_same_day",
        "fallback_enabled": True,
        "required_next_component": (
            "Medir la latencia habitual de publicación SiAR y, si suele superar un día, "
            "evaluar explícitamente un horizonte ET0 de dos días antes de desplegarlo."
        ),
        "decision": (
            "Mantener persistencia en Streamlit: el adaptador ya recupera las columnas "
            "reales, pero Ridge no debe extrapolar dos días sin evaluación específica."
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
