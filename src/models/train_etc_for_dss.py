"""Evalúa ETc SiAR sin lluvia y prepara modelos para la recomendación de mañana.

La ETc (ET0 × Kc) es la demanda previa a descontar precipitación. El informe
histórico de necesidad neta se conserva como experimento independiente.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.dss.config import DEMO_CASES
from src.dss.data_access import load_case
from src.models.retrain_cases_2026 import grouped_cases
from src.models.train_evaluate import (
    FEATURE_COLUMNS, MODEL_LABELS, TARGET, _models, prepare_modeling_data,
    train_and_evaluate,
)


DEFAULT_DIR = Path("models/deployed_etc_2026")
DEFAULT_REPORT = Path("docs/data_samples/etc_model_deployment_2026.json")


def prepared_campaign(case) -> pd.DataFrame:
    daily, _ = load_case(case)
    complete = (
        daily["record_status"].eq("completo")
        & daily[["kc", "et0_mm", "etc_mm"]].notna().all(axis=1)
    )
    source = pd.DataFrame({
        "observed_date": daily["date"],
        "crop_coefficient_kc": daily["kc"],
        TARGET: daily["etc_mm"].where(complete),
    })
    # Los retardos se crean dentro de cada campaña: nunca se conectan dos años.
    prepared = prepare_modeling_data(source)
    return prepared.loc[prepared["crop_coefficient_kc"].gt(0)].copy()


def evaluate_cases() -> tuple[dict, dict]:
    report = {
        "target": "ETc SiAR, mm/día, antes de descontar lluvia",
        "feature_columns": FEATURE_COLUMNS,
        "selection": "MAE medio en tres cortes temporales; 15 % final reservado",
        "rain_policy": "AEMET se aplica después de predecir ETc; no se descuenta dos veces",
        "deployment_horizon": "solo mañana; días posteriores usan el método físico existente",
        "cases": {},
    }
    fitted_models = {}
    for key, campaigns in grouped_cases(DEMO_CASES).items():
        data = pd.concat(
            [prepared_campaign(case) for case in campaigns], ignore_index=True
        ).sort_values("observed_date").reset_index(drop=True)
        if len(data) < 30:
            raise ValueError(f"Datos activos insuficientes para {key}.")
        evaluation, _, _ = train_and_evaluate(data)
        # Baseline operativo ya utilizado por la app: ET0 media reciente × Kc.
        test_start = pd.Timestamp(evaluation["split"]["test_start"])
        observed = pd.concat([load_case(case)[0] for case in campaigns], ignore_index=True)
        observed = observed.sort_values("date").reset_index(drop=True)
        physical_errors = []
        for _, row in data.loc[data["observed_date"].ge(test_start)].iterrows():
            previous = observed.loc[observed["date"].lt(row["observed_date"])].tail(7)
            recent_et0 = previous["et0_mm"].dropna()
            if not recent_et0.empty:
                physical_errors.append(abs(
                    float(recent_et0.mean()) * row["crop_coefficient_kc"] - row[TARGET]
                ))
        selected = evaluation["selected_model"]
        physical_mae = float(np.mean(physical_errors))
        model_mae = evaluation["test"][selected]["mae_mm_day"]
        model = _models()[selected]
        model.fit(data[FEATURE_COLUMNS], data[TARGET])
        fitted_models[key] = model
        report["cases"][key] = {
            "crop": campaigns[0].crop,
            "station_code": campaigns[0].station_code,
            "years": [case.campaign_year for case in campaigns],
            "active_rows": len(data),
            "trained_through": data["observed_date"].max().date().isoformat(),
            "selected_model": selected,
            "selected_model_label": MODEL_LABELS[selected],
            "cv_mae_mm_day": evaluation["cross_validation"]["summary"][selected]["mae_mm_day"]["mean"],
            "test_mae_mm_day": model_mae,
            "test_persistence_mae_mm_day": evaluation["test"]["persistence"]["mae_mm_day"],
            "physical_baseline_test_mae_mm_day": physical_mae,
            "physical_baseline_test_rows": len(physical_errors),
            "deploy_model_for_dose": bool(model_mae < physical_mae),
            "test_rows": evaluation["split"]["test_rows"],
            "artifact": f"{key}.joblib",
        }
    return report, fitted_models


def main() -> None:
    report, fitted = evaluate_cases()
    DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    for key, model in fitted.items():
        joblib.dump(model, DEFAULT_DIR / f"{key}.joblib", compress=3)
        entry = report["cases"][key]
        print(f"{key}: {entry['selected_model_label']} | prueba {entry['test_mae_mm_day']:.3f} mm/día")
    DEFAULT_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
