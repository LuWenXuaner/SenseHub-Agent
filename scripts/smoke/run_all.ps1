# SenseHub Agent smoke tests (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Root

Write-Host "=== SenseHub Agent Smoke Tests ===" -ForegroundColor Cyan

if (-not (Test-Path "config\local.env")) {
    Write-Host "Missing config\local.env" -ForegroundColor Red
    exit 1
}

$Python = $null
Get-Content "config\local.env" | ForEach-Object {
    if ($_ -match "^PYTHON_PATH=(.+)$") { $Python = $Matches[1].Trim() }
}
if (-not $Python -or -not (Test-Path $Python)) {
    Write-Host "Invalid PYTHON_PATH in config\local.env" -ForegroundColor Red
    exit 1
}

& $Python scripts\smoke\test_env.py
if ($LASTEXITCODE -ne 0) { exit 1 }

& $Python scripts\smoke\test_llm.py
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "`n--- Phase 1 API tests (backend must be running) ---" -ForegroundColor Cyan
& $Python scripts\smoke\test_phase1.py
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "`n--- Phase 3/4 API tests ---" -ForegroundColor Cyan
& $Python scripts\smoke\test_phase34.py
exit $LASTEXITCODE
