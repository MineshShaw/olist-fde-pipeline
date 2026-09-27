# Technical specification: architecture and runtime

## Scope

The system is a Python batch pipeline for Olist order-delivery reliability analysis. It is not a streaming ingestion service or a durable warehouse. Its primary user-facing interface is a Streamlit dashboard backed by CSV and PNG artifacts from one run partition.

## Components

| Component | Responsibility | Boundary |
| --- | --- | --- |
| `src.config` | Resolve defaults, YAML, environment, explicit overrides; validate shape and constraints. | Configuration is loaded in-process; Python itself does not source `.env`. |
| `src.extract` | Read CSV, SQLite query results, and paginated HTTP JSON. | API pages and result sets accumulate in memory. |
| `src.validate` | Parse order timestamps and classify malformed, missing-delivered, and reversed lifecycle events. | Other extracted entities pass through unvalidated. |
| `src.transform` | Aggregate one-to-many item/payment sources to order grain, enrich customer/geolocation, and produce seller accountability. | Seller membership is associative, not exclusive causality; no carrier/payment-authorization events. |
| `src.model` | Derive delivery-lateness and stage durations; aggregate KPI rows. | Reports all-comparable and late-only stage averages; KPI rate is based on comparable valid delivered orders. |
| `src.visualize` | Produce transit histogram and late-order stage chart. | PNG files are created inside the hidden staging run. |
| `src.pipeline` | API preflight, orchestration, reconciliation, staged artifact publication, dashboard handoff. | Single process; Streamlit takes over the pipeline process. |
| `src.logger` | Run-specific file and terminal messages. | One file handler plus terminal handler on a Python logger. |
| `src.dashboard` | Browse available output runs and artifact contents. | Reads output files; no direct API/database connection. |
| `data.api.main` | Local FastAPI fixture for payments/geolocation with pagination and rate limiting. | In-memory, local-demo fixture; not production service. |

## End-to-end sequence

1. `run_pipeline.sh` moves to repository root, creates/activates `.venv`, sources trusted `.env` if present, writes local Streamlit browser usage config, installs requirements, and selects/shape-checks run date.
2. It executes `python -m src.pipeline --run-date DATE`.
3. Pipeline creates `<output>/.<DATE>.staging-<id>` and preflights the configured payments endpoint; unreachable API records a failed attempt before extraction.
4. Extractor reads all configured sources. API extraction validates payload and pagination metadata and reconciles record totals if supplied.
5. Validator partitions orders into clean/anomaly frames; pipeline asserts clean + anomaly count equals raw.
6. Modeler calculates the event model and KPI table. Transform aggregates items/payments and joins customer/geolocation; seller facts are computed at a separate seller grain.
7. Visualizer and CSV writers create all outputs in staging. The pipeline writes `_SUCCESS.json`, swaps the previous run directory to a backup, promotes staging, and restores the backup if promotion fails.
8. Dashboard lists only runs with a valid `_SUCCESS.json`; it renders enriched order and seller data via cached CSV readers.

## Run lifecycle and failure modes

- Extraction/API preflight errors are fail-fast; any attempt status/log is kept under a hidden, unpublished staging directory.
- Validation schema errors fail before model creation.
- A mismatch in row reconciliation raises an error.
- If no clean orders remain, anomaly evidence is saved to the failed attempt, and the previous published partition remains untouched.
- A failed artifact write before publication leaves the previous completed partition in place; failures during the two-rename swap trigger backup restoration. The directory swap is not a single atomic exchange for concurrent readers.
- A successful partition is discoverable only after its completion manifest is written and promoted.
- Dashboard takeover is not a detached child process. Stopping the Streamlit process stops the current command.

## Runtime topology

The local FastAPI fixture should be running separately if the pipeline is configured to use it. By default its URL is `http://localhost:8000`. The dashboard defaults to port 8501; both fixture and dashboard ports may conflict with services already bound to those ports.

No distributed queue, cloud object storage, database output sink, scheduler, container, deployment manifest, or authentication layer is included in the current architecture.
