# Visualization function specification

Module: `src/visualize.py`

## `DataVisualizer(viz_dir=None, logger=None, output_dir=None, config=None)`

Constructs a visualizer with a configured Matplotlib/Seaborn style and output directory. `output_dir`, if provided, takes precedence over `viz_dir`. If neither is provided, raises `ValueError`. The constructor does not create the target directory; the pipeline creates it before chart generation.

## `generate_insights(event_model) -> None`

Writes configured PNG artifacts and removes stale optional charts.

### Transit distribution

If `transit_days` is present, plot a histogram with KDE and `is_late` hue, configured bins and colors; save to the configured transit chart name. It expects `is_late` to be available for the hue argument. If `transit_days` is absent, remove an existing transit chart at the destination.

### Late-order bottleneck chart

Late rows are selected from truthy `is_late` values; if `is_late` is absent, the late subset is empty. When late rows exist, all of `approval_days`, `dispatch_days`, and `transit_days` must exist or a `ValueError` is raised. The chart shows mean duration by stage, saved to the configured bottleneck chart name. If no late rows exist, remove any existing stale bottleneck chart.

### Side effects and errors

- Saves with `bbox_inches="tight"`.
- Closes each Matplotlib figure in `finally`, including save failures.
- Logs chart generation, skip, and stale deletion decisions.
- Filesystem and plotting errors propagate. There is no transactional staging or cleanup of a newly created first chart if generation of the second chart subsequently fails.
