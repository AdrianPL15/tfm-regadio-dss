"""Cuantifica qué método habría estado disponible durante 2026."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pandas as pd

from src.dss.predict_et0 import history_from_siar_records, predict_et0_with_fallback


ROOT = Path(__file__).resolve().parents[2]
STATIONS = ("AL01", "Z06", "BA08")
RAW_PATTERN = "data/raw/siar/weather/daily/station={station}/period=2026-01-01_2026-10-28/*.json"
DETAIL = ROOT / "docs/data_samples/et0_operational_coverage_2026.csv"
SUMMARY = ROOT / "docs/data_samples/et0_operational_coverage_2026_summary.json"


def _load_station(station: str) -> pd.DataFrame:
    paths = sorted(ROOT.glob(RAW_PATTERN.format(station=station)))
    if not paths:
        raise FileNotFoundError(f"Falta el histórico raw 2026 de {station}")
    envelope = json.loads(paths[-1].read_text(encoding="utf-8"))
    current = history_from_siar_records(envelope["data"], station)
    previous = pd.read_csv(ROOT / f"data/interim/et0_history_{station}_2021_2025.csv")
    previous["date"] = pd.to_datetime(previous["date"])
    return pd.concat([previous, current], ignore_index=True).sort_values("date")


def _classify(method: str) -> str:
    if method.startswith("ridge_et0_multiyear_h"):
        return "ridge"
    if method == "mean_7d_fallback":
        return "mean_7d"
    if method == "persistence_fallback":
        return "persistence"
    return "unavailable"


def build() -> dict:
    rows = []
    for station in STATIONS:
        complete = _load_station(station)
        first_issue = pd.Timestamp("2026-01-01").date()
        last_target = pd.Timestamp("2026-10-28").date()
        for publication_lag in (1, 2):
            last_issue = last_target - timedelta(days=6)
            issue = first_issue
            while issue <= last_issue:
                cutoff = issue - timedelta(days=publication_lag)
                # Solo 14 jornadas pueden alimentar retardos y medias; 45 días
                # preservan holgura para huecos sin reconstruir cinco años por caso.
                available = complete.loc[
                    pd.to_datetime(complete["date"]).dt.date <= cutoff
                ].tail(45)
                for forecast_day in range(1, 8):
                    target = issue + timedelta(days=forecast_day - 1)
                    result = predict_et0_with_fallback(
                        station, available, target, monitoring_path=None
                    )
                    rows.append(
                        {
                            "station_code": station,
                            "issue_date": issue.isoformat(),
                            "assumed_publication_lag_days": publication_lag,
                            "forecast_day": forecast_day,
                            "model_horizon_days": (target - cutoff).days,
                            "target_date": target.isoformat(),
                            "method": result.get("method"),
                            "method_group": _classify(str(result.get("method", ""))),
                            "fallback_reason": result.get("fallback_reason"),
                        }
                    )
                issue += timedelta(days=1)
    detail = pd.DataFrame(rows)
    DETAIL.parent.mkdir(parents=True, exist_ok=True)
    detail.to_csv(DETAIL, index=False, encoding="utf-8")
    grouped = (
        detail.groupby(
            ["station_code", "assumed_publication_lag_days", "forecast_day", "method_group"]
        ).size().rename("days").reset_index()
    )
    totals = grouped.groupby(
        ["station_code", "assumed_publication_lag_days", "forecast_day"]
    )["days"].transform("sum")
    grouped["coverage_pct"] = (100 * grouped["days"] / totals).round(2)
    summary = {
        "year": 2026,
        "forecast_days": 7,
        "publication_lag_scenarios_days": [1, 2],
        "note": (
            "Simulación retrospectiva con disponibilidad final de SiAR y un retraso "
            "fijo supuesto; no reconstruye las horas reales de publicación."
        ),
        "rows": grouped.to_dict(orient="records"),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    result = build()
    print(f"Cobertura calculada: {len(result['rows'])} agregados")
