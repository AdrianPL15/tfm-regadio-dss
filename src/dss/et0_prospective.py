"""Registro local, inmutable e idempotente de predicciones ET0 prospectivas."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = ROOT / "data/raw/siar/prospective_et0/predictions.csv"
DEFAULT_SUMMARY = ROOT / "docs/data_samples/et0_prospective_validation_latest.json"
MINIMUM_GATE_CASES = 30
GATE_WINDOW_CASES = 60
RECOMMENDED_VALIDATION_CASES = 60
MINIMUM_RELATIVE_IMPROVEMENT = 0.05


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
            "status": (
                "collecting"
                if len(consolidated) < MINIMUM_GATE_CASES
                else "minimum_window_reached"
            ),
            "records": int(len(log)),
            "provisional": int(log["status"].eq("provisional").sum()),
            "consolidated": int(len(consolidated)),
            "pending": int(log["status"].eq("pending").sum()),
            "revisions_detected": int(pd.to_numeric(log["revision_count"]).fillna(0).sum()),
            "consolidation_days": consolidation_days,
            "minimum_validation_cases": MINIMUM_GATE_CASES,
            "recommended_validation_cases": RECOMMENDED_VALIDATION_CASES,
            "gate_window_cases": GATE_WINDOW_CASES,
            "minimum_relative_improvement_pct": (
                MINIMUM_RELATIVE_IMPROVEMENT * 100.0
            ),
            "interpretation": (
                "Registro prospectivo; no sustituye la evaluación rolling-origin hasta "
                "alcanzar una ventana temporal suficiente."
            ),
        }
        scoring = consolidated if not consolidated.empty else valid
        scoring = scoring.sort_values(["target_date", "issued_at_utc"])
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
        gate_scoring = consolidated.copy()
        gate_scoring["actual"] = pd.to_numeric(
            gate_scoring.get("actual_et0_latest_mm"), errors="coerce"
        )
        gate_scoring["ridge"] = pd.to_numeric(
            gate_scoring.get("prediction_et0_mm"), errors="coerce"
        )
        gate_scoring["mean_7d"] = pd.to_numeric(
            gate_scoring.get("baseline_mean_7d_mm"), errors="coerce"
        )
        gate_scoring = gate_scoring.dropna(subset=["actual", "ridge", "mean_7d"])
        gate_scoring = gate_scoring.sort_values(["target_date", "issued_at_utc"]).tail(
            GATE_WINDOW_CASES
        )
        summary["gate_evaluation_cases"] = int(len(gate_scoring))
        summary["status"] = (
            "collecting"
            if len(gate_scoring) < MINIMUM_GATE_CASES
            else "minimum_window_reached"
        )
        if not gate_scoring.empty:
            ridge_gate_mae = float((gate_scoring["ridge"] - gate_scoring["actual"]).abs().mean())
            mean_gate_mae = float((gate_scoring["mean_7d"] - gate_scoring["actual"]).abs().mean())
            relative_improvement = (
                (mean_gate_mae - ridge_gate_mae) / mean_gate_mae
                if mean_gate_mae > 0
                else float("-inf")
            )
            summary["gate_ridge_mae_mm_day"] = ridge_gate_mae
            summary["gate_mean_7d_mae_mm_day"] = mean_gate_mae
            summary["observed_relative_improvement_pct"] = (
                relative_improvement * 100.0
                if math.isfinite(relative_improvement)
                else None
            )
        else:
            relative_improvement = float("-inf")

        if len(gate_scoring) < MINIMUM_GATE_CASES:
            summary["deployment_gate"] = "experimental_ridge_collecting_evidence"
            summary["gate_reason"] = (
                f"faltan casos pareados: {len(gate_scoring)}/{MINIMUM_GATE_CASES}"
            )
        elif relative_improvement >= MINIMUM_RELATIVE_IMPROVEMENT:
            summary["deployment_gate"] = "ridge"
            summary["gate_reason"] = (
                "Ridge supera el margen mínimo frente a media 7 días en la ventana reciente"
            )
        else:
            summary["deployment_gate"] = "physical_mean_7d"
            summary["gate_reason"] = (
                "Ridge no alcanza una mejora relativa del 5 % frente a media 7 días"
            )
        summary["gate_rule"] = (
            "Con al menos 30 casos consolidados y pareados, evaluar los 60 más "
            "recientes y usar Ridge solo si reduce al menos un 5 % el MAE de la "
            "media física de 7 días."
        )
        # El agregado anterior se conserva como diagnóstico, pero la operación
        # decide por estación y horizonte, sin compensar grupos entre sí.
        group_gates = {}
        for (station, horizon), group in log.groupby(["station_code", "horizon_days"]):
            paired = group.loc[group["status"].eq("consolidated")].copy()
            for label, column in {
                "actual": "actual_et0_latest_mm", "ridge": "prediction_et0_mm",
                "mean_7d": "baseline_mean_7d_mm",
            }.items():
                paired[label] = pd.to_numeric(paired[column], errors="coerce")
            paired = paired.dropna(subset=["actual", "ridge", "mean_7d"])
            paired = paired.sort_values(["target_date", "issued_at_utc"]).drop_duplicates(
                "target_date", keep="last"
            ).tail(GATE_WINDOW_CASES)
            n_dates = int(paired["target_date"].nunique())
            ridge_mae = float((paired["ridge"] - paired["actual"]).abs().mean()) if n_dates else None
            mean_mae = float((paired["mean_7d"] - paired["actual"]).abs().mean()) if n_dates else None
            improvement = (100 * (mean_mae - ridge_mae) / mean_mae) if mean_mae else None
            decision = (
                "experimental_ridge_collecting_evidence" if n_dates < MINIMUM_GATE_CASES
                else "ridge" if improvement is not None and improvement >= 100 * MINIMUM_RELATIVE_IMPROVEMENT
                else "physical_mean_7d"
            )
            group_gates[f"{str(station).upper()}:h{int(horizon)}"] = {
                "deployment_gate": decision, "distinct_target_dates": n_dates,
                "gate_evaluation_cases": len(paired), "ridge_mae_mm_day": ridge_mae,
                "mean_7d_mae_mm_day": mean_mae,
                "observed_relative_improvement_pct": improvement,
            }
        summary["group_gates"] = group_gates
        summary["operational_gate_scope"] = "station_and_horizon"
        summary["distinct_target_dates"] = int(log["target_date"].nunique())
        summary["gate_rule"] = (
            "Decisión por estación y horizonte: al menos 30 fechas objetivo distintas, "
            "consolidadas y pareadas; evaluar hasta las 60 más recientes y exigir "
            "una mejora del MAE del 5 %. El agregado global es solo diagnóstico. "
            "El umbral no constituye una prueba de significación estadística."
        )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary
