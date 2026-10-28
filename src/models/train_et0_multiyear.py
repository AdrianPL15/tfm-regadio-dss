"""Experimento aislado de predicción de ET0 a un día para una estación SiAR.

Entrena con 2021-2024 y reserva 2025 completo como prueba. Todas las variables
se construyen con información disponible hasta el día anterior a la fecha que
se predice.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor


DEFAULT_INPUT = Path("data/interim/et0_history_AL01_2021_2025.csv")
DEFAULT_METRICS = Path("docs/data_samples/et0_multiyear_metrics.csv")
DEFAULT_PREDICTIONS = Path("docs/data_samples/et0_multiyear_predictions_2025.csv")
DEFAULT_SUMMARY = Path("docs/data_samples/et0_multiyear_summary.json")

WEATHER_CURRENT = [
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
]


def build_feature_table(
    history: pd.DataFrame,
    horizon_days: int = 1,
) -> tuple[pd.DataFrame, list[str]]:
    if horizon_days < 1:
        raise ValueError("horizon_days debe ser un entero positivo.")
    data = history.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data = data.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    if not data.empty:
        calendar = pd.date_range(data["date"].min(), data["date"].max(), freq="D")
        data = data.set_index("date").reindex(calendar).rename_axis("date").reset_index()
    data["prediction_date"] = data["date"] + pd.Timedelta(days=horizon_days)
    data["target_et0_mm"] = data["et0_mm"].shift(-horizon_days)

    feature_names: list[str] = []
    for lag in (1, 2, 3, 7, 14):
        name = f"et0_lag_{lag}d"
        data[name] = data["et0_mm"].shift(lag - 1)
        feature_names.append(name)
    for window in (3, 7, 14):
        name = f"et0_mean_{window}d"
        data[name] = data["et0_mm"].rolling(window, min_periods=max(2, window // 2)).mean()
        feature_names.append(name)

    for column in WEATHER_CURRENT:
        if column in data.columns:
            name = f"{column}_lag_1d"
            data[name] = data[column]
            feature_names.append(name)

    day = data["prediction_date"].dt.dayofyear
    period = np.where(data["prediction_date"].dt.is_leap_year, 366.0, 365.0)
    data["target_day_sin"] = np.sin(2 * np.pi * day / period)
    data["target_day_cos"] = np.cos(2 * np.pi * day / period)
    feature_names.extend(["target_day_sin", "target_day_cos"])
    data["baseline_persistence"] = data["et0_lag_1d"]
    data["baseline_mean_7d"] = data["et0_mean_7d"]
    data["month_day"] = data["prediction_date"].dt.strftime("%m-%d")
    return data, feature_names


def _models() -> dict[str, object]:
    return {
        "Ridge": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=1.0)),
            ]
        ),
        "Random Forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=300,
                        max_depth=12,
                        min_samples_leaf=3,
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "HistGradientBoosting": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        max_iter=300,
                        learning_rate=0.05,
                        max_leaf_nodes=15,
                        l2_regularization=1.0,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "XGBoost": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    XGBRegressor(
                        n_estimators=400,
                        learning_rate=0.03,
                        max_depth=4,
                        min_child_weight=3,
                        subsample=0.8,
                        colsample_bytree=0.8,
                        reg_lambda=1.0,
                        objective="reg:squarederror",
                        random_state=42,
                        n_jobs=4,
                    ),
                ),
            ]
        ),
    }


def _metric_row(phase: str, model: str, y_true: pd.Series, prediction: np.ndarray) -> dict[str, object]:
    return {
        "phase": phase,
        "model": model,
        "n": int(len(y_true)),
        "mae_mm": float(mean_absolute_error(y_true, prediction)),
        "rmse_mm": float(mean_squared_error(y_true, prediction) ** 0.5),
        "r2": float(r2_score(y_true, prediction)),
        "bias_mm": float(np.mean(np.asarray(prediction) - np.asarray(y_true))),
    }


def run_experiment(history: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    station_codes = history.get("station_code", pd.Series(dtype=str)).dropna().astype(str).unique()
    station_code = str(station_codes[0]) if len(station_codes) == 1 else "UNKNOWN"
    table, features = build_feature_table(history)
    table = table[table["target_et0_mm"].notna()].copy()
    train = table[table["prediction_date"].dt.year <= 2024].copy()
    test = table[table["prediction_date"].dt.year == 2025].copy()
    if train.empty or test.empty:
        raise ValueError("Se requieren datos de entrenamiento hasta 2024 y prueba en 2025.")

    climatology = train.groupby("month_day")["target_et0_mm"].mean()
    train["baseline_climatology"] = train["month_day"].map(climatology)
    test["baseline_climatology"] = test["month_day"].map(climatology)
    fair_test = test.dropna(
        subset=["target_et0_mm", "baseline_persistence", "baseline_mean_7d", "baseline_climatology"]
    ).copy()

    metrics: list[dict[str, object]] = []
    predictions = fair_test[["prediction_date", "target_et0_mm"]].copy()
    for name, column in {
        "Persistencia": "baseline_persistence",
        "Media móvil 7 días": "baseline_mean_7d",
        "Climatología": "baseline_climatology",
    }.items():
        pred = fair_test[column].to_numpy()
        predictions[name] = pred
        metrics.append(_metric_row("test_2025", name, fair_test["target_et0_mm"], pred))

    validation_rows: list[dict[str, object]] = []
    train_valid = train.dropna(subset=["target_et0_mm"]).reset_index(drop=True)
    splitter = TimeSeriesSplit(n_splits=4)
    for name, estimator in _models().items():
        fold_mae = []
        for fold, (train_idx, valid_idx) in enumerate(splitter.split(train_valid), 1):
            fold_train = train_valid.iloc[train_idx]
            fold_valid = train_valid.iloc[valid_idx]
            model = clone(estimator)
            model.fit(fold_train[features], fold_train["target_et0_mm"])
            pred = np.clip(model.predict(fold_valid[features]), 0, None)
            mae = float(mean_absolute_error(fold_valid["target_et0_mm"], pred))
            fold_mae.append(mae)
            validation_rows.append(
                {"phase": f"validation_fold_{fold}", "model": name, "n": len(valid_idx), "mae_mm": mae}
            )
        metrics.append(
            {
                "phase": "validation_mean",
                "model": name,
                "n": int(sum(row["n"] for row in validation_rows if row["model"] == name)),
                "mae_mm": float(np.mean(fold_mae)),
                "rmse_mm": np.nan,
                "r2": np.nan,
                "bias_mm": np.nan,
            }
        )
        fitted = clone(estimator)
        fitted.fit(train_valid[features], train_valid["target_et0_mm"])
        pred = np.clip(fitted.predict(fair_test[features]), 0, None)
        predictions[name] = pred
        metrics.append(_metric_row("test_2025", name, fair_test["target_et0_mm"], pred))

    metrics_frame = pd.DataFrame(metrics)
    validation = metrics_frame[metrics_frame["phase"] == "validation_mean"].sort_values("mae_mm")
    selected = str(validation.iloc[0]["model"])
    test_metrics = metrics_frame[metrics_frame["phase"] == "test_2025"].sort_values("mae_mm")
    summary = {
        "station_code": station_code,
        "target": "ET0 del día siguiente (mm/día)",
        "train_period": [train["prediction_date"].min().date().isoformat(), train["prediction_date"].max().date().isoformat()],
        "test_period": [fair_test["prediction_date"].min().date().isoformat(), fair_test["prediction_date"].max().date().isoformat()],
        "feature_count": len(features),
        "features": features,
        "selected_by_validation": selected,
        "best_test_model": str(test_metrics.iloc[0]["model"]),
        "best_test_mae_mm": float(test_metrics.iloc[0]["mae_mm"]),
        "persistence_test_mae_mm": float(
            test_metrics.loc[test_metrics["model"] == "Persistencia", "mae_mm"].iloc[0]
        ),
        "integration_decision": "pending_statistical_and_irrigation_impact_evaluation",
    }
    predictions["prediction_date"] = predictions["prediction_date"].dt.date.astype(str)
    return metrics_frame, predictions, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    history = pd.read_csv(args.input)
    metrics, predictions, summary = run_experiment(history)
    for path in (args.metrics, args.predictions, args.summary):
        path.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(args.metrics, index=False, encoding="utf-8")
    predictions.to_csv(args.predictions, index=False, encoding="utf-8")
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Seleccionado por validación: {summary['selected_by_validation']}; "
        f"mejor en prueba: {summary['best_test_model']} "
        f"(MAE={summary['best_test_mae_mm']:.3f} mm/día)."
    )


if __name__ == "__main__":
    main()
