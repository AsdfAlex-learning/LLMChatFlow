Param(
  [string]$EnvName = "llmchatflow",
  [string]$PyVer = "3.11"
)
$ErrorActionPreference = "Stop"

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
  throw "conda not found"
}

conda create -y -n $EnvName ("python=" + $PyVer)
& conda "shell.powershell" "hook" | Out-String | Invoke-Expression
conda activate $EnvName

python -m pip install -U pip setuptools wheel
pip install -r requirements.txt
pip install -e .

if (Test-Path ".env.example" -and -not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

Write-Output "OK: conda env ready"
