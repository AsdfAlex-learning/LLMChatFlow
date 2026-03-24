#!/usr/bin/env bash
set -e
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON=python
fi
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "python not found"
  exit 1
fi
"$PYTHON" -m venv .venv
if [ -f ".venv/bin/activate" ]; then
  . ".venv/bin/activate"
else
  if [ -f ".venv/Scripts/activate" ]; then
    . ".venv/Scripts/activate"
  else
    echo "venv activate script not found"
    exit 1
  fi
fi
python -m pip install -U pip setuptools wheel
pip install -r requirements.txt
pip install -e .
if [ -f ".env.example" ] && [ ! -f ".env" ]; then
  cp .env.example .env
fi
echo "OK: venv ready"
