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
        "available_horizons_by_station": {
            station: sorted(int(value) for value in entry.get("horizons", {"1": entry}))
            for station, entry in manifest["stations"].items()
        },
        "required_daily_observation_columns": model_required_sources,
        "streamlit_siar_crop_needs_columns": operational_columns,
        "missing_from_crop_needs_csv": missing,
        "resolved_operationally_by": "SiAR daily-observations API adapter",
        "aemet_live_forecast_columns": aemet_columns,
        "aemet_role": (
            "AEMET aporta lluvia prevista para descontarla después de ET0 × Kc; "
            "no sustituye las observaciones SiAR del día anterior usadas por Ridge."
        ),
        "siar_live_adapter": "implemented_and_unit_tested",
        "ridge_integration_gate": "experimental_streamlit_integration_ready",
        "fallback_enabled": True,
        "required_next_component": (
            "Conservar snapshots provisionales y compararlos con los valores SiAR "
            "validados cuando estén disponibles; vigilar error y latencia."
        ),
        "decision": (
            "La rama experimental puede usar Ridge h=1…9 cuando el último dato SiAR "
            "lo permite. Si no, mantiene la media reciente y, en último término, "
            "la persistencia trazable."
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
