$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

Write-Host "Resetting local Freight Back Office OS environment..." -ForegroundColor Yellow

$pathsToRemove = @(
    "data\sandbox\uploaded-docs\*",
    "data\sandbox\extracted-results\*",
    "data\sandbox\test-results\*",
    "backend\.pytest_cache",
    "backend\htmlcov",
    "backend\.coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache"
)

foreach ($path in $pathsToRemove) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if (Test-Path "docker-compose.yml") {
    Write-Host "Stopping Docker services..." -ForegroundColor Cyan
    docker compose down --remove-orphans
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

Write-Host "Local environment reset complete." -ForegroundColor Green
Write-Host "Next recommended steps:" -ForegroundColor Cyan
Write-Host "1. Review .env" -ForegroundColor White
Write-Host "2. Run infra\scripts\bootstrap.ps1" -ForegroundColor White
Write-Host "3. Run docker compose up -d or start services manually" -ForegroundColor White