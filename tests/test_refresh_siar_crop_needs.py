"""Controles de actualización SiAR sin depender de su disponibilidad en red."""

from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.data.refresh_siar_crop_needs import (
    CASES, SiARRefreshError, compare_rows, fetch_validated_case, parse_csv, refresh,
)
from src.dss.data_access import load_crop_needs_bytes


META = {
    "requested_start_date": "2026-01-01", "requested_end_date": "2026-01-01",
    "crop": "Cultivo", "station_code": "AL01", "active_months": [1],
}
OLD = b"Fecha;Kc;ET0;ETc;Pe;ETc - Pe\n01/01/2026;0,20;2,00;0,40;0,00;0,40\n"
NEW = OLD + b"02/01/2026;0,20;2,10;0,42;0,00;0,42\n"


class RefreshSiARTests(unittest.TestCase):
    def test_parses_official_csv_and_detects_new_date(self):
        old = parse_csv(OLD, META, date(2026, 1, 2))
        new = parse_csv(NEW, META, date(2026, 1, 2))
        self.assertEqual(compare_rows(old, new), [date(2026, 1, 2)])

    def test_rejects_revision_of_existing_day(self):
        revised = OLD.replace(b"2,00", b"3,00")
        with self.assertRaisesRegex(SiARRefreshError, "modificó"):
            compare_rows(parse_csv(OLD, META, date(2026, 1, 2)),
                         parse_csv(revised, META, date(2026, 1, 2)))

    def test_rejects_future_and_duplicate_rows(self):
        for content in (OLD + OLD.splitlines()[1] + b"\n", NEW):
            with self.assertRaises(SiARRefreshError):
                parse_csv(content, META, date(2026, 1, 1))

    def test_rejects_backfilled_date(self):
        first = ("01/01/2026", "0,20", "2,00", "0,40", "0,00", "0,40")
        third = ("03/01/2026", "0,20", "2,00", "0,40", "0,00", "0,40")
        second = ("02/01/2026", "0,20", "2,00", "0,40", "0,00", "0,40")
        with self.assertRaisesRegex(SiARRefreshError, "dentro del histórico"):
            compare_rows({date(2026, 1, 1): first, date(2026, 1, 3): third},
                         {date(2026, 1, 1): first, date(2026, 1, 2): second,
                          date(2026, 1, 3): third})

    def test_live_case_uses_download_in_memory(self):
        with patch("src.data.refresh_siar_crop_needs.download_csv", return_value=NEW):
            content, metadata, additions = fetch_validated_case(META, OLD, date(2026, 1, 2))
        history = load_crop_needs_bytes(content, "SiAR web")
        self.assertEqual(metadata["last_returned_date"], "2026-01-02")
        self.assertEqual(metadata["record_count"], 2)
        self.assertEqual(additions, [date(2026, 1, 2)])
        self.assertEqual(history["date"].max().date(), date(2026, 1, 2))

    def test_all_cases_are_validated_before_any_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for stem in CASES:
                (root / f"{stem}.csv").write_bytes(OLD)
                (root / f"{stem}.metadata.json").write_text(json.dumps(META), encoding="utf-8")
            with patch("src.data.refresh_siar_crop_needs.download_csv",
                       side_effect=[NEW, NEW, OLD.replace(b"2,00", b"3,00"), NEW]):
                with self.assertRaises(SiARRefreshError):
                    refresh(date(2026, 1, 2), data_dir=root)
            for stem in CASES:
                self.assertEqual((root / f"{stem}.csv").read_bytes(), OLD)


if __name__ == "__main__":
    unittest.main()
