"""Comprobaciones del experimento reproducible de maíz y algodón."""

import unittest
from dataclasses import replace

from src.models.evaluate_crop_cases import (
    EXTENSION_CASES,
    evaluate_cases,
    modeling_source_for_case,
)
from src.models.train_evaluate import EXCLUDED_SAME_DAY_FEATURES, FEATURE_COLUMNS, TARGET


class EvaluateCropCasesTests(unittest.TestCase):
    def test_csvs_are_complete_and_keep_cases_separate(self):
        self.assertEqual({case.crop for case in EXTENSION_CASES}, {"Maíz", "Algodón"})
        for case in EXTENSION_CASES:
            source, quality = modeling_source_for_case(case)
            self.assertEqual(len(source), 183)
            self.assertEqual(quality["complete_rows"], 183)
            self.assertEqual(quality["missing_dates"], 0)
            self.assertEqual(source["observed_date"].nunique(), 183)
            self.assertEqual(source["station_code"].unique().tolist(), [case.station_code])
            self.assertEqual(source["crop"].unique().tolist(), [case.crop])
            self.assertTrue((source[TARGET] >= 0).all())
            self.assertIn("et0_pm_mm", source.columns)
            self.assertTrue(source["et0_pm_mm"].notna().all())

    def test_metadata_mismatch_is_rejected(self):
        bad_case = replace(EXTENSION_CASES[0], crop="Otro cultivo")
        with self.assertRaisesRegex(ValueError, "Metadatos incoherentes"):
            modeling_source_for_case(bad_case)

    def test_evaluation_has_temporal_holdout_and_no_feature_leakage(self):
        report, predictions = evaluate_cases()
        self.assertEqual(set(report["cases"]), {"maiz_Z06", "algodon_BA08"})
        self.assertEqual(len(predictions), 56)
        self.assertEqual(report["features"], FEATURE_COLUMNS)
        self.assertTrue(set(EXCLUDED_SAME_DAY_FEATURES).isdisjoint(report["features"]))
        for case_key, case_result in report["cases"].items():
            evaluation = case_result["evaluation"]
            split = evaluation["split"]
            self.assertLess(split["development_end"], split["test_start"])
            self.assertEqual(split["development_rows"], 155)
            self.assertEqual(split["test_rows"], 28)
            self.assertEqual(len(evaluation["cross_validation"]["folds"]), 3)
            for fold in evaluation["cross_validation"]["folds"]:
                self.assertLess(fold["train_end"], fold["validation_start"])
            selected_by_cv = min(
                evaluation["cross_validation"]["summary"],
                key=lambda model: evaluation["cross_validation"]["summary"][model]["mae_mm_day"]["mean"],
            )
            self.assertEqual(evaluation["selected_model"], selected_by_cv)
            self.assertEqual((predictions["case"] == case_key).sum(), 28)


if __name__ == "__main__":
    unittest.main()
