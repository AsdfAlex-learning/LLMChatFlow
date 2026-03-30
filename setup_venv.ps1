Param(
  [string]$Python = "python",
  [string]$VenvDir = ".venv",
  [switch]$Force
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-VenvSetup {
  & $Python --version | Out-Null

  if ($Force -and (Test-Path $VenvDir)) {
    Remove-Item -Recurse -Force $VenvDir
  }

  if (-not (Test-Path $VenvDir)) {
    & $Python -m venv $VenvDir
  }

  $venvPython = Join-Path $VenvDir "Scripts\python.exe"
  if (-not (Test-Path $venvPython)) {
    throw "venv python not found: $venvPython"
  }

  & $venvPython -m pip install -U pip setuptools wheel
  & $venvPython -m pip install -r requirements.txt
  & $venvPython -m pip install -e .

  $hasEnvExample = Test-Path ".env.example"
  $hasEnv = Test-Path ".env"
  if ($hasEnvExample -and -not $hasEnv) {
    Copy-Item ".env.example" ".env"
  }
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $projectRoot
try {
  Invoke-VenvSetup
  Write-Output "OK: venv ready"
}
finally {
  Pop-Location
}
