# Makefile for Georgian Voiceover App
# Simplifies common development tasks

.PHONY: help install install-dev test test-unit test-integration test-cov test-fast clean lint format security run celery

# Default target
help:
	@echo "Georgian Voiceover App - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install production dependencies"
	@echo "  make install-dev    Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run all tests"
	@echo "  make test-unit      Run unit tests only"
	@echo "  make test-integration  Run integration tests only"
	@echo "  make test-cov       Run tests with coverage report"
	@echo "  make test-fast      Run tests in parallel (fast)"
	@echo "  make test-watch     Run tests in watch mode"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Run linters (flake8, pylint)"
	@echo "  make format         Format code with black"
	@echo "  make type-check     Run mypy type checking"
	@echo "  make security       Run security checks (bandit, safety)"
	@echo ""
	@echo "Application:"
	@echo "  make run            Run Flask development server"
	@echo "  make celery         Run Celery worker"
	@echo "  make redis          Start Redis (Docker)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          Clean generated files"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# Testing
test:
	pytest

test-unit:
	pytest -m unit

test-integration:
	pytest -m integration

test-cov:
	pytest --cov=src --cov=app --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

test-fast:
	pytest -n auto

test-watch:
	pytest-watch

test-smoke:
	pytest -m smoke

# Code Quality
lint:
	@echo "Running flake8..."
	flake8 src/ app.py celery_app.py --max-line-length=120 --exclude=venv,env,.venv
	@echo "Running pylint..."
	pylint src/ app.py celery_app.py --max-line-length=120 || true

format:
	@echo "Formatting with black..."
	black src/ tests/ app.py celery_app.py --line-length=120
	@echo "Sorting imports with isort..."
	isort src/ tests/ app.py celery_app.py

type-check:
	mypy src/ app.py celery_app.py --ignore-missing-imports

security:
	@echo "Running bandit security scanner..."
	bandit -r src/ app.py -ll
	@echo "Checking dependencies for vulnerabilities..."
	safety check

# Application
run:
	python app.py

celery:
	celery -A celery_app worker --loglevel=info

redis:
	docker-compose up redis

# Cleanup
clean:
	@echo "Cleaning generated files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type f -name '.coverage' -delete
	find . -type f -name 'coverage.xml' -delete
	find . -type f -name 'coverage.json' -delete
	@echo "Clean complete!"

# CI/CD simulation
ci:
	@echo "=== Running CI Pipeline ==="
	@echo "1. Installing dependencies..."
	make install-dev
	@echo "2. Running linters..."
	make lint
	@echo "3. Running type checks..."
	make type-check
	@echo "4. Running security checks..."
	make security
	@echo "5. Running tests with coverage..."
	make test-cov
	@echo "=== CI Pipeline Complete ==="

# Pre-commit hook
pre-commit:
	@echo "Running pre-commit checks..."
	make format
	make lint
	make test-unit
	@echo "Pre-commit checks passed!"
