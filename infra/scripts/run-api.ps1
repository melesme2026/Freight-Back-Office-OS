$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}

Write-Host "Starting Freight Back Office OS API..." -ForegroundColor Cyan
Set-Location "$root\backend"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000