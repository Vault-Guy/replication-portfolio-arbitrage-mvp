# Pipeline: цепочка работы SARB

## Точка входа

`scripts/smoke_test.py` или ноутбуки. Оркестрирующая функция — `run_market_smoke(market, target, universe_size)`, которая последовательно вызывает все шаги ниже.

---

## 1. Загрузка конфига — `sarb/config.py` + `configs/{market}.yaml`

```
load_run_config("usa")
  → читает configs/usa.yaml
  → возвращает RunConfig (train_window, entry_z, exit_z, transaction_cost_bps, ...)
```

---

## 2. Загрузка данных — `sarb/data/{market}_loader.py`

```
load_market_prices("usa")
  → динамически импортирует sarb.data.usa_loader
  → читает сырой архив (ZIP/CSV)
  → возвращает pd.DataFrame [дата × тикер] с ценами
```

---

## 3. Выбор target + universe

- **target** — актив, который хотим реплицировать (например, `CSCO`)
- **universe** — N лучших по покрытию активов (без target), используются для построения синтетика

---

## 4. PCA Replication Pipeline — `sarb/pipeline.py` + `sarb/pca_replication.py`

Ядро системы. Работает **скользящим окном**:

```
for каждое rebalance окно:
    train = log_prices[ t - train_window : t ]        # исторические данные
    oos   = log_prices[ t : t + rebalance_frequency ] # будущие данные (OOS)

    fit_pca_synthetic_etf(train):
        1. Фильтрация universe по покрытию (min_asset_coverage)
        2. StandardScaler → нормализация
        3. PCA → выбор N компонент (по порогу объяснённой дисперсии)
        4. OLS/Ridge регрессия: target ≈ intercept + PC_scores @ coef

    apply_pca_synthetic_etf(oos, model):
        → synthetic_log_price[t] = intercept + PC_scores[t] @ coef

    spread[t] = target_log_price[t] - synthetic_log_price[t]
```

Результат: полный out-of-sample ряд `spread` + метаданные по каждому окну.

---

## 5. Z-score — `sarb/spread.py`

```
zscore[t] = (spread[t] - mean(spread[t-lookback:t-1]))
             / std(spread[t-lookback:t-1])
```

Полностью каузальный: использует только прошлые данные.

---

## 6. Генерация позиций — `sarb/signals.py`

Mean-reversion логика с гистерезисом:

```
если zscore > +entry_z  → SHORT spread (position = -1)  # спред аномально высок
если zscore < -entry_z  → LONG  spread (position = +1)  # спред аномально низок
если |zscore| < exit_z  → FLAT         (position =  0)  # возврат к среднему
```

Опциональные риск-стопы: `max_holding_period` (time stop), `stop_loss_z`.

Позиции сдвигаются на 1 бар (`shift_bars=1`) — исполнение следующим баром.

---

## 7. Бэктест — `sarb/backtest.py`

```
P&L[t] = execution_position[t] × (spread[t] - spread[t-1])
          - |Δposition[t]| × transaction_cost_bps / 10_000
```

Затем: кривая капитала, метрики (Sharpe, Sortino, макс. просадка, CAGR).

---

## 8. Результат — `sarb/run.py`

`UnifiedPipelineResult` — единая структура со всеми компонентами: цены, покрытие, репликация, бэктест, метрики, caveats (предупреждения о selection bias).

---

## Схема потока данных

```
configs/*.yaml
      |
      v
  RunConfig
      |
      v
data/{market}_loader --> prices DataFrame
      |
      v
 to_log_prices()
      |
      v
PCA Replication (скользящее окно)
  train --> fit (PCA + regression)
  oos   --> apply --> synthetic_log_price
      |
      v
spread = target - synthetic
      |
      v
rolling_zscore()
      |
      v
generate_positions() --> shift 1 бар
      |
      v
P&L + transaction costs
      |
      v
equity_curve + PerformanceMetrics
      |
      v
UnifiedPipelineResult
```
