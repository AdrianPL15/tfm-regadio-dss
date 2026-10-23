"""Archiva predicciones AEMET tal como se emitieron para evaluación futura.

Uso: python -m src.data.archive_aemet_forecast --municipio 04013
Los archivos quedan en data/raw y data/interim, excluidos de Git por defecto.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.data.aemet_client import AEMETClient
from src.dss.aemet_forecast import forecast_from_payloads


def archive_forecast(
    municipality_code: str,
    *,
    client: Any | None = None,
    raw_root: Path = Path("data/raw/aemet/forecast"),
    interim_root: Path = Path("data/interim/aemet/forecast"),
) -> dict[str, Path]:
    if len(municipality_code) != 5 or not municipality_code.isdigit():
        raise ValueError("El código municipal debe contener cinco dígitos.")
    provider = client or AEMETClient()
    daily = provider.get_daily_municipality_forecast(municipality_code)
    hourly = provider.get_hourly_municipality_forecast(municipality_code)
    if not isinstance(daily, list) or not isinstance(hourly, list):
        raise ValueError("La respuesta AEMET no contiene los productos esperados.")
    normalized = forecast_from_payloads(daily, hourly)
    if normalized["municipality_code"].iat[0] != municipality_code:
        raise ValueError("El municipio solicitado no coincide con la respuesta AEMET.")
    stamp = normalized["issued_at"].iat[0].replace(":", "").replace("-", "")
    stamp = stamp.replace("T", "_")
    raw_dir = Path(raw_root) / f"municipality={municipality_code}"
    interim_dir = Path(interim_root) / f"municipality={municipality_code}"
    raw_dir.mkdir(parents=True, exist_ok=True)
    interim_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "daily_raw": raw_dir / f"{stamp}_daily.json",
        "hourly_raw": raw_dir / f"{stamp}_hourly.json",
        "daily_normalized": interim_dir / f"{stamp}_daily.csv",
    }
    payloads = {
        "daily_raw": json.dumps(daily, ensure_ascii=False, indent=2) + "\n",
        "hourly_raw": json.dumps(hourly, ensure_ascii=False, indent=2) + "\n",
        "daily_normalized": normalized.to_csv(index=False, lineterminator="\n"),
    }
    for label, content in payloads.items():
        path = paths[label]
        if path.exists():
            existing = path.read_bytes().decode("utf-8-sig").replace("\r\r\n", "\n").replace("\r\n", "\n")
            if existing != content.replace("\r\n", "\n"):
                raise FileExistsError(f"Existe otra versión para la misma emisión: {path}")
            continue
        path.write_text(content, encoding="utf-8-sig" if label == "daily_normalized" else "utf-8")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--municipio", required=True, help="Código INE municipal de cinco dígitos.")
    args = parser.parse_args()
    if len(args.municipio) != 5 or not args.municipio.isdigit():
        raise ValueError("El código municipal debe contener cinco dígitos.")
    paths = archive_forecast(args.municipio)
    for label, path in paths.items():
        print(f"{label}: {path}")


if __name__ == "__main__":
    main()
