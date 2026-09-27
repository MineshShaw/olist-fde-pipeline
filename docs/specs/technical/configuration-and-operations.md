# Technical specification: configuration and operations

## Configuration sources and precedence

`PipelineConfig` merges:

1. Internal defaults in `src/config.py`.
2. YAML at repository-root `config.yaml`, or path selected by `OLIST_CONFIG_FILE`.
3. Environment variables present in `ENV_OVERRIDES`.
4. Explicit constructor values.

Higher precedence wins. `.env` is only read by `run_pipeline.sh` and `run_tests.sh` as shell syntax, with exported assignments; it is not a Python dotenv file. Do not put untrusted shell content in `.env`.

YAML unknown keys and type mismatches are rejected. Environment overrides convert according to their mapping; malformed numbers/list values raise `ValueError`. Semantic validation runs after merge.

## Environment override map

Supported prefixes and themes are defined by `ENV_OVERRIDES` in `src/config.py`. They include:

- API endpoint/base URL, timeout, retry settings, page size/parameters.
- Raw/output roots, output subdirectory names, SQLite filename.
- CSV inputs, encoding and delimiter; SQLite queries.
- Timestamp names, seconds per day, delivered status.
- Chart palette/style/size/bins and artifact names.
- Dashboard theme/title/icon/layout/script/port/default-run environment and sidebar height.
- Seller minimum-volume threshold.
- API response key names and seller artifact naming.

Use `.env.example` and `config.yaml.example` as authoritative examples; unsupported `OLIST_*` names do not change config.

## Path resolution

| Path setting | Resolution |
| --- | --- |
| `paths.raw_data` | Relative to repository root. |
| `paths.output_dir` | Relative to repository root. |
| CSV filenames | `data_dir / filename`; absolute filename overrides root by `pathlib` semantics. |
| `paths.sqlite_file` | `data_dir / sqlite_file`; absolute filename overrides root. |
| output subdirectory names | `run_dir / subdirectory`. |
| dashboard script | Passed to Streamlit as configured; expected to be valid relative to process working directory, which wrappers set to repository root. |

## Script operations

`run_pipeline.sh [YYYY-MM-DD]`:

- Uses `set -Eeuo pipefail` and moves to repository root.
- Checks exact `.python-version` before creating/using the virtual environment.
- Validates a real GNU/Linux calendar date before dependency installation.
- Creates `.venv` if its activation file is absent and activates it.
- Sources local `.env`, if present.
- Writes `.streamlit/config.toml` with browser usage collection disabled.
- Installs pinned direct requirements constrained by the CPython 3.14 Linux transitive snapshot.
- Defaults run date to system date.
- Executes Python pipeline; Streamlit then retains the process.

Before extraction the Python pipeline checks HTTP reachability of the configured payments endpoint. It does not start a local fixture server. Start an API matching `api.url` and endpoint contract separately.

`run_tests.sh` performs the same environment bootstrap and invokes `python -m pytest tests/ -v`; test failure propagates as a non-zero script status.

## Local API fixture

Start from project root after installing dependencies:

```bash
uvicorn data.api.main:app --host 127.0.0.1 --port 8000
```

Fixture file paths are module-relative. `OLIST_API_RATE_LIMIT` and `OLIST_API_RATE_WINDOW` configure process-local throttling at module import. The pipeline has configured timeout/retries and needs a routable URL matching `api.url`.

## Streamlit handoff

After staged artifact generation, pipeline writes `_SUCCESS.json` and promotes the run partition, then pipeline:

- Sets `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`.
- Sets the environment variable named by `ui.default_run_date_env` to current run date.
- Sets `STREAMLIT_THEME_BASE` from `ui.default_theme`.
- Replaces `sys.argv` with `streamlit run <script> --server.port <port> --theme.base <theme>`.
- Calls `stcli.main()` in the same process and exits with its result.

The default port is 8501. To stop the server, interrupt the pipeline terminal. A pre-existing port occupant can prevent Streamlit startup.

## Dependency/test policy

`requirements.txt` pins direct dependencies. `constraints-py3.14-linux.txt` pins the transitive environment observed for CPython 3.14 on Linux; it is platform/interpreter targeted and must be regenerated for other targets. `.python-version` records the exact version expected by scripts. The test suite is offline except local fixture route tests invoked in-process. `test_api.py` is a manual smoke check and requires a running fixture server.
