"""Normaliza los CSV históricos descargados desde la consulta pública de SiAR."""

from __future__ import annotations

import argparse
from pathlib import Path
import unicodedata

import pandas as pd


DEFAULT_INPUT = Path("data/raw/siar/public_history/station=AL01")
DEFAULT_OUTPUT = Path("data/interim/et0_history_AL01_2021_2025.csv")
DEFAULT_QUALITY = Path("docs/data_samples/et0_history_quality_AL01_2021_2025.csv")


CANONICAL_COLUMNS = {
    "fecha": "date",
    "temp media (oc)": "temperature_mean_c",
    "temp max (oc)": "temperature_max_c",
    "temp min (oc)": "temperature_min_c",
    "hum media (%)": "humidity_mean_pct",
    "hum max (%)": "humidity_max_pct",
    "hum min (%)": "humidity_min_pct",
    "vel viento (m/s)": "wind_speed_mean_ms",
    "dir viento (o)": "wind_direction_deg",
    "vel v. max (m/s)": "wind_speed_max_ms",
    "dir v. vel max (o)": "wind_max_direction_deg",
    "rad (mj/m2)": "solar_radiation_mj_m2",
    "precip (mm)": "precipitation_mm",
    "p. efect (mm)": "effective_precipitation_mm",
    "et0 (mm)": "et0_mm",
    "to s. 10 cm (oc)": "soil_temperature_10cm_c",
    "to s. 30 cm (oc)": "soil_temperature_30cm_c",
}


def _plain(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(ascii_value.lower().strip().split())


def _read_siar_csv(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path, sep=";", decimal=",", encoding="cp1252")
    rename = {}
    for column in data.columns:
        key = _plain(column).replace("º", "o")
        if key in CANONICAL_COLUMNS:
            rename[column] = CANONICAL_COLUMNS[key]
    data = data.rename(columns=rename)
    required = {
        "date",
        "temperature_mean_c",
        "temperature_max_c",
        "temperature_min_c",
        "humidity_mean_pct",
        "wind_speed_mean_ms",
        "solar_radiation_mj_m2",
        "precipitation_mm",
        "et0_mm",
    }
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"{path.name}: faltan columnas {sorted(missing)}")
    data["date"] = pd.to_datetime(data["date"], dayfirst=True, errors="raise")
    selected = [name for name in CANONICAL_COLUMNS.values() if name in data.columns]
    data = data[selected].copy()
    for column in data.columns.difference(["date"]):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data["source_file"] = path.name
    return data


def prepare_history(input_root: Path = DEFAULT_INPUT, station_code: str = "AL01") -> pd.DataFrame:
    files = sorted(input_root.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No hay CSV históricos en {input_root}")
    data = pd.concat([_read_siar_csv(path) for path in files], ignore_index=True)
    duplicates = data[data.duplicated("date", keep=False)]
    if not duplicates.empty:
        conflicts = duplicates.groupby("date")["et0_mm"].nunique(dropna=False)
        if (conflicts > 1).any():
            raise ValueError("Hay fechas duplicadas con valores ET0 incompatibles.")
        data = data.drop_duplicates("date", keep="last")
    data["station_code"] = station_code.upper()
    columns = ["date", "station_code"] + [
        column for column in data.columns if column not in {"date", "station_code"}
    ]
    return data[columns].sort_values("date").reset_index(drop=True)


def quality_by_year(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, group in data.groupby(data["date"].dt.year, sort=True):
        expected = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
        observed = pd.DatetimeIndex(group["date"])
        missing_dates = expected.difference(observed)
        rows.append(
            {
                "station_code": (
                    str(group["station_code"].iloc[0])
                    if "station_code" in group.columns
                    else "UNKNOWN"
                ),
                "year": int(year),
                "expected_days": int(len(expected)),
                "observed_days": int(observed.nunique()),
                "missing_calendar_days": int(len(missing_dates)),
                "calendar_coverage_pct": round(100 * observed.nunique() / len(expected), 2),
                "et0_missing": int(group["et0_mm"].isna().sum()),
                "temperature_missing": int(group["temperature_mean_c"].isna().sum()),
                "humidity_missing": int(group["humidity_mean_pct"].isna().sum()),
                "radiation_missing": int(group["solar_radiation_mj_m2"].isna().sum()),
                "wind_missing": int(group["wind_speed_mean_ms"].isna().sum()),
                "precipitation_missing": int(group["precipitation_mm"].isna().sum()),
                "first_date": group["date"].min().date().isoformat(),
                "last_date": group["date"].max().date().isoformat(),
            }
        )
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--quality", type=Path, default=DEFAULT_QUALITY)
    parser.add_argument("--station-code", default="AL01")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = prepare_history(args.input_root, args.station_code)
    quality = quality_by_year(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.quality.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(args.output, index=False, encoding="utf-8")
    quality.to_csv(args.quality, index=False, encoding="utf-8")
    print(
        f"Histórico {args.station_code.upper()}: {len(data)} filas, {data['date'].min().date()} a "
        f"{data['date'].max().date()}, ET0 ausente={int(data['et0_mm'].isna().sum())}."
    )


if __name__ == "__main__":
    main()
