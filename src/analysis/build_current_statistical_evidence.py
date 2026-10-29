"""Amplía la incertidumbre estadística de los experimentos ya documentados.

Calcula intervalos bootstrap pareados por bloques temporales para:

* DSS frente a persistencia a un día y por horizonte (capítulo 5);
* persistencia frente a los cinco modelos de aprendizaje (capítulo 4).

El estimando es siempre MAE del método de referencia menos MAE del método
comparado. Un valor positivo favorece al método comparado. No se interpreta
como transferencia a otras campañas.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from src.analysis.build_validation_5_3 import (
    TEST_START,
    horizon_errors,
    select_window,
    window_selection,
)
from src.dss.config import CropCase, RecommendationRequest
from src.dss.data_access import load_case
from src.dss.engine import campaign_plan


DATA_SAMPLES = Path("docs/data_samples")
REPLICATES = 5_000
BLOCK_DAYS = 7
SEED = 42


def paired_block_bootstrap(
    reference_absolute_error: Iterable[float],
    candidate_absolute_error: Iterable[float],
    *,
    replicates: int = REPLICATES,
    block_days: int = BLOCK_DAYS,
    seed: int = SEED,
) -> dict[str, float | int | str]:
    """Estima la diferencia pareada de MAE preservando dependencia local."""

    reference = np.asarray(list(reference_absolute_error), dtype=float)
    candidate = np.asarray(list(candidate_absolute_error), dtype=float)
    valid = np.isfinite(reference) & np.isfinite(candidate)
    reference = reference[valid]
    candidate = candidate[valid]
    if reference.size == 0:
        raise ValueError("No hay errores pareados válidos.")

    rng = np.random.default_rng(seed)
    n = reference.size
    effective_block = min(block_days, n)
    differences = np.empty(replicates, dtype=float)
    blocks_needed = int(np.ceil(n / effective_block))
    for replicate in range(replicates):
        starts = rng.integers(0, n, size=blocks_needed)
        indices = np.concatenate(
            [(start + np.arange(effective_block)) % n for start in starts]
        )[:n]
        differences[replicate] = reference[indices].mean() - candidate[indices].mean()

    observed = reference.mean() - candidate.mean()
    lower, upper = np.quantile(differences, [0.025, 0.975])
    return {
        "n": int(n),
        "estimand": "MAE referencia - MAE candidato; positivo favorece al candidato",
        "observed_difference_mm_day": round(float(observed), 3),
        "ci_95_lower_mm_day": round(float(lower), 3),
        "ci_95_upper_mm_day": round(float(upper), 3),
        "probability_difference_positive": round(float((differences > 0).mean()), 3),
        "replicates": replicates,
        "block_days": block_days,
        "seed": seed,
    }


def _record(scope: str, comparison: str, result: dict) -> dict:
    return {"scope": scope, "comparison": comparison, **result}


def build(output_dir: Path = DATA_SAMPLES) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    history, metadata = load_case(CropCase())

    records: list[dict] = []

    # Capítulo 5: recomendación emitida a un día.
    plan = campaign_plan(RecommendationRequest(issue_date=pd.Timestamp("2025-05-02").date()), history, metadata)
    plan["period"] = np.where(plan["date"] >= TEST_START, "prueba", "desarrollo")
    comparable = plan.dropna(
        subset=["net_need_mm", "reference_need_mm", "persistence_baseline_mm"]
    ).sort_values("date")
    for period, group in comparable.groupby("period", sort=False):
        reference = (group["persistence_baseline_mm"] - group["reference_need_mm"]).abs()
        candidate = (group["net_need_mm"] - group["reference_need_mm"]).abs()
        records.append(
            _record(
                f"dss_un_dia_{period}",
                "Persistencia frente a DSS ET0 reciente × Kc",
                paired_block_bootstrap(reference, candidate),
            )
        )

    # Capítulo 5: comparación por horizonte con la ventana fijada en desarrollo.
    selected_window = select_window(window_selection(history)["desarrollo"])
    horizons = horizon_errors(history, selected_window).sort_values(
        ["period", "horizon_day", "issue_date"]
    )
    for (period, horizon), group in horizons.groupby(["period", "horizon_day"], sort=True):
        records.append(
            _record(
                f"dss_horizonte_{period}_d{int(horizon)}",
                "Persistencia extendida frente a DSS ET0 reciente × Kc",
                paired_block_bootstrap(
                    group["error_persistence_mm"].abs(),
                    group["error_et0_kc_mm"].abs(),
                ),
            )
        )

    # Capítulo 4: cada modelo frente a la persistencia sobre los mismos 23 días.
    predictions = pd.read_csv(output_dir / "model_predictions_4_3.csv").sort_values("observed_date")
    persistence = predictions["absolute_error_persistence_mm"]
    model_names = ("ridge", "random_forest", "knn", "svr", "xgboost")
    for model in model_names:
        records.append(
            _record(
                "modelos_prueba_2025",
                f"Persistencia frente a {model}",
                paired_block_bootstrap(
                    persistence,
                    predictions[f"absolute_error_{model}_mm"],
                ),
            )
        )

    frame = pd.DataFrame(records)
    frame.to_csv(output_dir / "statistical_evidence_current.csv", index=False)
    report = {
        "method": "bootstrap pareado por bloques temporales circulares",
        "interpretation": (
            "Los intervalos describen incertidumbre interna de los tramos reutilizados; "
            "no acreditan transferencia a otras campañas."
        ),
        "results": records,
    }
    (output_dir / "statistical_evidence_current.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DATA_SAMPLES)
    args = parser.parse_args()
    report = build(args.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
