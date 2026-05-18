# Parameter range analysis (grid search)

- Source: `results\grid_search\grid_search_results.csv` (1440 rows).
- Outputs: `results\parameter_analysis/`.

## Rebalance frequency (median Sharpe, full sample)

| rebalance_frequency | median_sharpe_ratio |
| --- | --- |
| 24.0 | 0.7442449320416362 |
| 5.0 | 0.6582821878166146 |
| 72.0 | 0.622104239839937 |
| 10.0 | 0.5731249715150883 |
| 21.0 | 0.5561669744897919 |
| 168.0 | 0.3962103642643635 |
| 63.0 | 0.25663696103595884 |
| 336.0 | 0.07422654297030801 |

## Entry z (median Sharpe, full sample)

| entry_z | median_sharpe_ratio |
| --- | --- |
| 2.0 | 0.577972583039992 |
| 2.5 | 0.5259138268434456 |
| 1.5 | 0.5228299698084 |
| 1.0 | 0.49025271355144007 |
| 3.0 | 0.45444566359286315 |

## Exit z (median Sharpe, full sample)

| exit_z | median_sharpe_ratio |
| --- | --- |
| 0.0 | 0.6136516671154113 |
| 0.25 | 0.5696195293445276 |
| 0.5 | 0.5255863435256857 |
| 0.75 | 0.4596958242509853 |
| 1.0 | 0.36265512376779213 |

## Top 10% Sharpe — global parameter frequencies

See `top10_parameter_frequencies_global.csv` for full tables. Rebalance / entry / exit / pair / triple frequencies describe which settings dominate the best decile.

**Rebalance (top 10% Sharpe, global):** 24.0 (30.6%), 5.0 (22.2%), 10.0 (16.0%), 72.0 (13.9%), 21.0 (9.0%), 168.0 (5.6%), 63.0 (2.1%), 336.0 (0.7%)


### Concentration (top 10% Sharpe slice)

- Largest single-market share of rows in this slice: **50.7%** (crypto).
- Largest single-target share: **18.1%** (AFKS).

## Robust combinations (triple)

File `robust_parameter_combos.csv` ranks `rebalance|entry|exit` by median Sharpe and counts how often each combo appears in the top 10% Sharpe slice across distinct targets and markets.

| rebalance_entry_exit | n_rows_total | n_distinct_targets_top10_sharpe | n_distinct_markets_top10_sharpe | n_distinct_market_target_pairs_top10_sharpe | mean_rank_sharpe | median_rank_sharpe | mean_rank_total_return | median_max_drawdown | median_turnover | median_sharpe_ratio | median_total_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24\|2.0\|0.0 | 5 | 4 | 1 | 4 | 65.4 | 15.0 | 77.2 | -0.7716813463477965 | 0.0045568332942188 | 1.4951875831996424 | 25.98784539754132 |
| 24\|3.0\|0.0 | 5 | 3 | 1 | 3 | 329.0 | 20.0 | 161.8 | -0.6603257460025506 | 0.0018970507705546 | 1.4423477479654518 | 17.038969281063917 |
| 24\|2.5\|0.0 | 5 | 5 | 1 | 5 | 41.2 | 30.0 | 36.2 | -0.7485987443009772 | 0.0030516431924882 | 1.3583713986512624 | 46.04396174506599 |
| 24\|1.5\|0.0 | 5 | 4 | 1 | 4 | 176.2 | 80.0 | 107.2 | -0.6516354720624936 | 0.0059539052496798 | 1.0684887928360671 | 12.896493967076188 |
| 24\|2.5\|0.25 | 5 | 3 | 1 | 3 | 234.2 | 82.0 | 292.6 | -0.6415951146764838 | 0.0050848783540639 | 1.0603527272983502 | 9.21417430999826 |
| 24\|1.0\|0.0 | 5 | 3 | 1 | 3 | 380.0 | 91.0 | 251.2 | -0.7465762485303193 | 0.0083118203864507 | 1.0365536653712877 | 11.6379619617699 |
| 72\|2.5\|0.0 | 5 | 3 | 1 | 3 | 136.8 | 101.0 | 42.4 | -0.7942121950963663 | 0.0030547722806118 | 1.0127321273592809 | 36.11593619994506 |
| 72\|2.0\|0.0 | 5 | 3 | 1 | 3 | 169.2 | 103.0 | 116.8 | -0.7874910004567409 | 0.0042830321520769 | 1.0091594611447292 | 19.668477110454887 |
| 24\|2.0\|0.5 | 5 | 3 | 1 | 3 | 287.6 | 130.0 | 348.2 | -0.5446915132509569 | 0.0075970977379428 | 0.9591370816513504 | 12.756011753307758 |
| 24\|3.0\|0.5 | 5 | 2 | 1 | 2 | 264.0 | 154.0 | 402.2 | -0.5709055151811215 | 0.0037158726433544 | 0.9190884272265398 | 4.640613804635368 |
| 24\|2.5\|0.5 | 5 | 2 | 1 | 2 | 189.2 | 156.0 | 299.8 | -0.5179927134907805 | 0.0053977939450833 | 0.916952778612619 | 10.066826507776767 |
| 5\|2.0\|0.0 | 10 | 5 | 2 | 5 | 296.6 | 168.0 | 352.5 | -0.2983604034371852 | 0.0243255196815568 | 0.9119706289469616 | 4.057550796500523 |
| 72\|3.0\|0.0 | 5 | 2 | 1 | 2 | 317.6 | 171.0 | 92.8 | -0.7319181862861978 | 0.0019752796683094 | 0.8965812645823098 | 16.26865715422233 |
| 24\|1.5\|0.25 | 5 | 2 | 1 | 2 | 309.0 | 178.0 | 314.4 | -0.6469336746350658 | 0.0099871959026888 | 0.8918913554277248 | 8.867154550970392 |
| 24\|2.0\|0.25 | 5 | 2 | 1 | 2 | 241.2 | 191.0 | 299.8 | -0.6181732152261832 | 0.0069995731967562 | 0.8718222677910912 | 12.604899316576056 |
| 72\|1.5\|0.0 | 5 | 2 | 1 | 2 | 232.8 | 192.0 | 125.6 | -0.6542564178728014 | 0.0057302667605413 | 0.8707444863355948 | 12.720912464763154 |
| 24\|3.0\|0.25 | 5 | 2 | 1 | 2 | 204.2 | 208.0 | 320.4 | -0.5753493685520552 | 0.0036376437455996 | 0.8558223676252186 | 9.607515038675832 |
| 5\|2.5\|0.0 | 10 | 3 | 1 | 3 | 336.8 | 210.5 | 371.0 | -0.35715509269946955 | 0.01612752698231815 | 0.8515937017755764 | 7.249361869748599 |
| 72\|3.0\|0.5 | 5 | 1 | 1 | 1 | 383.4 | 230.0 | 463.0 | -0.6256540034977905 | 0.0035985292967222 | 0.8274784315347806 | 4.2666746677646055 |
| 72\|1.0\|0.0 | 5 | 1 | 1 | 1 | 386.6 | 241.0 | 222.2 | -0.7462175300534082 | 0.0077544219430915 | 0.8179960441775288 | 8.42076256970296 |

## Stability across markets

| market | median | mean | std |
| --- | --- | --- | --- |
| crypto | 0.48838536687430667 | 0.5165536026832435 | 0.4451612922656912 |
| russia | 0.5721163274343015 | 0.567922419931726 | 0.2953838573156509 |
| usa | 0.45374538147963905 | 0.4710928444438567 | 0.2569694148188889 |

## Stability across targets (Sharpe dispersion)

Higher `std` means more target-specific luck; lower spread suggests more homogeneous parameter luck.

| target | median | mean | std |
| --- | --- | --- | --- |
| ETH | 0.5706997723157108 | 0.5947512064329784 | 0.47664348581810045 |
| BTC | 0.4136331808426603 | 0.49022000216462747 | 0.44017434741686534 |
| SOL | 0.36789963793129743 | 0.3982909180747127 | 0.4395292592019787 |
| BNB | 0.6839959218811547 | 0.6897081078731119 | 0.43540473352671544 |
| XRP | 0.3891002524506427 | 0.4097977788707867 | 0.3642155484003819 |
| AFKS | 0.6567615884863585 | 0.7040883188858484 | 0.3161709638508174 |
| GAZP | 0.5805466933251533 | 0.5906179892710378 | 0.29920096712410454 |
| NVDA | 0.6597984228383003 | 0.6200211720120559 | 0.2867007008168209 |
| LKOH | 0.5418263573953463 | 0.4603882820053217 | 0.2751798107190496 |
| BRK.B | 0.5377834332524511 | 0.5500788480854822 | 0.27108737801592875 |
| CHMF | 0.49833862891917813 | 0.49721843544047556 | 0.2705394186492043 |
| AFLT | 0.5837918964765829 | 0.5872990740559466 | 0.25526033441465973 |
| MSFT | 0.4012226063263262 | 0.3897080561266159 | 0.2181342671589747 |
| AAPL | 0.2667723980782527 | 0.2990931143751126 | 0.1803397505778724 |
| AMZN | 0.5261362313961401 | 0.49656303162001686 | 0.17661950462446435 |

## Top-decile Sharpe — trade and drawdown context

- Median `number_of_trades` in top 10% Sharpe rows: **94.0**.
- Median `max_drawdown` in top 10% Sharpe rows: **-0.381**.

## Suspicious flags (within top 10% Sharpe)

- Turnover 95th percentile (full sample): **0.069897**.
- Best Sharpe row: market **crypto**, target **ETH**.

| market | target | universe_selection_method | universe_size_requested | universe_size_actual | universe_assets | missing_priority_assets | filled_from_fallback | train_window | rebalance_frequency | pca_explained_variance | zscore_lookback | entry_z | exit_z | transaction_cost_bps | annualization_factor | total_return | annualized_return | annualized_volatility | sharpe_ratio | max_drawdown | turnover | number_of_trades | average_holding_period | hit_rate | flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| usa | NVDA | priority | 30 | 30 | AAPL,MSFT,AVGO,ORCL,AMD,CSCO,QCOM,TXN,IBM,ACN,ADI,GOOGL,META,NFLX,DIS,VZ,AMZN,TSLA,HD,MCD,LOW,WMT,COST,PG,KO,PEP,PM,BRK-B,JPM,V | TMUS,CMCSA,BKNG,SBUX | nan | 252 | 10 | 0.8 | 60 | 1.0 | 0.25 | 5.0 | 252.0 | 24.664342638276104 | 0.4357441123022452 | 0.410888626459688 | 1.0604920268947764 | -0.3419177549048091 | 0.0707651481645289 | 143 | 23.95238095238096 | 0.5321404903909874 | high_turnover_p95 |
| crypto | XRP | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.0 | 0.0 | 10.0 | 8760.0 | 237.39131224689808 | 1.5543502843064343 | 1.03956874827718 | 1.4951875831996424 | -0.8666934878873505 | 0.0048697488852382 | 125 | 50496.0 | 0.5090304182509505 | deep_drawdown |
| crypto | XRP | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.5 | 0.0 | 10.0 | 8760.0 | 165.72283470522817 | 1.402564500344464 | 1.0395716349231017 | 1.349175423056068 | -0.8027564911873281 | 0.0032269420323867 | 83 | 50493.0 | 0.5106252351811142 | deep_drawdown |
| crypto | XRP | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 72 | 0.8 | 336 | 2.0 | 0.0 | 10.0 | 8760.0 | 135.633114233449 | 1.322021276351096 | 1.1012381623399032 | 1.2004862540742998 | -0.8583700800920006 | 0.0045568332942188 | 117 | 50493.0 | 0.5054165923989464 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 1.0 | 0.0 | 10.0 | 8760.0 | 21.90687643434796 | 0.7099802815999565 | 0.6612177529689245 | 1.073746550833041 | -0.7465762485303193 | 0.0086638504263474 | 222 | 50794.0 | 0.5032681025317951 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.0 | 0.0 | 10.0 | 8760.0 | 20.98864076708707 | 0.6980370161315392 | 0.6604678100235475 | 1.0568827209105804 | -0.8169160613774937 | 0.0045568332942188 | 117 | 50684.0 | 0.5048141425301871 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.0 | 0.5 | 10.0 | 8760.0 | 12.756011753307758 | 0.5669242644879142 | 0.4954104429908275 | 1.1443526726351445 | -0.7026529566410826 | 0.0084682781819604 | 431 | 104.46046511627908 | 0.5067010997818246 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.5 | 0.0 | 10.0 | 8760.0 | 40.77495431820005 | 0.8953848762244647 | 0.6591605779638023 | 1.3583713986512624 | -0.7485987443009772 | 0.0029922553391222 | 77 | 50323.0 | 0.5061105260020269 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 72 | 0.8 | 336 | 1.0 | 0.0 | 10.0 | 8760.0 | 20.223953550122847 | 0.6877712542808243 | 0.703660340788566 | 0.9774193803647718 | -0.7462175300534082 | 0.0080380192443088 | 206 | 50795.0 | 0.5017226104931588 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 72 | 0.8 | 336 | 1.5 | 0.0 | 10.0 | 8760.0 | 56.797070638077926 | 1.003788926783943 | 0.7035542816748771 | 1.4267398449972175 | -0.7223998762323198 | 0.006082296800438 | 156 | 50794.0 | 0.503209040437847 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 72 | 0.8 | 336 | 2.5 | 0.0 | 10.0 | 8760.0 | 21.966308311499134 | 0.7107395400281682 | 0.7018040810865117 | 1.0127321273592809 | -0.7942121950963663 | 0.0029140264413674 | 75 | 50323.0 | 0.5048586133577092 | deep_drawdown |
| crypto | BNB | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,SOL,XRP,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 168 | 0.8 | 336 | 1.5 | 0.0 | 10.0 | 8760.0 | 59.83565903941841 | 1.0214559424487462 | 0.8363724449519097 | 1.2212931554763005 | -0.8022906008369652 | 0.0060040679026832 | 154 | 50794.0 | 0.5029924794267039 | deep_drawdown |
| crypto | SOL | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,XRP,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 1.5 | 0.25 | 10.0 | 8760.0 | 23.884171681593177 | 0.8237009767983432 | 0.8520246004921918 | 0.9667572700629926 | -0.7142706176336209 | 0.0099871959026888 | 462 | 124.13157894736842 | 0.5058299766800933 | deep_drawdown |
| crypto | SOL | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,XRP,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.0 | 0.0 | 10.0 | 8760.0 | 504.8258478845456 | 2.2024729168552684 | 1.0884710191767846 | 2.02345572647493 | -0.7716813463477965 | 0.004502774221084 | 106 | 46354.0 | 0.5067523838287958 | deep_drawdown |
| crypto | SOL | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,XRP,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 24 | 0.8 | 336 | 2.5 | 0.0 | 10.0 | 8760.0 | 46.04396174506599 | 1.0542702514655424 | 1.0822270865782615 | 0.9741673115934366 | -0.8153533548008202 | 0.0030516431924882 | 72 | 45868.0 | 0.5056902415627452 | deep_drawdown |
| crypto | SOL | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,XRP,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 72 | 0.8 | 336 | 1.5 | 0.25 | 10.0 | 8760.0 | 28.794008599647903 | 0.8873653017319296 | 0.9008155947583038 | 0.985068760904408 | -0.7098312999887672 | 0.0100401606425702 | 464 | 122.66375545851528 | 0.5027411890352439 | deep_drawdown |
| crypto | SOL | priority_with_coverage_fallback | 30 | 30 | BTC,ETH,XRP,BNB,TRX,ADA,AVAX,DOT,NEAR,ATOM,ALGO,DOGE,BCH,LTC,XLM,ETC,LINK,UNI,AAVE,INJ,FIL,VET,FET,GRT,THETA,XTZ,SAND,CHZ,DASH,HBAR | TON,SUI,ICP,MKR,RENDER,RNDR,ARB,OP,MATIC,POL,APT,SEI,EOS,MANA | CHZ,DASH,HBAR | 1440 | 72 | 0.8 | 336 | 2.0 | 0.0 | 10.0 | 8760.0 | 57.05584534121203 | 1.138312365152422 | 1.1279806700332469 | 1.0091594611447292 | -0.7874910004567409 | 0.0041228744766299 | 97 | 45973.0 | 0.5032519087290366 | deep_drawdown |

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
