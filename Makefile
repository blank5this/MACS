# MACS Makefile - Convenient development commands

.PHONY: help install dev test lint format clean docker-build docker-run erp-seed erp-test erp-run erp-stop erp-check erp-rag-rebuild erp-logs erp-restart demo demo-bg demo-stop demo-check demo-open demo-logs

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

# =====================================================================
# Local demo (no Docker, no Postgres — pure local FastAPI)
# =====================================================================
# One command to bring up the same UI you'd hit on Render / HF, but
# on your own laptop. Bind port matches the Gradio app.py (7860) for
# muscle-memory parity.

DEMO_HOST ?= 127.0.0.1
DEMO_PORT ?= 7860
DEMO_PIDFILE ?= .macs-demo.pid
DEMO_LOGFILE ?= .macs-demo.log

# Run the demo in the foreground. Ctrl+C to stop.
demo:
	@if [ -f "$(DEMO_PIDFILE)" ] && kill -0 $$(cat $(DEMO_PIDFILE)) 2>/dev/null; then \
		echo "[demo] Already running (pid $$(cat $(DEMO_PIDFILE))). Use 'make demo-stop' first."; \
		exit 1; \
	fi
	@DEMO_HOST=$(DEMO_HOST) DEMO_PORT=$(DEMO_PORT) \
		python -m macs_pkg.erp.web --host $(DEMO_HOST) --port $(DEMO_PORT)

# Run the demo in the background, log to a file, save the pid.
demo-bg:
	@if [ -f "$(DEMO_PIDFILE)" ] && kill -0 $$(cat $(DEMO_PIDFILE)) 2>/dev/null; then \
		echo "[demo] Already running (pid $$(cat $(DEMO_PIDFILE))). Use 'make demo-stop' first."; \
		exit 1; \
	fi
	@echo "[demo] Starting in background -> http://$(DEMO_HOST):$(DEMO_PORT) (log: $(DEMO_LOGFILE))"
	@DEMO_HOST=$(DEMO_HOST) DEMO_PORT=$(DEMO_PORT) \
		nohup python -m macs_pkg.erp.web --host $(DEMO_HOST) --port $(DEMO_PORT) \
		> $(DEMO_LOGFILE) 2>&1 & echo $$! > $(DEMO_PIDFILE)
	@sleep 1.5
	@echo "[demo] pid=$$(cat $(DEMO_PIDFILE))  tail logs with: make demo-logs"

# Tail the background demo log.
demo-logs:
	@if [ ! -f "$(DEMO_LOGFILE)" ]; then echo "[demo] No log file yet."; exit 1; fi
	@tail -f $(DEMO_LOGFILE)

# Health-check the demo (probes /healthz).
demo-check:
	@curl -sS -o /tmp/macs-demo-health.json -w "[demo] /healthz -> %{http_code} (%{time_total}s)\n" \
		--max-time 5 http://$(DEMO_HOST):$(DEMO_PORT)/healthz || true
	@cat /tmp/macs-demo-health.json 2>/dev/null && echo

# Stop the background demo.
demo-stop:
	@if [ ! -f "$(DEMO_PIDFILE)" ]; then echo "[demo] Not running."; exit 0; fi
	@PID=$$(cat $(DEMO_PIDFILE)); \
	if kill -0 $$PID 2>/dev/null; then \
		echo "[demo] Stopping pid $$PID..."; \
		kill $$PID; sleep 1; \
		kill -0 $$PID 2>/dev/null && kill -9 $$PID 2>/dev/null; \
	else \
		echo "[demo] pid $$PID not alive; cleaning pidfile."; \
	fi
	@rm -f $(DEMO_PIDFILE)

# Open the demo URL in the default browser.
demo-open:
	@python -c "import webbrowser; webbrowser.open('http://$(DEMO_HOST):$(DEMO_PORT)/')"

