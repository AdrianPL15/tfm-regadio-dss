"""Consolida la validación geográfica del experimento ET0 multianual."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


DATA_SAMPLES = Path("docs/data_samples")
STATIONS = {
    "AL01": {
        "crop": "Pimiento",
        "metrics": DATA_SAMPLES / "et0_multiyear_metrics.csv",
        "evaluation": DATA_SAMPLES / "et0_multiyear_evaluation_summary.json",
    },
    "Z06": {
        "crop": "Maíz",
        "metrics": DATA_SAMPLES / "et0_multiyear_metrics_Z06.csv",
        "evaluation": DATA_SAMPLES / "et0_multiyear_evaluation_summary_Z06.json",
    },
    "BA08": {
        "crop": "Algodón",
        "metrics": DATA_SAMPLES / "et0_multiyear_metrics_BA08.csv",
        "evaluation": DATA_SAMPLES / "et0_multiyear_evaluation_summary_BA08.json",
    },
}
DEFAULT_OUTPUT = DATA_SAMPLES / "et0_multiyear_geographic_validation.csv"


def build(output: Path = DEFAULT_OUTPUT) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for station, paths in STATIONS.items():
        metrics = pd.read_csv(paths["metrics"])
        test = metrics[metrics["phase"] == "test_2025"].set_index("model")
        evaluation = json.loads(paths["evaluation"].read_text(encoding="utf-8"))
        persistence_mae = float(test.loc["Persistencia", "mae_mm"])
        ridge_mae = float(test.loc["Ridge", "mae_mm"])
        irrigation = evaluation["irrigation_impact"]
        bootstrap = evaluation["bootstrap"]
        rows.append(
            {
                "station_code": station,
                "crop": paths["crop"],
                "test_days": int(test.loc["Ridge", "n"]),
                "ridge_mae_mm_day": ridge_mae,
                "persistence_mae_mm_day": persistence_mae,
                "et0_relative_improvement_pct": 100 * (persistence_mae - ridge_mae) / persistence_mae,
                "bootstrap_difference_mm_day": bootstrap["ridge_vs_persistence_mae_difference_mm_day"],
                "bootstrap_ci95_lower_mm_day": bootstrap["ci_95_mm_day"][0],
                "bootstrap_ci95_upper_mm_day": bootstrap["ci_95_mm_day"][1],
                "irrigation_paired_days": irrigation["paired_days"],
                "irrigation_relative_mae_improvement_pct": irrigation["relative_mae_improvement_pct"],
            }
        )
    result = pd.DataFrame(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False, encoding="utf-8")
    return result


if __name__ == "__main__":
    print(build().to_string(index=False))
