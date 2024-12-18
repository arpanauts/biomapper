# Makefile

.PHONY: test lint format typecheck check clean

# Run tests with coverage
test:
	pytest --cov=biomapper --cov-report=term-missing tests/

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
	poetry run mypy .

# Run all checks
check: format lint typecheck test

# Clean python cache files
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