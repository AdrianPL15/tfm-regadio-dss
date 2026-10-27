"""Validación temporal multicaso del motor de recomendación del DSS.

Amplía el piloto histórico de pimiento con tres campañas activas de 2026:
coliflor en AL01, alfalfa en Z06 y alcachofa en BA08. En cada caso se simula
una recomendación a un día usando solo la información disponible hasta el día
anterior. El 20 % cronológicamente final se reserva como prueba y no se usa
para ajustar la ventana de ET0, que permanece fijada en siete días por el
experimento original.

La referencia sigue siendo la necesidad neta calculada por SiAR. Por tanto,
esta validación mide fidelidad técnica y transferencia entre casos, no ahorro
de agua ni adecuación agronómica en parcelas reales.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.dss.config import DEMO_CASES, ET0_WINDOW_DAYS, CropCase, RecommendationRequest
from src.dss.data_access import load_case
from src.dss.engine import campaign_plan


DATA_SAMPLES = Path("docs/data_samples")
IMAGES = Path("docs/images")
ACTIVE_CASE_NAMES = ("Coliflor", "Alfalfa", "Alcachofa")
TEST_FRACTION = 0.20


def _metrics(error: pd.Series) -> dict[str, float | int]:
    clean = error.dropna()
    return {
        "n": int(clean.size),
        "mae_mm_day": round(float(clean.abs().mean()), 3),
        "rmse_mm_day": round(float(np.sqrt((clean**2).mean())), 3),
        "bias_mm_day": round(float(clean.mean()), 3),
    }


def _active_cases() -> list[CropCase]:
    selected = [
        case
        for case in DEMO_CASES
        if case.campaign_year == 2026 and case.crop in ACTIVE_CASE_NAMES
    ]
    if {case.crop for case in selected} != set(ACTIVE_CASE_NAMES):
        raise ValueError("No están disponibles los tres casos activos previstos.")
    return selected


def _complete_week_error(frame: pd.DataFrame) -> pd.Series:
    weekly = frame.copy()
    weekly["week_start"] = weekly["date"] - pd.to_timedelta(
        weekly["date"].dt.weekday, unit="D"
    )
    totals = weekly.groupby("week_start").agg(
        days=("date", "size"),
        dss_mm=("net_need_mm", "sum"),
        reference_mm=("reference_need_mm", "sum"),
    )
    totals = totals[totals["days"] == 7]
    return totals["dss_mm"] - totals["reference_mm"]


def evaluate_case(case: CropCase) -> tuple[dict[str, Any], pd.DataFrame]:
    history, metadata = load_case(case)
    observed = history.dropna(subset=["et0_mm", "kc", "pe_mm", "net_need_mm"])
    formula = (observed["et0_mm"] * observed["kc"] - observed["pe_mm"]).clip(lower=0)
    formula_error = formula - observed["net_need_mm"]

    plan = campaign_plan(
        RecommendationRequest(
            issue_date=(history["date"].min() + pd.Timedelta(days=1)).date(),
            horizon_days=1,
            case=case,
        ),
        history,
        metadata,
    )
    comparable = plan.dropna(
        subset=["net_need_mm", "persistence_baseline_mm", "reference_need_mm"]
    ).sort_values("date").reset_index(drop=True)
    if len(comparable) < 30:
        raise ValueError(f"{case.crop} {case.station_code} no tiene suficientes días comparables.")

    split = max(1, min(len(comparable) - 1, int(np.floor(len(comparable) * (1 - TEST_FRACTION)))))
    comparable["period"] = "desarrollo"
    comparable.loc[split:, "period"] = "prueba"
    comparable["error_dss_mm"] = comparable["net_need_mm"] - comparable["reference_need_mm"]
    comparable["error_persistence_mm"] = (
        comparable["persistence_baseline_mm"] - comparable["reference_need_mm"]
    )
    comparable["case_id"] = f"{case.crop}_{case.station_code}_{case.campaign_year}"
    comparable["crop"] = case.crop
    comparable["station_code"] = case.station_code

    periods: dict[str, Any] = {}
    for period, group in comparable.groupby("period", sort=False):
        dss = _metrics(group["error_dss_mm"])
        persistence = _metrics(group["error_persistence_mm"])
        improvement = (
            (1 - float(dss["mae_mm_day"]) / float(persistence["mae_mm_day"])) * 100
            if persistence["mae_mm_day"]
            else 0.0
        )
        periods[period] = {
            "dss": dss,
            "persistence": persistence,
            "mae_improvement_vs_persistence_pct": round(improvement, 1),
        }

    weekly_error = _complete_week_error(comparable)
    report = {
        "case_id": f"{case.crop}_{case.station_code}_{case.campaign_year}",
        "crop": case.crop,
        "station_code": case.station_code,
        "station_name": case.station_name,
        "province": case.province,
        "campaign_year": case.campaign_year,
        "source_file": case.source_file.as_posix(),
        "calendar_start": history["date"].min().strftime("%Y-%m-%d"),
        "calendar_end": history["date"].max().strftime("%Y-%m-%d"),
        "formula_check": {
            "days_compared": int(formula_error.size),
            "max_abs_difference_mm": round(float(formula_error.abs().max()), 3),
        },
        "comparable_days": int(len(comparable)),
        "development_days": int((comparable["period"] == "desarrollo").sum()),
        "test_days": int((comparable["period"] == "prueba").sum()),
        "test_start": comparable.loc[split, "date"].strftime("%Y-%m-%d"),
        "period_metrics": periods,
        "weekly": {
            "complete_weeks": int(weekly_error.size),
            "mae_mm": round(float(weekly_error.abs().mean()), 3),
            "max_abs_error_mm": round(float(weekly_error.abs().max()), 3),
        },
        "methods_used": comparable["method"].value_counts().to_dict(),
    }
    return report, comparable


def _plot(summary: pd.DataFrame, output: Path) -> None:
    labels = [f"{row.crop}\n{row.station_code}" for row in summary.itertuples()]
    x = np.arange(len(summary))
    width = 0.36
    fig, axis = plt.subplots(figsize=(8.5, 4.6), dpi=160)
    axis.bar(
        x - width / 2,
        summary["test_mae_dss_mm_day"],
        width,
        label="DSS: ET0 reciente × Kc",
        color="#E07A1F",
    )
    axis.bar(
        x + width / 2,
        summary["test_mae_persistence_mm_day"],
        width,
        label="Persistencia",
        color="#8D99AE",
    )
    axis.set_xticks(x, labels)
    axis.set_ylabel("MAE en prueba (mm/día)")
    axis.set_title("Transferencia temporal del motor a tres cultivos y regiones")
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", color="#D9E2EC", linewidth=0.6)
    axis.set_axisbelow(True)
    axis.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def build(output_dir: Path = DATA_SAMPLES, image_dir: Path = IMAGES) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, Any]] = []
    frames: list[pd.DataFrame] = []
    rows: list[dict[str, Any]] = []

    for case in _active_cases():
        report, comparable = evaluate_case(case)
        cases.append(report)
        frames.append(comparable)
        test = report["period_metrics"]["prueba"]
        rows.append(
            {
                "case_id": report["case_id"],
                "crop": report["crop"],
                "station_code": report["station_code"],
                "station_name": report["station_name"],
                "province": report["province"],
                "calendar_start": report["calendar_start"],
                "calendar_end": report["calendar_end"],
                "comparable_days": report["comparable_days"],
                "development_days": report["development_days"],
                "test_days": report["test_days"],
                "test_start": report["test_start"],
                "test_mae_dss_mm_day": test["dss"]["mae_mm_day"],
                "test_rmse_dss_mm_day": test["dss"]["rmse_mm_day"],
                "test_bias_dss_mm_day": test["dss"]["bias_mm_day"],
                "test_mae_persistence_mm_day": test["persistence"]["mae_mm_day"],
                "test_rmse_persistence_mm_day": test["persistence"]["rmse_mm_day"],
                "test_bias_persistence_mm_day": test["persistence"]["bias_mm_day"],
                "mae_improvement_vs_persistence_pct": test[
                    "mae_improvement_vs_persistence_pct"
                ],
                "weekly_mae_mm": report["weekly"]["mae_mm"],
            }
        )

    summary = pd.DataFrame(rows)
    summary.to_csv(output_dir / "dss_validation_multicaso_5_3.csv", index=False)
    _plot(summary, image_dir / "dss_validation_multicaso_5_3.png")

    pooled = pd.concat(frames, ignore_index=True)
    pooled_test = pooled[pooled["period"] == "prueba"]
    pooled_dss = _metrics(pooled_test["error_dss_mm"])
    pooled_persistence = _metrics(pooled_test["error_persistence_mm"])
    macro_dss = round(float(summary["test_mae_dss_mm_day"].mean()), 3)
    macro_persistence = round(float(summary["test_mae_persistence_mm_day"].mean()), 3)
    report = {
        "objective": "Validación temporal multicaso del motor de recomendación del DSS",
        "scope": "Tres campañas activas de 2026; evaluación técnica frente a la referencia SiAR",
        "cases": cases,
        "aggregate_test": {
            "pooled_dss": pooled_dss,
            "pooled_persistence": pooled_persistence,
            "macro_mae_dss_mm_day": macro_dss,
            "macro_mae_persistence_mm_day": macro_persistence,
            "cases_where_dss_beats_persistence": int(
                (summary["test_mae_dss_mm_day"] < summary["test_mae_persistence_mm_day"]).sum()
            ),
            "total_cases": int(len(summary)),
        },
        "method": {
            "issue_mode": "Recomendación diaria con información disponible hasta t-1",
            "configured_et0_window_days": ET0_WINDOW_DAYS,
            "split": "80 % cronológico para desarrollo y 20 % final para prueba en cada caso",
            "selection": "La ventana no se reajusta por caso ni con el tramo de prueba",
        },
        "limitations": [
            "La referencia es la necesidad neta calculada por SiAR, no el riego aplicado.",
            "Los tres casos pertenecen a una sola campaña, 2026.",
            "No se incorporan predicciones AEMET históricas archivadas antes de cada fecha.",
            "La comparación mide transferencia técnica, no ahorro de agua ni respuesta productiva.",
        ],
    }
    (output_dir / "dss_validation_multicaso_5_3.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DATA_SAMPLES)
    parser.add_argument("--image-dir", type=Path, default=IMAGES)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = build(args.output_dir, args.image_dir)
    print(json.dumps(report["aggregate_test"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
