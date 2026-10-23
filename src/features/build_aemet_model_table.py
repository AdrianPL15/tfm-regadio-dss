"""Une previsiones AEMET archivadas con la referencia SiAR sin fuga temporal.

Con las instantáneas disponibles de octubre de 2026 y los ciclos SiAR de 2025
la salida correcta es vacía. Se necesitan emisiones históricas solapadas antes
de entrenar un modelo nuevo con estos predictores.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.dss.config import CropCase, DEMO_CASES
from src.dss.data_access import load_case


COLUMNS = [
    "observed_date", "station_code", "crop", "municipality_code",
    "forecast_issued_at", "forecast_horizon_days", "forecast_precipitation_mm",
    "forecast_precipitation_probability_pct", "forecast_amount_status",
    "crop_coefficient_kc", "target_net_irrigation_need_mm", "forecast_source_file",
]


def join_forecasts_to_siar(case: CropCase, forecasts: pd.DataFrame) -> pd.DataFrame:
    """Selecciona la última emisión conocida antes del día objetivo."""
    required = {"date", "issued_at", "municipality_code", "precipitation_mm",
                "precipitation_probability_pct", "precipitation_amount_status"}
    missing = required - set(forecasts.columns)
    if missing:
        raise ValueError(f"Faltan campos de predicción AEMET: {sorted(missing)}")
    history, _ = load_case(case)
    observed = history.loc[history["net_need_mm"].notna(), ["date", "kc", "net_need_mm"]].copy()
    observed = observed.rename(columns={"date": "observed_date"})
    prediction = forecasts.copy()
    prediction["date"] = pd.to_datetime(prediction["date"], errors="raise").dt.normalize()
    prediction["issued_at"] = pd.to_datetime(prediction["issued_at"], errors="raise")
    prediction = prediction.loc[prediction["municipality_code"].astype(str).str.zfill(5) == case.aemet_municipality_code]
    if prediction.empty:
        return pd.DataFrame(columns=COLUMNS)
    joined = observed.merge(prediction, left_on="observed_date", right_on="date", how="inner")
    joined = joined.loc[joined["issued_at"] < joined["observed_date"]].copy()
    if joined.empty:
        return pd.DataFrame(columns=COLUMNS)
    joined = joined.sort_values(["observed_date", "issued_at"]).drop_duplicates(
        "observed_date", keep="last"
    )
    joined["station_code"] = case.station_code
    joined["crop"] = case.crop
    joined["municipality_code"] = case.aemet_municipality_code
    joined["forecast_horizon_days"] = (
        joined["observed_date"] - joined["issued_at"].dt.normalize()
    ).dt.days
    joined = joined.rename(columns={
        "issued_at": "forecast_issued_at",
        "precipitation_mm": "forecast_precipitation_mm",
        "precipitation_probability_pct": "forecast_precipitation_probability_pct",
        "precipitation_amount_status": "forecast_amount_status",
        "kc": "crop_coefficient_kc",
        "net_need_mm": "target_net_irrigation_need_mm",
        "source_file": "forecast_source_file",
    })
    if "forecast_source_file" not in joined:
        joined["forecast_source_file"] = pd.NA
    return joined[COLUMNS].sort_values("observed_date").reset_index(drop=True)


def load_archived_forecasts(root: Path) -> pd.DataFrame:
    files = sorted(Path(root).rglob("*_daily.csv"))
    if not files:
        return pd.DataFrame(columns=[
            "date", "issued_at", "municipality_code", "precipitation_mm",
            "precipitation_probability_pct", "precipitation_amount_status", "source_file",
        ])
    frames = []
    for path in files:
        frame = pd.read_csv(path, dtype={"municipality_code": str})
        frame["source_file"] = path.as_posix()
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forecast-root", type=Path, default=Path("data/interim/aemet/forecast"))
    parser.add_argument("--out", type=Path, default=Path("data/processed/aemet_siar_model_table.csv"))
    args = parser.parse_args()
    forecasts = load_archived_forecasts(args.forecast_root)
    frames = [join_forecasts_to_siar(case, forecasts) for case in DEMO_CASES]
    result = pd.concat(frames, ignore_index=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"Filas con predicción realmente anterior y referencia SiAR: {len(result)}")
    print(f"Tabla: {args.out}")
    if result.empty:
        print("No hay solapamiento temporal; no se entrena ningún modelo AEMET.")


if __name__ == "__main__":
    main()
