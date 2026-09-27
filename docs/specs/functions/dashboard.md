# Dashboard function specification

Module: `src/dashboard.py`

## Module initialization

Creates a `PipelineConfig`, sets the `STREAMLIT_THEME_BASE` environment default, imports Streamlit, and derives output root, default run date, labels, metric names, and chart names from configuration. The dashboard uses run artifact files only; it does not query the input sources.

## `available_runs(output_root=None) -> list[str]`

Returns output child-directory names, newest-first using reverse lexical ordering, only if the configured KPI artifact exists and `_SUCCESS.json` is valid JSON with `status=completed` and a matching `run_date`. Failed/hidden attempts and legacy partitions without a manifest are not listed. If output root does not exist, returns an empty list.

## Cached CSV loaders

`load_kpis`, `load_clean_data`, `load_anomalies`, and `load_seller_accountability` return `pandas.read_csv(path)`. Streamlit `cache_data` uses file path and modified timestamp as cache inputs. `_load_csv(loader, path)` obtains `st_mtime_ns` and invokes the appropriate cached loader; missing/unstatable files raise filesystem errors.

## Presentation helpers

- `_metric_value(metrics, key)`: return a float, replacing absent or null values with `0.0`.
- `_display_chart(run_dir, filename, caption)`: display configured PNG if present; otherwise show an informational message.

## `main() -> None`

1. Configure Streamlit page title, icon, and layout.
2. Render executive context and find available KPI-bearing runs.
3. If no runs are available, show an error and stop.
4. Render a sidebar radio list of run dates. Prefer `DEFAULT_RUN_DATE` (the configured environment variable name) when it matches an available run; otherwise select the newest.
5. Load and validate KPI CSV columns (`Metric`, `Value`); show an error and stop on filesystem, CSV parser, or required-column errors.
6. Render tabs:
   - **Executive Summary:** headline metrics with denominator, coverage, and exclusions; charts; stage averages for all comparable delivered orders and late orders.
   - **Full Data Explorer:** enriched order-context CSV, substring case-insensitive order-ID filter, row count, and interactive dataframe.
   - **Seller Accountability:** seller metrics filtered by configured `ui.seller_min_order_count`, with all seller rows in an expander and an attribution caveat.
   - **Quality Exceptions:** informational empty state when anomaly file does not exist; otherwise display count and exception dataframe.

### Dashboard caveats

- KPI file must include `Metric` and `Value`; malformed numeric values become null and render as zero.
- The stage table reads six named metrics and displays zero for any missing label.
- Seller metrics are association views: multi-seller orders contribute to each participating seller and do not prove exclusive fault.
- Anomaly count is based on the number of artifact rows, not distinct IDs beyond the row-level validator output.
- Files are cached by modification timestamp; external replacement preserving an identical nanosecond mtime could leave cached data until cache invalidation.
- UI behavior is dependent on Streamlit and its frontend CSS selectors for the scrollable sidebar.
