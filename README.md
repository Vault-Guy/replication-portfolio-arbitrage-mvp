# PCA-Based Statistical Arbitrage

Research project on synthetic asset replication with PCA and spread trading across U.S. equities, cryptocurrencies, and Russian equities.

**Co-authors:** [Nikita Lukianenko](https://github.com/Vault-Guy) and [Mikhail Chekunov](https://github.com/mikhailchekunov)  
**Original repository:** [mikhailchekunov/replication-portfolio-arbitrage-mvp](https://github.com/mikhailchekunov/replication-portfolio-arbitrage-mvp)

This repository is Nikita Lukianenko's fork of the jointly developed project and is maintained as part of his quantitative research portfolio.

---

## Project Structure

```
replication-portfolio-arbitrage-mvp/
│
├── COMMANDS.md           # run-command reference: full workflow and individual stages
│
├── configs/
│   ├── usa.yaml          # U.S. market parameters: data + strategy
│   ├── crypto.yaml       # crypto market parameters
│   └── russia.yaml       # Russian market parameters
│
├── data/
│   ├── usa_data.zip      # daily adjusted close prices for 142 U.S. stocks, 2016–2026
│   ├── crypto_data.zip   # hourly OHLCV data for 40+ cryptocurrencies, 2020–2026
│   └── russia_data.zip   # daily prices for ~26 Russian stocks from TradingView
│
├── scripts/
│   ├── 01_smoke_test.py              # quick pipeline check across all markets
│   ├── 02_grid_search.py             # parameter grid search: main research runner
│   ├── 03_analyze_grid_search.py     # post-processing of grid-search results
│   ├── 04_export_results_eu.py       # converts CSV output to EU-friendly Excel format
│   ├── analyze_parameter_ranges.py   # parameter-frequency analysis for top 5/10/20%
│   ├── crypto_parameter_grid.py      # staged extended parameter grid for crypto
│   ├── analyze_crypto_parameter_grid.py  # analysis of crypto parameter-grid results
│   └── inspect_zip.py                # utility for inspecting ZIP data archives
│
├── src/sarb/                     # core package: pip install -e ".[dev]"
│   ├── run.py                    # unified run_unified_pipeline() orchestrator
│   ├── reporting.py              # visualizations and summary tables
│   ├── core/
│   │   ├── config.py             # loads YAML configs into MarketConfig
│   │   └── universe.py           # asset-universe selection: priority + fallback
│   ├── data/
│   │   ├── base.py               # ZIP/CSV parsing, panel assembly, validation
│   │   └── loader.py             # generic loader driven by MarketConfig
│   ├── pca/
│   │   ├── model.py              # PCA replication: StandardScaler + PCA + OLS/Ridge
│   │   └── pipeline.py           # walk-forward loop over rebalance windows
│   ├── strategy/
│   │   ├── HOW_BACKTEST_WORKS.md # backtest logic: causality, shifts, transaction costs
│   │   ├── spread.py             # spread calculation and causal rolling z-score
│   │   ├── signals.py            # position generation with hysteresis
│   │   ├── backtest.py           # P&L, transaction costs, equity curve
│   │   └── metrics.py            # Sharpe, MDD, hit rate, turnover, and more
│   └── utils/
│       ├── io.py                 # saves CSV tables
│       ├── time.py               # annualization factor by bar frequency
│       └── eu_export.py          # EU-format conversion: BOM, ;, decimal comma
│
├── notebooks/                    # Jupyter notebooks for interactive analysis
│   ├── 01_inspect_data.ipynb
│   ├── 02_canonical_load.ipynb
│   ├── 03_walk_forward_signals.ipynb
│   ├── 04_run_usa_pipeline.ipynb
│   ├── 05_run_crypto_pipeline.ipynb
│   ├── 06_run_russia_pipeline.ipynb
│   ├── 07_compare_markets.ipynb
│   ├── 08_portfolio_growth_report.ipynb       # main analytics notebook
│   └── 09_replication_quality_analysis.ipynb  # replication-quality analysis
│
├── results/
│   ├── grid_search/              # grid-search results for all markets
│   ├── grid_search_eu/           # same results in EU-compatible format
│   └── parameter_analysis/       # analytics built on grid_search_results.csv
│
├── tests/                        # pytest test suite
└── pyproject.toml
```

---

## Strategy Logic

1. For a selected **target asset** such as AAPL, construct a **synthetic replica** using PCA regression on a universe of other assets from the same market.
2. Define the **spread** as the target log-price minus the synthetic replica log-price. The strategy tests whether this spread exhibits mean-reverting behavior.
3. When the spread deviates beyond a threshold measured by a rolling z-score, open a position designed to capture a return toward the mean.
4. Model fitting is performed on **rolling walk-forward windows**, so future data are not used during training.

```
ZIP archive → price panel → asset-universe selection
  → walk-forward PCA: train[fit] / OOS[apply] → spread
  → rolling z-score → hysteresis positions → shift by 1 bar
  → P&L − transaction costs → performance metrics
```

---

## Running the Project

### Installation

```bash
pip install -e ".[dev]"
```

### Smoke Test

```bash
python scripts/01_smoke_test.py
```

Runs the full pipeline on all three markets: U.S. equities with CSCO, crypto with BTC, and an automatically selected Russian-equity target. Results are printed to the console.

### Running the Research Pipeline

All commands for grid search, analysis, and export are documented in [COMMANDS.md](COMMANDS.md).

**Parameter grid:** `rebalance_frequency` × `entry_z` × `exit_z` × 5 target assets = approximately 300 combinations per market.

### Visualizing Results

The main analytics notebook is `notebooks/08_portfolio_growth_report.ipynb`. It reads `results/grid_search/best_by_target.csv`, reruns the pipeline with the selected parameters, and produces:

- portfolio-growth curves with an initial capital of $10,000 for each target in each market;
- summary tables with final capital, total return, Buy & Hold return, Sharpe ratio, maximum drawdown, and hit rate;
- a comparison chart for the strongest target from each market: U.S. equities, Russian equities, and crypto.

The notebook `notebooks/09_replication_quality_analysis.ipynb` provides deeper analysis of replication quality and spread stationarity:

- **Z-Score Heatmaps** — Sharpe-ratio heatmaps over the `entry_z × exit_z` space, both market-level and target-level;
- **Replication Quality** — R², Pearson correlation, tracking error, PCA explained variance, and rolling return correlation using a 63-day window;
- **Spread Half-Life** — mean-reversion speed estimated with an Ornstein–Uhlenbeck-style regression, together with an ADF stationarity test;
- **Summary Dashboard** — a Sharpe vs. Half-Life vs. R² scatter plot across all targets and markets.

### Tests

```bash
pytest tests/ -v
```

---

## Results

### `results/grid_search/` and `results/grid_search_eu/`

Both directories contain the same logical outputs. The EU version uses `;` as the delimiter and BOM encoding for easier Excel compatibility.

| File | Contents |
|------|----------|
| `grid_search_results.csv` | All successful runs: parameters + metrics, one row per parameter combination |
| `grid_search_failures.csv` | Failed runs with error tracebacks |
| `best_by_market.csv` | Best Sharpe result by market, suspicious-result flags such as `flag_few_trades` and `flag_large_drawdown`, plus aggregate metrics |
| `best_by_target.csv` | Best Sharpe result for each `(market, target)` pair |
| `summary_by_market.csv` | Market-level aggregates: `median_sharpe`, `best_sharpe`, `positive_sharpe_share` |
| `summary_by_target.csv` | Aggregates for each `(market, target)` pair |
| `top_robust_params.csv` | Parameters most frequently appearing in the top Sharpe decile: `top_decile_appearances`, `appearance_rate` |

Metrics computed for each run include `total_return`, `annualized_return`, `annualized_volatility`, `sharpe_ratio`, `max_drawdown`, `turnover`, `number_of_trades`, `average_holding_period`, and `hit_rate`.

### `results/parameter_analysis/`

Secondary analytics built on top of `grid_search_results.csv` to identify parameter choices that are more stable across targets and markets.

| File | Contents |
|------|----------|
| `median_performance_by_entry_z.csv` / `_exit_z` / `_rebalance` | Median performance metrics by individual parameter |
| `median_performance_by_entry_exit_pair.csv` | Median metrics by `entry_z\|exit_z` pair |
| `median_performance_by_full_param_combo.csv` | Median metrics by `rebalance\|entry_z\|exit_z` combination |
| `top10_parameter_frequencies_global.csv` | Parameter frequency among the top 10% of Sharpe results globally |
| `top10_parameter_frequencies_by_market.csv` | Same analysis by market |
| `top10_parameter_frequencies_by_target.csv` | Same analysis by target |
| `parameter_frequencies_all_top_groups_*.csv` | Frequencies for top 5/10/20% groups globally, by market, and by target |
| `robust_parameter_combos.csv` | Combinations that perform well across multiple targets and markets |
| `suspicious_top_results.csv` | High-ranked results flagged for issues such as high turnover or deep drawdown |
| `parameter_analysis_report.md` | Written report summarizing the parameter analysis |
