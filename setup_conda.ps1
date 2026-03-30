Param(
  [string]$EnvName = "llmchatflow",
  [string]$PyVer = "3.11",
  [switch]$Force
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
  throw "conda not found"
}

function Test-CondaEnvExists {
  param([string]$Name)
  $envs = & conda env list --json | ConvertFrom-Json
  foreach ($p in $envs.envs) {
    if ([System.IO.Path]::GetFileName($p) -eq $Name) {
      return $true
    }
  }
  return $false
}

function Invoke-CondaSetup {
  if ($Force) {
    try {
      & conda env remove -y -n $EnvName | Out-Null
    } catch {
    }
  }

  if (-not (Test-CondaEnvExists -Name $EnvName)) {
    & conda create -y -n $EnvName ("python=" + $PyVer)
  }

  & conda run -n $EnvName python -m pip install -U pip setuptools wheel
  & conda run -n $EnvName python -m pip install -r requirements.txt
  & conda run -n $EnvName python -m pip install -e .

  $hasEnvExample = Test-Path ".env.example"
  $hasEnv = Test-Path ".env"
  if ($hasEnvExample -and -not $hasEnv) {
    Copy-Item ".env.example" ".env"
  }
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $projectRoot
try {
  Invoke-CondaSetup
  Write-Output "OK: conda env ready"
} finally {
  Pop-Location
}
