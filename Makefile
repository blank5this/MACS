# MACS Makefile - Convenient development commands

.PHONY: help install dev test lint format clean docker-build docker-run erp-seed erp-test erp-run erp-stop erp-check erp-rag-rebuild erp-logs erp-restart

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

# =====================================================================
# ERP AI Copilot targets
# =====================================================================

# Bring up Postgres + seed it. Idempotent: if already seeded, the
# seed script is smart enough to no-op. Pass ERP_SEED_SCALE=medium
# or large to control volume.
ERP_SEED_SCALE ?= small

erp-up:
	docker compose --profile erp up -d postgres erp-init

# Seed (or re-seed) the ERP database. Use ERP_SEED_SCALE to control
# the volume: small ≈ 300 rows, medium ≈ 1000, large ≈ 5000.
erp-seed:
	@if [ -z "$$POSTGRES_HOST" ]; then \
		echo "Postgres not running locally. Trying docker compose..."; \
		docker compose --profile erp up erp-init; \
	else \
		ERP_SEED_SCALE=$(ERP_SEED_SCALE) python scripts/seed_erp_db.py --scale $(ERP_SEED_SCALE); \
	fi

# Rebuild the RAG index over data/erp_kb/. Useful after editing the
# knowledge-base files.
erp-rag-rebuild:
	python -c "from macs_pkg.erp.rag.indexer import build_erp_rag_engine; from pathlib import Path; build_erp_rag_engine(persist_dir=Path('~/.macs/erp_rag').expanduser(), force_rebuild=True); print('RAG index rebuilt')"

# Run only the ERP unit tests (no Postgres required). Pass
# ERP_INTEGRATION=1 to also run the DB-dependent ones.
erp-test:
	@if [ "$$ERP_INTEGRATION" = "1" ]; then \
		pytest tests/test_erp_web.py \
		       tests/test_erp_copilot_agent.py \
		       tests/test_erp_templates.py \
		       tests/test_erp_rag.py \
		       tests/test_nl2sql.py \
		       tests/test_nl2sql_safety.py \
		       tests/test_inventory_workflow.py \
		       tests/test_erp_health.py \
		       tests/test_erp_db.py \
		       tests/test_erp_mcp.py \
		       tests/test_e2e_workflow.py \
		       -v --tb=short; \
	else \
		pytest tests/test_erp_web.py \
		       tests/test_erp_copilot_agent.py \
		       tests/test_erp_templates.py \
		       tests/test_erp_rag.py \
		       tests/test_nl2sql.py \
		       tests/test_nl2sql_safety.py \
		       tests/test_inventory_workflow.py \
		       tests/test_erp_health.py \
		       -v --tb=short; \
	fi

# Bring up the full ERP stack (Postgres + web UI). Use
# ERP_SEED_SCALE=medium make erp-run to seed at medium volume.
erp-run:
	docker compose --profile erp up -d postgres erp-init erp-web
	@echo "ERP web UI: http://localhost:$${ERP_WEB_PORT:-8001}"
	@echo "Postgres: localhost:$${POSTGRES_PORT:-5432}"

# Stop the ERP stack. Volumes are preserved.
erp-stop:
	docker compose --profile erp down

# Tail logs from the ERP services.
erp-logs:
	docker compose --profile erp logs -f --tail=100

# Restart the ERP web service (picks up code changes).
erp-restart:
	docker compose --profile erp restart erp-web

# Run the CLI health check. Returns 0 if all subsystems OK.
erp-check:
	@python -c "from macs_pkg.erp.health import check_health_sync; r = check_health_sync(ping_db=True); print(r); import sys; sys.exit(0 if r.ok else 1)"

# Run lint on the ERP module only.
erp-lint:
	ruff check macs_pkg/erp/

# Aggregate ERP target: seed + lint + test in one shot.
erp-ci: erp-lint erp-test erp-check
	@echo "✓ ERP CI pipeline passed"
