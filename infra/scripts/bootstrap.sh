#!/usr/bin/env bash
set -euo pipefail

echo "Bootstrapping Freight Back Office OS local environment..."

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is not installed or not available on PATH." >&2
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

echo "Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing Python dependencies..."
pip install -e .[dev]

if [ -f "frontend/package.json" ]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "Error: npm is not installed or not available on PATH." >&2
    exit 1
  fi

  echo "Installing frontend dependencies..."
  (
    cd frontend
    if [ -f "package-lock.json" ]; then
      npm ci
    else
      npm install
    fi
  )
fi

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  echo "Creating .env from .env.example..."
  cp .env.example .env
fi

mkdir -p \
  data/sandbox/uploaded-docs \
  data/sandbox/extracted-results \
  data/sandbox/test-results \
  backend/alembic/versions

echo "Bootstrap complete."
echo "Next recommended steps:"
echo "1. Review .env"
echo "2. Run docker compose up -d"
echo "3. Or run backend locally with: cd backend && uvicorn app.main:app --reload"