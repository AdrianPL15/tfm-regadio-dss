"""Audita la cobertura temporal disponible para un experimento de ET0.

El informe distingue las observaciones meteorológicas de estación de los CSV
de necesidades hídricas por cultivo. Estos últimos contienen ET0, pero solo
durante el calendario solicitado y no sustituyen a una serie meteorológica
continua de varios años.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.dss.data_access import load_crop_needs


DEFAULT_WEATHER = Path("data/interim/et0_history_AL01_2021_2025.csv")
DEFAULT_CROP_ROOT = Path("data/external")
DEFAULT_CSV = Path("docs/data_samples/et0_history_inventory.csv")
DEFAULT_JSON = Path("docs/data_samples/et0_history_inventory.json")


def _coverage_record(
    *,
    source_type: str,
    source_file: Path,
    station: str,
    crop: str | None,
    dates: pd.Series,
    et0: pd.Series,
    observed_mask: pd.Series | None = None,
) -> dict[str, object]:
    valid_dates = pd.to_datetime(dates, errors="coerce").dropna().dt.normalize()
    mask = (
        pd.Series(True, index=dates.index)
        if observed_mask is None
        else observed_mask.fillna(False).astype(bool)
    )
    observed_dates = pd.to_datetime(dates[mask], errors="coerce").dropna().dt.normalize()
    observed_et0 = pd.to_numeric(et0[mask], errors="coerce")
    start = valid_dates.min()
    end = valid_dates.max()
    calendar_days = int((end - start).days + 1) if len(valid_dates) else 0
    unique_dates = int(observed_dates.nunique())
    years = sorted(int(year) for year in valid_dates.dt.year.unique())
    return {
        "source_type": source_type,
        "station_code": station,
        "crop": crop or "",
        "source_file": source_file.as_posix(),
        "rows": int(mask.sum()),
        "unique_dates": unique_dates,
        "start_date": start.date().isoformat() if len(valid_dates) else "",
        "end_date": end.date().isoformat() if len(valid_dates) else "",
        "calendar_days": calendar_days,
        "calendar_coverage_pct": (
            round(100 * unique_dates / calendar_days, 2) if calendar_days else 0.0
        ),
        "years": ",".join(str(year) for year in years),
        "year_count": len(years),
        "et0_valid": int(observed_et0.notna().sum()),
        "et0_missing": int(observed_et0.isna().sum()),
        "multiyear_full_weather_candidate": bool(
            source_type == "station_weather" and len(years) >= 3
        ),
    }


def build_inventory(
    weather_path: Path = DEFAULT_WEATHER,
    crop_root: Path = DEFAULT_CROP_ROOT,
) -> pd.DataFrame:
    records: list[dict[str, object]] = []

    if weather_path.exists():
        weather = pd.read_csv(weather_path)
        date_column = "date" if "date" in weather.columns else "observed_date"
        et0_column = "et0_mm" if "et0_mm" in weather.columns else "et0_pm_mm"
        records.append(
            _coverage_record(
                source_type="station_weather",
                source_file=weather_path,
                station=str(weather["station_code"].dropna().iloc[0]),
                crop=None,
                dates=weather[date_column],
                et0=weather[et0_column],
            )
        )

    for path in sorted(crop_root.glob("siar_necesidades_*.csv")):
        data = load_crop_needs(path)
        parts = path.stem.split("_")
        crop = parts[2] if len(parts) >= 5 else "desconocido"
        station = parts[3] if len(parts) >= 5 else "desconocida"
        records.append(
            _coverage_record(
                source_type="crop_calendar",
                source_file=path,
                station=station,
                crop=crop,
                dates=data["date"],
                et0=data["et0_mm"],
                observed_mask=data["record_status"] != "fecha_no_devuelta",
            )
        )

    return pd.DataFrame.from_records(records).sort_values(
        ["source_type", "station_code", "crop", "start_date"]
    ).reset_index(drop=True)


def write_inventory(
    inventory: pd.DataFrame,
    csv_path: Path = DEFAULT_CSV,
    json_path: Path = DEFAULT_JSON,
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    inventory.to_csv(csv_path, index=False, encoding="utf-8")
    summary = {
        "criterion": (
            "Candidato inicial: serie meteorológica diaria continua con al menos "
            "tres años; preferencia por cinco o más."
        ),
        "station_weather_series": int(
            (inventory["source_type"] == "station_weather").sum()
        ),
        "eligible_station_weather_series": int(
            inventory["multiyear_full_weather_candidate"].sum()
        ),
        "inventory": inventory.to_dict(orient="records"),
    }
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weather", type=Path, default=DEFAULT_WEATHER)
    parser.add_argument("--crop-root", type=Path, default=DEFAULT_CROP_ROOT)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inventory = build_inventory(args.weather, args.crop_root)
    write_inventory(inventory, args.csv, args.json)
    eligible = int(inventory["multiyear_full_weather_candidate"].sum())
    print(
        f"Inventariadas {len(inventory)} series; "
        f"candidatas meteorológicas multianuales: {eligible}."
    )


if __name__ == "__main__":
    main()
