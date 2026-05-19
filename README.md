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
│   └── grid_search/              # результаты гридсёрча (CSV)
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

## Результаты гридсёрча

| Файл | Содержимое |
|------|-----------|
| `results/grid_search/grid_search_results.csv` | Все успешные прогоны: параметры + метрики |
| `results/grid_search/grid_search_failures.csv` | Упавшие прогоны с трассировкой |
| `results/grid_search/best_by_market.csv` | Лучший Sharpe по каждому рынку |
| `results/grid_search/best_by_target.csv` | Лучший Sharpe по паре (рынок, цель) |
| `results/grid_search_eu/*.csv` | Те же файлы в EU-формате (`;`, BOM) |

Метрики на каждый прогон: `total_return`, `annualized_return`, `annualized_volatility`, `sharpe_ratio`, `max_drawdown`, `turnover`, `number_of_trades`, `average_holding_period`, `hit_rate`.

---

## Известные ограничения

- **Survivorship bias (USA):** вселенная содержит тикеры топ-100 по состоянию на 2026 год — результаты по USA завышены.
- **Sharpe без безрисковой ставки:** `sharpe = annualized_return / annualized_volatility`, ставка не вычитается.
- **Нет holdout-выборки:** оптимальные параметры выбираются по тем же данным, на которых обучается модель.
- **Стационарность спреда не проверяется:** тест ADF/KPSS не реализован.
