# Summary of measurements

Times are kernel-only seconds per multiplication (median and IQR of measured repetitions, warm-up excluded). Memory is the peak resident set of the whole process (MB = 10^6 bytes).

## Per-configuration results

| lang | n | reps | warmup | median_s | iqr_s | min_s | max_s | peak_mem_mb | java_heap_MB |
|---|---|---|---|---|---|---|---|---|---|
| c | 10 | 5 | 1 | 1.2e-06 | 1e-07 | 1e-06 | 1.3e-06 | 4.1 |  |
| c | 50 | 5 | 1 | 0.0001404 | 1e-05 | 0.0001387 | 0.0001527 | 4.1 |  |
| c | 100 | 5 | 1 | 0.0009324 | 1.73e-05 | 0.0009264 | 0.0012962 | 4.3 |  |
| c | 200 | 5 | 1 | 0.0064385 | 0.0007736 | 0.0064044 | 0.0077735 | 5.0 |  |
| c | 300 | 5 | 1 | 0.0461333 | 0.010114 | 0.0393451 | 0.0623683 | 6.2 |  |
| c | 500 | 5 | 1 | 0.175529 | 0.0249522 | 0.156404 | 0.197382 | 10.1 |  |
| c | 750 | 5 | 1 | 0.628339 | 0.158045 | 0.621062 | 0.851319 | 17.6 |  |
| c | 1000 | 5 | 1 | 1.63041 | 0.573538 | 1.46837 | 2.44179 | 28.1 |  |
| c | 1500 | 5 | 1 | 9.77523 | 1.15421 | 8.31957 | 11.3095 | 58.1 |  |
| c | 2000 | 5 | 1 | 28.9676 | 1.47343 | 26.9187 | 30.2844 | 100.1 |  |
| java | 10 | 5 | 3 | 3.84e-05 | 1.3e-06 | 3.83e-05 | 8.78e-05 | 44.0 | 1.3 |
| java | 50 | 5 | 3 | 0.000352 | 4.09e-05 | 0.0002942 | 0.0009648 | 44.5 | 1.4 |
| java | 100 | 5 | 3 | 0.0013325 | 0.0004314 | 0.0011331 | 0.0022595 | 44.9 | 1.6 |
| java | 200 | 5 | 3 | 0.0106036 | 0.0003248 | 0.0098702 | 0.0132468 | 46.3 | 2.3 |
| java | 300 | 5 | 3 | 0.0436445 | 0.0206174 | 0.0409869 | 0.0742158 | 51.3 | 3.5 |
| java | 500 | 5 | 3 | 0.199907 | 0.0059645 | 0.17508 | 0.210903 | 59.2 | 7.3 |
| java | 750 | 5 | 3 | 0.74977 | 0.0027069 | 0.738293 | 1.31405 | 74.3 | 14.8 |
| java | 1000 | 5 | 3 | 2.72122 | 0.20031 | 2.37719 | 3.88005 | 95.5 | 25.3 |
| java | 1500 | 5 | 3 | 12.724 | 1.02996 | 11.584 | 13.2887 | 119.3 | 55.3 |
| java | 2000 | 5 | 3 | 33.1779 | 11.3619 | 30.1125 | 43.2912 | 144.4 | 97.3 |
| python | 10 | 5 | 1 | 0.0001027 | 1.4e-06 | 0.0001018 | 0.000118 | 20.1 |  |
| python | 50 | 5 | 1 | 0.0125884 | 0.0008233 | 0.0110962 | 0.0136813 | 20.4 |  |
| python | 100 | 5 | 1 | 0.09602 | 0.0013599 | 0.0942473 | 0.104192 | 21.2 |  |
| python | 200 | 5 | 1 | 0.796071 | 0.0434055 | 0.757143 | 0.917486 | 24.6 |  |
| python | 300 | 5 | 1 | 3.11499 | 0.0786897 | 2.9097 | 3.50467 | 30.6 |  |
| python | 500 | 3 | 0 | 16.6778 | 1.30575 | 14.8869 | 17.4984 | 50.2 |  |
| python | 750 | 3 | 0 | 93.2725 | 22.5079 | 77.311 | 122.327 | 88.2 |  |
| python | 1000 | 3 | 0 | 311.98 | 33.2863 | 249.211 | 315.783 | 141.9 |  |

## Largest tested size that completed within the declared limits

| lang | largest_ok_n |
|---|---|
| c | 2000 |
| java | 2000 |
| python | 1000 |

## Fitted growth exponent (log-log slope of median time)

A pure n³ algorithm gives 3; cache and runtime effects move the slope.

| lang | sizes_used | fitted_exponent |
|---|---|---|
| c | n ≥ 100 (8 points) | 3.43 |
| java | n ≥ 100 (8 points) | 3.40 |
| python | n ≥ 100 (6 points) | 3.50 |

## Ratio of median times (language A / language B) at common sizes

| n | java / c | python / c | python / java |
|---|---|---|---|
| 10 | 32.00 | 85.58 | 2.67 |
| 50 | 2.51 | 89.66 | 35.76 |
| 100 | 1.43 | 102.98 | 72.06 |
| 200 | 1.65 | 123.64 | 75.08 |
| 300 | 0.95 | 67.52 | 71.37 |
| 500 | 1.14 | 95.01 | 83.43 |
| 750 | 1.19 | 148.44 | 124.40 |
| 1000 | 1.67 | 191.35 | 114.65 |
| 1500 | 1.30 |  |  |
| 2000 | 1.15 |  |  |

## Runs that were not 'ok' (timeouts, failures, skipped sizes)

| lang | n | status | reps_completed | timeout_s | note |
|---|---|---|---|---|---|
| python | 1500 | timeout | 0 | 900 | killed after 900 s; 0 measured reps finished |
| python | 2000 | skipped_after_timeout | 0 | 900 | not run: smaller size already ended with timeout |
