# Agent Knowledge Boundary Contracts

Portable, dependency-free conformance fixtures for agent knowledge pipelines. The repository keeps two related invariants in one public surface instead of publishing overlapping memory micro-tools:

1. **Ingestion policy:** source identity, currentness, evidence references, and export authority are separate checks.
2. **Prompt-boundary preservation:** stripping a fully delimited leading memory block must not remove, duplicate, or reorder the user text after it.

All checked-in examples are synthetic. The CLIs read local JSON, emit deterministic receipts, and perform no network, corpus, memory-store, or write-back operations.

## Quickstart

```bash
git clone https://github.com/prasithg/agent-knowledge-boundary-contracts.git
cd agent-knowledge-boundary-contracts
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .

knowledge-contract-lint fixtures/ingestion_policy_cases.json
active-memory-boundary fixtures/active_memory_boundary_cases.json
python -m unittest discover -s tests -v
```

Expected final lines:

```text
PASS 13/13 knowledge ingestion contract cases
PASS 5/5 active-memory boundary cases
```

Use `knowledge-contract-lint --json ...` for a machine-readable receipt.

## Contract 1: source, freshness, and export authority

The version-1 fixture asserts:

- item identity is `(source_id, slug)`, so the same slug may exist in different sources but not twice in one source;
- source IDs are unique and retained items from disabled sources fail closed;
- every claim cites evidence by its full source/slug identity;
- expired or superseded evidence cannot support a current claim;
- public claims require both `sensitivity: public` and `public_reuse: true`;
- malformed timestamps and destinations fail explicitly;
- multiple violations retain deterministic source/item/claim traversal order.

The validator reports all deterministic violations it can establish from already-materialized metadata:

```python
from knowledge_ingestion_contracts import evaluate_contract

violations = evaluate_contract(
    {
        "sources": [
            {"id": "notes", "enabled": True, "sensitivity": "private", "public_reuse": False}
        ],
        "items": [
            {"source_id": "notes", "slug": "draft", "observed_at": "2026-07-09T18:00:00Z"}
        ],
        "claims": [
            {"id": "post", "destination": "public", "evidence": [{"source_id": "notes", "slug": "draft"}]}
        ],
    },
    "2026-07-09T22:00:00Z",
)
assert [entry["code"] for entry in violations] == ["public_export_denied"]
```

## Contract 2: active-memory prefix preservation

The second fixture preserves the exact suffix after one or more complete leading `<active-memory>` blocks and their immediate blank separators. It covers separator counts 0–3, LF/CRLF, multiple blocks, no terminal newline, malformed blocks, and non-leading lookalikes.

```python
from active_memory_boundary import strip_leading_active_memory

text = "<active-memory>\nfact: synthetic\n</active-memory>\n\nSENTINEL: retain me\n"
assert strip_leading_active_memory(text) == "SENTINEL: retain me\n"
```

Production adapters should own their actual delimiters and port the fixture inputs/outputs rather than treating this illustrative tag as a protocol standard.

## Schemas and portability

- `schemas/ingestion-policy-bundle.schema.json` — versioned sources, items, claims, and expected cases. Valid cases must match the contract schema; intentionally invalid negative cases remain representable.
- `schemas/ingestion-receipt.schema.json` — machine-readable CLI receipt.
- `schemas/active-memory-boundary.schema.json` — versioned preservation vectors.

The Python validators enforce the semantic invariants and basic bundle shape with the standard library. They do not implement a general JSON Schema engine. Other implementations can consume the schemas and must preserve violation ordering if they compare exact receipts.

## Provenance

The source-scoping fixture was informed by public GBrain fixes [#2697](https://github.com/garrytan/gbrain/pull/2697) and [#2698](https://github.com/garrytan/gbrain/pull/2698). The prefix-preservation matrix was informed by OpenClaw [issue #105441](https://github.com/openclaw/openclaw/issues/105441) and [PR #105504](https://github.com/openclaw/openclaw/pull/105504). The implementations and synthetic fixtures here are original reference code; no upstream source or private corpus was copied. See [PROVENANCE.md](PROVENANCE.md).

## Security and negative space

This repository validates supplied metadata and synthetic strings. It does **not**:

- prove a connector never opened a disabled or private source;
- retrieve, redact, summarize, score, or export knowledge;
- authorize reuse based on content semantics or legal rights;
- validate digest faithfulness or safe-meaning preservation;
- mutate a memory store, transcript, prompt, or provider request;
- model streaming chunks, Unicode normalization, production delimiters, or full transcript assembly;
- safely accept unbounded or adversarial JSON uploads.

Treat it as a conformance-vector repository, not an ingestion service, policy engine, sanitizer, or security boundary. See [SECURITY.md](SECURITY.md).

## Development

```bash
make check
```

Python 3.9 or newer is supported. The package has no runtime dependencies and is licensed under MIT.
