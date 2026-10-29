"""Evalúa la robustez y el impacto agronómico del experimento ET0 multianual."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.analysis.build_current_statistical_evidence import paired_block_bootstrap


DATA_SAMPLES = Path("docs/data_samples")
DEFAULT_PREDICTIONS = DATA_SAMPLES / "et0_multiyear_predictions_2025.csv"
DEFAULT_CROP = Path("data/external/siar_necesidades_pimiento_AL01_2025.csv")
DEFAULT_STATISTICS = DATA_SAMPLES / "et0_multiyear_statistical_evidence.csv"
DEFAULT_IMPACT = DATA_SAMPLES / "et0_multiyear_irrigation_impact.csv"
DEFAULT_SUMMARY = DATA_SAMPLES / "et0_multiyear_evaluation_summary.json"
MODEL_COLUMNS = ("Ridge", "Random Forest", "HistGradientBoosting", "XGBoost")


def _read_crop(path: Path) -> pd.DataFrame:
    crop = pd.read_csv(path, sep=";", decimal=",")
    crop = crop.rename(
        columns={
            "Fecha": "date",
            "Kc": "kc",
            "ET0 (mm)": "siar_et0_mm",
            "ETc (mm)": "siar_etc_mm",
            "Pe (mm)": "effective_precipitation_mm",
            "ETc - Pe (mm)": "siar_net_need_mm",
            "ET0": "siar_et0_mm",
            "ETc": "siar_etc_mm",
            "Pe": "effective_precipitation_mm",
            "ETc - Pe": "siar_net_need_mm",
        }
    )
    crop["date"] = pd.to_datetime(crop["date"], dayfirst=True)
    return crop


def statistical_comparisons(predictions: pd.DataFrame) -> pd.DataFrame:
    """Bootstrap pareado por bloques contra persistencia, con semilla fija."""

    target = predictions["target_et0_mm"]
    reference_error = (predictions["Persistencia"] - target).abs()
    records: list[dict] = []
    for model in MODEL_COLUMNS:
        candidate_error = (predictions[model] - target).abs()
        result = paired_block_bootstrap(
            reference_error,
            candidate_error,
            replicates=5_000,
            block_days=7,
            seed=42,
        )
        records.append({"comparison": f"Persistencia frente a {model}", **result})
    return pd.DataFrame(records)


def irrigation_impact(predictions: pd.DataFrame, crop: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Propaga ET0 predicha a ETc y necesidad neta con Kc y Pe observados.

    Pe observada se utiliza únicamente para una evaluación retrospectiva aislada
    del error de ET0; no representa la previsión operativa de AEMET.
    """

    frame = crop.merge(predictions, left_on="date", right_on="prediction_date", how="inner")
    methods = ("Persistencia", "Ridge", "Random Forest", "HistGradientBoosting", "XGBoost")
    rows: list[dict] = []
    for method in methods:
        etc = frame[method] * frame["kc"]
        net = np.maximum(0.0, etc - frame["effective_precipitation_mm"])
        frame[f"etc_{method}_mm"] = etc
        frame[f"net_need_{method}_mm"] = net
        rows.append(
            {
                "method": method,
                "n_days": int(len(frame)),
                "etc_mae_mm_day": float(mean_absolute_error(frame["siar_etc_mm"], etc)),
                "etc_rmse_mm_day": float(mean_squared_error(frame["siar_etc_mm"], etc) ** 0.5),
                "net_need_mae_mm_day": float(mean_absolute_error(frame["siar_net_need_mm"], net)),
                "net_need_rmse_mm_day": float(mean_squared_error(frame["siar_net_need_mm"], net) ** 0.5),
                "campaign_net_need_predicted_mm": float(net.sum()),
                "campaign_net_need_reference_mm": float(frame["siar_net_need_mm"].sum()),
            }
        )
    return pd.DataFrame(rows), frame


def build(
    predictions_path: Path = DEFAULT_PREDICTIONS,
    crop_path: Path = DEFAULT_CROP,
    statistics_path: Path = DEFAULT_STATISTICS,
    impact_path: Path = DEFAULT_IMPACT,
    summary_path: Path = DEFAULT_SUMMARY,
    crop_name: str = "Pimiento",
    station_code: str = "AL01",
) -> dict:
    predictions = pd.read_csv(predictions_path)
    predictions["prediction_date"] = pd.to_datetime(predictions["prediction_date"])
    crop = _read_crop(crop_path)

    statistics = statistical_comparisons(predictions)
    impact, detail = irrigation_impact(predictions, crop)
    statistics_path.parent.mkdir(parents=True, exist_ok=True)
    statistics.to_csv(statistics_path, index=False)
    impact.to_csv(impact_path, index=False)

    ridge_stat = statistics.loc[statistics["comparison"].str.endswith("Ridge")].iloc[0]
    persistence = impact.loc[impact["method"] == "Persistencia"].iloc[0]
    ridge = impact.loc[impact["method"] == "Ridge"].iloc[0]
    summary = {
        "test_year": 2025,
        "paired_days_et0": int(ridge_stat["n"]),
        "bootstrap": {
            "method": "bootstrap pareado por bloques temporales circulares",
            "replicates": 5_000,
            "block_days": 7,
            "seed": 42,
            "ridge_vs_persistence_mae_difference_mm_day": float(ridge_stat["observed_difference_mm_day"]),
            "ci_95_mm_day": [
                float(ridge_stat["ci_95_lower_mm_day"]),
                float(ridge_stat["ci_95_upper_mm_day"]),
            ],
            "probability_difference_positive": float(ridge_stat["probability_difference_positive"]),
        },
        "irrigation_impact": {
            "crop": crop_name,
            "station": station_code,
            "paired_days": int(len(detail)),
            "persistence_net_need_mae_mm_day": float(persistence["net_need_mae_mm_day"]),
            "ridge_net_need_mae_mm_day": float(ridge["net_need_mae_mm_day"]),
            "relative_mae_improvement_pct": float(
                100 * (persistence["net_need_mae_mm_day"] - ridge["net_need_mae_mm_day"])
                / persistence["net_need_mae_mm_day"]
            ),
            "note": "Evaluación retrospectiva con Pe observada; no valida todavía la previsión AEMET.",
        },
        "integration_decision": "pending_geographical_validation_and_operational_design",
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--crop", type=Path, default=DEFAULT_CROP)
    parser.add_argument("--statistics", type=Path, default=DEFAULT_STATISTICS)
    parser.add_argument("--impact", type=Path, default=DEFAULT_IMPACT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--crop-name", default="Pimiento")
    parser.add_argument("--station-code", default="AL01")
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                args.predictions,
                args.crop,
                args.statistics,
                args.impact,
                args.summary,
                args.crop_name,
                args.station_code,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
