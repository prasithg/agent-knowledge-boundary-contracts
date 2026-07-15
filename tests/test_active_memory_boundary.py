import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from active_memory_boundary import END, START, evaluate_fixture, strip_leading_active_memory


class ActiveMemoryBoundaryContractTests(unittest.TestCase):
    def block(self, newline="\n"):
        return newline.join((START, "fact: synthetic", END)) + newline

    def test_checked_in_fixture_matches(self):
        fixture = ROOT / "fixtures" / "active_memory_boundary_cases.json"
        self.assertEqual(evaluate_fixture(fixture), [])
        bundle = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(bundle["schema_version"], 1)
        self.assertEqual(len(bundle["cases"]), 5)

    def test_separator_count_preserves_complete_user_suffix(self):
        suffix = "SENTINEL: retain me\nsecond line\n"
        for count in range(4):
            with self.subTest(separator_count=count):
                text = self.block() + ("\n" * count) + suffix
                self.assertEqual(strip_leading_active_memory(text), suffix)

    def test_crlf_preserves_complete_user_suffix(self):
        suffix = "SENTINEL: retain me\r\nsecond line\r\n"
        self.assertEqual(strip_leading_active_memory(self.block("\r\n") + "\r\n" + suffix), suffix)

    def test_multiple_leading_blocks_are_removed(self):
        suffix = "SENTINEL: retain me\n"
        self.assertEqual(strip_leading_active_memory(self.block() + self.block() + suffix), suffix)

    def test_suffix_without_terminal_newline_is_preserved(self):
        suffix = "SENTINEL: retain me"
        self.assertEqual(strip_leading_active_memory(self.block() + "\n\n" + suffix), suffix)

    def test_block_only_input_becomes_empty(self):
        self.assertEqual(strip_leading_active_memory(self.block()), "")

    def test_unterminated_leading_block_is_unchanged(self):
        text = f"{START}\nfact: synthetic\nSENTINEL: retain me\n"
        self.assertEqual(strip_leading_active_memory(text), text)

    def test_non_leading_block_is_unchanged(self):
        text = "user preface\n" + self.block() + "SENTINEL: retain me\n"
        self.assertEqual(strip_leading_active_memory(text), text)

    def test_valid_block_before_unterminated_lookalike_strips_only_valid_block(self):
        malformed = f"{START}\nfact: synthetic\nSENTINEL: retain me\n"
        self.assertEqual(strip_leading_active_memory(self.block() + malformed), malformed)

    def test_cli_reports_fixture_receipt(self):
        fixture = ROOT / "fixtures" / "active_memory_boundary_cases.json"
        completed = subprocess.run(
            [sys.executable, str(ROOT / "active_memory_boundary.py"), str(fixture)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PASS 5/5 active-memory boundary cases", completed.stdout)


if __name__ == "__main__":
    unittest.main()
