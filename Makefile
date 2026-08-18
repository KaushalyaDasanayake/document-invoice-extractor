.PHONY: golden eval

golden:
	python3 scripts/build_golden_set.py
	python3 scripts/validate_golden.py

PREDICTIONS_DIR ?= golden_set/expected

eval:
	python3 scripts/run_eval.py --predictions-dir $(PREDICTIONS_DIR)
