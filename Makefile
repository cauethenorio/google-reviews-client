.PHONY: install
install: ## Install the virtual environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using uv"
	@uv sync
	@uvx pre-commit install

.PHONY: lint
lint: ## Lint the code with ruff
	@uv run ruff check .
	@uv run ruff format --diff .

.PHONY: check
check: ## Run all code quality tools.
	@echo "🚀 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "🚀 Linting code: Running pre-commit"
	@uvx pre-commit run -a
	@echo "🚀 Static type checking: Running ty"
	@uv run ty check

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run python -m pytest

.PHONY: test-cov
test-cov: ## Run tests with coverage
	@uv run python -m coverage run -m pytest tests

.PHONY: cov-report
cov-report: ## Generate HTML coverage report
	@uv run python -m coverage html

.PHONY: cov-xml
cov-xml: ## Generate XML coverage report (for CI)
	@uv run python -m coverage xml

.PHONY: cov
cov: test-cov cov-report ## Run tests with coverage and open report

.PHONY: build
build: clean-build ## Build wheel file
	@echo "🚀 Creating wheel file"
	@uvx --from build pyproject-build --installer uv

.PHONY: clean-build
clean-build: ## Clean build artifacts
	@echo "🚀 Removing build artifacts"
	@uv run python -c "import shutil; import os; shutil.rmtree('dist') if os.path.exists('dist') else None"

.PHONY: publish
publish: ## Publish a release to PyPI.
	@echo "🚀 Publishing."
	@uvx twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

.PHONY: build-and-publish
build-and-publish: build publish ## Build and publish.

.PHONY: help
help:
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

.DEFAULT_GOAL := help
