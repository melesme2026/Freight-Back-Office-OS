$ErrorActionPreference = "Stop"

$checks = @(
  @{ Name = "Backend ruff"; Command = "python -m ruff check backend/app backend/tests" },
  @{ Name = "Backend compile"; Command = "python -m compileall -q backend/app" },
  @{ Name = "Backend unit tests"; Command = "python -m pytest backend/tests/unit -q" },
  @{ Name = "Backend integration tests"; Command = "python -m pytest backend/tests/integration -q" },
  @{ Name = "Frontend npm ci dry-run"; Command = "npm --prefix frontend ci --dry-run" },
  @{ Name = "Frontend typecheck"; Command = "npm --prefix frontend run typecheck" },
  @{ Name = "Frontend build"; Command = "npm --prefix frontend run build" },
  @{ Name = "Frontend lint"; Command = "npm --prefix frontend run lint" },
  @{ Name = "Playwright list"; Command = "npm --prefix frontend run e2e:list" },
  @{ Name = "Playwright Chromium"; Command = "npm --prefix frontend run e2e:chromium" },
  @{ Name = "Playwright mobile Chrome"; Command = "npm --prefix frontend run e2e:mobile" },
  @{ Name = "Docker compose config"; Command = "docker-compose config" },
  @{ Name = "Docker compose reset"; Command = "docker-compose down -v --remove-orphans" },
  @{ Name = "Docker compose up"; Command = "docker-compose up -d" },
  @{ Name = "Docker compose ps"; Command = "docker-compose ps" },
  @{ Name = "Alembic current"; Command = "docker-compose exec -T api alembic current"; MustContain = "20260509_0048" }
)

$failed = $false
foreach ($check in $checks) {
  Write-Host "`n==> $($check.Name)" -ForegroundColor Cyan
  $global:LASTEXITCODE = 0
  $output = Invoke-Expression $check.Command 2>&1
  $exitCode = if ($LASTEXITCODE -ne $null) { $LASTEXITCODE } else { 0 }
  $output | ForEach-Object { Write-Host $_ }
  if ($exitCode -ne 0 -or ($check.MustContain -and (($output -join "`n") -notmatch [regex]::Escape($check.MustContain)))) {
    Write-Host "FAIL: $($check.Name)" -ForegroundColor Red
    $failed = $true
    break
  }
  Write-Host "PASS: $($check.Name)" -ForegroundColor Green
}

if ($failed) {
  Write-Host "`nLAUNCH GATE: FAIL" -ForegroundColor Red
  exit 1
}

Write-Host "`nLAUNCH GATE: PASS" -ForegroundColor Green
