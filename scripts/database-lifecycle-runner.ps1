param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("local-dev", "local-prod")]
  [string]$Target,

  [Parameter(Mandatory = $true)]
  [ValidateSet("baseline", "connection", "migrate", "reset", "seed", "verify")]
  [string]$Action,

  [string]$Confirm,
  [switch]$ValidateOnly,
  [switch]$UseExample
)

$ErrorActionPreference = "Stop"
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else {
  Split-Path -Parent $MyInvocation.MyCommand.Path
}
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptRoot "..")).Path
$envPath = Join-Path $repoRoot ".env.$Target"
if ($UseExample) { $envPath = "$envPath.example" }

function Read-EnvFile {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Required env file is missing: $Path. Copy the matching .example file first."
  }
  $values = @{}
  foreach ($line in Get-Content -LiteralPath $Path) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
    $separator = $trimmed.IndexOf("=")
    if ($separator -lt 1) { continue }
    $key = $trimmed.Substring(0, $separator).Trim()
    $value = $trimmed.Substring($separator + 1).Trim()
    if (
      ($value.StartsWith('"') -and $value.EndsWith('"')) -or
      ($value.StartsWith("'") -and $value.EndsWith("'"))
    ) {
      $value = $value.Substring(1, $value.Length - 2)
    }
    $values[$key] = $value
  }
  return $values
}

$values = Read-EnvFile $envPath
foreach ($key in $values.Keys) {
  [Environment]::SetEnvironmentVariable($key, [string]$values[$key], "Process")
}

$requiredPhrase = $null
if ($Target -eq "local-prod" -and $Action -eq "reset") {
  $requiredPhrase = "RESET SUPABASE OMON"
  Write-Host ""
  Write-Host "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
  Write-Host " WARNING: THIS DELETES ALL DATA IN THE SUPABASE PUBLIC SCHEMA" -ForegroundColor Red
  Write-Host " No backup or dump is created by this Phase 3 workflow." -ForegroundColor Yellow
  Write-Host "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
}
if ($Target -eq "local-prod" -and $Action -eq "migrate") {
  $requiredPhrase = "MIGRATE SUPABASE OMON"
  Write-Host "WARNING: This applies migrations to Supabase local-prod." -ForegroundColor Yellow
}
if ($requiredPhrase -and -not $Confirm -and -not $ValidateOnly) {
  Write-Host "Type the exact confirmation phrase: $requiredPhrase" -ForegroundColor Yellow
  $Confirm = Read-Host "Confirmation"
}

$python = Join-Path $repoRoot "backend\venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { $python = "python" }
$arguments = @(
  (Join-Path $repoRoot "backend\scripts\database_lifecycle.py"),
  "--target", $Target,
  "--action", $Action
)
if ($Confirm) { $arguments += @("--confirm", $Confirm) }
if ($ValidateOnly) { $arguments += "--validate-only" }
if ($Target -eq "local-dev") {
  $arguments += @("--backend-port", "8000")
}

Write-Host "============================================================"
Write-Host " Omon Dashboard database lifecycle"
Write-Host "============================================================"
Write-Host "Target   : $Target"
Write-Host "Action   : $Action"
Write-Host "Env file : $envPath"
Write-Host "Secrets  : hidden"
Write-Host "============================================================"

& $python @arguments
exit $LASTEXITCODE
