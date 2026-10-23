"""Incorpora dos casos en ciclo en octubre de 2026 con CSV oficiales SiAR.

Se ejecuta una sola vez desde la raíz del repositorio. No reemplaza archivos
existentes ni modifica las campañas históricas. Las actualizaciones posteriores
las realiza ``refresh_siar_crop_needs.py``.
"""

from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from src.data.refresh_siar_crop_needs import (
    DATA_DIR, SiARRefreshError, _atomic_write, download_csv, parse_csv,
)


NEW_CASES = (
    ("siar_necesidades_maiz_Z06_2026", "siar_necesidades_alfalfa_Z06_2026",
     "Alfalfa", "Mar / Oct", list(range(3, 11)), "2026-03-01"),
    ("siar_necesidades_algodon_BA08_2026", "siar_necesidades_alcachofa_BA08_2026",
     "Alcachofa", "Ene / Dic", list(range(1, 13)), "2026-01-01"),
)


def seed(today: date, data_dir: Path = DATA_DIR) -> list[str]:
    if today.year != 2026:
        raise SiARRefreshError("Esta carga inicial solo corresponde a la campaña 2026.")
    staged = []
    report = []
    for template_stem, stem, crop, cycle, months, start in NEW_CASES:
        csv_path = data_dir / f"{stem}.csv"
        meta_path = data_dir / f"{stem}.metadata.json"
        if csv_path.exists() or meta_path.exists():
            raise SiARRefreshError(f"El caso {stem} ya existe; no se sobrescribe.")
        template = json.loads((data_dir / f"{template_stem}.metadata.json").read_text(encoding="utf-8"))
        metadata = dict(template)
        metadata.update(crop=crop, crop_cycle=cycle, active_months=months,
                        requested_start_date=start, requested_end_date=today.isoformat(),
                        retrieved_at=today.isoformat())
        content = download_csv(metadata, today)
        rows = parse_csv(content, metadata, today)
        last = max(rows)
        if (today - last).days > 2 or float(rows[last][1].replace(",", ".")) <= 0:
            raise SiARRefreshError(f"{crop} no tiene un Kc positivo y reciente.")
        metadata.update(first_returned_date=min(rows).isoformat(),
                        last_returned_date=last.isoformat(), record_count=len(rows),
                        notes=(f"CSV oficial descargado el {today:%d/%m/%Y}; última jornada "
                               f"publicada {last:%d/%m/%Y}, con Kc positivo. El calendario "
                               "SiAR no acredita el sistema productivo ni los riegos reales. "
                               "La predicción de mañana usa una hipótesis de Kc dentro del mes."))
        staged.append((csv_path, content, meta_path,
                       (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")))
        report.append(f"{crop} {metadata['station_code']}: {len(rows)} filas; última {last}")
    for csv_path, content, meta_path, meta_content in staged:
        _atomic_write(csv_path, content)
        _atomic_write(meta_path, meta_content)
    return report


if __name__ == "__main__":
    for line in seed(datetime.now(ZoneInfo("Europe/Madrid")).date()):
        print(line)
