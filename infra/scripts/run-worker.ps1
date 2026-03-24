$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}

Write-Host "Starting Freight Back Office OS Celery worker..." -ForegroundColor Cyan
Set-Location "$root\backend"
celery -A app.workers.celery_app.celery_app worker --loglevel=info