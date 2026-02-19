#!/usr/bin/env bash
set -e
ENV_NAME="${1:-llmchatflow}"
PY_VER="${PY_VER:-3.11}"
if ! command -v conda >/dev/null 2>&1; then
  echo "conda not found"
  exit 1
fi
eval "$(conda shell.bash hook)"
conda create -y -n "$ENV_NAME" python="$PY_VER"
conda activate "$ENV_NAME"
python -m pip install -U pip
pip install -r requirements.txt
if [ -f ".env.example" ] && [ ! -f ".env" ]; then
  cp .env.example .env
fi
echo "OK"
