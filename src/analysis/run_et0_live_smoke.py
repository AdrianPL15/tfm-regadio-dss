"""Prueba viva del selector experimental ET0 h=1…9 sin tocar Streamlit."""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from src.data.siar_client import SiARClient
from src.dss.predict_et0 import history_from_siar_records, predict_et0_with_fallback
from src.dss.et0_prospective import record_prediction


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/data_samples/et0_live_siar_smoke_latest.json"
RAW_ROOT = ROOT / "data/raw/siar/provisional_et0"
STATIONS = ("AL01", "Z06", "BA08")


def run_live_smoke(
    target_day: date,
    *,
    lookback_days: int = 30,
    output: Path = DEFAULT_OUTPUT,
    stations: tuple[str, ...] = STATIONS,
) -> dict:
    client = SiARClient()
    issued_at = date.today().isoformat()
    results = []
    for station in stations:
        start = target_day - timedelta(days=lookback_days)
        end = target_day - timedelta(days=1)
        try:
            records = client.get_data(
                "Diarios", "ESTACION", station, start, end, calculated=True
            )
            history = history_from_siar_records(records, station)
            snapshot = RAW_ROOT / f"issued={issued_at}" / f"station={station}.csv"
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            history.to_csv(snapshot, index=False, encoding="utf-8")
            prediction = predict_et0_with_fallback(station, history, target_day)
            recorded = record_prediction(prediction)
            last_date = (
                history["date"].max().date().isoformat() if not history.empty else None
            )
            results.append(
                {
                    "station_code": station,
                    "query_start": start.isoformat(),
                    "query_end": end.isoformat(),
                    "records": int(len(history)),
                    "last_observation_date": last_date,
                    "prediction": prediction,
                    "prospective_record_created": recorded,
                    "provisional_snapshot": str(snapshot.relative_to(ROOT)).replace("\\", "/"),
                    "validated_comparison_status": "pending_future_requery",
                }
            )
        except Exception as exc:  # La prueba debe registrar fallos por estación y continuar.
            results.append(
                {
                    "station_code": station,
                    "query_start": start.isoformat(),
                    "query_end": end.isoformat(),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "validated_comparison_status": "not_available",
                }
            )
    report = {
        "experiment": "ET0 multianual: prueba operativa h=1/h=9",
        "issued_at": issued_at,
        "target_date": target_day.isoformat(),
        "results": results,
        "provisional_vs_validated": (
            "Los valores quedan archivados como snapshot provisional. La comparación "
            "solo podrá cerrarse al volver a consultar esas mismas fechas después de "
            "su validación por SiAR."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--lookback-days", type=int, default=30)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--stations", nargs="+", default=list(STATIONS),
        help="Códigos de estación que se consultarán secuencialmente.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    report = run_live_smoke(
        args.target_date,
        lookback_days=args.lookback_days,
        output=args.output,
        stations=tuple(code.upper() for code in args.stations),
    )
    for item in report["results"]:
        prediction = item.get("prediction", {})
        print(
            f"{item['station_code']}: último={item.get('last_observation_date')}, "
            f"método={prediction.get('method', item.get('error_type'))}"
        )
