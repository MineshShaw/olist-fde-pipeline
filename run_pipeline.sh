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

if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "${PROJECT_ROOT}/.env"
    set +a
fi

mkdir -p .streamlit
printf '[browser]\ngatherUsageStats = false\n' > .streamlit/config.toml

python -m pip install --upgrade pip
if [[ -f "$REQUIREMENTS_FILE" ]]; then
    python -m pip install -r "$REQUIREMENTS_FILE"
else
    python -m pip install pandas requests pytest streamlit matplotlib seaborn
fi

if [[ $# -ge 1 ]]; then
    RUN_DATE="$1"
else
    RUN_DATE="$(date +%F)"
fi

if [[ ! "$RUN_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    printf 'Error: run date must use YYYY-MM-DD format; received: %s\n' "$RUN_DATE" >&2
    exit 2
fi

exec python -m src.pipeline --run-date "$RUN_DATE"
