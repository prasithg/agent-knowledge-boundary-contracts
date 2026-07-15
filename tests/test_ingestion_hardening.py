import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from knowledge_ingestion_contracts import evaluate_bundle, evaluate_contract


BASE_SOURCE = {
    "id": "public-docs",
    "enabled": True,
    "sensitivity": "public",
    "public_reuse": True,
}
BASE_ITEM = {
    "source_id": "public-docs",
    "slug": "release-note",
    "observed_at": "2026-07-09T18:00:00Z",
}
BASE_CLAIM = {
    "id": "claim-1",
    "destination": "public",
    "evidence": [{"source_id": "public-docs", "slug": "release-note"}],
}
AS_OF = "2026-07-09T22:00:00Z"


def contract():
    return {
        "sources": [copy.deepcopy(BASE_SOURCE)],
        "items": [copy.deepcopy(BASE_ITEM)],
        "claims": [copy.deepcopy(BASE_CLAIM)],
    }


class IngestionHardeningTests(unittest.TestCase):
    def test_bundle_requires_supported_schema_version(self):
        with self.assertRaisesRegex(ValueError, "schema_version"):
            evaluate_bundle({"cases": []})
        with self.assertRaisesRegex(ValueError, "unsupported schema_version"):
            evaluate_bundle({"schema_version": 2, "as_of": AS_OF, "cases": []})

    def test_duplicate_source_ids_are_rejected(self):
        candidate = contract()
        candidate["sources"].append(copy.deepcopy(BASE_SOURCE))
        self.assertEqual(
            [entry["code"] for entry in evaluate_contract(candidate, AS_OF)],
            ["duplicate_source_id"],
        )

    def test_malformed_timestamps_fail_closed_without_a_traceback(self):
        candidate = contract()
        candidate["items"][0]["observed_at"] = "not-a-timestamp"
        self.assertEqual(
            [entry["code"] for entry in evaluate_contract(candidate, AS_OF)],
            ["invalid_timestamp"],
        )

    def test_invalid_destination_is_rejected(self):
        candidate = contract()
        candidate["claims"][0]["destination"] = "partner"
        self.assertEqual(
            [entry["code"] for entry in evaluate_contract(candidate, AS_OF)],
            ["invalid_claim"],
        )

    def test_public_reuse_requires_both_public_sensitivity_and_permission(self):
        sensitivity_denied = contract()
        sensitivity_denied["sources"][0]["sensitivity"] = "internal"
        permission_denied = contract()
        permission_denied["sources"][0]["public_reuse"] = False
        self.assertEqual(
            [entry["code"] for entry in evaluate_contract(sensitivity_denied, AS_OF)],
            ["public_export_denied"],
        )
        self.assertEqual(
            [entry["code"] for entry in evaluate_contract(permission_denied, AS_OF)],
            ["public_export_denied"],
        )

    def test_multiple_violations_are_stable_and_source_ordered(self):
        candidate = contract()
        candidate["sources"][0]["enabled"] = False
        candidate["items"][0]["expires_at"] = "2026-07-09T20:00:00Z"
        self.assertEqual(
            [entry["code"] for entry in evaluate_contract(candidate, AS_OF)],
            ["disabled_source_item", "stale_claim"],
        )

    def test_claim_id_and_superseded_identity_are_required(self):
        missing_claim_id = contract()
        del missing_claim_id["claims"][0]["id"]
        malformed_supersession = contract()
        malformed_supersession["items"][0]["superseded_by"] = {}
        self.assertEqual(
            [entry["code"] for entry in evaluate_contract(missing_claim_id, AS_OF)],
            ["invalid_claim"],
        )
        self.assertEqual(
            [entry["code"] for entry in evaluate_contract(malformed_supersession, AS_OF)],
            ["invalid_item"],
        )

    def test_schema_disallowed_properties_fail_closed(self):
        candidate = contract()
        candidate["sources"][0]["private_path"] = "synthetic"
        self.assertEqual(
            [entry["code"] for entry in evaluate_contract(candidate, AS_OF)],
            ["invalid_source"],
        )
        with self.assertRaisesRegex(ValueError, "unexpected field"):
            evaluate_bundle(
                {
                    "schema_version": 1,
                    "as_of": AS_OF,
                    "cases": [],
                    "extra": True,
                }
            )

    def test_contract_requires_all_three_arrays(self):
        self.assertEqual(
            [entry["code"] for entry in evaluate_contract({}, AS_OF)],
            ["invalid_contract"],
        )

    def test_malformed_case_returns_controlled_cli_error(self):
        bundle = {"schema_version": 1, "as_of": AS_OF, "cases": ["not-an-object"]}
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "malformed.json"
            path.write_text(json.dumps(bundle), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(ROOT / "knowledge_ingestion_contracts.py"), str(path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("case 0 must be an object", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
