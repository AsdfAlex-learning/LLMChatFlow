Param(
  [string]$Python = "python"
)
& $Python -m venv .venv
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
  . ".\.venv\Scripts\Activate.ps1"
}
python -m pip install -U pip setuptools wheel
pip install -r requirements.txt
if (Test-Path ".env.example" -and -not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}
Write-Output "OK"
