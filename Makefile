.PHONY: help install test eval eval-json ablation lint fmt typecheck verify serve cli clean all

help:
	@echo "install     Install the package with dev extras"
	@echo "test        Run the test suite"
	@echo "eval        Run the five-layer eval harness (release gate)"
	@echo "ablation    Run the scoped vs naive retrieval ablation"
	@echo "verify      Show which rule parameters still need verification"
	@echo "lint        Ruff check"
	@echo "fmt         Ruff format and fix"
	@echo "typecheck   Mypy strict"
	@echo "serve       Run the API on :8000"
	@echo "all         lint + typecheck + test + eval"

install:
	pip install -e ".[dev]"

test:
	pytest tests -v

eval:
	python -m evals.runner

eval-json:
	python -m evals.runner --json

ablation:
	python -m evals.ablation

verify:
	python -m deduction_graph.cli rules 2024 --unverified
	python -m deduction_graph.cli rules 2025 --unverified

lint:
	ruff check src evals tests scripts

fmt:
	ruff format src evals tests scripts
	ruff check --fix src evals tests scripts

typecheck:
	mypy

serve:
	uvicorn deduction_graph.api.main:app --reload --port 8000

cli:
	python -m deduction_graph.cli ask "What is the standard deduction for a single filer in 2024?"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage dist build

all: lint typecheck test eval
