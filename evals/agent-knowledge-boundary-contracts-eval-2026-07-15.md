# Agent knowledge boundary contracts eval — 2026-07-15

## Intent

Consolidate the source/freshness/export candidate and the overlapping active-memory preservation prototype into one portable contract repository. Preserve the latter's five vectors, separator matrix, public provenance, and negative space without publishing another micro-repository.

## Baseline

Before productization, the ingestion repository's standard-library suite passed:

```text
Ran 7 tests in 0.033s
OK
```

The checked-in ingestion CLI matched 8/8 cases. The portfolio triage had independently counted 13 static assertion sites in that original suite.

## Red-capable regressions

Two targeted gates were added before production changes.

`python3 -B -m unittest tests.test_ingestion_hardening -v` observed 2 failures out of 7 tests:

- a missing `schema_version` was accepted;
- a non-object case produced exit 1 instead of a controlled exit-2 CLI error.

`python3 -B -m unittest tests.test_active_memory_boundary -v` failed to import because the consolidated module did not yet exist. This establishes that the absorbed active-memory vectors were not already passing accidentally.

## Green result

`make check` completed successfully:

```text
Ran 27 tests in 0.092s
OK
PASS 13/13 knowledge ingestion contract cases
PASS 5/5 active-memory boundary cases
```

The project gate also compiled both modules and all tests, then parsed both fixture bundles and all three JSON Schemas with `python3 -m json.tool`. In a disposable environment, `jsonschema`'s Draft 2020-12 validator checked all three schemas and validated the ingestion bundle, generated receipt, and active-memory bundle (`VALID` for each).

An AST count found 27 test methods and 43 static assertion sites. This is a source-site count, not a dynamic assertion-execution count; loops and subtests can execute one site more than once.

## Independent review fix

A fresh read-only reviewer returned `NEEDS_FIX`: the semantic validator could accept a missing claim ID, malformed `superseded_by` identity, or schema-disallowed fields even though the versioned schema rejected them. Three focused regressions reproduced the blocker and failed before the fix. The stdlib validator now enforces required contract arrays, required claim IDs, exact supersession identities, and closed field sets at bundle, case, contract, source, item, claim, and evidence-reference boundaries. The three targeted regressions then passed, followed by the 27-test project gate and a repeated clean-wheel smoke. A fresh fix re-review returned `PASS` with no blocking findings.

Local interpreter checks passed on every CI version available here: Python 3.9.6, 3.11.14, and 3.13.9. Each ran 27/27 tests and both fixture CLIs successfully.

## Clean package smoke

A PEP 517 wheel was built, installed without dependencies into a fresh Python 3.9.6 virtual environment, and both installed entry points were executed against copied repository fixtures.

```text
agent_knowledge_boundary_contracts-0.1.0-py3-none-any.whl
distribution=0.1.0
ingestion=PASS 13/13 schema_version=1
active_memory=PASS 5/5 active-memory boundary cases
```

## Negative space

The fixture validates supplied metadata and synthetic strings only. It does not prove connector non-access, evidence truth or licensing, digest faithfulness, semantic redaction, production delimiter compatibility, prompt-injection safety, streaming behavior, or full transcript assembly. The CLIs read entire trusted local files into memory and are not unbounded upload validators.
