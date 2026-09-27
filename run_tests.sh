#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"
REQUIREMENTS_FILE="${PROJECT_ROOT}/requirements.txt"

cd "$PROJECT_ROOT"

if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
    printf 'Creating Python virtual environment at %s\n' "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
if [[ -f "$REQUIREMENTS_FILE" ]]; then
    python -m pip install -r "$REQUIREMENTS_FILE"
else
    python -m pip install pandas requests pytest streamlit matplotlib seaborn
fi

python -m pytest tests/ -v
