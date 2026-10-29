"""Emite diariamente h=1…9 sin selección manual y revisa valores SiAR previos."""

from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from src.data.siar_client import SiARClient, SiARError
from src.dss.et0_prospective import record_prediction, validate_log
from src.dss.predict_et0 import history_from_siar_records, predict_et0_with_fallback


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs/data_samples/et0_prospective_ledger.csv"
SUMMARY = ROOT / "docs/data_samples/et0_prospective_validation_latest.json"
RUN_REPORT = ROOT / "docs/data_samples/et0_prospective_daily_latest.json"
STATIONS = ("AL01", "Z06", "BA08")


def _fetch_with_quota_retry(client: SiARClient, station: str) -> pd.DataFrame:
    end = datetime.now(ZoneInfo("Europe/Madrid")).date() - timedelta(days=1)
    start = end - timedelta(days=44)
    for attempt in range(2):
        try:
            records = client.get_data(
                "Diarios", "ESTACION", station, start, end, calculated=True
            )
            return history_from_siar_records(records, station)
        except SiARError as exc:
            if attempt == 0 and "máximo de datos" in str(exc):
                time.sleep(65)
                continue
            raise
    raise RuntimeError("reintento SiAR agotado")


def run() -> dict:
    local_today = datetime.now(ZoneInfo("Europe/Madrid")).date()
    if not LEDGER.exists():
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=[
            "issued_at_utc", "station_code", "target_date", "horizon_days",
            "prediction_et0_mm", "baseline_mean_7d_mm", "baseline_persistence_mm",
            "artifact", "artifact_sha256", "actual_et0_first_mm",
            "actual_et0_latest_mm", "actual_first_seen_utc",
            "actual_last_checked_utc", "revision_count", "status",
        ]).to_csv(LEDGER, index=False, encoding="utf-8")
    client = SiARClient()
    histories: list[pd.DataFrame] = []
    station_reports = []
    for station in STATIONS:
        try:
            history = _fetch_with_quota_retry(client, station)
            histories.append(history)
            if history.empty:
                raise ValueError("SiAR no devolvió observaciones")
            last_day = history["date"].max().date()
            created = 0
            methods: dict[str, str] = {}
            for horizon in range(1, 10):
                target = last_day + timedelta(days=horizon)
                prediction = predict_et0_with_fallback(station, history, target)
                methods[str(horizon)] = str(prediction.get("method"))
                created += int(record_prediction(prediction, log_path=LEDGER))
            station_reports.append(
                {
                    "station_code": station,
                    "last_observation_date": last_day.isoformat(),
                    "records_received": int(len(history)),
                    "new_emissions": created,
                    "methods_by_horizon": methods,
                    "status": "ok",
                }
            )
        except (SiARError, ValueError, OSError, KeyError, TypeError) as exc:
            station_reports.append(
                {
                    "station_code": station,
                    "status": "source_error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
    actuals = pd.concat(histories, ignore_index=True) if histories else pd.DataFrame(
        columns=["date", "station_code", "et0_mm"]
    )
    validation = validate_log(actuals, log_path=LEDGER, summary_path=SUMMARY)
    report = {
        "run_date": local_today.isoformat(),
        "selection_policy": "todas las estaciones y h=1…9, sin apertura de la app",
        "stations": station_reports,
        "validation": validation,
    }
    RUN_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
