# Polish article trading

PCA-based statistical arbitrage research across US equities, crypto, and Russian equities.

## Grid search

Run the parameter grid from the project root after installing the package (`pip install -e ".[dev]"`).

```bash
python scripts/grid_search.py --market all
```

Useful options:

- `--market usa|crypto|russia|all` limits which market grids are executed.
- `--max-runs N` runs only the first `N` successful pipeline executions for quick smoke testing.
- `--dry-run` prints the planned run count and parameter combinations without executing the pipeline.

Outputs are written to `results/grid_search/`:

- `grid_search_results.csv` — one row per successful run with metrics and selected universe.
- `grid_search_failures.csv` — failed runs with error messages.
- `best_by_market.csv` — top Sharpe ratio per market.
- `best_by_target.csv` — top Sharpe ratio per market and target.

Result CSV files use a European/Russian Excel-friendly layout:

- semicolon-separated columns (`;`)
- comma decimal separator (`,`)
- UTF-8 with BOM (`utf-8-sig`)

Use `python scripts/analyze_grid_search.py` to rebuild the summary tables from `grid_search_results.csv`.
