$ErrorActionPreference = "Stop"

Write-Host "Bootstrapping Freight Back Office OS local environment..." -ForegroundColor Cyan

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
. .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -e .[dev]

if (Test-Path "frontend\package.json") {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location frontend
    npm install
    Pop-Location
}

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
    }
}

$dirs = @(
    "data\sandbox\uploaded-docs",
    "data\sandbox\extracted-results",
    "data\sandbox\test-results",
    "backend\alembic\versions"
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Host "Bootstrap complete." -ForegroundColor Green
Write-Host "Next recommended steps:" -ForegroundColor Cyan
Write-Host "1. Review .env"
Write-Host "2. Run docker compose up -d"
Write-Host "3. Or run backend locally with: uvicorn app.main:app --reload" -ForegroundColor White