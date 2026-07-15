#!/usr/bin/env python3
"""Check lossless removal of fully delimited leading active-memory blocks."""

import argparse
import json
import sys
from pathlib import Path

START = "<active-memory>"
END = "</active-memory>"
FIXTURE_SCHEMA_VERSION = 1


def strip_leading_active_memory(text):
    """Strip complete leading memory blocks and adjacent blank separators."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != START:
        return text

    cursor = 0
    removed_block = False
    while cursor < len(lines) and lines[cursor].rstrip("\r\n") == START:
        end = cursor + 1
        while end < len(lines) and lines[end].rstrip("\r\n") != END:
            end += 1
        if end == len(lines):
            return text if not removed_block else "".join(lines[cursor:])

        removed_block = True
        cursor = end + 1
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1

    return "".join(lines[cursor:])


def validate_fixture_bundle(bundle):
    if not isinstance(bundle, dict):
        raise ValueError("fixture bundle must be an object")
    version = bundle.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ValueError("schema_version must be an integer")
    if version != FIXTURE_SCHEMA_VERSION:
        raise ValueError("unsupported schema_version %r" % version)
    cases = bundle.get("cases")
    if not isinstance(cases, list):
        raise ValueError("fixture bundle must contain a cases array")

    seen_names = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError("case %d must be an object" % index)
        name = case.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("case %d name must be a non-empty string" % index)
        if name in seen_names:
            raise ValueError("case name %r is duplicated" % name)
        seen_names.add(name)
        if not isinstance(case.get("input"), str) or not isinstance(case.get("expected"), str):
            raise ValueError("case %r input and expected must be strings" % name)
    return cases


def evaluate_bundle(bundle):
    cases = validate_fixture_bundle(bundle)
    failures = []
    for case in cases:
        actual = strip_leading_active_memory(case["input"])
        if actual != case["expected"]:
            failures.append(case["name"])
    return failures


def evaluate_fixture(path):
    bundle = json.loads(path.read_text(encoding="utf-8"))
    return evaluate_bundle(bundle)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="versioned JSON fixture bundle")
    args = parser.parse_args(argv)
    try:
        bundle = json.loads(args.fixture.read_text(encoding="utf-8"))
        cases = validate_fixture_bundle(bundle)
        failures = evaluate_bundle(bundle)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    if failures:
        print("FAIL %d/%d active-memory boundary cases: %s" % (len(cases) - len(failures), len(cases), ", ".join(failures)))
        return 1
    print("PASS %d/%d active-memory boundary cases" % (len(cases), len(cases)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
