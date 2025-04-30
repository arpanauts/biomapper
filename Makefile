.PHONY: test lint lint-fix format typecheck check clean docs docs-clean docs-serve full-check all

# Default target when just running 'make'
all: check

# Run tests with coverage
test:
	poetry run pytest --cov=biomapper --cov-report=term-missing tests/

# Run linting
lint:
	poetry run ruff check .

# Auto-fix linting issues
lint-fix:
	poetry run ruff check --fix .

# Format code
format:
	poetry run ruff format .

# Type checking
typecheck:
	poetry run mypy --python-version=3.11 .

# Build documentation
docs:
	cd docs && SPHINX_DEBUG=1 make html

# Clean documentation build files
docs-clean:
	cd docs && make clean

# Serve documentation locally
docs-serve:
	cd docs/build/html && python3 -m http.server 8000

# Clean everything - python cache and documentation files
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "*.egg" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	find . -type d -name ".ruff_cache" -exec rm -r {} +
	cd docs && make clean

# Run all checks and build docs
check:
	poetry run ruff format . && \
	poetry run ruff check . && \
	poetry run mypy --python-version=3.11 . && \
	poetry run pytest --cov=biomapper --cov-report=term-missing tests/ && \
	(cd docs && SPHINX_DEBUG=1 make html && cd ..)

# Full check with clean first
full-check: clean check