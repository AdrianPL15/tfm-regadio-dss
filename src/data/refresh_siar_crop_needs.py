"""Actualiza las seis instantáneas 2026 de necesidades netas desde SiAR Web.

La web pública usa formulario, sesión y CSRF. No es la API SiAR documentada;
este adaptador valida identidad, calendario y coincidencia histórica antes de
escribir. No necesita el token de la API meteorológica SiAR.

    python -m src.data.refresh_siar_crop_needs --check
    python -m src.data.refresh_siar_crop_needs
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
import io
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urljoin
from zoneinfo import ZoneInfo
import zipfile

from bs4 import BeautifulSoup
import requests


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "external"
BASE = "https://servicio.mapa.gob.es/siarweb/"
CASES = (
    "siar_necesidades_pimiento_AL01_2026",
    "siar_necesidades_coliflor_AL01_2026",
    "siar_necesidades_maiz_Z06_2026",
    "siar_necesidades_algodon_BA08_2026",
    "siar_necesidades_alfalfa_Z06_2026",
    "siar_necesidades_alcachofa_BA08_2026",
)
HEADERS = ("Fecha", "Kc", "ET0", "ETc", "Pe", "ETc - Pe")
HEADER_ALIASES = {"ET0 (mm)": "ET0", "ETc (mm)": "ETc", "Pe (mm)": "Pe", "ETc - Pe (mm)": "ETc - Pe"}


class SiARRefreshError(RuntimeError):
    """Descarga o validación fallida; no se debe publicar el CSV."""


def _get(session: requests.Session, path: str, **kwargs) -> requests.Response:
    try:
        response = session.get(urljoin(BASE, path), timeout=45, **kwargs)
        response.raise_for_status()
        return response
    except requests.RequestException as exc:
        raise SiARRefreshError(f"SiAR no respondió a {path}: {exc}") from exc


def _text(element) -> str:
    return element.get_text(" ", strip=True) if element is not None else ""


def _station_details(session: requests.Session, form: BeautifulSoup, metadata: dict) -> tuple[str, dict]:
    code = metadata["station_code"]
    choices = [option for option in form.select('select[name="idEstacion"] option')
               if _text(option).split(" - ", 1)[0] == code]
    if len(choices) != 1:
        raise SiARRefreshError(f"No se encontró una estación única para {code}.")
    option = choices[0]
    station_value = option.get("value", "")
    if not re.fullmatch(r"\d+_\d+", station_value):
        raise SiARRefreshError("Identificador de estación SiAR inesperado.")
    station_id, province_id = station_value.split("_")
    try:
        details = _get(session, "necesidadesHidricasRest/obtenerDatosEstacion",
                       params={"idProvincia": province_id, "idEstacion": station_id}).json()
    except requests.exceptions.JSONDecodeError as exc:
        raise SiARRefreshError("SiAR no devolvió datos de estación válidos.") from exc
    if not isinstance(details, dict):
        raise SiARRefreshError("Formato de estación SiAR inesperado.")
    if str(details.get("idEstacion")) != station_id or str(details.get("idProvincia")) != province_id:
        raise SiARRefreshError(f"Identidad de estación inconsistente para {code}.")
    if details.get("comarca") != metadata["region"] or details.get("provincia") != metadata["province"]:
        raise SiARRefreshError(f"La comarca o provincia de {code} cambió en SiAR.")
    if _text(option) != f"{code} - {metadata['station_name']}":
        raise SiARRefreshError(f"El nombre de la estación {code} cambió en SiAR.")
    return station_value, details


def _crop_details(session: requests.Session, metadata: dict, comarca_id: int) -> dict:
    try:
        crops = _get(session, "necesidadesHidricasRest/obtenerCultivosXComarca",
                     params={"idComarca": comarca_id}).json()
    except requests.exceptions.JSONDecodeError as exc:
        raise SiARRefreshError("SiAR no devolvió un catálogo de cultivos válido.") from exc
    if not isinstance(crops, list) or any(not isinstance(item, dict) for item in crops):
        raise SiARRefreshError("Formato de cultivos SiAR inesperado.")
    matching = [item for item in crops if item.get("cultivo") == metadata["crop"]]
    if len(matching) != 1:
        raise SiARRefreshError(f"No se encontró un cultivo único: {metadata['crop']}.")
    crop = matching[0]
    months = list(range(int(crop["minMes"]), int(crop["maxMes"]) + 1))
    if months != metadata["active_months"] or int(crop["idComarca"]) != comarca_id:
        raise SiARRefreshError(f"El ciclo o la comarca de {metadata['crop']} cambió en SiAR.")
    return crop


def download_csv(metadata: dict, today: date, session: requests.Session | None = None) -> bytes:
    """Obtiene el CSV diario desde el formulario y comprueba su identidad."""
    if today.year != date.fromisoformat(metadata["requested_start_date"]).year:
        raise SiARRefreshError("La campaña configurada no corresponde al año actual.")
    session = session or requests.Session()
    start = _get(session, "necesidadesHidricas/inicio")
    form = BeautifulSoup(start.content, "html.parser")
    csrf = form.select_one('input[name="_csrf"]')
    if csrf is None or not csrf.get("value"):
        raise SiARRefreshError("No se encontró el token CSRF del formulario SiAR.")
    station_value, station = _station_details(session, form, metadata)
    crop = _crop_details(session, metadata, int(station["idComarca"]))
    community = form.select_one(
        f'select[name="idCAEstacion"] option[value="{station["idCCAA"]}"]'
    )
    if _text(community) != metadata["community"]:
        raise SiARRefreshError("La comunidad autónoma cambió en SiAR.")
    payload = {
        "_csrf": csrf["value"], "esCalculo": "1", "idCAEstacion": station["idCCAA"],
        "idProvinciaEstacion": station["idProvincia"],
        "provinciaEstHidden": station["idProvincia"], "chkProvincia": "1",
        "radioProvCom": "on", "chkComRegante": "0", "idEstacion": station_value,
        "sEstacion": f"{metadata['station_code']} - {metadata['station_name']}",
        "comarcaEstacion": metadata["region"], "idComarca": station["idComarca"],
        "chkComarca": "0", "idCultivo": crop["idCultivo"], "tipoCalculo": "2",
        "fechaInicial": metadata["requested_start_date"], "fechaFinal": today.isoformat(),
    }
    try:
        result = session.post(urljoin(BASE, "necesidadesHidricas/calculo"),
                              data=payload, headers={"Referer": start.url}, timeout=60)
        result.raise_for_status()
    except requests.RequestException as exc:
        raise SiARRefreshError(f"Falló el cálculo de SiAR: {exc}") from exc
    page = BeautifulSoup(result.content, "html.parser")
    expected = {
        "datosEstacion_descProvincia": metadata["province"],
        "datosEstacion_SEstacion": metadata["station_name"],
        "datosEstacion_comarca": metadata["region"],
        "datosEstacion_cultivo": metadata["crop"],
        "datosEstacion_cultivo_tipoCalculo": "Diarios",
        "datosEstacion_cultivo_fechaIni": date.fromisoformat(metadata["requested_start_date"]).strftime("%d/%m/%Y"),
        "datosEstacion_cultivo_fechaFin": today.strftime("%d/%m/%Y"),
    }
    for element_id, value in expected.items():
        if value not in _text(page.find(id=element_id)):
            raise SiARRefreshError(f"Resultado SiAR no coincide en {element_id}: {value}.")
    exported = _get(session, "necesidadesHidricas/exportCSV", headers={"Referer": result.url})
    if not exported.content.startswith(b"PK\x03\x04") or len(exported.content) > 2_000_000:
        raise SiARRefreshError("SiAR no devolvió un ZIP CSV de tamaño razonable.")
    try:
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if len(names) != 1 or not names[0].lower().endswith(".csv"):
                raise SiARRefreshError("El ZIP de SiAR no contiene exactamente un CSV.")
            if not names[0].startswith(metadata["station_code"] + "_"):
                raise SiARRefreshError("El nombre del CSV no coincide con la estación.")
            info = archive.getinfo(names[0])
            if info.file_size > 2_000_000:
                raise SiARRefreshError("El CSV de SiAR es demasiado grande.")
            return archive.read(info)
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise SiARRefreshError("El ZIP de SiAR está corrupto.") from exc


def parse_csv(content: bytes, metadata: dict, today: date) -> dict[date, tuple[str, ...]]:
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        names = [HEADER_ALIASES.get(name, name) for name in (reader.fieldnames or [])]
        if tuple(names) != HEADERS:
            raise SiARRefreshError(f"Columnas CSV inesperadas: {names}.")
        rows: dict[date, tuple[str, ...]] = {}
        for raw in reader:
            if None in raw or None in raw.values():
                raise SiARRefreshError("Fila CSV incompleta o con columnas extra.")
            values = tuple(raw[key] for key in reader.fieldnames or [])
            day = datetime.strptime(values[0], "%d/%m/%Y").date()
            if day in rows or day > today:
                raise SiARRefreshError("CSV con fecha duplicada o futura.")
            for index, value in enumerate(values[1:], 1):
                if value:
                    number = float(value.replace(",", "."))
                    if not 0 <= number <= (3 if index == 1 else 100):
                        raise SiARRefreshError("CSV con valor agronómico fuera de rango.")
            rows[day] = values
    except (UnicodeError, ValueError, TypeError, csv.Error) as exc:
        raise SiARRefreshError(f"CSV de SiAR inválido: {exc}") from exc
    if not rows or len(rows) > 366:
        raise SiARRefreshError("El CSV de SiAR está vacío o supera una campaña.")
    start = date.fromisoformat(metadata["requested_start_date"])
    if min(rows) != start or max(rows) > today or any(day.year != start.year for day in rows):
        raise SiARRefreshError("El calendario devuelto no coincide con la campaña solicitada.")
    return rows


def compare_rows(old: dict[date, tuple[str, ...]], new: dict[date, tuple[str, ...]]) -> list[date]:
    changed = [day for day, values in old.items() if day not in new or new[day] != values]
    if changed:
        preview = ", ".join(day.isoformat() for day in changed[:5])
        raise SiARRefreshError(f"SiAR modificó u omitió {len(changed)} fechas ya guardadas ({preview}). Revisión manual necesaria.")
    additions = sorted(set(new) - set(old))
    if additions and additions[0] <= max(old):
        raise SiARRefreshError("SiAR añadió una fecha dentro del histórico: revisión manual necesaria.")
    return additions


def fetch_validated_case(metadata: dict, old_content: bytes, today: date) -> tuple[bytes, dict, list[date]]:
    """Devuelve una instantánea segura para la app, sin modificar el repositorio."""
    old = parse_csv(old_content, metadata, today)
    fresh = download_csv(metadata, today)
    new = parse_csv(fresh, metadata, today)
    additions = compare_rows(old, new)
    updated = dict(metadata)
    updated.update(retrieved_at=today.isoformat(), requested_end_date=today.isoformat(),
                   first_returned_date=min(new).isoformat(),
                   last_returned_date=max(new).isoformat(), record_count=len(new))
    return fresh, updated, additions


def _atomic_write(path: Path, content: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".siar_", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def refresh(today: date, check: bool = False, data_dir: Path = DATA_DIR) -> list[str]:
    """Prepara los seis casos antes de escribir cualquiera de ellos."""
    staged = []
    report = []
    with requests.Session() as session:
        for stem in CASES:
            csv_path = data_dir / f"{stem}.csv"
            meta_path = data_dir / f"{stem}.metadata.json"
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            old = parse_csv(csv_path.read_bytes(), metadata, today)
            fresh = download_csv(metadata, today, session=session)
            new = parse_csv(fresh, metadata, today)
            additions = compare_rows(old, new)
            report.append(f"{metadata['crop']} {metadata['station_code']}: {len(additions)} nuevas; última {max(new)}")
            if additions:
                updated = dict(metadata)
                updated.update(retrieved_at=today.isoformat(), requested_end_date=today.isoformat(),
                               first_returned_date=min(new).isoformat(),
                               last_returned_date=max(new).isoformat(), record_count=len(new))
                updated["notes"] = (
                    f"CSV oficial descargado el {today:%d/%m/%Y}; última jornada publicada "
                    f"{max(new):%d/%m/%Y}. No son riegos reales ni previsiones futuras. "
                    "La actualización conserva intacto el histórico previamente versionado."
                )
                staged.append((csv_path, fresh, meta_path,
                               (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode("utf-8")))
    if not check:
        for csv_path, csv_bytes, meta_path, meta_bytes in staged:
            _atomic_write(csv_path, csv_bytes)
            _atomic_write(meta_path, meta_bytes)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validar y mostrar cambios sin escribir archivos.")
    args = parser.parse_args()
    today = datetime.now(ZoneInfo("Europe/Madrid")).date()
    try:
        for line in refresh(today, check=args.check):
            print(line)
    except (SiARRefreshError, OSError, KeyError, requests.exceptions.JSONDecodeError) as exc:
        print(f"Actualización detenida: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
