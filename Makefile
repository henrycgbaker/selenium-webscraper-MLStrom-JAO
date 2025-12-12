# Makefile for JAO Scraper Development
# Provides convenient shortcuts for common development tasks

.PHONY: help install install-dev setup format lint type-check security test clean pre-commit ci all

# Default target
help:
	@echo "JAO Scraper - Development Makefile"
	@echo ""
	@echo "Setup:"
	@echo "  make install        - Install package (production)"
	@echo "  make install-dev    - Install package with dev dependencies"
	@echo "  make setup          - Complete development environment setup"
	@echo ""
	@echo "Development:"
	@echo "  make format         - Format code with Black and isort"
	@echo "  make lint           - Run Flake8 linting"
	@echo "  make type-check     - Run mypy type checking"
	@echo "  make security       - Run security scans (Bandit, Safety)"
	@echo "  make test           - Run tests"
	@echo "  make check          - Quick check (format + lint)"
	@echo "  make ci             - Run all CI checks locally"
	@echo "  make clean          - Clean cache and build files"
	@echo ""
	@echo "JAO Scraper:"
	@echo "  make jao-api        - Run JAO API scraper"
	@echo "  make jao-selenium   - Run JAO Selenium scraper"
	@echo "  make jao-status     - Check scraper status"
	@echo ""

# Install production dependencies
install:
	pip install --upgrade pip
	pip install -e .

# Install development dependencies
install-dev:
	pip install --upgrade pip
	pip install -e ".[dev]"

# Complete setup for development
setup: install-dev
	pre-commit install
	@echo ""
	@echo "Development environment setup complete!"
	@echo "Run 'make help' to see available commands."

# Format code
format:
	@echo "Running Black..."
	black --line-length=100 src/ scripts/ tests/
	@echo ""
	@echo "Running isort..."
	isort --profile=black --line-length=100 src/ scripts/ tests/
	@echo ""
	@echo "Code formatting complete!"

# Run linting
lint:
	@echo "Running Flake8..."
	flake8 src/ scripts/ tests/ \
		--max-line-length=100 \
		--extend-ignore=E203,W503 \
		--exclude=__pycache__,.git,.venv,venv,build,dist \
		--statistics \
		--count

# Run type checking
type-check:
	@echo "Running mypy..."
	mypy src/webscraper/ \
		--ignore-missing-imports \
		--no-strict-optional

# Run security scans
security:
	@echo "Running Bandit..."
	bandit -r src/ scripts/ \
		-c pyproject.toml \
		--exclude ./tests/ || true
	@echo ""
	@echo "Running Safety..."
	safety check || true
	@echo ""
	@echo "Security scans complete!"

# Run pre-commit hooks
pre-commit:
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

# Run tests
test:
	@echo "Running tests..."
	pytest tests/ -v --cov=webscraper --cov-report=term-missing

# Run all CI checks locally
ci: format lint type-check test
	@echo ""
	@echo "All CI checks complete!"

# Run all quality checks
all: format lint type-check security test
	@echo ""
	@echo "All quality checks complete!"

# Quick check before commit
check: format lint
	@echo ""
	@echo "Quick check complete! Ready to commit."

# Clean cache and build files
clean:
	@echo "Cleaning cache and build files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/ src/*.egg-info/
	rm -rf .coverage htmlcov/
	rm -rf .mypy_cache/ .pytest_cache/ .ruff_cache/
	rm -f bandit-report.json safety-report.json pip-audit-report.json
	@echo "Clean complete!"

# Validate package structure
validate:
	@echo "Validating package imports..."
	@python -c "from webscraper import BaseScraper, ScraperConfig; print('webscraper - OK')"
	@python -c "from scripts.jao.api_scraper import JAOAPIScraper; print('JAO API Scraper - OK')"
	@python -c "from scripts.jao.scraper import JAOSeleniumScraper; print('JAO Selenium Scraper - OK')"
	@echo "Package structure validated!"

# Show project stats
stats:
	@echo "Project Statistics:"
	@echo ""
	@echo "Python files:"
	@find . -name "*.py" -not -path "*/venv/*" -not -path "*/.venv/*" | wc -l
	@echo ""
	@echo "Lines of code:"
	@find . -name "*.py" -not -path "*/venv/*" -not -path "*/.venv/*" -exec wc -l {} + | tail -1

# JAO Scraper shortcuts
JAO_START_DATE ?= 2022-06-08
JAO_END_DATE ?= 2024-12-31
JAO_OUTPUT_DIR ?= ./data

jao-api:
	python -m scripts.jao.api_scraper \
		--start-date $(JAO_START_DATE) \
		--end-date $(JAO_END_DATE) \
		--output-dir $(JAO_OUTPUT_DIR)

jao-selenium:
	python -m scripts.jao.scraper \
		--start-date $(JAO_START_DATE) \
		--end-date $(JAO_END_DATE) \
		--output-dir $(JAO_OUTPUT_DIR) \
		--headless

jao-status:
	@if [ -f "$(JAO_OUTPUT_DIR)/scraper_state.json" ]; then \
		python -m webscraper.cli status --state-file $(JAO_OUTPUT_DIR)/scraper_state.json; \
	else \
		echo "No state file found at $(JAO_OUTPUT_DIR)/scraper_state.json"; \
	fi
