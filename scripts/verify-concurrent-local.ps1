param(
  [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else {
  Split-Path -Parent $MyInvocation.MyCommand.Path
}
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptRoot "..")).Path

$profiles = @(
  @{
    Name = "local-dev"
    DbTarget = "postgres-local"
    BackendPort = 8000
    FrontendPort = 5173
    ApiUrl = "http://127.0.0.1:8000"
    FrontendUrl = "http://127.0.0.1:5173"
    TempDir = "backend/output/imports/temp/local-dev"
  },
  @{
    Name = "local-prod"
    DbTarget = "supabase"
    BackendPort = 8001
    FrontendPort = 5174
    ApiUrl = "http://127.0.0.1:8001"
    FrontendUrl = "http://127.0.0.1:5174"
    TempDir = "backend/output/imports/temp/local-prod"
  }
)

function Read-EnvFile {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Required env file is missing: $Path"
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

function Require-Equal {
  param([string]$Label, [string]$Actual, [string]$Expected)
  if ($Actual -ne $Expected) {
    throw "$Label must be '$Expected', got '$Actual'."
  }
}

function Normalize-PathValue {
  param([string]$Value)
  return ($Value -replace "\\", "/").TrimEnd("/")
}

$resolved = @{}
foreach ($profile in $profiles) {
  $name = $profile.Name
  $backendEnvPath = Join-Path $repoRoot ".env.$name"
  $frontendEnvPath = Join-Path $repoRoot "apps\web\.env.$name"
  $backendEnv = Read-EnvFile $backendEnvPath
  $frontendEnv = Read-EnvFile $frontendEnvPath

  Require-Equal "$name APP_ENV" $backendEnv.APP_ENV $name
  Require-Equal "$name ENV_PROFILE" $backendEnv.ENV_PROFILE $name
  Require-Equal "$name DB_TARGET" $backendEnv.DB_TARGET $profile.DbTarget
  Require-Equal "$name BACKEND_PORT" $backendEnv.BACKEND_PORT ([string]$profile.BackendPort)
  Require-Equal "$name VITE_API_URL" $frontendEnv.VITE_API_URL $profile.ApiUrl
  Require-Equal "$name VITE_API_BASE_URL" $frontendEnv.VITE_API_BASE_URL $profile.ApiUrl
  Require-Equal "$name IMPORT_TEMP_DIR" `
    (Normalize-PathValue $backendEnv.IMPORT_TEMP_DIR) `
    (Normalize-PathValue $profile.TempDir)

  $resolved[$name] = @{
    Backend = $backendEnv
    Frontend = $frontendEnv
  }
}

$devTemp = Normalize-PathValue $resolved["local-dev"].Backend.IMPORT_TEMP_DIR
$prodTemp = Normalize-PathValue $resolved["local-prod"].Backend.IMPORT_TEMP_DIR
if ($devTemp -eq $prodTemp) {
  throw "IMPORT_TEMP_DIR must differ between local-dev and local-prod."
}

if ($ValidateOnly) {
  Write-Host "Concurrent configuration validation PASS."
  Write-Host "local-dev : backend 8000, frontend 5173, API 8000, isolated temp"
  Write-Host "local-prod: backend 8001, frontend 5174, API 8001, isolated temp"
  exit 0
}

foreach ($profile in $profiles) {
  foreach ($port in @($profile.BackendPort, $profile.FrontendPort)) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $listener) {
      throw "$($profile.Name) expected port $port is not listening."
    }
  }

  $info = Invoke-RestMethod `
    -Uri "$($profile.ApiUrl)/api/system/info" `
    -Method Get `
    -TimeoutSec 15
  Require-Equal "$($profile.Name) system APP_ENV" $info.app_env $profile.Name
  Require-Equal "$($profile.Name) system ENV_PROFILE" $info.env_profile $profile.Name
  Require-Equal "$($profile.Name) system DB_TARGET" $info.db_target $profile.DbTarget
  Require-Equal "$($profile.Name) system backend port" `
    ([string]$info.backend_port) ([string]$profile.BackendPort)
  Require-Equal "$($profile.Name) system temp dir" `
    (Normalize-PathValue $info.import_temp_dir) `
    (Normalize-PathValue $profile.TempDir)

  if (-not $info.migration_table_found) {
    throw "$($profile.Name) schema_migrations table was not found."
  }
  Require-Equal "$($profile.Name) migration count" ([string]$info.migration_count) "24"
  Require-Equal "$($profile.Name) latest migration" `
    $info.latest_migration "021_backfill_blu_transaction_search_index.sql"

  if ($profile.Name -eq "local-dev") {
    if ($info.database_host -notin @("localhost", "127.0.0.1", "::1")) {
      throw "local-dev system info does not show a loopback database host."
    }
    Require-Equal "local-dev database name" $info.database_name "finance_dashboard_local"
  } elseif ($info.database_host -notlike "*supabase*") {
    throw "local-prod system info does not show a masked Supabase host."
  }

  $health = Invoke-RestMethod `
    -Uri "$($profile.ApiUrl)/api/health/db" `
    -Method Get `
    -TimeoutSec 15
  Require-Equal "$($profile.Name) database health" $health.database "connected"

  $frontend = Invoke-WebRequest `
    -Uri $profile.FrontendUrl `
    -UseBasicParsing `
    -TimeoutSec 15
  if ($frontend.StatusCode -ne 200) {
    throw "$($profile.Name) frontend returned HTTP $($frontend.StatusCode)."
  }

  $cors = Invoke-WebRequest `
    -Uri "$($profile.ApiUrl)/api/system/info" `
    -Method Options `
    -Headers @{
      Origin = $profile.FrontendUrl
      "Access-Control-Request-Method" = "GET"
    } `
    -UseBasicParsing `
    -TimeoutSec 15
  Require-Equal "$($profile.Name) CORS origin" `
    $cors.Headers["Access-Control-Allow-Origin"] $profile.FrontendUrl

  $crossOrigin = if ($profile.Name -eq "local-dev") {
    "http://127.0.0.1:5174"
  } else {
    "http://127.0.0.1:5173"
  }
  $crossOriginRejected = $false
  try {
    $crossCors = Invoke-WebRequest `
      -Uri "$($profile.ApiUrl)/api/system/info" `
      -Method Options `
      -Headers @{
        Origin = $crossOrigin
        "Access-Control-Request-Method" = "GET"
      } `
      -UseBasicParsing `
      -TimeoutSec 15
    if ($crossCors.Headers["Access-Control-Allow-Origin"] -ne $crossOrigin) {
      $crossOriginRejected = $true
    }
  } catch {
    $response = $_.Exception.Response
    if ($response -and [int]$response.StatusCode -eq 400) {
      $crossOriginRejected = $true
    } else {
      throw
    }
  }
  if (-not $crossOriginRejected) {
    throw "$($profile.Name) incorrectly allows cross-environment origin $crossOrigin."
  }

  & powershell -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $scriptRoot "database-lifecycle-runner.ps1") `
    -Target $profile.Name `
    -Action baseline
  if ($LASTEXITCODE -ne 0) {
    throw "$($profile.Name) fresh baseline verification failed."
  }

  Write-Host "$($profile.Name) concurrent runtime verification PASS."
}

Write-Host "============================================================"
Write-Host "Concurrent local environment verification PASS"
Write-Host "Ports       : 8000, 8001, 5173, 5174"
Write-Host "API mapping : local-dev -> 8000, local-prod -> 8001"
Write-Host "DB targets  : postgres-local, supabase"
Write-Host "Temp dirs   : isolated"
Write-Host "CORS        : PASS"
Write-Host "Cross-CORS  : rejected"
Write-Host "Baselines   : PASS"
Write-Host "============================================================"
exit 0
