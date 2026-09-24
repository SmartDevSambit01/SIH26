.DEFAULT_GOAL := help

BACKEND_VENV := backend/.venv
SCRIPTS_VENV := .venv

.PHONY: help install install-backend install-scripts install-frontend backend frontend dev test build lint clean

help:
	@echo "SARVAS — available commands:"
	@echo "  make install     Install backend, scripts, and frontend dependencies"
	@echo "  make backend     Run the FastAPI backend        (http://127.0.0.1:8000)"
	@echo "  make frontend    Run the Vite frontend dev server (http://127.0.0.1:5173)"
	@echo "  make dev         Run backend + frontend together (Ctrl+C stops both)"
	@echo "  make test        Run the backend test suite"
	@echo "  make build       Production-build the frontend"
	@echo "  make lint        Lint the frontend"
	@echo "  make clean       Remove venvs, node_modules, and build output"

install: install-backend install-scripts install-frontend

install-backend:
	python3 -m venv $(BACKEND_VENV)
	$(BACKEND_VENV)/bin/pip install -q --upgrade pip
	$(BACKEND_VENV)/bin/pip install -q -r backend/requirements.txt

install-scripts:
	python3 -m venv $(SCRIPTS_VENV)
	$(SCRIPTS_VENV)/bin/pip install -q --upgrade pip
	$(SCRIPTS_VENV)/bin/pip install -q -r scripts/requirements.txt

install-frontend:
	cd frontend && npm install

backend:
	$(BACKEND_VENV)/bin/uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting backend + frontend (Ctrl+C stops both)..."
	@trap 'kill 0' EXIT INT TERM; \
	$(BACKEND_VENV)/bin/uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000 & \
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_gpm_ingestion.py

build:
	cd frontend && npm run build

lint:
	cd frontend && npm run lint

clean:
	rm -rf $(BACKEND_VENV) $(SCRIPTS_VENV) frontend/node_modules frontend/dist
