"""Reconsulta SiAR y compara una instantánea provisional ET0 ya archivada."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

from src.analysis.run_et0_live_smoke import RAW_ROOT, STATIONS
from src.data.siar_client import SiARClient
from src.dss.predict_et0 import history_from_siar_records


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/data_samples/et0_provisional_requery_latest.json"
VALUE_COLUMNS = (
    "et0_mm",
    "temperature_mean_c",
    "temperature_max_c",
    "temperature_min_c",
    "humidity_mean_pct",
    "humidity_max_pct",
    "humidity_min_pct",
    "wind_speed_mean_ms",
    "wind_speed_max_ms",
    "solar_radiation_mj_m2",
    "precipitation_mm",
)


def compare_frames(original: pd.DataFrame, current: pd.DataFrame) -> dict:
    left = original.copy()
    right = current.copy()
    left["date"] = pd.to_datetime(left["date"], errors="raise")
    right["date"] = pd.to_datetime(right["date"], errors="raise")
    common_columns = [
        column for column in VALUE_COLUMNS if column in left.columns and column in right.columns
    ]
    merged = left[["date", *common_columns]].merge(
        right[["date", *common_columns]], on="date", how="outer",
        suffixes=("_snapshot", "_requery"), indicator=True,
    )
    changed_cells = 0
    by_column = {}
    for column in common_columns:
        before = pd.to_numeric(merged[f"{column}_snapshot"], errors="coerce")
        after = pd.to_numeric(merged[f"{column}_requery"], errors="coerce")
        comparable = before.notna() & after.notna()
        delta = (after - before).abs()
        changed = comparable & delta.gt(1e-9)
        changed_cells += int(changed.sum())
        by_column[column] = {
            "comparable_values": int(comparable.sum()),
            "changed_values": int(changed.sum()),
            "max_absolute_change": (
                float(delta[comparable].max()) if comparable.any() else None
            ),
        }
    return {
        "snapshot_rows": int(len(left)),
        "requery_rows": int(len(right)),
        "common_dates": int((merged["_merge"] == "both").sum()),
        "only_snapshot_dates": int((merged["_merge"] == "left_only").sum()),
        "only_requery_dates": int((merged["_merge"] == "right_only").sum()),
        "changed_cells": changed_cells,
        "columns": by_column,
    }


def requery_snapshot(issued_date: date, output: Path = DEFAULT_OUTPUT) -> dict:
    client = SiARClient()
    rows = []
    for station in STATIONS:
        snapshot_path = RAW_ROOT / f"issued={issued_date.isoformat()}" / f"station={station}.csv"
        if not snapshot_path.is_file():
            rows.append({"station_code": station, "status": "snapshot_missing"})
            continue
        snapshot = pd.read_csv(snapshot_path)
        start = pd.to_datetime(snapshot["date"]).min().date()
        end = pd.to_datetime(snapshot["date"]).max().date()
        records = client.get_data(
            "Diarios", "ESTACION", station, start, end, calculated=True
        )
        current = history_from_siar_records(records, station)
        rows.append(
            {
                "station_code": station,
                "status": "compared",
                **compare_frames(snapshot, current),
            }
        )
    report = {
        "snapshot_issued_at": issued_date.isoformat(),
        "requeried_at": date.today().isoformat(),
        "interpretation": (
            "La reconsulta detecta revisiones, pero SiAR no expone aquí una marca que "
            "certifique por sí sola que el valor ya sea definitivo."
        ),
        "results": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issued-date", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(requery_snapshot(args.issued_date, args.output), ensure_ascii=False, indent=2))
