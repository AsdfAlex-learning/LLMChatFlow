Param(
  [string]$Python = "python"
)
$ErrorActionPreference = "Stop"

& $Python --version | Out-Null
& $Python -m venv .venv

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
  throw "venv activate script not found"
}
. ".\.venv\Scripts\Activate.ps1"

python -m pip install -U pip setuptools wheel
pip install -r requirements.txt
pip install -e .

if (Test-Path ".env.example" -and -not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

Write-Output "OK: venv ready"
