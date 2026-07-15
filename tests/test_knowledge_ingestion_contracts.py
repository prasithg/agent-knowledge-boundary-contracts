import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from knowledge_ingestion_contracts import evaluate_bundle, evaluate_contract


class KnowledgeIngestionContractsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_path = ROOT / "fixtures" / "ingestion_policy_cases.json"
        cls.bundle = json.loads(cls.fixture_path.read_text(encoding="utf-8"))

    def case(self, case_id):
        return next(case for case in self.bundle["cases"] if case["id"] == case_id)

    def test_fixture_bundle_matches_expected_behavior(self):
        result = evaluate_bundle(self.bundle)
        self.assertTrue(result["passed"])
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["total"], 13)
        self.assertEqual(result["matched"], 13)

    def test_source_identity_is_scoped_by_source_and_slug(self):
        valid = evaluate_contract(
            self.case("valid_same_slug_across_sources")["contract"],
            self.bundle["as_of"],
        )
        invalid = evaluate_contract(
            self.case("invalid_same_source_duplicate_slug")["contract"],
            self.bundle["as_of"],
        )
        self.assertEqual(valid, [])
        self.assertEqual([v["code"] for v in invalid], ["duplicate_source_slug"])

    def test_disabled_source_items_fail_closed(self):
        violations = evaluate_contract(
            self.case("invalid_disabled_source_retained")["contract"],
            self.bundle["as_of"],
        )
        self.assertEqual([v["code"] for v in violations], ["disabled_source_item"])

    def test_stale_and_superseded_claims_are_rejected(self):
        expired = evaluate_contract(
            self.case("invalid_expired_digest_claim")["contract"],
            self.bundle["as_of"],
        )
        superseded = evaluate_contract(
            self.case("invalid_superseded_digest_claim")["contract"],
            self.bundle["as_of"],
        )
        self.assertEqual([v["code"] for v in expired], ["stale_claim"])
        self.assertEqual([v["code"] for v in superseded], ["superseded_claim"])

    def test_private_source_cannot_support_public_export(self):
        violations = evaluate_contract(
            self.case("invalid_public_export_private_source")["contract"],
            self.bundle["as_of"],
        )
        self.assertEqual([v["code"] for v in violations], ["public_export_denied"])

    def test_malformed_contract_fails_closed(self):
        violations = evaluate_contract({"sources": "not-a-list"}, self.bundle["as_of"])
        self.assertEqual(violations[0]["code"], "invalid_contract")

    def test_cli_reports_fixture_receipt(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "knowledge_ingestion_contracts.py"), str(self.fixture_path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PASS 13/13 knowledge ingestion contract cases", completed.stdout)
        self.assertIn("invalid_public_export_private_source: MATCH invalid", completed.stdout)


if __name__ == "__main__":
    unittest.main()
