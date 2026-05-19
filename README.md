# Статистический арбитраж на основе PCA-репликации

Исследовательский проект: PCA-репликация синтетического индекса и торговля спредом на рынках акций США, криптовалют и российских акций.

---

## Структура проекта

```
replication-portfolio-arbitrage-mvp/
│
├── COMMANDS.md           # шпаргалка по командам запуска (полный цикл и по шагам)
│
├── configs/
│   ├── usa.yaml          # параметры рынка USA (данные + стратегия)
│   ├── crypto.yaml       # параметры рынка Crypto
│   └── russia.yaml       # параметры рынка Russia
│
├── data/
│   ├── usa_data.zip      # дневные adj. close 142 акций США, 2016–2026
│   ├── crypto_data.zip   # почасовые OHLCV 40+ криптовалют, 2020–2026
│   └── russia_data.zip   # дневные цены ~26 акций РФ (TradingView)
│
├── scripts/
│   ├── 01_smoke_test.py              # быстрая проверка пайплайна на всех рынках
│   ├── 02_grid_search.py             # перебор параметров (основной инструмент)
│   ├── 03_analyze_grid_search.py     # постобработка результатов гридсёрча
│   ├── 04_export_results_eu.py       # конвертация CSV в EU-формат для Excel
│   ├── analyze_parameter_ranges.py   # детальный анализ частот параметров (топ-5/10/20%)
│   ├── crypto_parameter_grid.py      # стейджированный грид для крипто с расш. параметрами
│   ├── analyze_crypto_parameter_grid.py  # анализ результатов crypto_parameter_grid
│   └── inspect_zip.py                # утилита для инспекции ZIP-архивов с данными
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
│   │   ├── HOW_BACKTEST_WORKS.md # описание логики бэктеста (каузальность, сдвиги, издержки)
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
│   ├── 07_compare_markets.ipynb
│   ├── 08_portfolio_growth_report.ipynb  ← ОСНОВНОЙ НОУТБУК АНАЛИТИКИ (см. ниже)
│   └── 09_replication_quality_analysis.ipynb  ← анализ качества репликации и half-life
│
├── results/
│   ├── grid_search/              # результаты гридсёрча по всем рынкам
│   ├── grid_search_eu/           # то же в EU-формате (для Excel)
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

### Запуск расчётов

Все команды для запуска гридсёрча, анализа и экспорта — в [COMMANDS.md](COMMANDS.md).

**Параметры перебора:** `rebalance_frequency` × `entry_z` × `exit_z` × 5 целевых активов = ~300 комбинаций на рынок.

### Визуализация результатов

Основной ноутбук для построения аналитики — `notebooks/08_portfolio_growth_report.ipynb`. Читает `results/grid_search/best_by_target.csv`, перезапускает пайплайн с лучшими параметрами и строит:
- кривые роста портфеля (стартовый капитал $10 000) по каждому таргету на каждом рынке;
- сводные таблицы метрик: финальный капитал, общий прирост, Buy & Hold, Sharpe, MDD, % прибыльных сделок;
- сравнительный график лучшего таргета с каждого рынка (США / Россия / Крипто).

Ноутбук `notebooks/09_replication_quality_analysis.ipynb` — углублённый анализ качества репликации и стационарности спреда:
- **Z-Score Heatmaps** — тепловые карты коэффициента Шарпа в пространстве `entry_z × exit_z` (агрегированные по рынку и отдельные по таргетам);
- **Качество репликации** — R², корреляция Пирсона, Tracking Error, PCA Explained Variance и скользящая корреляция доходностей (окно 63 дня);
- **Half-Life спреда** — скорость возврата к среднему по модели Орнштейна-Уленбека (ОУ-регрессия) + ADF-тест стационарности;
- **Сводный дашборд** — scatter-plot «Sharpe vs Half-Life vs R²» по всем таргетам и рынкам одновременно.

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

### `results/parameter_analysis/`

Вторичная аналитика поверх `grid_search_results.csv` для выбора устойчивых параметров.

| Файл | Содержимое |
|------|-----------|
| `median_performance_by_entry_z.csv` / `_exit_z` / `_rebalance` | Медианные метрики по одному параметру |
| `median_performance_by_entry_exit_pair.csv` | Медианные метрики по паре `entry_z\|exit_z` |
| `median_performance_by_full_param_combo.csv` | Медианные метрики по тройке `rebalance\|entry_z\|exit_z` |
| `top10_parameter_frequencies_global.csv` | Частота параметров среди top-10% по Sharpe (глобально) |
| `top10_parameter_frequencies_by_market.csv` | То же, разбивка по рынкам |
| `top10_parameter_frequencies_by_target.csv` | То же, разбивка по таргетам |
| `parameter_frequencies_all_top_groups_*.csv` | Частоты для топ-5/10/20% (глобально / по рынкам / по таргетам) |
| `robust_parameter_combos.csv` | Комбинации, хорошо работающие по нескольким таргетам и рынкам одновременно |
| `suspicious_top_results.csv` | Результаты из топа с флагами аномалий (`high_turnover`, `deep_drawdown`) |
| `parameter_analysis_report.md` | Текстовый отчёт с выводами по анализу параметров |
