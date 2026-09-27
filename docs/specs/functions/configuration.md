# Configuration function specification

Module: `src/config.py`

## `PipelineConfig(...)`

Constructs the shared configuration object consumed by extraction, validation, modeling, visualization, logging, pipeline orchestration, and dashboard code.

### Inputs

All constructor arguments are optional:

| Argument | Meaning |
| --- | --- |
| `data_dir` | Explicit raw-data root override. |
| `base_output_dir` | Explicit output root override. |
| `api_url` | Explicit API base URL override. |
| `api_timeout` | Explicit request timeout override. |
| `api_max_retries` | Explicit retry-count override. |
| `api_retry_backoff` | Explicit initial retry delay override. |
| `db_query` | Explicit default SQLite query override. |
| `api_page_size` | Explicit API page-size override. |
| `config_path` | Optional path to the YAML file. Relative paths resolve from repository root. |

`OLIST_CONFIG_FILE` selects the YAML path when `config_path` is omitted. Environment variables listed in `ENV_OVERRIDES` provide overrides.

### Precedence

Values merge in this order, with later sources winning:

1. A deep copy of `DEFAULTS`.
2. YAML content, if the selected file exists.
3. Present `OLIST_*` variables, converted to expected Python types.
4. Non-`None` explicit constructor arguments.

An absent YAML file is accepted and leaves defaults in effect. The constructor does not load `.env`; the run scripts source that file as shell before launching Python.

### Outputs

The instance exposes normalized settings as attributes: resolved `project_root`, `data_dir`, `base_output_dir`; API settings and response-key names; CSV filenames/encoding/delimiter; SQLite file/query settings; model timestamp names and seconds-per-day; validation delivered status; output subdirectories; artifact names; visualization settings; and dashboard UI settings. `settings` contains the merged mapping and `config_path` records the resolved YAML path.

Raw-data/output roots resolve relative to repository root. CSV and SQLite filenames are later joined to `data_dir`. Output subdirectories are later joined to a run partition. `sqlite_file` remains a string so absolute paths remain meaningful when joined using `pathlib`.

### Errors

Raises `ValueError` for unreadable/invalid YAML, non-mapping roots, unknown keys, wrong YAML shape/scalar type, invalid environment-value conversion, and invalid constrained settings. The validation constraints include positive timeout/page size, nonnegative retry count/backoff, integer retry count/page size, retry multiplier at least 1, port 1–65535, supported theme, positive chart dimensions, positive histogram bins, positive seconds/day, and positive sidebar height.

### Supporting functions

- `_merge_mapping(target, source)`: recursively merge mapping values into a target; replace non-mapping leaf values.
- `_set_nested(target, dotted_key, value)`: write an override at a dotted path, creating intermediate mappings as needed.
- `_convert_environment_value(converter, value)`: convert text with its configured type. Lists are comma-separated floats and must contain exactly two values.
- `_copy_mapping(mapping)`: deep-copy a mapping to avoid mutations to shared defaults.
- `_validate_mapping_shape(expected, supplied, prefix)`: recursively reject unknown keys, invalid nested section types, and leaf values of an unexpected YAML type.

## Configuration contract cautions

- Only settings explicitly listed in `ENV_OVERRIDES` have environment variable overrides.
- Environment list conversion supports the configured two-dimensional figure sizes, not arbitrary YAML lists.
- Numeric scalar validation in YAML checks that the supplied value is numeric; semantic ranges are checked separately by `PipelineConfig._validate`.
- Explicit constructor arguments are supported only for the listed constructor parameters.
