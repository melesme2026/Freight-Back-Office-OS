#!/usr/bin/env bash
set -euo pipefail

echo "Bootstrapping Freight Back Office OS local environment..."

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

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
  echo "Installing frontend dependencies..."
  (
    cd frontend
    npm install
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
echo "3. Or run backend locally with: uvicorn app.main:app --reload"