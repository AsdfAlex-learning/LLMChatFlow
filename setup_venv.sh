#!/usr/bin/env bash
set -e
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON=python
fi
"$PYTHON" -m venv .venv
if [ -f ".venv/bin/activate" ]; then
  . ".venv/bin/activate"
else
  . ".venv/Scripts/activate"
fi
python -m pip install -U pip setuptools wheel
pip install -r requirements.txt
pip install -e .
if [ -f ".env.example" ] && [ ! -f ".env" ]; then
  cp .env.example .env
fi
echo "OK"
