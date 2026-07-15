# Security policy

## Scope

This repository is a local conformance fixture. Its production modules parse user-selected local JSON files, evaluate in-memory metadata or synthetic text, print receipts, and exit. They do not perform network access, subprocess launch, credential discovery, corpus access, persistence, or memory-store mutation.

## Trust boundaries

- Treat fixture paths and JSON as trusted local test input.
- The CLIs read entire files into memory; do not expose them as unbounded upload validators.
- A passing ingestion receipt proves only the supplied metadata satisfies this contract. It cannot prove a connector avoided a disabled source or that evidence content is safe, truthful, licensed, or non-sensitive.
- `strip_leading_active_memory` recognizes illustrative literal delimiters. It is not a general prompt sanitizer and must not be used to claim prompt-injection protection.
- Violation messages can include source IDs, slugs, and timestamps from the supplied fixture. Do not feed secrets or private identifiers into public CI logs.

## Reporting

Please open a GitHub security advisory for a vulnerability in the checked-in code. For ordinary contract gaps, open an issue with a minimized synthetic fixture and the expected receipt.
