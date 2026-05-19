# Parameter range analysis (grid search)

- Source: `results/grid_search/grid_search_results.csv` (2269 rows).
- Outputs: `results/parameter_analysis/`.

## Rebalance frequency (median Sharpe, full sample)

| rebalance_frequency | median_sharpe_ratio |
| --- | --- |
| 24.0 | 0.9130074514563914 |
| 72.0 | 0.7651429223121522 |
| 5.0 | 0.6394614973785213 |
| 10.0 | 0.5545145015713261 |
| 168.0 | 0.524616081883593 |
| 21.0 | 0.5231266003397984 |
| 63.0 | 0.2489703869517155 |
| 336.0 | 0.2286515574837613 |

## Entry z (median Sharpe, full sample)

| entry_z | median_sharpe_ratio |
| --- | --- |
| 2.0 | 0.544668346081463 |
| 1.5 | 0.5378726477674951 |
| 2.5 | 0.5245013090830559 |
| 1.0 | 0.5183845396606489 |
| 3.0 | 0.48572360769999834 |

## Exit z (median Sharpe, full sample)

| exit_z | median_sharpe_ratio |
| --- | --- |
| 0.25 | 0.5932708478135782 |
| 0.5 | 0.5739564571024454 |
| 0.75 | 0.4926977460916099 |
| 1.0 | 0.3838645384974084 |

## Top 10% Sharpe — global parameter frequencies

See `top10_parameter_frequencies_global.csv` for full tables. Rebalance / entry / exit / pair / triple frequencies describe which settings dominate the best decile.

**Rebalance (top 10% Sharpe, global):** 24.0 (33.9%), 72.0 (24.2%), 168.0 (13.7%), 5.0 (12.3%), 10.0 (7.9%), 336.0 (5.3%), 21.0 (2.6%)


### Concentration (top 10% Sharpe slice)

- Largest single-market share of rows in this slice: **77.1%** (crypto).
- Largest single-target share: **28.2%** (ATOM).

## Robust combinations (triple)

File `robust_parameter_combos.csv` ranks `rebalance|entry|exit` by median Sharpe and counts how often each combo appears in the top 10% Sharpe slice across distinct targets and markets.

| rebalance_entry_exit | n_rows_total | n_distinct_targets_top10_sharpe | n_distinct_markets_top10_sharpe | n_distinct_market_target_pairs_top10_sharpe | mean_rank_sharpe | median_rank_sharpe | mean_rank_total_return | median_max_drawdown | median_turnover | median_sharpe_ratio | median_total_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24\|2.5\|0.25 | 10 | 7 | 1 | 7 | 373.8 | 99.5 | 424.0 | -0.4980945373353457 | 0.0053293436595478 | 1.2919627937899287 | 13.990264751835628 |
| 24\|3.0\|0.25 | 10 | 6 | 1 | 6 | 377.3 | 112.5 | 479.6 | -0.47597614455500725 | 0.0037060940311350503 | 1.258357392665813 | 10.363022986382356 |
| 24\|3.0\|0.5 | 10 | 6 | 1 | 6 | 455.2 | 125.5 | 552.5 | -0.47726676709980953 | 0.0038576356491850502 | 1.2206832296977552 | 5.995591043981518 |
| 24\|2.5\|0.5 | 10 | 6 | 1 | 6 | 397.6 | 156.0 | 461.1 | -0.48192708404509566 | 0.0056618164750058 | 1.1353580304246595 | 10.269076291489892 |
| 24\|2.0\|0.25 | 10 | 5 | 1 | 5 | 394.0 | 192.5 | 419.0 | -0.5334303228093038 | 0.00744152389892825 | 1.089868575553241 | 14.905212196870053 |
| 24\|2.0\|0.5 | 10 | 5 | 1 | 5 | 469.0 | 234.0 | 491.7 | -0.516790754076283 | 0.0080869123054056 | 1.0346711853630386 | 13.420655446359163 |
| 24\|2.5\|0.75 | 10 | 5 | 1 | 5 | 530.3 | 254.5 | 591.2 | -0.46785966264689627 | 0.00597260283143565 | 1.013923754732546 | 5.5242958891193945 |
| 24\|3.0\|0.75 | 10 | 5 | 1 | 5 | 595.6 | 256.0 | 742.6 | -0.443758284447449 | 0.00393586454693985 | 1.0095956469368979 | 4.325964046370989 |
| 72\|2.5\|0.25 | 10 | 5 | 1 | 5 | 566.0 | 272.0 | 485.9 | -0.5332666501692679 | 0.0050653211296252006 | 0.9880413656069058 | 7.922427246089788 |
| 72\|3.0\|0.25 | 10 | 5 | 1 | 5 | 518.2 | 295.5 | 561.9 | -0.5033122181661904 | 0.0034566920251674 | 0.9780372115113557 | 8.45827704820244 |
| 24\|1.5\|0.25 | 10 | 4 | 1 | 4 | 462.8 | 276.0 | 427.4 | -0.5520625128244436 | 0.010639130094656949 | 0.97741076473822 | 19.709538855533175 |
| 72\|2.5\|0.5 | 10 | 4 | 1 | 4 | 610.8 | 314.5 | 556.1 | -0.5120302507714951 | 0.0053195650473284 | 0.9457358119046492 | 6.484735171328366 |
| 72\|2.5\|0.75 | 10 | 3 | 1 | 3 | 652.4 | 367.5 | 632.7 | -0.48399138792171215 | 0.00568137369944455 | 0.9161018199036248 | 5.526072145355537 |
| 24\|3.0\|1.0 | 10 | 5 | 1 | 5 | 721.1 | 423.5 | 906.4 | -0.43232054524856556 | 0.00412313994212125 | 0.9012940626887148 | 2.7500402388094445 |
| 72\|3.0\|0.5 | 10 | 4 | 1 | 4 | 612.0 | 361.5 | 668.3 | -0.47739558305008645 | 0.003539857623406 | 0.896970204739574 | 5.4137260079989415 |
| 24\|1.5\|0.5 | 10 | 3 | 1 | 3 | 593.1 | 369.0 | 525.2 | -0.5676976171504924 | 0.01198857858092775 | 0.8908778727320914 | 16.351578298173813 |
| 72\|3.0\|0.75 | 10 | 4 | 1 | 4 | 678.8 | 436.5 | 775.7 | -0.4465428426787402 | 0.0036113334633117496 | 0.8668967836605306 | 4.177238610018858 |
| 24\|2.0\|0.75 | 10 | 3 | 1 | 3 | 646.3 | 438.5 | 620.6 | -0.5383038769696289 | 0.008917922879246 | 0.8525102890864584 | 8.828352726077018 |
| 24\|1.0\|0.5 | 10 | 3 | 1 | 3 | 708.1 | 511.0 | 547.1 | -0.6098119387549521 | 0.01965501056090115 | 0.8085724197247177 | 10.422601822936219 |
| 72\|1.5\|0.25 | 10 | 4 | 1 | 4 | 713.7 | 566.5 | 501.3 | -0.5810236294597759 | 0.01030665727919885 | 0.8070779959879903 | 14.925948405197332 |

## Stability across markets

| market | median | mean | std |
| --- | --- | --- | --- |
| crypto | 0.6177622458328085 | 0.6423145982687709 | 0.5510508329278068 |
| russia | 0.5091676500506301 | 0.5099338676699877 | 0.27784482278751643 |
| usa | 0.4757494717246916 | 0.48970025806578943 | 0.2938057281343016 |

## Stability across targets (Sharpe dispersion)

Higher `std` means more target-specific luck; lower spread suggests more homogeneous parameter luck.

| target | median | mean | std |
| --- | --- | --- | --- |
| AVAX | 0.8302449378508941 | 0.8282167215190561 | 0.46601173799971796 |
| LINK | 0.8993975494503137 | 0.818265812532266 | 0.45047633227854966 |
| ATOM | 1.4887377245854487 | 1.4525557120891082 | 0.4438756812377111 |
| ETH | 0.4815145124412811 | 0.566014045309936 | 0.4181478150826108 |
| BNB | 0.6191702252697016 | 0.6260617554317418 | 0.3696560863585781 |
| ADA | 0.8844727827430979 | 0.9458510093238577 | 0.36586470329434356 |
| SOL | 0.3525800271642756 | 0.33211146707865563 | 0.3616759900343672 |
| JPM | 0.842135991661684 | 0.7942957673341495 | 0.3482423733106961 |
| XRP | 0.43524912443695124 | 0.42232233595489493 | 0.34215264968567566 |
| BTC | 0.49003956128767723 | 0.5013428389948297 | 0.32695324713032614 |
| AFKS | 0.6567615884863607 | 0.6869821541479441 | 0.3020477773136984 |
| NVDA | 0.7214447011604503 | 0.6439910743868359 | 0.29878531230824407 |
| LKOH | 0.5500719289561833 | 0.4529101931390336 | 0.29092739906246123 |
| CHMF | 0.4825619748600407 | 0.4814946820358833 | 0.2665123005016144 |
| BRK.B | 0.532288640990457 | 0.5259328005267102 | 0.2628020419289428 |

## Top-decile Sharpe — trade and drawdown context

- Median `number_of_trades` in top 10% Sharpe rows: **272.0**.
- Median `max_drawdown` in top 10% Sharpe rows: **-0.434**.

## Suspicious flags (within top 10% Sharpe)

- Turnover 95th percentile (full sample): **0.077665**.
- Best Sharpe row: market **crypto**, target **ATOM**.

| market | target | universe_selection_method | universe_size_requested | universe_size_actual | universe_assets | missing_priority_assets | filled_from_fallback | train_window | rebalance_frequency | pca_explained_variance | zscore_lookback | entry_z | exit_z | transaction_cost_bps | annualization_factor | total_return | annualized_return | annualized_volatility | sharpe_ratio | max_drawdown | turnover | number_of_trades | average_holding_period | hit_rate | flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| usa | JPM | priority | 30 | 30 | NVDA,AAPL,MSFT,AVGO,ORCL,AMD,CSCO,QCOM,TXN,IBM,ACN,ADI,GOOGL,META,NFLX,DIS,VZ,AMZN,TSLA,HD,MCD,LOW,WMT,COST,PG,KO,PEP,PM,BRK-B,V | TMUS,CMCSA,BKNG,SBUX | nan | 252 | 5 | 0.8 | 60 | 1.0 | 0.5 | 5.0 | 252.0 | 6.433575308574832 | 0.2505453311380761 | 0.1911208497529323 | 1.3109262095787222 | -0.2158064259867593 | 0.0888987173816895 | 196 | 11.92079207920792 | 0.5431893687707641 | high_turnover_p95 |
| usa | JPM | priority | 30 | 30 | NVDA,AAPL,MSFT,AVGO,ORCL,AMD,CSCO,QCOM,TXN,IBM,ACN,ADI,GOOGL,META,NFLX,DIS,VZ,AMZN,TSLA,HD,MCD,LOW,WMT,COST,PG,KO,PEP,PM,BRK-B,V | TMUS,CMCSA,BKNG,SBUX | nan | 252 | 5 | 0.8 | 60 | 1.0 | 0.75 | 5.0 | 252.0 | 3.943445326933621 | 0.1949594259570204 | 0.1814792668192837 | 1.074279334350409 | -0.1923330350340146 | 0.1021671826625387 | 228 | 9.28448275862069 | 0.5348189415041783 | high_turnover_p95 |
| usa | JPM | priority | 30 | 30 | NVDA,AAPL,MSFT,AVGO,ORCL,AMD,CSCO,QCOM,TXN,IBM,ACN,ADI,GOOGL,META,NFLX,DIS,VZ,AMZN,TSLA,HD,MCD,LOW,WMT,COST,PG,KO,PEP,PM,BRK-B,V | TMUS,CMCSA,BKNG,SBUX | nan | 252 | 10 | 0.8 | 60 | 1.0 | 0.5 | 5.0 | 252.0 | 4.976284840809249 | 0.2204984533465843 | 0.2034179327818027 | 1.08396762434462 | -0.2143237818748139 | 0.0818222025652366 | 180 | 12.96774193548387 | 0.5248756218905473 | high_turnover_p95 |
| usa | JPM | priority | 30 | 30 | NVDA,AAPL,MSFT,AVGO,ORCL,AMD,CSCO,QCOM,TXN,IBM,ACN,ADI,GOOGL,META,NFLX,DIS,VZ,AMZN,TSLA,HD,MCD,LOW,WMT,COST,PG,KO,PEP,PM,BRK-B,V | TMUS,CMCSA,BKNG,SBUX | nan | 252 | 10 | 0.8 | 60 | 1.0 | 0.75 | 5.0 | 252.0 | 4.7954718233639575 | 0.2163264326866472 | 0.1936321783978815 | 1.1172029074740495 | -0.1946318698692324 | 0.0995134896063688 | 222 | 9.63716814159292 | 0.5234159779614325 | high_turnover_p95 |
| russia | SBER | coverage | 30 | 25 | AFKS,AFLT,ALRS,CHMF,GAZP,GMKN,HYDR,IRAO,LKOH,MAGN,MGNT,MOEX,MTSS,NLMK,NVTK,PHOR,PLZL,RASP,ROSN,RTKM,SNGS,TATN,TRNFP,VTBR,YDEX | nan | nan | 252 | 21 | 0.8 | 60 | 1.0 | 0.5 | 10.0 | 252.0 | 12.516894202137182 | 0.2744255797056827 | 0.2546291998823565 | 1.077745913793361 | -0.2799524448361824 | 0.081670362158167 | 209 | 14.891891891891891 | 0.5009074410163339 | high_turnover_p95 |

## Plain-language takeaways

1. **Rebalance:** higher median Sharpe at certain horizons (see table) suggests those horizons align better with this PCA + z-score setup on average; verify per market in `median_performance_by_rebalance.csv`.
2. **Entry z:** tighter entries (higher `entry_z`) often reduce trade count but can improve Sharpe when spreads mean-revert cleanly; the median-Sharpe-by-entry table shows which entries are favored on average.
3. **Exit z:** larger exit bands (higher `exit_z`) can clip winners or reduce turnover; the exit-z table summarizes average ranking.
4. **Robust combos:** combinations that appear in many targets' top-10% Sharpe sets are less likely to be one-off target luck; see `robust_parameter_combos.csv` columns `n_distinct_targets_top10_sharpe` and `n_distinct_markets_top10_sharpe`.
5. **Cross-market:** if market medians diverge strongly, the same parameters behave differently by calendar and microstructure.
6. **Cross-target:** wide `std` in per-target Sharpe means parameter quality is not portable blindly across names.
7. **Trades / drawdowns:** if top-decile rows often have very few trades or very deep drawdowns, headline Sharpe may be fragile.

## Caveat

**Grid search is in-sample on this dataset.** It does **not** prove out-of-sample profitability or future performance.
