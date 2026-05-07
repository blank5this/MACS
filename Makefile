# MACS Makefile - Convenient development commands

.PHONY: help install dev test lint format clean docker-build docker-run

# Default target
help:
	@echo "MACS - Multi-Agent Collaboration System"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:' Makefile | sed 's/:.*//g' | sed 's/^/  /'

# Install production dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
dev:
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov black isort mypy

# Run tests
test:
	pytest tests/ -v --tb=short

# Run tests with coverage
test-cov:
	pytest tests/ -v --cov=macs_pkg --cov-report=html --cov-report=term

# Lint code
lint:
	black --check macs_pkg/ tests/
	isort --check macs_pkg/ tests/
	mypy macs_pkg/

# Format code
format:
	black macs_pkg/ tests/
	isort macs_pkg/ tests/

# Type check
typecheck:
	mypy macs_pkg/

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/
	rm -rf __pycache__/ macs_pkg/__pycache__/
	rm -rf .pytest_cache/ .coverage htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Build Docker image
docker-build:
	docker build -t macs:latest .

# Run Docker container
docker-run:
	docker run -it --rm macs:latest python -c "from macs_pkg.llm import MiniMaxProvider; print('MACS ready!')"

# Run with docker-compose
docker-up:
	docker-compose up -d

# Stop docker-compose
docker-down:
	docker-compose down

# Development shell with docker-compose
docker-dev:
	docker-compose run --rm dev

# Run tests in Docker
docker-test:
	docker-compose --profile test up --abort-on-container-exit

# Format and check all in one
check: format lint test

# Create a new Provider template
new-provider:
	@echo "Creating new provider template..."
	@read -p "Provider name (e.g., MyProvider): " name; \
	python -c "name='$$name'; print('macs_pkg/llm/' + name.lower() + '.py')" && \
	echo "Created template. Don't forget to update __init__.py!"

# Release (requires bump2version or similar)
release-patch:
	bump2version patch && git push && git push --tags

release-minor:
	bump2version minor && git push && git push --tags

release-major:
	bump2version major && git push && git push --tags
