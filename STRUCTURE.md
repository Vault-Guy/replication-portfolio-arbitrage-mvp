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
│   └── inspect_zip.py                # утилита для инспекции ZIP-архивов с данными
│
├── src/sarb/                     # основной пакет (pip install -e ".[dev]")
│   ├── run.py                    # единый оркестратор run_unified_pipeline()
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
│   ├── 08_portfolio_growth_report.ipynb  ← ОСНОВНОЙ НОУТБУК АНАЛИТИКИ (см. ниже)
│   └── 09_replication_quality_analysis.ipynb  ← АНАЛИТИКА КАЧЕСТВА РЕПЛИКАЦИИ (см. ниже)
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