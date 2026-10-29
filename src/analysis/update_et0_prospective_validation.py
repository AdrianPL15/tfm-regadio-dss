"""Reconsulta SiAR y cierra las predicciones ET0 prospectivas ya observables."""

from __future__ import annotations

import json
from datetime import date

import pandas as pd

from src.data.siar_client import SiARClient
from src.dss.et0_prospective import DEFAULT_LOG, validate_log
from src.dss.predict_et0 import history_from_siar_records


def update() -> dict:
    if not DEFAULT_LOG.exists():
        return validate_log(pd.DataFrame(columns=["date", "station_code", "et0_mm"]))
    log = pd.read_csv(DEFAULT_LOG)
    pending = log.loc[log["status"].eq("pending")].copy()
    if pending.empty:
        return validate_log(pd.DataFrame(columns=["date", "station_code", "et0_mm"]))
    client = SiARClient()
    frames = []
    for station, group in pending.groupby("station_code"):
        start = pd.to_datetime(group["target_date"]).min().date()
        end = min(pd.to_datetime(group["target_date"]).max().date(), date.today())
        if start > end:
            continue
        records = client.get_data(
            "Diarios", "ESTACION", str(station), start, end, calculated=True
        )
        frames.append(history_from_siar_records(records, str(station)))
    actuals = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["date", "station_code", "et0_mm"]
    )
    return validate_log(actuals)


if __name__ == "__main__":
    print(json.dumps(update(), ensure_ascii=False, indent=2))
