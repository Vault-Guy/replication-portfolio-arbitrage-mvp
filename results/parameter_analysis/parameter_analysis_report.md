# Parameter range analysis (grid search)

- Source: `results/grid_search/grid_search_results.csv` (1440 rows).
- Outputs: `results/parameter_analysis/`.

## Rebalance frequency (median Sharpe, full sample)

| rebalance_frequency | median_sharpe_ratio |
| --- | --- |
| 24.0 | 0.8433050740780564 |
| 5.0 | 0.6582821878166213 |
| 72.0 | 0.6363866902060803 |
| 10.0 | 0.5731249715150863 |
| 21.0 | 0.5561669744897935 |
| 168.0 | 0.4412895725370082 |
| 63.0 | 0.2566369610359555 |
| 336.0 | 0.16762919770055218 |

## Entry z (median Sharpe, full sample)

| entry_z | median_sharpe_ratio |
| --- | --- |
| 2.0 | 0.5808277532560233 |
| 1.5 | 0.5430435661266133 |
| 2.5 | 0.5272576035462402 |
| 1.0 | 0.4922924926159665 |
| 3.0 | 0.47122525795506826 |

## Exit z (median Sharpe, full sample)

| exit_z | median_sharpe_ratio |
| --- | --- |
| 0.0 | 0.6224598913203312 |
| 0.25 | 0.5750850992194235 |
| 0.5 | 0.5438672923615575 |
| 0.75 | 0.4811218867694861 |
| 1.0 | 0.3706903250354488 |

## Top 10% Sharpe — global parameter frequencies

See `top10_parameter_frequencies_global.csv` for full tables. Rebalance / entry / exit / pair / triple frequencies describe which settings dominate the best decile.

**Rebalance (top 10% Sharpe, global):** 24.0 (31.2%), 5.0 (20.1%), 10.0 (14.6%), 72.0 (14.6%), 21.0 (7.6%), 168.0 (6.9%), 336.0 (2.8%), 63.0 (2.1%)


### Concentration (top 10% Sharpe slice)

- Largest single-market share of rows in this slice: **55.6%** (crypto).
- Largest single-target share: **17.4%** (AFKS).

## Robust combinations (triple)

File `robust_parameter_combos.csv` ranks `rebalance|entry|exit` by median Sharpe and counts how often each combo appears in the top 10% Sharpe slice across distinct targets and markets.

| rebalance_entry_exit | n_rows_total | n_distinct_targets_top10_sharpe | n_distinct_markets_top10_sharpe | n_distinct_market_target_pairs_top10_sharpe | mean_rank_sharpe | median_rank_sharpe | mean_rank_total_return | median_max_drawdown | median_turnover | median_sharpe_ratio | median_total_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24\|3.0\|0.0 | 5 | 3 | 1 | 3 | 320.6 | 24.0 | 137.0 | -0.6324460501127946 | 0.0018579363216772 | 1.39302907699304 | 15.531720064283334 |
| 24\|2.0\|0.0 | 5 | 5 | 1 | 5 | 42.8 | 30.0 | 50.2 | -0.7716813463477967 | 0.0045568332942188 | 1.331827719867584 | 29.81320284426439 |
| 24\|2.5\|0.0 | 5 | 5 | 1 | 5 | 48.8 | 39.0 | 31.4 | -0.7471087368486078 | 0.0030516431924882 | 1.2755864040656957 | 46.04396174506575 |
| 24\|1.5\|0.0 | 5 | 3 | 1 | 3 | 90.4 | 40.0 | 81.8 | -0.6516354720624946 | 0.0059539052496798 | 1.269699028094213 | 41.06810053297187 |
| 24\|3.0\|0.5 | 5 | 3 | 1 | 3 | 234.2 | 51.0 | 376.4 | -0.5086720796002073 | 0.0036376437455996 | 1.210430747484113 | 4.918635165161585 |
| 24\|3.0\|0.25 | 5 | 3 | 1 | 3 | 137.4 | 55.0 | 278.8 | -0.5343073684391175 | 0.0035594148478447 | 1.1976733811912044 | 10.160211602102676 |
| 24\|2.5\|0.25 | 5 | 3 | 1 | 3 | 141.6 | 81.0 | 247.6 | -0.6415951146764847 | 0.0051239928029414 | 1.1013702389697513 | 9.586361849839964 |
| 72\|2.0\|0.0 | 5 | 3 | 1 | 3 | 128.0 | 114.0 | 83.6 | -0.7874910004567408 | 0.0042830321520769 | 1.0091594611447414 | 22.102316810711784 |
| 72\|1.5\|0.0 | 5 | 3 | 1 | 3 | 203.0 | 134.0 | 106.0 | -0.6542564178727992 | 0.0056520378627865 | 0.9739313520586764 | 14.775215067820527 |
| 72\|3.0\|0.0 | 5 | 3 | 1 | 3 | 279.4 | 136.0 | 74.8 | -0.6984848053970318 | 0.0018970507705546 | 0.969777061674121 | 19.223173449273176 |
| 24\|2.0\|0.5 | 5 | 3 | 1 | 3 | 220.6 | 142.0 | 314.8 | -0.544691513250958 | 0.0077055464288508 | 0.9591370816513508 | 11.762764256781333 |
| 168\|2.0\|0.0 | 5 | 1 | 1 | 1 | 287.0 | 159.0 | 97.4 | -0.8469747153575751 | 0.004009231009935 | 0.9249663200187584 | 24.518802315934003 |
| 24\|2.5\|0.5 | 5 | 2 | 1 | 2 | 166.4 | 168.0 | 286.8 | -0.5179927134907796 | 0.0054369083939607 | 0.9169527786126171 | 8.575737772992827 |
| 5\|2.0\|0.0 | 10 | 5 | 2 | 5 | 310.9 | 182.5 | 362.4 | -0.2983604034371829 | 0.0243255196815568 | 0.9119706289469568 | 4.057550796500525 |
| 24\|3.0\|0.75 | 5 | 2 | 1 | 2 | 385.2 | 178.0 | 575.4 | -0.5129806517122879 | 0.003676758194477 | 0.9055943596583602 | 3.5674360637586364 |
| 24\|2.0\|0.25 | 5 | 2 | 1 | 2 | 138.8 | 191.0 | 236.2 | -0.6181732152261827 | 0.0069995731967562 | 0.89627643349524 | 14.081187114801306 |
| 72\|2.5\|0.25 | 5 | 1 | 1 | 1 | 368.2 | 201.0 | 325.8 | -0.6124060601750088 | 0.0050457639051865 | 0.8828273317374054 | 6.353218707906953 |
| 72\|2.5\|0.0 | 5 | 2 | 1 | 2 | 213.2 | 221.0 | 63.6 | -0.7835853198791993 | 0.0030547722806118 | 0.8576109757190169 | 36.11593619994449 |
| 24\|1.5\|0.25 | 5 | 2 | 1 | 2 | 207.2 | 224.0 | 260.4 | -0.6711992782171246 | 0.0099871959026888 | 0.8552047752968378 | 8.330730419602565 |
| 5\|2.5\|0.0 | 10 | 3 | 1 | 3 | 353.5 | 230.5 | 381.5 | -0.3571550926994685 | 0.01612752698231815 | 0.8515937017755814 | 7.24936186974853 |

## Stability across markets

| market | median | mean | std |
| --- | --- | --- | --- |
| crypto | 0.5312312598141825 | 0.5685825638928236 | 0.443653070150329 |
| russia | 0.5721163274343084 | 0.5679224199317265 | 0.2953838573156517 |
| usa | 0.4537453814796421 | 0.4710928444438553 | 0.2569694148188893 |

## Stability across targets (Sharpe dispersion)

Higher `std` means more target-specific luck; lower spread suggests more homogeneous parameter luck.

| target | median | mean | std |
| --- | --- | --- | --- |
| ETH | 0.621575999993207 | 0.6726151770473706 | 0.49082971628629823 |
| BTC | 0.5697231070880231 | 0.6475258503103887 | 0.44696959257649793 |
| SOL | 0.3678996379313001 | 0.39829091807471406 | 0.43952925920197905 |
| BNB | 0.6805577227935453 | 0.689703421671802 | 0.3967023277787848 |
| XRP | 0.397863132601573 | 0.43477745235984283 | 0.34888048084635365 |
| AFKS | 0.6567615884863607 | 0.7040883188858488 | 0.3161709638508188 |
| GAZP | 0.5805466933251515 | 0.5906179892710413 | 0.2992009671241041 |
| NVDA | 0.6597984228382965 | 0.6200211720120543 | 0.28670070081682003 |
| LKOH | 0.5418263573953487 | 0.4603882820053237 | 0.275179810719052 |
| BRK.B | 0.5377834332524476 | 0.5500788480854819 | 0.2710873780159305 |
| CHMF | 0.4983386289191801 | 0.4972184354404729 | 0.2705394186492044 |
| AFLT | 0.5837918964765851 | 0.5872990740559463 | 0.2552603344146605 |
| MSFT | 0.40122260632633266 | 0.38970805612661935 | 0.21813426715897558 |
| AAPL | 0.2667723980782466 | 0.29909311437510994 | 0.18033975057787355 |
| AMZN | 0.5261362313961322 | 0.4965630316200111 | 0.17661950462446463 |

## Top-decile Sharpe — trade and drawdown context

- Median `number_of_trades` in top 10% Sharpe rows: **100.0**.
- Median `max_drawdown` in top 10% Sharpe rows: **-0.361**.

## Suspicious flags (within top 10% Sharpe)

- Turnover 95th percentile (full sample): **0.069897**.
- Best Sharpe row: market **crypto**, target **ETH**.

| market | target | universe_selection_method | universe_size_requested | universe_size_actual | universe_assets | missing_priority_assets | filled_from_fallback | train_window | rebalance_frequency | pca_explained_variance | zscore_lookback | entry_z | exit_z | transaction_cost_bps | annualization_factor | total_return | annualized_return | annualized_volatility | sharpe_ratio | max_drawdown | turnover | number_of_trades | average_holding_period | hit_rate | flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| usa | NVDA | priority | 30 | 30 | AAPL,MSFT,AVGO,ORCL,AMD,CSCO,QCOM,TXN,IBM,ACN,ADI,GOOGL,META,NFLX,DIS,VZ,AMZN,TSLA,HD,MCD,LOW,WMT,COST,PG,KO,PEP,PM,BRK-B,JPM,V | TMUS,CMCSA,BKNG,SBUX | nan | 252 | 10 | 0.8 | 60 | 1.0 | 0.25 | 5.0 | 252.0 | 24.66434263827594 | 0.4357441123022441 | 0.4108886264596876 | 1.0604920268947746 | -0.3419177549048093 | 0.0707651481645289 | 143 | 23.952380952380953 | 0.5321404903909874 | high_turnover_p95 |
| crypto | SOL | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,XRP,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 1.5 | 0.25 | 10.0 | 8760.0 | 23.88417168159382 | 0.8237009767983521 | 0.8520246004921914 | 0.9667572700630034 | -0.7142706176336204 | 0.0099871959026888 | 462 | 124.13157894736842 | 0.5058299766800933 | deep_drawdown |
| crypto | SOL | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,XRP,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.0 | 0.0 | 10.0 | 8760.0 | 504.8258478845379 | 2.202472916855259 | 1.0884710191767846 | 2.023455726474922 | -0.7716813463477967 | 0.004502774221084 | 106 | 46354.0 | 0.5067523838287958 | deep_drawdown |
| crypto | SOL | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,XRP,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.5 | 0.0 | 10.0 | 8760.0 | 46.04396174506575 | 1.0542702514655409 | 1.0822270865782613 | 0.9741673115934352 | -0.8153533548008199 | 0.0030516431924882 | 72 | 45868.0 | 0.5056902415627452 | deep_drawdown |
| crypto | SOL | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,XRP,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 72 | 0.8 | 336 | 1.5 | 0.25 | 10.0 | 8760.0 | 28.7940085996481 | 0.8873653017319318 | 0.9008155947583038 | 0.9850687609044104 | -0.7098312999887684 | 0.0100401606425702 | 464 | 122.66375545851528 | 0.5027411890352439 | deep_drawdown |
| crypto | SOL | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,XRP,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 72 | 0.8 | 336 | 2.0 | 0.0 | 10.0 | 8760.0 | 57.05584534121407 | 1.1383123651524358 | 1.1279806700332469 | 1.0091594611447414 | -0.7874910004567408 | 0.0041228744766299 | 97 | 45973.0 | 0.5032519087290366 | deep_drawdown |
| crypto | XRP | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.0 | 0.0 | 10.0 | 8760.0 | 159.16544516867089 | 1.3861050857202677 | 1.0407540442678878 | 1.331827719867584 | -0.8560525237882223 | 0.0047915199874833 | 123 | 50496.0 | 0.5099017743979721 | deep_drawdown |
| crypto | XRP | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.5 | 0.0 | 10.0 | 8760.0 | 137.56665756310176 | 1.3276181225740733 | 1.04079043045813 | 1.2755864040656957 | -0.7806148800283075 | 0.0032269420323867 | 83 | 50493.0 | 0.5116946903531182 | deep_drawdown |
| crypto | XRP | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 72 | 0.8 | 336 | 2.0 | 0.0 | 10.0 | 8760.0 | 96.4823195886141 | 1.191519479877854 | 1.107312623677171 | 1.0760461448737468 | -0.8398608748586398 | 0.004478604396464 | 115 | 50493.0 | 0.5058721010833185 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 1.0 | 0.0 | 10.0 | 8760.0 | 17.893316531617327 | 0.6544694885068518 | 0.6566635457326667 | 0.9966587802230336 | -0.7506485504201823 | 0.0085856215285926 | 220 | 50794.0 | 0.5024018584872229 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.0 | 0.0 | 10.0 | 8760.0 | 18.978831031892312 | 0.6703802165394932 | 0.6558339020286641 | 1.022179875828062 | -0.8158309576766447 | 0.0045568332942188 | 117 | 50684.0 | 0.5047746823455134 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.5 | 0.0 | 10.0 | 8760.0 | 27.378499402248863 | 0.7738954400053899 | 0.6545753207799899 | 1.1822863090579376 | -0.7471087368486078 | 0.0029140264413674 | 75 | 50323.0 | 0.5059714245971028 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 72 | 0.8 | 336 | 1.5 | 0.0 | 10.0 | 8760.0 | 51.530668896185 | 0.9712574874055048 | 0.6966777679416548 | 1.3941272882513531 | -0.7223998762323192 | 0.006082296800438 | 156 | 50794.0 | 0.5027956057802102 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 168 | 0.8 | 336 | 1.5 | 0.0 | 10.0 | 8760.0 | 86.10312992515878 | 1.149656553115714 | 0.8297798490518329 | 1.3854958690903325 | -0.8022906008369658 | 0.006082296800438 | 156 | 50794.0 | 0.5029727920620546 | deep_drawdown |

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
