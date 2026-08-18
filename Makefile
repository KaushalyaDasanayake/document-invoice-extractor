.PHONY: golden

golden:
	python3 scripts/build_golden_set.py
	python3 scripts/validate_golden.py
