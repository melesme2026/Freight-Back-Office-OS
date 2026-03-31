SHELL := /bin/sh

.PHONY: help up down build api web worker beat test lint format clean

help:
	@echo "Available targets:"
	@echo "  up       - Start local stack with Docker Compose"
	@echo "  down     - Stop local stack"
	@echo "  build    - Build Docker images"
	@echo "  api      - Run backend API locally"
	@echo "  web      - Run frontend locally"
	@echo "  worker   - Run Celery worker locally"
	@echo "  beat     - Run Celery beat locally"
	@echo "  test     - Run backend tests"
	@echo "  lint     - Run frontend lint and typecheck"
	@echo "  format   - Placeholder format target"
	@echo "  clean    - Remove common local artifacts"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

api:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd frontend && npm run dev

worker:
	cd backend && celery -A app.workers.celery_app.celery_app worker --loglevel=info

beat:
	cd backend && celery -A app.workers.celery_app.celery_app beat --loglevel=info

test:
	cd backend && pytest

lint:
	cd frontend && npm run check

format:
	@echo "Add black / ruff format / prettier in the next pass."

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} \; || true
	find . -type f -name "*.pyc" -delete || true
	rm -rf backend/.pytest_cache backend/htmlcov .pytest_cache .mypy_cache .ruff_cache || true