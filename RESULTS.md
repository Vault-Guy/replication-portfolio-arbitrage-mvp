## Структура `results/`

```
results/
├── grid_search/              # Грид-поиск по рынкам USA + Crypto + Russia
├── grid_search_eu/           # То же самое, но для европейских рынков
├── crypto_parameter_grid/    # Расширенный грид только по крипте (новые параметры: stop_loss, max_holding_period, regression_type и др.)
└── parameter_analysis/       # Аналитика поверх результатов grid_search
```

---

### `grid_search/` и `grid_search_eu/` — идентичная структура

| Файл | Что хранится |
|---|---|
| `grid_search_results.csv` | Сырые результаты каждого прогона (1 строка = 1 комбинация параметров × target). Метрики: `total_return`, `sharpe_ratio`, `max_drawdown`, `turnover`, `hit_rate` и др. |
| `best_by_market.csv` | Лучшая конфигурация по каждому рынку (выбрана по Sharpe). Добавлены флаги подозрительных результатов (`flag_few_trades`, `flag_large_drawdown` и др.) + агрегаты по всем прогонам (`median_sharpe`, `positive_sharpe_share`) |
| `best_by_target.csv` | Лучшая конфигурация по каждому `(market, target)`. Аналогично `best_by_market`, но более детально — по конкретным тикерам |
| `summary_by_market.csv` | Агрегированная статистика по рынку: `median_sharpe`, `best_sharpe`, `best_total_return`, `positive_sharpe_share` по всем конфигурациям для каждого target |
| `summary_by_target.csv` | Агрегаты по каждому `(market, target)` — схоже с `summary_by_market`, но с `runs` и `target_count` |
| `top_robust_params.csv` | Параметры (`rebalance_frequency`, `entry_z`, `exit_z`), которые чаще всего попадают в топ-дециль по Sharpe: `top_decile_appearances`, `appearance_rate` |
| `grid_search_failures.csv` | Комбинации, завершившиеся ошибкой: содержит параметры + `error` |

---

### `crypto_parameter_grid/` — расширенный грид для крипты

Схема значительно богаче: добавлены `fingerprint` (JSON-хэш всех параметров), `stage` (`core`/другие), `stop_loss_z`, `max_holding_period`, `regression_type` (`OLS`/Ridge), `ridge_alpha`, `min_asset_coverage`, `valid_rebalance_share`.

| Файл | Что хранится |
|---|---|
| `crypto_parameter_grid_results.csv` | Полные сырые результаты расширенного грида |
| `core_results.csv` | Только прогоны со `stage=core` |
| `partial_results.csv` | Промежуточные/частичные результаты (вероятно, чекпоинт во время долгого прогона) |

---

### `parameter_analysis/` — аналитика поверх `grid_search_results.csv`

| Файл | Что хранится |
|---|---|
| `median_performance_by_entry_z.csv` | Медианные метрики (`sharpe`, `total_return`, `drawdown`, `turnover`) сгруппированные по `entry_z` |
| `median_performance_by_exit_z.csv` | То же по `exit_z` |
| `median_performance_by_rebalance.csv` | То же по `rebalance_frequency` |
| `median_performance_by_entry_exit_pair.csv` | То же по паре `entry_z\|exit_z` |
| `median_performance_by_full_param_combo.csv` | То же по тройке `rebalance\|entry_z\|exit_z` |
| `top10_parameter_frequencies_global.csv` | Частота каждого значения параметра среди top-10% по Sharpe — глобально |
| `top10_parameter_frequencies_by_market.csv` | То же, но разбито по рынкам |
| `top10_parameter_frequencies_by_target.csv` | То же, но разбито по таргетам |
| `parameter_frequencies_all_top_groups_global.csv` | Расширенная версия: частоты для нескольких групп (top5, top10 и др.) одновременно |
| `parameter_frequencies_all_top_groups_by_market.csv` / `_by_target.csv` | То же, разбито по рынкам / таргетам |
| `robust_parameter_combos.csv` | Комбинации, которые одновременно хорошо работают по нескольким таргетам/рынкам (по рангам) |
| `suspicious_top_results.csv` | Результаты из топа, которые подозрительны: `high_turnover`, `deep_drawdown` и подобные флаги |
| `parameter_analysis_report.md` | Текстовый отчёт с описанием источника данных и ссылками на файлы |

---

**Итого:** `results/` — это выходная директория двух пайплайнов (грид-поиск и анализ параметров). `grid_search*` хранят сырые и агрегированные метрики по рынкам. `crypto_parameter_grid` — расширенный эксперимент с более богатыми параметрами. `parameter_analysis` — вторичная аналитика для выбора устойчивых параметров.
