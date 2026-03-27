# scripts/dev.ps1
param(
  [string]$CsvDir = ".\data\drafts",
  [switch]$Ingest,
  [switch]$ResetDb
)

$ErrorActionPreference = "Stop"

function Exec($cmd) {
  Write-Host ">> $cmd" -ForegroundColor Cyan
  cmd /c $cmd
  if ($LASTEXITCODE -ne 0) { throw "Command failed: $cmd" }
}

if ($ResetDb) {
  Exec "docker compose down -v"
}

Exec "docker compose up -d db api"
Exec "docker compose exec api alembic upgrade head"

if ($Ingest) {
  Exec "docker compose exec api python scripts/ingest_csvs.py --csv-dir $CsvDir"
}

Write-Host ""
Write-Host "API:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host "UI:   http://localhost:3000" -ForegroundColor Green