param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("local-dev", "local-prod")]
  [string]$Target,

  [Parameter(Mandatory = $true)]
  [ValidateSet("backend", "frontend")]
  [string]$Service,

  [switch]$ValidateOnly,
  [switch]$UseExample
)

$ErrorActionPreference = "Stop"

$scriptRoot = if ($PSScriptRoot) {
  $PSScriptRoot
} else {
  Split-Path -Parent $MyInvocation.MyCommand.Path
}
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptRoot "..")).Path

$profiles = @{
  "local-dev" = @{
    AppEnv = "local-dev"
    DbTarget = "postgres-local"
    BackendPort = "8000"
    FrontendPort = "5173"
    ApiUrl = "http://127.0.0.1:8000"
  }
  "local-prod" = @{
    AppEnv = "local-prod"
    DbTarget = "supabase"
    BackendPort = "8001"
    FrontendPort = "5174"
    ApiUrl = "http://127.0.0.1:8001"
  }
}

$profile = $profiles[$Target]

function Get-EnvPath {
  param(
    [string]$RelativePath
  )

  $path = Join-Path $repoRoot $RelativePath

  if ($UseExample) {
    return "$path.example"
  }

  return $path
}

function Read-EnvFile {
  param(
    [string]$Path
  )

  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Required env file is missing: $Path. Copy the matching .example file first."
  }

  $values = @{}

  foreach ($line in Get-Content -LiteralPath $Path) {
    $trimmed = $line.Trim()

    if (-not $trimmed -or $trimmed.StartsWith("#")) {
      continue
    }

    $separator = $trimmed.IndexOf("=")

    if ($separator -lt 1) {
      continue
    }

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

function Import-EnvValues {
  param(
    [hashtable]$Values
  )

  foreach ($key in $Values.Keys) {
    [Environment]::SetEnvironmentVariable($key, [string]$Values[$key], "Process")
  }
}

function Require-Value {
  param(
    [hashtable]$Values,
    [string]$Key,
    [string]$Expected
  )

  $actual = ""

  if ($Values.ContainsKey($Key)) {
    $actual = [string]$Values[$Key]
  }

  if ($actual -ne $Expected) {
    throw "$Key must be $Expected for $Target, got '$actual'."
  }
}

function Require-Port {
  param(
    [hashtable]$Values,
    [string]$Expected
  )

  $backendPort = ""
  $port = ""

  if ($Values.ContainsKey("BACKEND_PORT")) {
    $backendPort = [string]$Values["BACKEND_PORT"]
  }

  if ($Values.ContainsKey("PORT")) {
    $port = [string]$Values["PORT"]
  }

  if ($backendPort -ne $Expected -and $port -ne $Expected) {
    throw "BACKEND_PORT or PORT must be $Expected for $Target."
  }
}

function Show-BackendBanner {
  param(
    [string]$EnvFile
  )

  Write-Host "============================================================"
  Write-Host " Omon Dashboard backend runner"
  Write-Host "============================================================"
  Write-Host "APP_ENV      : $env:APP_ENV"
  Write-Host "ENV_PROFILE  : $env:ENV_PROFILE"
  Write-Host "DB_TARGET    : $env:DB_TARGET"
  Write-Host "BACKEND_PORT : $env:BACKEND_PORT"
  Write-Host "PORT         : $env:PORT"
  Write-Host "Env file     : $EnvFile"
  Write-Host "Secrets      : hidden"
  Write-Host "============================================================"
}

function Show-FrontendBanner {
  param(
    [string]$EnvFile
  )

  Write-Host "============================================================"
  Write-Host " Omon Dashboard frontend runner"
  Write-Host "============================================================"
  Write-Host "Target            : $Target"
  Write-Host "Frontend port     : $($profile.FrontendPort)"
  Write-Host "VITE_API_URL      : $env:VITE_API_URL"
  Write-Host "VITE_API_BASE_URL : $env:VITE_API_BASE_URL"
  Write-Host "Env file          : $EnvFile"
  Write-Host "Secrets           : hidden"
  Write-Host "============================================================"
}

if ($Service -eq "backend") {
  $envFile = Get-EnvPath ".env.$Target"
  $values = Read-EnvFile $envFile

  Require-Value $values "APP_ENV" $profile.AppEnv
  Require-Value $values "DB_TARGET" $profile.DbTarget
  Require-Port $values $profile.BackendPort

  Import-EnvValues $values
  Show-BackendBanner $envFile

  if ($ValidateOnly) {
    Write-Host "Backend runner validation passed for $Target."
    exit 0
  }

  $python = Join-Path $repoRoot "backend\venv\Scripts\python.exe"

  if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
  }

  Push-Location (Join-Path $repoRoot "backend")
  try {
    & $python -m uvicorn app.main:app --host 127.0.0.1 --port $profile.BackendPort
    exit $LASTEXITCODE
  } finally {
    Pop-Location
  }
}

$envFile = Get-EnvPath "apps\web\.env.$Target"
$values = Read-EnvFile $envFile

Require-Value $values "VITE_API_URL" $profile.ApiUrl
Require-Value $values "VITE_API_BASE_URL" $profile.ApiUrl

Import-EnvValues $values
Show-FrontendBanner $envFile

if ($ValidateOnly) {
  Write-Host "Frontend runner validation passed for $Target."
  exit 0
}

$npm = "npm.cmd"

Push-Location (Join-Path $repoRoot "apps\web")
try {
  & $npm run dev -- --host 127.0.0.1 --port $profile.FrontendPort --mode $Target
  exit $LASTEXITCODE
} finally {
  Pop-Location
}
