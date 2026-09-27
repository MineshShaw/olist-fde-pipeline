# Pipeline and logging function specification

Modules: `src/pipeline.py`, `src/logger.py`

## `PipelineOrchestrator(run_date, config=None, base_output_dir=None)`

Creates a configured run context. If `config` is omitted, creates `PipelineConfig` with optional output-root override. Creates a hidden sibling staging directory with log, data, and visualization subdirectories; the published partition is not modified at initialization.

```text
<output-root>/.<run_date>.staging-<unique-id>/{<logs-dir>,<data-dir>,<visualizations-dir>}
```

The constructor does not validate `run_date`; `run_pipeline.sh` checks a calendar-valid date before environment installation.

## `PipelineOrchestrator.run()`

Executes these fail-fast steps:

1. Check the configured payments API endpoint responds successfully under a bounded timeout.
2. Extract configured sources through `DataExtractor.run_all`; count raw orders.
3. Validate datasets and reconcile raw count with clean + anomalous rows.
4. Save anomaly evidence in the attempt stage; if no clean orders remain, fail without replacing the published partition.
5. Build the event model and KPI table; count delivered anomalies for exclusion and coverage metrics.
6. Aggregate Items and Payments to order grain, enrich customer/geolocation fields, and build seller-order accountability.
7. Generate charts and write every artifact into staging.
8. Write `_SUCCESS.json` to staging, move any prior partition to a backup, promote staging, restore the backup if promotion fails, and clean the backup.
9. Set dashboard environment variables and hand off the current process to Streamlit CLI (`sys.argv` replacement and `sys.exit(stcli.main())`).

The handoff sets `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`, the configured default-run-date variable, and `STREAMLIT_THEME_BASE`, then selects configured script, port, and theme.

### Failure behavior and persistence

Exceptions before promotion are logged, recorded in `_RUN_STATUS.json`, and leave any prior published partition unchanged. The hidden attempt directory is retained for logs and anomaly evidence. Same-filesystem directory renames and backup restoration protect against failed promotion; this is not a single atomic exchange to readers during the brief rename interval. A failure after successful publication, including dashboard startup failure, does not invalidate the completed run.

## `__main__` CLI

The module parser requires `--run-date` and then constructs `PipelineConfig` and `PipelineOrchestrator`. Missing argument exits through argparse error handling. The shell wrapper supplies this argument.

## `PipelineLogger(config, run_date)`

Creates `<output-root>/<run_date>/<logs-dir>/pipeline.log`, obtains a run-date-named Python logger, sets INFO, disables propagation, and attaches a formatted file handler and terminal handler. Existing handlers for the same logger name are cleared before attaching replacements.

Methods `info(message)`, `warn(message)`, and `error(message)` forward to the underlying logger's INFO, WARNING, and ERROR levels. `default_logger()` creates a logger using default config and today's date.

### Logging caveat

Each `PipelineLogger` construction clears logger handlers by name. Constructing multiple loggers for the same run in one process can replace the handlers attached by earlier instances.
