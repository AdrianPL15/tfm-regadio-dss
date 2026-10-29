"""Registro local, inmutable e idempotente de predicciones ET0 prospectivas."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = ROOT / "data/raw/siar/prospective_et0/predictions.csv"
DEFAULT_SUMMARY = ROOT / "docs/data_samples/et0_prospective_validation_latest.json"


def record_prediction(
    prediction: dict,
    *,
    log_path: Path = DEFAULT_LOG,
    issued_at: datetime | None = None,
) -> bool:
    """Añade una emisión Ridge una sola vez; devuelve ``True`` si se escribió."""

    method = str(prediction.get("method", ""))
    if not method.startswith("ridge_et0_multiyear_h"):
        return False
    issued = issued_at or datetime.now(timezone.utc)
    row = {
        "issued_at_utc": issued.astimezone(timezone.utc).isoformat(),
        "station_code": prediction["station_code"],
        "target_date": prediction["target_date"],
        "horizon_days": int(prediction["horizon_days"]),
        "prediction_et0_mm": float(prediction["et0_mm"]),
        "baseline_mean_7d_mm": prediction.get("baseline_mean_7d_mm"),
        "baseline_persistence_mm": prediction.get("baseline_persistence_mm"),
        "artifact": prediction.get("artifact"),
        "artifact_sha256": prediction.get("artifact_sha256"),
        "actual_et0_first_mm": None,
        "actual_et0_latest_mm": None,
        "actual_first_seen_utc": None,
        "actual_last_checked_utc": None,
        "revision_count": 0,
        "status": "pending",
    }
    key = (row["station_code"], row["target_date"], row["artifact_sha256"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        existing = pd.read_csv(log_path, dtype=str)
        duplicate = (
            existing["station_code"].eq(str(key[0]))
            & existing["target_date"].eq(str(key[1]))
            & existing["artifact_sha256"].fillna("").eq(str(key[2] or ""))
        )
        if duplicate.any():
            return False
        frame = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    else:
        frame = pd.DataFrame([row])
    frame.to_csv(log_path, index=False, encoding="utf-8")
    return True


def validate_log(
    actuals: pd.DataFrame,
    *,
    log_path: Path = DEFAULT_LOG,
    summary_path: Path = DEFAULT_SUMMARY,
    validated_at: datetime | None = None,
    consolidation_days: int = 7,
) -> dict:
    """Guarda la primera ET0, detecta revisiones y consolida tras una espera."""

    if not log_path.exists():
        summary = {"status": "no_predictions_recorded", "records": 0}
    else:
        log = pd.read_csv(log_path)
        migration_defaults = {
            "actual_et0_first_mm": None,
            "actual_et0_latest_mm": None,
            "actual_first_seen_utc": None,
            "actual_last_checked_utc": None,
            "revision_count": 0,
        }
        if "actual_et0_mm" in log.columns:
            migration_defaults["actual_et0_first_mm"] = log["actual_et0_mm"]
            migration_defaults["actual_et0_latest_mm"] = log["actual_et0_mm"]
        for column, default in migration_defaults.items():
            if column not in log.columns:
                log[column] = default
        for column in ("actual_first_seen_utc", "actual_last_checked_utc"):
            log[column] = log[column].astype("string")
        log["status"] = log["status"].astype("string")
        observed = actuals.copy()
        observed["target_date"] = pd.to_datetime(observed["date"]).dt.date.astype(str)
        observed["station_code"] = observed["station_code"].astype(str).str.upper()
        lookup = observed.set_index(["station_code", "target_date"])["et0_mm"]
        checked = (validated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        stamp = checked.isoformat()
        for index, row in log.iterrows():
            key = (str(row["station_code"]).upper(), str(row["target_date"]))
            if key in lookup.index and pd.notna(lookup.loc[key]):
                observed_value = float(lookup.loc[key])
                previous = pd.to_numeric(
                    pd.Series([row.get("actual_et0_latest_mm")]), errors="coerce"
                ).iat[0]
                if pd.isna(previous):
                    log.at[index, "actual_et0_first_mm"] = observed_value
                    log.at[index, "actual_first_seen_utc"] = stamp
                elif not abs(float(previous) - observed_value) < 1e-9:
                    previous_revisions = pd.to_numeric(
                        pd.Series([row.get("revision_count", 0)]), errors="coerce"
                    ).fillna(0).iat[0]
                    log.at[index, "revision_count"] = int(previous_revisions) + 1
                log.at[index, "actual_et0_latest_mm"] = observed_value
                log.at[index, "actual_last_checked_utc"] = stamp
                target = pd.Timestamp(row["target_date"]).date()
                log.at[index, "status"] = (
                    "consolidated"
                    if target <= checked.date() - timedelta(days=consolidation_days)
                    else "provisional"
                )
        log.to_csv(log_path, index=False, encoding="utf-8")
        valid = log.loc[log["status"].isin(["provisional", "consolidated"])].copy()
        consolidated = log.loc[log["status"].eq("consolidated")].copy()
        summary = {
            "status": "collecting" if len(consolidated) < 30 else "minimum_window_reached",
            "records": int(len(log)),
            "provisional": int(log["status"].eq("provisional").sum()),
            "consolidated": int(len(consolidated)),
            "pending": int(log["status"].eq("pending").sum()),
            "revisions_detected": int(pd.to_numeric(log["revision_count"]).fillna(0).sum()),
            "consolidation_days": consolidation_days,
            "minimum_validation_days": 30,
            "recommended_validation_days": 60,
            "interpretation": (
                "Registro prospectivo; no sustituye la evaluación rolling-origin hasta "
                "alcanzar una ventana temporal suficiente."
            ),
        }
        scoring = consolidated if not consolidated.empty else valid
        if not scoring.empty:
            actual = pd.to_numeric(scoring["actual_et0_latest_mm"])
            for label, column in {
                "ridge": "prediction_et0_mm",
                "mean_7d": "baseline_mean_7d_mm",
                "persistence": "baseline_persistence_mm",
            }.items():
                candidate = pd.to_numeric(scoring[column], errors="coerce")
                mask = actual.notna() & candidate.notna()
                if mask.any():
                    summary[f"{label}_mae_mm_day"] = float(
                        (candidate[mask] - actual[mask]).abs().mean()
                    )
        if len(consolidated) < 30:
            summary["deployment_gate"] = "experimental_ridge_collecting_evidence"
        elif (
            summary.get("ridge_mae_mm_day", float("inf"))
            < summary.get("mean_7d_mae_mm_day", float("inf"))
        ):
            summary["deployment_gate"] = "ridge"
        else:
            summary["deployment_gate"] = "physical_mean_7d"
        summary["gate_rule"] = (
            "Con al menos 30 predicciones consolidadas, usar Ridge solo si su MAE "
            "prospectivo es menor que el de la media física de 7 días."
        )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary
