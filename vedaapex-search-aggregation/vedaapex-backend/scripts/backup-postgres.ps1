param(
  [string]$OutputDir = (Join-Path $PSScriptRoot "..\\backups")
)

$ErrorActionPreference = "Stop"

if (-not $env:DATABASE_URL) {
  throw "DATABASE_URL is required."
}

if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) {
  throw "pg_dump is required and was not found in PATH."
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $OutputDir "vedaapex-$timestamp.dump"

& pg_dump --format=custom --file $backupFile $env:DATABASE_URL

Write-Host "Backup created at $backupFile"
