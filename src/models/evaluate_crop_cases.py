"""Extiende la evaluación temporal del 4.3 a maíz y algodón de SiAR.

Se entrena un modelo *por caso* con los quince predictores seguros del
piloto. No se mezclan cultivos ni se emplean ET0, ETc, Pe o la etiqueta del
mismo día como entrada; ET0 y necesidad solo entran mediante históricos
desplazados. Los CSV originales permanecen sin modificar.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.dss.config import CropCase, DEMO_CASES
from src.dss.data_access import load_case
from src.models.train_evaluate import (
    FEATURE_COLUMNS,
    MODEL_LABELS,
    MODEL_ORDER,
    TARGET,
    _apply_plot_style,
    plot_predictions,
    train_and_evaluate,
)


DEFAULT_REPORT = Path("docs/data_samples/model_evaluation_multicultivo_2025.json")
DEFAULT_PREDICTIONS = Path("docs/data_samples/model_predictions_multicultivo_2025.csv")
DEFAULT_IMAGE_ROOT = Path("docs/images")
EXTENSION_CASES = tuple(
    case for case in DEMO_CASES
    if case.crop in {"Maíz", "Algodón"} and case.campaign_year == 2025
)


def modeling_source_for_case(case: CropCase) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Prepara Kc, ET0 histórica, fecha y etiqueta con controles de calidad."""
    daily, metadata = load_case(case)
    if metadata.get("crop") != case.crop or metadata.get("station_code") != case.station_code:
        raise ValueError(f"Metadatos incoherentes para {case.crop}/{case.station_code}.")
    if metadata.get("record_count") != len(daily):
        raise ValueError(f"El recuento de metadatos no coincide para {case.crop}.")
    if daily.empty or daily["date"].duplicated().any():
        raise ValueError(f"Fechas vacías o duplicadas para {case.crop}.")
    if (daily["record_status"] != "completo").any():
        raise ValueError(f"El caso {case.crop} contiene jornadas incompletas; revisar fuente.")
    if daily[["kc", "et0_mm", "etc_mm", "pe_mm", "net_need_mm"]].isna().any().any():
        raise ValueError(f"El caso {case.crop} contiene variables numéricas ausentes.")
    if (daily[["kc", "et0_mm", "etc_mm", "pe_mm", "net_need_mm"]] < 0).any().any():
        raise ValueError(f"El caso {case.crop} contiene valores físicos negativos.")
    calculated = np.maximum(0, daily["etc_mm"] - daily["pe_mm"])
    if not np.allclose(daily["net_need_mm"], calculated, atol=0.011, rtol=0):
        raise ValueError(f"La necesidad neta no concuerda con ETc - Pe para {case.crop}.")

    source = pd.DataFrame(
        {
            "observed_date": daily["date"],
            "station_code": case.station_code,
            "crop": case.crop,
            "crop_coefficient_kc": daily["kc"],
            "et0_pm_mm": daily["et0_mm"],
            TARGET: daily["net_need_mm"],
        }
    )
    quality = {
        "source_csv": case.source_file.as_posix(),
        "source_metadata": case.metadata_file.as_posix(),
        "original_rows": len(daily),
        "complete_rows": int((daily["record_status"] == "completo").sum()),
        "missing_dates": int((daily["record_status"] == "fecha_no_devuelta").sum()),
        "missing_numeric_rows": int(daily[["kc", "et0_mm", "etc_mm", "pe_mm", "net_need_mm"]].isna().any(axis=1).sum()),
        "target_zero_days": int((daily["net_need_mm"] == 0).sum()),
        "target_mean_mm_day": float(daily["net_need_mm"].mean()),
        "target_max_mm_day": float(daily["net_need_mm"].max()),
        "kc_distinct_values": int(daily["kc"].nunique()),
        "date_start": daily["date"].min().date().isoformat(),
        "date_end": daily["date"].max().date().isoformat(),
    }
    return source, quality


def evaluate_cases(cases: tuple[CropCase, ...] = EXTENSION_CASES) -> tuple[dict[str, Any], pd.DataFrame]:
    """Ejecuta el protocolo 4.3 sin seleccionar modelos según la prueba final."""
    if not cases:
        raise ValueError("No se han indicado casos para evaluar.")
    results: dict[str, Any] = {}
    predictions: list[pd.DataFrame] = []
    for case in cases:
        crop_slug = case.crop.lower().translate(str.maketrans("áéíóúüñ", "aeiouun"))
        key = f"{crop_slug}_{case.station_code}"
        source, quality = modeling_source_for_case(case)
        case_report, case_predictions, _ = train_and_evaluate(source)
        case_report["input_stage"] = "siar_crop_needs_csv"
        case_report["limitations"] = [
            "Una sola campaña y estación; no mide generalización entre años o lugares.",
            "La etiqueta es la necesidad neta calculada por SiAR, no riego aplicado ni rendimiento real.",
            "La persistencia es un pronóstico a un día con la referencia del día anterior ya conocida.",
            "Los resultados no prueban ahorro de agua ni seguridad agronómica.",
        ]
        case_predictions.insert(0, "case", key)
        predictions.append(case_predictions)
        results[key] = {
            "crop": case.crop,
            "station_code": case.station_code,
            "station_name": case.station_name,
            "province": case.province,
            "community": case.community,
            "source_quality": quality,
            "evaluation": case_report,
        }
    report = {
        "experiment": "Extensión multicultivo del protocolo predictivo 4.3",
        "scope": "Entrenamiento y evaluación independientes por cultivo y estación; no modelo común",
        "year": 2025,
        "features": FEATURE_COLUMNS,
        "target": TARGET,
        "selection_rule": "Menor MAE medio en tres cortes temporales del desarrollo; prueba final reservada",
        "cases": results,
        "pimiento_reference": "docs/data_samples/model_evaluation_4_3.json (experimento original, no reentrenado aquí)",
    }
    return report, pd.concat(predictions, ignore_index=True)


def plot_case_comparison(report: dict[str, Any], output: Path) -> None:
    """Compara validación y prueba por caso, sin usar prueba para seleccionar."""
    _apply_plot_style()
    cases = list(report["cases"].values())
    fig, axes = plt.subplots(1, len(cases), figsize=(6 * len(cases), 4.8), sharey=True)
    if len(cases) == 1:
        axes = [axes]
    for ax, case in zip(axes, cases):
        evaluation = case["evaluation"]
        x = np.arange(len(MODEL_ORDER))
        cv = [evaluation["cross_validation"]["summary"][name]["mae_mm_day"]["mean"] for name in MODEL_ORDER]
        test = [evaluation["test"][name]["mae_mm_day"] for name in MODEL_ORDER]
        ax.bar(x - 0.19, cv, width=0.38, label="Validación", color="#64748B")
        ax.bar(x + 0.19, test, width=0.38, label="Prueba final", color="#2563EB")
        ax.set_xticks(x, [MODEL_LABELS[name] for name in MODEL_ORDER], rotation=38, ha="right")
        ax.set_title(f"{case['crop']} · {case['station_code']}")
        ax.set_ylabel("MAE (mm/día)")
        ax.grid(axis="y")
        ax.legend(frameon=False)
        selected = MODEL_ORDER.index(evaluation["selected_model"])
        ax.axvspan(selected - 0.47, selected + 0.47, color="#FBBF24", alpha=0.14)
    fig.suptitle("Modelos por cultivo · selección temporal y prueba independiente", fontweight="bold")
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--image-root", type=Path, default=DEFAULT_IMAGE_ROOT)
    args = parser.parse_args()
    report, predictions = evaluate_cases()
    for path in (args.report, args.predictions):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.image_root.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    predictions.to_csv(args.predictions, index=False, encoding="utf-8-sig")
    plot_case_comparison(report, args.image_root / "model_comparison_multicultivo_2025.png")
    _apply_plot_style()
    for key, result in report["cases"].items():
        case_predictions = predictions.loc[predictions["case"] == key].drop(columns="case")
        plot_predictions(
            case_predictions,
            args.image_root / f"model_predictions_{key}_2025.png",
            title=f"Evaluación temporal: {result['crop']} · {result['station_code']}",
        )
        selected = result["evaluation"]["selected_model"]
        mae = result["evaluation"]["test"][selected]["mae_mm_day"]
        print(f"{result['crop']} ({result['station_code']}): {selected}; MAE prueba = {mae:.3f} mm/día")
    print(f"Informe: {args.report}")


if __name__ == "__main__":
    main()
