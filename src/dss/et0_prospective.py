"""Registro local, inmutable e idempotente de predicciones ET0 prospectivas."""

from __future__ import annotations

import json
from datetime import datetime, timezone
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
        "actual_et0_mm": None,
        "validated_at_utc": None,
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
) -> dict:
    """Cierra predicciones pendientes cuando SiAR ya publicó la ET0 observada."""

    if not log_path.exists():
        summary = {"status": "no_predictions_recorded", "records": 0}
    else:
        log = pd.read_csv(log_path)
        log["validated_at_utc"] = log["validated_at_utc"].astype("string")
        log["status"] = log["status"].astype("string")
        observed = actuals.copy()
        observed["target_date"] = pd.to_datetime(observed["date"]).dt.date.astype(str)
        observed["station_code"] = observed["station_code"].astype(str).str.upper()
        lookup = observed.set_index(["station_code", "target_date"])["et0_mm"]
        stamp = (validated_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
        for index, row in log.loc[log["status"].eq("pending")].iterrows():
            key = (str(row["station_code"]).upper(), str(row["target_date"]))
            if key in lookup.index and pd.notna(lookup.loc[key]):
                log.at[index, "actual_et0_mm"] = float(lookup.loc[key])
                log.at[index, "validated_at_utc"] = stamp
                log.at[index, "status"] = "validated"
        log.to_csv(log_path, index=False, encoding="utf-8")
        valid = log.loc[log["status"].eq("validated")].copy()
        summary = {
            "status": "collecting" if len(valid) < 30 else "minimum_window_reached",
            "records": int(len(log)),
            "validated": int(len(valid)),
            "pending": int(log["status"].eq("pending").sum()),
            "minimum_validation_days": 30,
            "recommended_validation_days": 60,
            "interpretation": (
                "Registro prospectivo; no sustituye la evaluación rolling-origin hasta "
                "alcanzar una ventana temporal suficiente."
            ),
        }
        if not valid.empty:
            actual = pd.to_numeric(valid["actual_et0_mm"])
            for label, column in {
                "ridge": "prediction_et0_mm",
                "mean_7d": "baseline_mean_7d_mm",
                "persistence": "baseline_persistence_mm",
            }.items():
                candidate = pd.to_numeric(valid[column], errors="coerce")
                mask = actual.notna() & candidate.notna()
                if mask.any():
                    summary[f"{label}_mae_mm_day"] = float(
                        (candidate[mask] - actual[mask]).abs().mean()
                    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary
