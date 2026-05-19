# Команды для запуска расчётов

## Полный цикл (с нуля)

```bash
rm -rf results/grid_search/* results/grid_search_eu/* results/parameter_analysis/* results/crypto_parameter_grid/*
```

```bash
python scripts/02_grid_search.py --market all
```

```bash
python scripts/analyze_parameter_ranges.py
```

```bash
python scripts/03_analyze_grid_search.py
```

```bash
python scripts/04_export_results_eu.py
```

---

## Запуск по одному рынку

```bash
python scripts/02_grid_search.py --market usa
```

```bash
python scripts/02_grid_search.py --market crypto
```

```bash
python scripts/02_grid_search.py --market russia
```

---

## Быстрая проверка

```bash
python scripts/02_grid_search.py --market all --max-runs 10
```

```bash
python scripts/02_grid_search.py --market all --dry-run
```

---

## Только анализ (если grid search уже запущен)

```bash
python scripts/03_analyze_grid_search.py
```

```bash
python scripts/analyze_parameter_ranges.py
```

```bash
python scripts/04_export_results_eu.py
```

---

## Где результаты

| Папка | Что внутри |
|-------|-----------|
| `results/grid_search/` | Основные CSV: все прогоны, лучшие параметры, сводки |
| `results/grid_search_eu/` | Те же файлы с запятой как десятичным разделителем |
| `results/parameter_analysis/` | Частоты параметров, robust-комбинации, Markdown-отчёт |
| `results/BASELINE_SNAPSHOT.md` | Снапшот результатов до рефакторинга для сравнения |

Описание всех столбцов в CSV: `results/grid_search/README.md`
