"""Genera la evidencia XAI del apartado 4.3 sobre el corte temporal original.

El análisis explica Random Forest y XGBoost con TreeSHAP. Ambos modelos se
ajustan solo con el periodo de desarrollo y se explican sobre los 23 días del
tramo de prueba ya reservado en ``train_evaluate.py``. De este modo, la capa
XAI no introduce un conjunto de datos ni una partición diferentes.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "tfm-regadio-dss-matplotlib")
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from src.models.train_evaluate import (
    FEATURE_COLUMNS,
    TARGET,
    _models,
    _nonnegative_prediction,
    load_modeling_dataset,
    prepare_modeling_data,
    regression_metrics,
    temporal_holdout,
)


DEFAULT_INPUT = Path("data/processed/modeling_dataset_daily.csv")
DEFAULT_REPORT = Path("docs/data_samples/xai_analysis_4_3.json")
DEFAULT_IMPORTANCE = Path("docs/data_samples/xai_feature_importance_4_3.csv")
DEFAULT_LOCAL = Path("docs/data_samples/xai_local_explanations_4_3.csv")
DEFAULT_FIGURE = Path("docs/images/model_xai_4_3.png")
MODEL_NAMES = ("random_forest", "xgboost")

FEATURE_LABELS = {
    "crop_coefficient_kc": "Kc",
    "day_of_year_sin": "Día del año (seno)",
    "day_of_year_cos": "Día del año (coseno)",
    "net_irrigation_need_mm_lag_1d": "Necesidad t-1",
    "net_irrigation_need_mm_lag_3d": "Necesidad t-3",
    "net_irrigation_need_mm_lag_7d": "Necesidad t-7",
    "net_irrigation_need_mm_sum_3d": "Suma previa 3 días",
    "net_irrigation_need_mm_sum_7d": "Suma previa 7 días",
    "net_irrigation_need_mm_sum_14d": "Suma previa 14 días",
}


def _tree_shap(
    pipeline: Any, features: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray, float]:
    """Devuelve matriz imputada, contribuciones SHAP y valor base medio."""
    transformed = pipeline.named_steps["imputer"].transform(features)
    model = pipeline.named_steps["model"]
    explanation = shap.TreeExplainer(model)(transformed)
    values = np.asarray(explanation.values, dtype=float)
    base_values = np.asarray(explanation.base_values, dtype=float)
    return transformed, values, float(base_values.mean())


def summarize_importance(model_name: str, shap_values: np.ndarray) -> pd.DataFrame:
    """Resume importancia global y dirección media sin afirmar causalidad."""
    mean_absolute = np.abs(shap_values).mean(axis=0)
    total = float(mean_absolute.sum())
    summary = pd.DataFrame(
        {
            "model": model_name,
            "feature": FEATURE_COLUMNS,
            "feature_label": [FEATURE_LABELS[name] for name in FEATURE_COLUMNS],
            "mean_absolute_shap_mm": mean_absolute,
            "mean_signed_shap_mm": shap_values.mean(axis=0),
            "importance_share_pct": (
                mean_absolute / total * 100 if total else np.zeros_like(mean_absolute)
            ),
        }
    ).sort_values("mean_absolute_shap_mm", ascending=False)
    summary.insert(1, "rank", np.arange(1, len(summary) + 1))
    return summary.reset_index(drop=True)


def local_explanations(
    model_name: str,
    dates: pd.Series,
    actual: pd.Series,
    predicted: np.ndarray,
    shap_values: np.ndarray,
    base_value: float,
) -> pd.DataFrame:
    """Recoge la principal contribución positiva y negativa de cada día."""
    rows: list[dict[str, Any]] = []
    for index, contributions in enumerate(shap_values):
        positive_index = int(np.argmax(contributions))
        negative_index = int(np.argmin(contributions))
        rows.append(
            {
                "model": model_name,
                "observed_date": pd.Timestamp(dates.iloc[index]).date().isoformat(),
                "actual_mm": float(actual.iloc[index]),
                "prediction_mm": float(predicted[index]),
                "absolute_error_mm": float(abs(predicted[index] - actual.iloc[index])),
                "base_value_mm": base_value,
                "top_positive_feature": FEATURE_COLUMNS[positive_index],
                "top_positive_shap_mm": float(contributions[positive_index]),
                "top_negative_feature": FEATURE_COLUMNS[negative_index],
                "top_negative_shap_mm": float(contributions[negative_index]),
                "shap_sum_prediction_mm": float(base_value + contributions.sum()),
            }
        )
    return pd.DataFrame(rows)


def _plot(
    importance: pd.DataFrame,
    local: pd.DataFrame,
    shap_by_model: dict[str, np.ndarray],
    output: Path,
) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10.5,
            "axes.labelsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.facecolor": "#F8FAFC",
            "figure.facecolor": "white",
            "grid.color": "#D9E2EC",
            "grid.alpha": 0.65,
        }
    )
    labels = [FEATURE_LABELS[name] for name in FEATURE_COLUMNS]
    forest = (
        importance.loc[importance["model"] == "random_forest"]
        .set_index("feature")
        .reindex(FEATURE_COLUMNS)
    )
    boost = (
        importance.loc[importance["model"] == "xgboost"]
        .set_index("feature")
        .reindex(FEATURE_COLUMNS)
    )
    order = np.argsort(
        forest["mean_absolute_shap_mm"].to_numpy()
        + boost["mean_absolute_shap_mm"].to_numpy()
    )
    positions = np.arange(len(FEATURE_COLUMNS))

    fig = plt.figure(figsize=(10.2, 8.0), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1.35, 1])
    global_axis = fig.add_subplot(grid[0, :])
    width = 0.36
    global_axis.barh(
        positions - width / 2,
        forest["mean_absolute_shap_mm"].to_numpy()[order],
        height=width,
        color="#0F766E",
        label="Random Forest",
    )
    global_axis.barh(
        positions + width / 2,
        boost["mean_absolute_shap_mm"].to_numpy()[order],
        height=width,
        color="#7C3AED",
        label="XGBoost",
    )
    global_axis.set_yticks(positions, np.asarray(labels)[order])
    global_axis.set_xlabel("Contribución media absoluta SHAP (mm/día)")
    global_axis.set_title("a) Importancia global sobre el tramo de prueba")
    global_axis.grid(axis="x")
    global_axis.legend(frameon=False, loc="lower right")

    palette = {"random_forest": "#0F766E", "xgboost": "#7C3AED"}
    titles = {"random_forest": "Random Forest", "xgboost": "XGBoost"}
    for axis, model_name in zip(
        (fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1])), MODEL_NAMES
    ):
        subset = local.loc[local["model"] == model_name]
        worst = subset.loc[subset["absolute_error_mm"].idxmax()]
        row_index = subset.index.get_loc(worst.name)
        values = shap_by_model[model_name][row_index]
        top = np.argsort(np.abs(values))[-5:]
        local_order = top[np.argsort(values[top])]
        colors = ["#DC2626" if values[i] > 0 else "#2563EB" for i in local_order]
        axis.barh(
            np.arange(len(local_order)), values[local_order], color=colors, alpha=0.9
        )
        axis.axvline(0, color="#475569", lw=0.8)
        axis.set_yticks(
            np.arange(len(local_order)), np.asarray(labels)[local_order], fontsize=8
        )
        axis.set_xlabel("Contribución SHAP (mm/día)")
        axis.set_title(
            f"{titles[model_name]}: mayor error ({worst['observed_date']})\n"
            f"referencia {worst['actual_mm']:.2f}; predicción {worst['prediction_mm']:.2f} mm/día"
        )
        axis.grid(axis="x")

    fig.suptitle(
        "Explicabilidad de los modelos de árboles en la prueba temporal",
        fontsize=13,
        fontweight="bold",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_xai_analysis(input_path: Path = DEFAULT_INPUT) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    data = prepare_modeling_data(load_modeling_dataset(input_path))
    holdout = temporal_holdout(data)
    importance_frames: list[pd.DataFrame] = []
    local_frames: list[pd.DataFrame] = []
    shap_by_model: dict[str, np.ndarray] = {}
    metrics: dict[str, dict[str, float]] = {}
    bases: dict[str, float] = {}

    for model_name in MODEL_NAMES:
        pipeline = _models()[model_name]
        pipeline.fit(holdout.development[FEATURE_COLUMNS], holdout.development[TARGET])
        predicted = _nonnegative_prediction(pipeline, holdout.test[FEATURE_COLUMNS])
        _, shap_values, base_value = _tree_shap(
            pipeline, holdout.test[FEATURE_COLUMNS]
        )
        shap_by_model[model_name] = shap_values
        bases[model_name] = base_value
        metrics[model_name] = regression_metrics(
            holdout.test[TARGET], predicted, holdout.test["observed_date"]
        )
        importance_frames.append(summarize_importance(model_name, shap_values))
        local_frames.append(
            local_explanations(
                model_name,
                holdout.test["observed_date"].reset_index(drop=True),
                holdout.test[TARGET].reset_index(drop=True),
                predicted,
                shap_values,
                base_value,
            )
        )

    importance = pd.concat(importance_frames, ignore_index=True)
    local = pd.concat(local_frames, ignore_index=True)
    _plot(importance, local, shap_by_model, DEFAULT_FIGURE)

    report: dict[str, Any] = {
        "method": "TreeSHAP",
        "scope": "Random Forest y XGBoost del piloto original de pimiento AL01",
        "interpretation_warning": (
            "Las contribuciones describen el comportamiento de cada modelo; "
            "no demuestran causalidad ni explican por sí solas el error."
        ),
        "development_rows": int(len(holdout.development)),
        "test_rows": int(len(holdout.test)),
        "test_start": holdout.test["observed_date"].min().date().isoformat(),
        "test_end": holdout.test["observed_date"].max().date().isoformat(),
        "test_kc_unique": sorted(
            float(value) for value in holdout.test["crop_coefficient_kc"].unique()
        ),
        "models": {},
    }
    for model_name in MODEL_NAMES:
        subset = importance.loc[importance["model"] == model_name]
        worst = local.loc[
            local.loc[local["model"] == model_name, "absolute_error_mm"].idxmax()
        ]
        report["models"][model_name] = {
            "metrics": metrics[model_name],
            "expected_value_mm": bases[model_name],
            "top_features": subset.head(5).to_dict(orient="records"),
            "worst_local_explanation": worst.to_dict(),
        }
    return report, importance, local


def main() -> None:
    report, importance, local = build_xai_analysis()
    DEFAULT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    importance.to_csv(DEFAULT_IMPORTANCE, index=False)
    local.to_csv(DEFAULT_LOCAL, index=False)
    print(f"Informe XAI: {DEFAULT_REPORT}")
    print(f"Importancias: {DEFAULT_IMPORTANCE}")
    print(f"Explicaciones locales: {DEFAULT_LOCAL}")
    print(f"Figura: {DEFAULT_FIGURE}")


if __name__ == "__main__":
    main()
