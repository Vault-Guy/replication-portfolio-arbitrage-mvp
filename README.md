# Статистический арбитраж на основе PCA-репликации

Исследовательский проект: PCA-репликация синтетического индекса и торговля спредом на рынках акций США, криптовалют и российских акций.

---

## Структура проекта

```
replication-portfolio-arbitrage-mvp/
│
├── configs/
│   ├── usa.yaml          # параметры рынка USA (данные + стратегия)
│   ├── crypto.yaml       # параметры рынка Crypto
│   └── russia.yaml       # параметры рынка Russia
│
├── data/
│   ├── usa_data.zip      # дневные adj. close 142 акций США, 2016–2026
│   ├── crypto_data.zip   # почасовые OHLCV 40+ криптовалют, 2020–2026
│   └── russia_data.zip   # дневные цены ~20 акций РФ (TradingView)
│
├── scripts/
│   ├── 01_smoke_test.py          # быстрая проверка пайплайна на всех рынках
│   ├── 02_grid_search.py         # перебор параметров (основной инструмент)
│   ├── 03_analyze_grid_search.py # постобработка результатов гридсёрча
│   └── 04_export_results_eu.py   # конвертация CSV в EU-формат для Excel
│
├── src/sarb/                     # основной пакет (pip install -e ".[dev]")
│   ├── run.py                    # единый оркестратор run_unified_pipeline()
│   ├── reporting.py              # визуализация и сводные таблицы
│   ├── core/
│   │   ├── config.py             # загрузка YAML-конфигов → MarketConfig
│   │   └── universe.py           # выбор вселенной активов (приоритет + fallback)
│   ├── data/
│   │   ├── base.py               # парсинг zip/CSV, сборка панели, валидация
│   │   └── loader.py             # универсальный загрузчик через MarketConfig
│   ├── pca/
│   │   ├── model.py              # fit/apply PCA-репликации (StandardScaler + PCA + OLS/Ridge)
│   │   └── pipeline.py           # walk-forward цикл по rebalance-окнам
│   ├── strategy/
│   │   ├── spread.py             # вычисление спреда и каузального rolling z-score
│   │   ├── signals.py            # генерация позиций с гистерезисом
│   │   ├── backtest.py           # P&L, транзакционные издержки, equity curve
│   │   └── metrics.py            # Sharpe, MDD, hit rate, оборачиваемость и др.
│   └── utils/
│       ├── io.py                 # сохранение CSV-таблиц
│       ├── time.py               # фактор аннуализации по частоте баров
│       └── eu_export.py          # конвертация в EU-формат (BOM, ;, запятая)
│
├── notebooks/                    # Jupyter-ноутбуки для интерактивного анализа
│   ├── 01_inspect_data.ipynb
│   ├── 02_canonical_load.ipynb
│   ├── 03_walk_forward_signals.ipynb
│   ├── 04_run_usa_pipeline.ipynb
│   ├── 05_run_crypto_pipeline.ipynb
│   ├── 06_run_russia_pipeline.ipynb
│   └── 07_compare_markets.ipynb
│
├── results/
│   ├── grid_search/              # результаты гридсёрча по всем рынкам
│   ├── grid_search_eu/           # то же в EU-формате (для Excel)
│   ├── crypto_parameter_grid/    # расширенный грид только по крипте
│   └── parameter_analysis/       # аналитика поверх grid_search_results.csv
│
├── tests/                        # тесты (pytest)
└── pyproject.toml
```

---

## Логика стратегии

1. Для выбранного **целевого актива** (например, AAPL) строится **синтетический аналог** через PCA-регрессию на вселенной из других активов того же рынка.
2. **Спред** = лог-цена цели − лог-цена синтетика. Предполагается стационарным (mean-reverting).
3. При отклонении спреда выше порога (rolling z-score) открывается позиция на возврат к среднему.
4. Обучение — по **скользящему окну** (walk-forward), без использования будущих данных.

```
ZIP-архив → панель цен → выбор вселенной
  → walk-forward PCA: train[fit] / OOS[apply] → спред
  → rolling z-score → позиции с гистерезисом → shift 1 бар
  → P&L − транзакционные издержки → метрики
```

---

## Запуск

### Установка

```bash
pip install -e ".[dev]"
```

### Smoke test (быстрая проверка)

```bash
python scripts/01_smoke_test.py
```

Запускает полный пайплайн на трёх рынках (USA: CSCO, Crypto: BTC, Russia: авто), результат только в консоли.

### Гридсёрч

```bash
python scripts/02_grid_search.py --dry-run          # просмотр плана
python scripts/02_grid_search.py --market usa        # только USA
python scripts/02_grid_search.py --market all        # все рынки
python scripts/02_grid_search.py --market crypto --max-runs 5  # тест
```

**Параметры перебора:** `rebalance_frequency` × `entry_z` × `exit_z` × 5 целевых активов = ~300 комбинаций на рынок.

### Анализ и экспорт

```bash
python scripts/03_analyze_grid_search.py   # сводные таблицы и топ-параметры
python scripts/04_export_results_eu.py     # EU-формат для Excel
```

### Тесты

```bash
pytest tests/ -v
```

---

## Результаты

### `results/grid_search/` и `results/grid_search_eu/`

Идентичная структура; EU-версия использует разделитель `;` и BOM для совместимости с Excel.

| Файл | Содержимое |
|------|-----------|
| `grid_search_results.csv` | Все успешные прогоны: параметры + метрики (1 строка = 1 комбинация) |
| `grid_search_failures.csv` | Упавшие прогоны с трассировкой ошибки |
| `best_by_market.csv` | Лучший Sharpe по каждому рынку + флаги подозрительных результатов (`flag_few_trades`, `flag_large_drawdown`) + агрегаты (`median_sharpe`, `positive_sharpe_share`) |
| `best_by_target.csv` | Лучший Sharpe по каждой паре `(market, target)` |
| `summary_by_market.csv` | Агрегаты по рынку: `median_sharpe`, `best_sharpe`, `positive_sharpe_share` |
| `summary_by_target.csv` | Агрегаты по паре `(market, target)` |
| `top_robust_params.csv` | Параметры, чаще всего попадающие в топ-дециль по Sharpe: `top_decile_appearances`, `appearance_rate` |

Метрики на каждый прогон: `total_return`, `annualized_return`, `annualized_volatility`, `sharpe_ratio`, `max_drawdown`, `turnover`, `number_of_trades`, `average_holding_period`, `hit_rate`.

### `results/crypto_parameter_grid/`

Расширенный грид только по криптовалютам с дополнительными параметрами: `stop_loss_z`, `max_holding_period`, `regression_type` (OLS/Ridge), `ridge_alpha`, `min_asset_coverage`. Каждый прогон имеет `fingerprint` (JSON-хэш параметров) и `stage` (`core`/другие).

| Файл | Содержимое |
|------|-----------|
| `crypto_parameter_grid_results.csv` | Полные сырые результаты |
| `core_results.csv` | Только прогоны со `stage=core` |
| `partial_results.csv` | Промежуточный чекпоинт долгого прогона |

### `results/parameter_analysis/`

Вторичная аналитика поверх `grid_search_results.csv` для выбора устойчивых параметров.

| Файл | Содержимое |
|------|-----------|
| `median_performance_by_entry_z.csv` / `_exit_z` / `_rebalance` | Медианные метрики по одному параметру |
| `median_performance_by_entry_exit_pair.csv` | Медианные метрики по паре `entry_z\|exit_z` |
| `median_performance_by_full_param_combo.csv` | Медианные метрики по тройке `rebalance\|entry_z\|exit_z` |
| `top10_parameter_frequencies_*.csv` | Частота каждого значения параметра среди top-10% по Sharpe (глобально / по рынкам / по таргетам) |
| `robust_parameter_combos.csv` | Комбинации, хорошо работающие одновременно по нескольким таргетам и рынкам |
| `suspicious_top_results.csv` | Результаты из топа с флагами аномалий (`high_turnover`, `deep_drawdown`) |
