#!/usr/bin/env python3
"""Validate synthetic knowledge-ingestion, digest, and export contracts."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SENSITIVITY_LEVELS = {"public", "internal", "private"}
DESTINATIONS = {"private", "internal", "public"}
BUNDLE_SCHEMA_VERSION = 1
CONTRACT_FIELDS = {"sources", "items", "claims"}
SOURCE_FIELDS = {"id", "enabled", "sensitivity", "public_reuse"}
ITEM_FIELDS = {"source_id", "slug", "observed_at", "expires_at", "superseded_by"}
CLAIM_FIELDS = {"id", "destination", "evidence"}
IDENTITY_FIELDS = {"source_id", "slug"}


def violation(code, path, message):
    return {"code": code, "path": path, "message": message}


def unexpected_field_violations(value, allowed, code, path):
    return [
        violation(code, "%s.%s" % (path, field), "unexpected field %r" % field)
        for field in sorted(set(value) - allowed, key=repr)
    ]


def parse_timestamp(value):
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be a non-empty string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def evaluate_contract(contract, as_of):
    """Return deterministic violations; an empty list means the contract is valid."""
    if not isinstance(contract, dict):
        return [violation("invalid_contract", "$", "contract must be an object")]

    violations = unexpected_field_violations(contract, CONTRACT_FIELDS, "invalid_contract", "$")
    missing_fields = sorted(CONTRACT_FIELDS - set(contract))
    if missing_fields:
        violations.append(
            violation(
                "invalid_contract",
                "$",
                "contract is missing required fields: %s" % ", ".join(missing_fields),
            )
        )
        return violations

    sources = contract["sources"]
    items = contract["items"]
    claims = contract["claims"]
    if not isinstance(sources, list) or not isinstance(items, list) or not isinstance(claims, list):
        violations.append(
            violation(
                "invalid_contract",
                "$",
                "sources, items, and claims must be arrays",
            )
        )
        return violations

    try:
        as_of_time = parse_timestamp(as_of)
    except (TypeError, ValueError) as exc:
        return [violation("invalid_contract", "$.as_of", str(exc))]

    source_index = {}
    for index, source in enumerate(sources):
        path = "$.sources[%d]" % index
        if not isinstance(source, dict):
            violations.append(violation("invalid_source", path, "source must be an object"))
            continue
        violations.extend(unexpected_field_violations(source, SOURCE_FIELDS, "invalid_source", path))
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id:
            violations.append(violation("invalid_source", path + ".id", "id must be a non-empty string"))
            continue
        if source_id in source_index:
            violations.append(
                violation("duplicate_source_id", path + ".id", "source id %r is duplicated" % source_id)
            )
            continue
        if not isinstance(source.get("enabled"), bool):
            violations.append(
                violation("invalid_source", path + ".enabled", "enabled must be a boolean")
            )
            continue
        if source.get("sensitivity") not in SENSITIVITY_LEVELS:
            violations.append(
                violation(
                    "invalid_source",
                    path + ".sensitivity",
                    "sensitivity must be public, internal, or private",
                )
            )
            continue
        if not isinstance(source.get("public_reuse"), bool):
            violations.append(
                violation("invalid_source", path + ".public_reuse", "public_reuse must be a boolean")
            )
            continue
        source_index[source_id] = source

    item_index = {}
    item_times = {}
    for index, item in enumerate(items):
        path = "$.items[%d]" % index
        if not isinstance(item, dict):
            violations.append(violation("invalid_item", path, "item must be an object"))
            continue
        violations.extend(unexpected_field_violations(item, ITEM_FIELDS, "invalid_item", path))
        source_id = item.get("source_id")
        slug = item.get("slug")
        if not isinstance(source_id, str) or not source_id or not isinstance(slug, str) or not slug:
            violations.append(
                violation(
                    "invalid_item",
                    path,
                    "source_id and slug must be non-empty strings",
                )
            )
            continue
        identity = (source_id, slug)
        if identity in item_index:
            violations.append(
                violation(
                    "duplicate_source_slug",
                    path,
                    "item identity (%s, %s) is duplicated" % identity,
                )
            )
            continue

        source = source_index.get(source_id)
        if source is None:
            violations.append(
                violation("unknown_source", path + ".source_id", "source %r is not declared" % source_id)
            )
        elif not source["enabled"]:
            violations.append(
                violation(
                    "disabled_source_item",
                    path,
                    "disabled source %r produced a retained item" % source_id,
                )
            )

        parsed_times = {}
        for field in ("observed_at", "expires_at"):
            value = item.get(field)
            if field == "expires_at" and value is None:
                continue
            try:
                parsed_times[field] = parse_timestamp(value)
            except (TypeError, ValueError) as exc:
                violations.append(violation("invalid_timestamp", path + "." + field, str(exc)))
        if "superseded_by" in item:
            superseded_by = item["superseded_by"]
            if (
                not isinstance(superseded_by, dict)
                or set(superseded_by) != IDENTITY_FIELDS
                or not all(
                    isinstance(superseded_by.get(field), str) and superseded_by.get(field)
                    for field in IDENTITY_FIELDS
                )
            ):
                violations.append(
                    violation(
                        "invalid_item",
                        path + ".superseded_by",
                        "superseded_by must contain only non-empty source_id and slug strings",
                    )
                )
        item_index[identity] = item
        item_times[identity] = parsed_times

    for index, claim in enumerate(claims):
        path = "$.claims[%d]" % index
        if not isinstance(claim, dict):
            violations.append(violation("invalid_claim", path, "claim must be an object"))
            continue
        violations.extend(unexpected_field_violations(claim, CLAIM_FIELDS, "invalid_claim", path))
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id:
            violations.append(violation("invalid_claim", path + ".id", "id must be a non-empty string"))
        destination = claim.get("destination")
        evidence = claim.get("evidence")
        if destination not in DESTINATIONS:
            violations.append(
                violation(
                    "invalid_claim",
                    path + ".destination",
                    "destination must be private, internal, or public",
                )
            )
        if not isinstance(evidence, list) or not evidence:
            violations.append(
                violation("claim_without_evidence", path + ".evidence", "claim must cite evidence")
            )
            continue

        for evidence_index, reference in enumerate(evidence):
            ref_path = "%s.evidence[%d]" % (path, evidence_index)
            if not isinstance(reference, dict):
                violations.append(
                    violation("invalid_evidence_ref", ref_path, "evidence reference must be an object")
                )
                continue
            violations.extend(
                unexpected_field_violations(reference, IDENTITY_FIELDS, "invalid_evidence_ref", ref_path)
            )
            source_id = reference.get("source_id")
            slug = reference.get("slug")
            if not isinstance(source_id, str) or not source_id or not isinstance(slug, str) or not slug:
                violations.append(
                    violation(
                        "invalid_evidence_ref",
                        ref_path,
                        "source_id and slug must be non-empty strings",
                    )
                )
                continue
            identity = (source_id, slug)
            item = item_index.get(identity)
            if item is None:
                violations.append(
                    violation(
                        "unknown_evidence_ref",
                        ref_path,
                        "no item exists for source %r and slug %r" % identity,
                    )
                )
                continue

            expires_at = item_times.get(identity, {}).get("expires_at")
            if expires_at is not None and expires_at <= as_of_time:
                violations.append(
                    violation(
                        "stale_claim",
                        ref_path,
                        "claim cites evidence that expired at %s" % item["expires_at"],
                    )
                )
            if item.get("superseded_by"):
                violations.append(
                    violation(
                        "superseded_claim",
                        ref_path,
                        "claim cites evidence superseded by %r" % item["superseded_by"],
                    )
                )

            source = source_index.get(source_id)
            if (
                destination == "public"
                and source is not None
                and (source["sensitivity"] != "public" or not source["public_reuse"])
            ):
                violations.append(
                    violation(
                        "public_export_denied",
                        ref_path,
                        "source %r is not authorized for public reuse" % source_id,
                    )
                )

    return violations


def evaluate_bundle(bundle):
    if not isinstance(bundle, dict):
        raise ValueError("fixture bundle must be an object")
    unexpected_bundle_fields = sorted(set(bundle) - {"schema_version", "as_of", "cases"}, key=repr)
    if unexpected_bundle_fields:
        raise ValueError("fixture bundle has unexpected field %r" % unexpected_bundle_fields[0])
    schema_version = bundle.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise ValueError("schema_version must be an integer")
    if schema_version != BUNDLE_SCHEMA_VERSION:
        raise ValueError("unsupported schema_version %r" % schema_version)
    if not isinstance(bundle.get("cases"), list):
        raise ValueError("fixture bundle must contain a cases array")
    as_of = bundle.get("as_of")
    try:
        parse_timestamp(as_of)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid as_of: %s" % exc) from exc

    results = []
    seen_ids = set()
    for index, case in enumerate(bundle["cases"]):
        if not isinstance(case, dict):
            raise ValueError("case %d must be an object" % index)
        unexpected_case_fields = sorted(
            set(case) - {"id", "expected_valid", "expected_codes", "contract"}, key=repr
        )
        if unexpected_case_fields:
            raise ValueError("case %d has unexpected field %r" % (index, unexpected_case_fields[0]))
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("case %d id must be a non-empty string" % index)
        if case_id in seen_ids:
            raise ValueError("case id %r is duplicated" % case_id)
        seen_ids.add(case_id)
        expected_valid = case.get("expected_valid")
        expected_codes = case.get("expected_codes")
        if not isinstance(expected_valid, bool):
            raise ValueError("case %r expected_valid must be a boolean" % case_id)
        if not isinstance(expected_codes, list) or not all(
            isinstance(code, str) and code for code in expected_codes
        ):
            raise ValueError("case %r expected_codes must be an array of non-empty strings" % case_id)

        violations = evaluate_contract(case.get("contract"), as_of)
        actual_valid = not violations
        actual_codes = [entry["code"] for entry in violations]
        matched = actual_valid == expected_valid and actual_codes == expected_codes
        results.append(
            {
                "id": case_id,
                "matched": matched,
                "actual_valid": actual_valid,
                "actual_codes": actual_codes,
                "expected_valid": expected_valid,
                "expected_codes": expected_codes,
                "violations": violations,
            }
        )
    matched_count = sum(1 for result in results if result["matched"])
    return {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "passed": matched_count == len(results),
        "matched": matched_count,
        "total": len(results),
        "results": results,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="JSON fixture bundle to evaluate")
    parser.add_argument("--json", action="store_true", help="emit a JSON receipt")
    args = parser.parse_args(argv)

    try:
        bundle = json.loads(args.fixture.read_text(encoding="utf-8"))
        receipt = evaluate_bundle(bundle)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        for result in receipt["results"]:
            state = "valid" if result["actual_valid"] else "invalid"
            codes = " [%s]" % ", ".join(result["actual_codes"]) if result["actual_codes"] else ""
            marker = "MATCH" if result["matched"] else "MISMATCH"
            print("%s: %s %s%s" % (result["id"], marker, state, codes))
        status = "PASS" if receipt["passed"] else "FAIL"
        print("%s %d/%d knowledge ingestion contract cases" % (status, receipt["matched"], receipt["total"]))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
