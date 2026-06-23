.DEFAULT_GOAL := help
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Modules enabled for local dev. Override: make run MODULES=dogs
MODULES ?= dogs,subscriptions,feature_requests
export HESTIA_ENABLED_MODULES = $(MODULES)

.PHONY: help install seed run mcp test fmt clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Create venv and install deps (incl. dev)
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"

seed: ## Seed the default household (use TOKEN=1 to mint a Hermes token)
	$(PY) -m scripts.seed $(if $(TOKEN),--token,)

run: ## Run the API + dashboard (http://127.0.0.1:8000)
	$(VENV)/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

mcp: ## Run the MCP server for agents (stdio by default)
	$(PY) -m app.mcp.server

test: ## Run the test suite
	$(PY) -m pytest

fmt: ## Format + lint with ruff (if installed)
	@$(VENV)/bin/ruff check --fix . 2>/dev/null || echo "ruff not installed (pip install ruff)"
	@$(VENV)/bin/ruff format . 2>/dev/null || true

clean: ## Remove caches and the local SQLite db
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -f hestia.db hestia.db-wal hestia.db-shm
	rm -rf .pytest_cache
