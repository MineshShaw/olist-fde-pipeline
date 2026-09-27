# Function specifications

These documents describe the current implementation contract, not a future design. Behavior that appears as a limitation or dependency is called out explicitly; change this specification when code contracts change.

| Specification | Scope |
| --- | --- |
| [Configuration](configuration.md) | Configuration loading, overrides, nested mapping, and validation helpers. |
| [Extraction](extraction.md) | CSV, SQLite, and paginated REST data access. |
| [Validation](validation.md) | Required schema, timestamp coercion, chronology rules, and anomaly outputs. |
| [Modeling](modeling.md) | Event-model fields, duration calculations, KPI denominator, and outputs. |
| [Transformation](transformation.md) | Order-level joins, one-to-many aggregation, postal-code normalization, seller-order facts. |
| [Visualization](visualization.md) | Transit distribution and late-order bottleneck chart generation. |
| [Pipeline and logging](pipeline-and-logging.md) | Run initialization, orchestration, artifact persistence, process handoff, and log methods. |
| [Dashboard](dashboard.md) | Available-run discovery, cached artifact readers, and Streamlit UI behavior. |
| [Local API fixture](api-fixture.md) | Fixture loading, rate limiting, pagination, and endpoint contracts. |
