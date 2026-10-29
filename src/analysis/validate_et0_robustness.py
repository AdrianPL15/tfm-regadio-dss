"""Pruebas de robustez del experimento multianual de ET0.

Compara el modelo completo con una ablacion limitada a la propia ET0 y la
estacionalidad, una persistencia corregida por climatologia y la referencia
operativa de media movil de siete dias. La evaluacion usa origen rodante: cada
anio se predice entrenando exclusivamente con anios anteriores.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.analysis.build_current_statistical_evidence import paired_block_bootstrap
from src.models.train_et0_multiyear import _models, build_feature_table


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/data_samples/et0_multiyear_robustness.csv"
DEFAULT_SUMMARY = ROOT / "docs/data_samples/et0_multiyear_robustness_summary.json"
DEFAULT_PREDICTIONS = ROOT / "docs/data_samples/et0_multiyear_robustness_predictions.csv"
DEFAULT_UNCERTAINTY = ROOT / "docs/data_samples/et0_multiyear_robustness_uncertainty.csv"
DEFAULT_UNCERTAINTY_BY_HORIZON = (
    ROOT / "docs/data_samples/et0_multiyear_uncertainty_by_horizon.csv"
)
STATIONS = {
    "AL01": ROOT / "data/interim/et0_history_AL01_2021_2025.csv",
    "Z06": ROOT / "data/interim/et0_history_Z06_2021_2025.csv",
    "BA08": ROOT / "data/interim/et0_history_BA08_2021_2025.csv",
}


def _seasonally_adjusted_persistence(
    train_history: pd.DataFrame,
    test_table: pd.DataFrame,
) -> pd.Series:
    """Corrige ET0(t) con el cambio climatologico esperado entre t y t+1."""
    observed = train_history.copy()
    observed["date"] = pd.to_datetime(observed["date"], errors="raise")
    observed = observed.dropna(subset=["et0_mm"])
    observed["month_day"] = observed["date"].dt.strftime("%m-%d")
    climatology = observed.groupby("month_day")["et0_mm"].mean()
    if "02-29" not in climatology.index and {"02-28", "03-01"}.issubset(climatology.index):
        climatology.loc["02-29"] = float(
            (climatology.loc["02-28"] + climatology.loc["03-01"]) / 2.0
        )

    current_month_day = pd.to_datetime(test_table["date"]).dt.strftime("%m-%d")
    target_month_day = pd.to_datetime(test_table["prediction_date"]).dt.strftime("%m-%d")
    current_climate = current_month_day.map(climatology)
    target_climate = target_month_day.map(climatology)
    return test_table["baseline_persistence"] + target_climate - current_climate


def _metric_row(
    station: str,
    year: int,
    horizon_days: int,
    method: str,
    y_true: pd.Series,
    pred: np.ndarray,
) -> dict:
    return {
        "station_code": station,
        "test_year": year,
        "horizon_days": horizon_days,
        "method": method,
        "n": int(len(y_true)),
        "mae_mm_day": float(mean_absolute_error(y_true, pred)),
        "rmse_mm_day": float(mean_squared_error(y_true, pred) ** 0.5),
        "r2": float(r2_score(y_true, pred)),
        "bias_mm_day": float(np.mean(np.asarray(pred) - np.asarray(y_true))),
    }


def evaluate_station(
    history: pd.DataFrame,
    station: str,
    test_years: tuple[int, ...] = (2023, 2024, 2025),
    horizon_days: int = 1,
    *,
    return_predictions: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    table, full_features = build_feature_table(history, horizon_days=horizon_days)
    reduced_features = [
        name
        for name in full_features
        if name.startswith("et0_") or name in {"target_day_sin", "target_day_cos"}
    ]
    rows: list[dict] = []
    prediction_rows: list[pd.DataFrame] = []

    for year in test_years:
        train = table[
            (table["prediction_date"].dt.year < year) & table["target_et0_mm"].notna()
        ].copy()
        test = table[
            (table["prediction_date"].dt.year == year) & table["target_et0_mm"].notna()
        ].copy()
        if train.empty or test.empty:
            continue

        train_history = history[pd.to_datetime(history["date"]).dt.year < year].copy()
        test["baseline_seasonal_persistence"] = _seasonally_adjusted_persistence(
            train_history, test
        )
        fair = test.dropna(
            subset=[
                "target_et0_mm",
                "baseline_persistence",
                "baseline_mean_7d",
                "baseline_seasonal_persistence",
            ]
        ).copy()
        y_true = fair["target_et0_mm"]

        for method, column in {
            "Persistencia": "baseline_persistence",
            "Persistencia ajustada estacionalmente": "baseline_seasonal_persistence",
            "Media movil 7 dias": "baseline_mean_7d",
        }.items():
            rows.append(
                _metric_row(
                    station, year, horizon_days, method, y_true, fair[column].to_numpy()
                )
            )

        model_predictions: dict[str, np.ndarray] = {}
        for method, features in {
            "Ridge ET0 + estacionalidad": reduced_features,
            "Ridge completo": full_features,
        }.items():
            model = clone(_models()["Ridge"])
            model.fit(train[features], train["target_et0_mm"])
            pred = np.clip(model.predict(fair[features]), 0, None)
            model_predictions[method] = pred
            rows.append(_metric_row(station, year, horizon_days, method, y_true, pred))

        prediction_rows.append(
            pd.DataFrame(
                {
                    "station_code": station,
                    "test_year": year,
                    "horizon_days": horizon_days,
                    "prediction_date": fair["prediction_date"].dt.date.astype(str),
                    "target_et0_mm": y_true.to_numpy(),
                    "mean_7d_prediction_mm": fair["baseline_mean_7d"].to_numpy(),
                    "seasonal_persistence_prediction_mm": fair[
                        "baseline_seasonal_persistence"
                    ].to_numpy(),
                    "ridge_full_prediction_mm": model_predictions["Ridge completo"],
                    "ridge_reduced_prediction_mm": model_predictions[
                        "Ridge ET0 + estacionalidad"
                    ],
                }
            )
        )

    metrics = pd.DataFrame(rows)
    if not return_predictions:
        return metrics
    predictions = pd.concat(prediction_rows, ignore_index=True) if prediction_rows else pd.DataFrame()
    return metrics, predictions


def build_uncertainty(predictions: pd.DataFrame) -> pd.DataFrame:
    """Cuantifica Ridge frente a las dos referencias y frente a la ablación."""

    rows: list[dict] = []
    for (station, year, horizon), group in predictions.groupby(
        ["station_code", "test_year", "horizon_days"], sort=True
    ):
        target = group["target_et0_mm"]
        ridge_error = (group["ridge_full_prediction_mm"] - target).abs()
        for reference_name, column in {
            "media_7d": "mean_7d_prediction_mm",
            "persistencia_estacional": "seasonal_persistence_prediction_mm",
            "ridge_reducido": "ridge_reduced_prediction_mm",
        }.items():
            reference_error = (group[column] - target).abs()
            result = paired_block_bootstrap(
                reference_error,
                ridge_error,
                replicates=5_000,
                block_days=7,
                seed=42,
            )
            rows.append(
                {
                    "station_code": station,
                    "test_year": int(year),
                    "horizon_days": int(horizon),
                    "comparison": f"{reference_name}_vs_ridge_completo",
                    **result,
                }
            )
    return pd.DataFrame(rows)


def classify_interval(row: pd.Series) -> str:
    """Clasifica el IC95 de referencia - Ridge sin ocultar casos inconclusos."""

    lower = float(row["ci_95_lower_mm_day"])
    upper = float(row["ci_95_upper_mm_day"])
    if lower > 0:
        return "favorece_ridge_completo"
    if upper < 0:
        return "favorece_referencia"
    return "cruza_cero"


def summarize_uncertainty_by_horizon(uncertainty: pd.DataFrame) -> pd.DataFrame:
    """Cuenta la evidencia por contraste y horizonte (nueve ventanas cada uno)."""

    frame = uncertainty.copy()
    frame["interval_class"] = frame.apply(classify_interval, axis=1)
    counts = (
        frame.groupby(["comparison", "horizon_days", "interval_class"], sort=True)
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    for column in (
        "favorece_ridge_completo",
        "cruza_cero",
        "favorece_referencia",
    ):
        if column not in counts:
            counts[column] = 0
    counts["total_ventanas"] = counts[
        ["favorece_ridge_completo", "cruza_cero", "favorece_referencia"]
    ].sum(axis=1)
    return counts[
        [
            "comparison",
            "horizon_days",
            "favorece_ridge_completo",
            "cruza_cero",
            "favorece_referencia",
            "total_ventanas",
        ]
    ]


def build_summary(results: pd.DataFrame, uncertainty: pd.DataFrame | None = None) -> dict:
    comparisons = []
    for (station, year, horizon), group in results.groupby(
        ["station_code", "test_year", "horizon_days"]
    ):
        by_method = group.set_index("method")["mae_mm_day"]
        full = float(by_method["Ridge completo"])
        reduced = float(by_method["Ridge ET0 + estacionalidad"])
        mean_7d = float(by_method["Media movil 7 dias"])
        seasonal = float(by_method["Persistencia ajustada estacionalmente"])
        comparisons.append(
            {
                "station_code": station,
                "test_year": int(year),
                "horizon_days": int(horizon),
                "ridge_full_mae_mm_day": full,
                "ridge_reduced_mae_mm_day": reduced,
                "seasonal_persistence_mae_mm_day": seasonal,
                "mean_7d_mae_mm_day": mean_7d,
                "full_vs_reduced_improvement_pct": 100.0 * (reduced - full) / reduced,
                "full_vs_mean_7d_improvement_pct": 100.0 * (mean_7d - full) / mean_7d,
                "full_beats_reduced": bool(full < reduced),
                "full_beats_mean_7d": bool(full < mean_7d),
                "full_beats_seasonal_persistence": bool(full < seasonal),
            }
        )
    comparison_frame = pd.DataFrame(comparisons)
    summary = {
        "protocol": "rolling_origin_yearly_by_forecast_horizon",
        "test_years": sorted(int(year) for year in results["test_year"].unique()),
        "stations": sorted(results["station_code"].unique().tolist()),
        "comparisons": comparisons,
        "horizons_days": sorted(int(value) for value in results["horizon_days"].unique()),
        "ridge_full_wins_vs_reduced": int(comparison_frame["full_beats_reduced"].sum()),
        "ridge_full_wins_vs_mean_7d": int(comparison_frame["full_beats_mean_7d"].sum()),
        "ridge_full_wins_vs_seasonal_persistence": int(
            comparison_frame["full_beats_seasonal_persistence"].sum()
        ),
        "total_station_years": int(len(comparison_frame)),
    }
    if uncertainty is not None:
        classified = uncertainty.copy()
        classified["interval_class"] = classified.apply(classify_interval, axis=1)
        by_horizon = summarize_uncertainty_by_horizon(uncertainty)
        totals = (
            classified.groupby(["comparison", "interval_class"]).size().unstack(fill_value=0)
        )
        comparison_counts = {}
        for comparison, row in totals.iterrows():
            comparison_counts[comparison] = {
                "favorece_ridge_completo": int(row.get("favorece_ridge_completo", 0)),
                "cruza_cero": int(row.get("cruza_cero", 0)),
                "favorece_referencia": int(row.get("favorece_referencia", 0)),
                "total": int(row.sum()),
            }
        summary["bootstrap"] = {
            "method": "bootstrap pareado por bloques temporales circulares",
            "replicates": 5_000,
            "block_days": 7,
            "seed": 42,
            "comparisons": int(len(uncertainty)),
            "counts_by_comparison": comparison_counts,
            "counts_by_horizon": by_horizon.to_dict(orient="records"),
            "interpretation": (
                "Incertidumbre muestral interna de cada ventana estación-año; "
                "no demuestra transferencia a campañas futuras."
            ),
        }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--uncertainty", type=Path, default=DEFAULT_UNCERTAINTY)
    parser.add_argument(
        "--uncertainty-by-horizon",
        type=Path,
        default=DEFAULT_UNCERTAINTY_BY_HORIZON,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frames = []
    prediction_frames = []
    for station, path in STATIONS.items():
        history = pd.read_csv(path)
        for horizon_days in range(1, 10):
            metrics, predictions = evaluate_station(
                history, station, horizon_days=horizon_days, return_predictions=True
            )
            frames.append(metrics)
            prediction_frames.append(predictions)
    results = pd.concat(frames, ignore_index=True)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    uncertainty = build_uncertainty(predictions)
    uncertainty_by_horizon = summarize_uncertainty_by_horizon(uncertainty)
    summary = build_summary(results, uncertainty)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False, encoding="utf-8")
    predictions.to_csv(args.predictions, index=False, encoding="utf-8")
    uncertainty.to_csv(args.uncertainty, index=False, encoding="utf-8")
    uncertainty_by_horizon.to_csv(
        args.uncertainty_by_horizon, index=False, encoding="utf-8"
    )
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "Ridge completo gana frente a media movil 7 dias en "
        f"{summary['ridge_full_wins_vs_mean_7d']}/{summary['total_station_years']} "
        "combinaciones estacion-anio."
    )


if __name__ == "__main__":
    main()
