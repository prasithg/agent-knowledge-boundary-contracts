.PHONY: check

check:
	python3 -m unittest discover -s tests -v
	python3 knowledge_ingestion_contracts.py fixtures/ingestion_policy_cases.json
	python3 active_memory_boundary.py fixtures/active_memory_boundary_cases.json
	python3 -m py_compile knowledge_ingestion_contracts.py active_memory_boundary.py tests/*.py
	python3 -m json.tool fixtures/ingestion_policy_cases.json >/dev/null
	python3 -m json.tool fixtures/active_memory_boundary_cases.json >/dev/null
	python3 -m json.tool schemas/ingestion-policy-bundle.schema.json >/dev/null
	python3 -m json.tool schemas/ingestion-receipt.schema.json >/dev/null
	python3 -m json.tool schemas/active-memory-boundary.schema.json >/dev/null
