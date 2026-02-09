.PHONY: install dev clean build publish formula help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install vegitate into current environment
	pip install .

dev: ## Install in editable mode for development
	pip install -e ".[dev]"

build: ## Build sdist and wheel
	python -m build

clean: ## Remove build artifacts
	rm -rf build/ dist/ src/*.egg-info .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

publish: build ## Publish to PyPI (requires twine)
	twine upload dist/*

formula: ## Regenerate Homebrew formula with latest PyPI hashes
	python scripts/generate_formula.py
