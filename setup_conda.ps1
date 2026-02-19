Param(
  [string]$EnvName = "llmchatflow",
  [string]$PyVer = "3.11"
)
conda create -y -n $EnvName ("python=" + $PyVer)
conda activate $EnvName
python -m pip install -U pip
pip install -r requirements.txt
pip install -e .
if (Test-Path ".env.example" -and -not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}
Write-Output "OK"
