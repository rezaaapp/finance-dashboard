$ErrorActionPreference = "Stop"

$scriptRoot = if ($PSScriptRoot) {
  $PSScriptRoot
} else {
  Split-Path -Parent $MyInvocation.MyCommand.Path
}
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptRoot "..")).Path

$stagedFiles = @(git -C $repoRoot diff --cached --name-only)
if ($LASTEXITCODE -ne 0) {
  [Console]::Error.WriteLine("Security check failed: unable to inspect staged files with git diff --cached --name-only.")
  exit 1
}

if (-not $stagedFiles) {
  Write-Host "Security check passed: no staged files."
  exit 0
}

$blockedFiles = @()

foreach ($file in $stagedFiles) {
  $normalized = $file -replace "\\", "/"
  $name = Split-Path -Path $normalized -Leaf

  $isEnvFile = $name -like ".env*" -and $name -ne ".env.example"
  $isBlockedJson = $name -ieq "credentials.json" `
    -or $name -ilike "service-account*.json" `
    -or $name -ilike "google-service-account*.json" `
    -or $name -ieq "token.json"
  $isBlockedKey = $name -ilike "*.pem" -or $name -ilike "*.key"
  $isBackendOutputJson = $normalized -ilike "backend/output/*.json"

  if ($isEnvFile -or $isBlockedJson -or $isBlockedKey -or $isBackendOutputJson) {
    $blockedFiles += $file
  }
}

if ($blockedFiles.Count -gt 0) {
  [Console]::Error.WriteLine("Security check failed. The following staged files look like secrets or generated private output and must not be committed:")
  foreach ($file in $blockedFiles) {
    [Console]::Error.WriteLine(" - $file")
  }
  [Console]::Error.WriteLine("Unstage/remove these files or commit only safe example files such as .env.example.")
  exit 1
}

Write-Host "Security check passed: no blocked staged files found."
exit 0
