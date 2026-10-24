"""Reentrena por cultivo y estación con todas las campañas SiAR disponibles.

La selección se hace con validación cronológica y la prueba final queda fuera
del ajuste. Después de evaluar, se reajusta el enfoque elegido con todos los
días válidos y activos para disponer de un artefacto reproducible. Estos modelos
no sustituyen el motor de reglas de la aplicación Streamlit.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.dss.config import CropCase, DEMO_CASES
from src.dss.data_access import load_case
from src.models.train_evaluate import (
    FEATURE_COLUMNS,
    MODEL_LABELS,
    TARGET,
    _models,
    prepare_modeling_data,
    train_and_evaluate,
)


DEFAULT_REPORT = Path("docs/data_samples/model_retraining_2026.json")
DEFAULT_PREDICTIONS = Path("docs/data_samples/model_predictions_retraining_2026.csv")
DEFAULT_FIGURE = Path("docs/images/model_retraining_2026.png")
DEFAULT_MODEL_DIR = Path("models/retrained_2026")


def grouped_cases(cases: tuple[CropCase, ...] = DEMO_CASES) -> dict[str, list[CropCase]]:
    """Agrupa campañas del mismo cultivo/estación sin mezclar ubicaciones."""
    grouped: dict[str, list[CropCase]] = defaultdict(list)
    for case in cases:
        slug = case.crop.lower().translate(str.maketrans("áéíóúüñ", "aeiouun"))
        grouped[f"{slug}_{case.station_code}"].append(case)
    return {key: sorted(value, key=lambda item: item.campaign_year) for key, value in grouped.items()}


def source_for_case(case: CropCase) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Conserva huecos diarios, pero nunca inventa una etiqueta de entrenamiento."""
    daily, metadata = load_case(case)
    if metadata.get("crop") != case.crop or metadata.get("station_code") != case.station_code:
        raise ValueError(f"Metadatos incoherentes: {case.crop}/{case.station_code}/{case.campaign_year}.")
    raw_rows = len(pd.read_csv(case.source_file, sep=";", encoding="utf-8-sig"))
    if metadata.get("record_count") != raw_rows:
        raise ValueError(f"Recuento SiAR incoherente: {case.source_file}.")
    if daily.empty or daily["date"].duplicated().any():
        raise ValueError(f"Fechas vacías o duplicadas: {case.source_file}.")
    numeric = ["kc", "et0_mm", "etc_mm", "pe_mm", "net_need_mm"]
    complete = daily["record_status"].eq("completo") & daily[numeric].notna().all(axis=1)
    if (daily.loc[complete, numeric] < 0).any().any():
        raise ValueError(f"Variables físicas negativas: {case.source_file}.")
    expected = np.maximum(0, daily.loc[complete, "etc_mm"] - daily.loc[complete, "pe_mm"])
    if not np.allclose(daily.loc[complete, "net_need_mm"], expected, atol=0.011, rtol=0):
        raise ValueError(f"Necesidad neta incompatible con ETc - Pe: {case.source_file}.")
    source = pd.DataFrame({
        "observed_date": daily["date"],
        "station_code": case.station_code,
        "crop": case.crop,
        "campaign_year": case.campaign_year,
        "crop_coefficient_kc": daily["kc"],
        TARGET: daily["net_need_mm"].where(complete),
    })
    quality = {
        "source_csv": case.source_file.as_posix(),
        "source_metadata": case.metadata_file.as_posix(),
        "csv_rows": raw_rows,
        "calendar_rows": len(daily),
        "complete_rows": int(complete.sum()),
        "excluded_incomplete_rows": int((~complete).sum()),
        "active_complete_rows": int((complete & daily["kc"].gt(0)).sum()),
        "last_observed_date": daily.loc[complete, "date"].max().date().isoformat(),
    }
    return source, quality


def prepare_group(campaigns: list[CropCase]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    sources, quality = zip(*(source_for_case(case) for case in campaigns))
    combined = pd.concat(sources, ignore_index=True).sort_values("observed_date")
    prepared = prepare_modeling_data(combined)
    # El test de final de campaña no debe ganar por predecir ceros fuera del ciclo.
    active = prepared.loc[prepared["crop_coefficient_kc"].gt(0)].reset_index(drop=True)
    if len(active) < 30:
        raise ValueError(f"Muestra activa insuficiente para {campaigns[0].crop}.")
    return active, list(quality)


def evaluate_and_refit(
    cases: tuple[CropCase, ...] = DEMO_CASES,
    model_dir: Path = DEFAULT_MODEL_DIR,
) -> tuple[dict[str, Any], pd.DataFrame, dict[str, Any]]:
    results: dict[str, Any] = {}
    predictions: list[pd.DataFrame] = []
    fitted: dict[str, Any] = {}
    for key, campaigns in grouped_cases(cases).items():
        active, quality = prepare_group(campaigns)
        evaluation, predicted, _ = train_and_evaluate(active)
        selected = evaluation["selected_model"]
        final_model = _models()[selected]
        final_model.fit(active[FEATURE_COLUMNS], active[TARGET])
        fitted[key] = final_model
        predicted.insert(0, "case", key)
        predictions.append(predicted)
        results[key] = {
            "crop": campaigns[0].crop,
            "station_code": campaigns[0].station_code,
            "station_name": campaigns[0].station_name,
            "campaigns": [item.campaign_year for item in campaigns],
            "source_quality": quality,
            "active_rows_by_year": {
                str(year): int((active["campaign_year"] == year).sum())
                for year in sorted(active["campaign_year"].unique())
            },
            "evaluation": evaluation,
            "final_refit": {
                "model": selected,
                "rows": len(active),
                "start": active["observed_date"].min().date().isoformat(),
                "end": active["observed_date"].max().date().isoformat(),
                "evaluated_on_refit": False,
                "artifact": (model_dir / f"{key}.joblib").as_posix(),
            },
        }
    report = {
        "experiment": "Reentrenamiento por cultivo y estación con campañas SiAR disponibles hasta el 22/10/2026",
        "scope": "Seis modelos independientes; no se ha entrenado un modelo nacional compartido",
        "target": TARGET,
        "features": FEATURE_COLUMNS,
        "selection": "MAE medio de tres cortes temporales; último 15 % activo reservado para prueba",
        "source_rows_csv": sum(q["csv_rows"] for c in results.values() for q in c["source_quality"]),
        "valid_active_rows": sum(sum(c["active_rows_by_year"].values()) for c in results.values()),
        "cases": results,
        "limitations": [
            "La etiqueta es la necesidad neta calculada por SiAR, no el riego aplicado en campo.",
            "El Kc del día evaluado procede del calendario SiAR; el uso futuro requiere proyectarlo.",
            "Persistencia es una predicción rodante a un día con el dato del día anterior disponible.",
            "El reajuste final usa todo el histórico y no tiene una prueba independiente posterior.",
            "AEMET no entra en este entrenamiento: faltan emisiones históricas archivadas antes de cada fecha objetivo.",
            "Streamlit sigue usando el motor físico y de reglas; no consume estos artefactos predictivos.",
        ],
    }
    return report, pd.concat(predictions, ignore_index=True), fitted


def plot_results(report: dict[str, Any], output: Path) -> None:
    labels, selected_cv_mae, selected_test_mae = [], [], []
    for case in report["cases"].values():
        evaluation = case["evaluation"]
        selected = evaluation["selected_model"]
        labels.append(f"{case['crop']} {case['station_code']}\n{MODEL_LABELS[selected]}")
        selected_cv_mae.append(evaluation["cross_validation"]["summary"][selected]["mae_mm_day"]["mean"])
        selected_test_mae.append(evaluation["test"][selected]["mae_mm_day"])
    fig, axis = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(labels))
    axis.bar(x - 0.18, selected_cv_mae, 0.36, color="#64748B", label="Validación temporal")
    axis.bar(x + 0.18, selected_test_mae, 0.36, color="#2563EB", label="Prueba final")
    axis.set_xticks(x, labels)
    axis.set_ylabel("MAE del modelo elegido (mm/día)")
    axis.set_title("Error de validación y prueba en cada caso")
    axis.legend(frameon=False)
    axis.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--figure", type=Path, default=DEFAULT_FIGURE)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()
    report, predictions, fitted = evaluate_and_refit(model_dir=args.model_dir)
    for path in (args.report, args.predictions, args.figure):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.model_dir.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    predictions.to_csv(args.predictions, index=False, encoding="utf-8-sig")
    plot_results(report, args.figure)
    for key, model in fitted.items():
        joblib.dump(model, args.model_dir / f"{key}.joblib")
        evaluation = report["cases"][key]["evaluation"]
        print(f"{key}: {MODEL_LABELS[evaluation['selected_model']]} "
              f"| MAE prueba {evaluation['test'][evaluation['selected_model']]['mae_mm_day']:.3f} mm/día")
    print(f"Informe: {args.report}")


if __name__ == "__main__":
    main()
