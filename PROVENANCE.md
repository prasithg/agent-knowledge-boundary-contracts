# Provenance

This umbrella consolidates two previously separate synthetic contract lanes.

## Source-scoped ingestion policy

Public design signals:

- GBrain PR [#2697](https://github.com/garrytan/gbrain/pull/2697): source/path/slug distinctions in schema statistics.
- GBrain PR [#2698](https://github.com/garrytan/gbrain/pull/2698): source-scoped same-slug mutation lookup.

The fixture generalizes those identity lessons into source enablement, freshness, supersession, evidence, and export-authority checks. Its Python implementation and synthetic cases were written independently; no GBrain implementation was copied.

## Active-memory prefix preservation

Public design signals:

- OpenClaw issue [#105441](https://github.com/openclaw/openclaw/issues/105441).
- OpenClaw PR [#105504](https://github.com/openclaw/openclaw/pull/105504).

The five portable vectors and separator-count test matrix were preserved from the local `active-memory-boundary-contract` prototype and consolidated here instead of publishing that prototype as a standalone repository. The source prototype remains untouched. This repository does not copy OpenClaw source or claim compatibility with OpenClaw's private production delimiters.

## Data provenance

Every fixture value is synthetic. No message, browser row, credential, memory record, customer artifact, or private corpus content is included.
