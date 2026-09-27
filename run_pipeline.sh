#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"
REQUIREMENTS_FILE="${PROJECT_ROOT}/requirements.txt"
CONSTRAINTS_FILE="${PROJECT_ROOT}/constraints-py3.14-linux.txt"
EXPECTED_PYTHON_VERSION="$(<"${PROJECT_ROOT}/.python-version")"

cd "$PROJECT_ROOT"

if [[ $# -gt 1 ]]; then
    printf 'Usage: %s [YYYY-MM-DD]\n' "$0" >&2
    exit 2
fi

if [[ $# -ge 1 ]]; then
    RUN_DATE="$1"
else
    RUN_DATE="$(date +%F)"
fi

if [[ ! "$RUN_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] \
    || ! NORMALIZED_DATE="$(date -d "$RUN_DATE" +%F 2>/dev/null)" \
    || [[ "$NORMALIZED_DATE" != "$RUN_DATE" ]]; then
    printf 'Error: run date must be a real calendar date in YYYY-MM-DD format; received: %s\n' \
        "$RUN_DATE" >&2
    exit 2
fi

ACTUAL_PYTHON_VERSION="$(python3 -c 'import platform; print(platform.python_version())')"
if [[ "$ACTUAL_PYTHON_VERSION" != "$EXPECTED_PYTHON_VERSION" ]]; then
    printf 'Error: Python %s is required; found %s.\n' \
        "$EXPECTED_PYTHON_VERSION" "$ACTUAL_PYTHON_VERSION" >&2
    exit 2
fi

if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
    printf 'Creating Python virtual environment at %s\n' "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"

VENV_PYTHON_VERSION="$(python -c 'import platform; print(platform.python_version())')"
if [[ "$VENV_PYTHON_VERSION" != "$EXPECTED_PYTHON_VERSION" ]]; then
    printf 'Error: .venv uses Python %s; required version is %s. Recreate .venv.\n' \
        "$VENV_PYTHON_VERSION" "$EXPECTED_PYTHON_VERSION" >&2
    exit 2
fi

if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "${PROJECT_ROOT}/.env"
    set +a
fi

mkdir -p .streamlit
printf '[browser]\ngatherUsageStats = false\n' > .streamlit/config.toml

python -m pip install --upgrade "pip==26.2.1"
if [[ -f "$REQUIREMENTS_FILE" ]]; then
    python -m pip install -r "$REQUIREMENTS_FILE" -c "$CONSTRAINTS_FILE"
else
    python -m pip install \
        "pandas==3.0.6" \
        "matplotlib==3.11.2" \
        "seaborn==0.13.2" \
        "requests==2.34.2" \
        "streamlit==1.64.0" \
        "fastapi==0.141.1" \
        "uvicorn==0.54.0" \
        "jupyter==1.1.1" \
        "pytest==9.1.1" \
        "PyYAML==6.0.3" \
        -c "$CONSTRAINTS_FILE"
fi

exec python -m src.pipeline --run-date "$RUN_DATE"
