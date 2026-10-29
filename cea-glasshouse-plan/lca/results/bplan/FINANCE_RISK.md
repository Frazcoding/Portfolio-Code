# BP36: financing on the verified designs, phasing and Monte Carlo

Central scheme: supplier credit + plant asset finance, 1-yr holiday. Nominal, post-tax (finance.py). Inputs in the bplan_finance_risk.py docstring.

## Designs at parity -10 % (central scheme)

| Design | Capex GBP M | kg/yr (t) | Min price GBP/kg | DSCR yr 1 | min DSCR | Project IRR real pre-tax | Equity IRR nom. | at GBP 1.02: min DSCR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| lit lead 2.9 ha 150 umol 2T | 11.45 | 2,698 | 1.237 | 2.13 | 1.56 | 15.2 % | 21.8 % | 0.49 |
| verified site_002 4.44 ha 232 umol 4T | 16.30 | 4,382 | 1.246 | 2.00 | 1.58 | 15.5 % | 22.1 % | 0.18 |
| verified site_028 4.61 ha 245 umol 4T | 16.96 | 4,550 | 1.315 | 1.66 | 1.47 | 13.9 % | 19.0 % | -0.16 |
| verified site_002 5.54 ha 219 umol 2T | 18.89 | 5,468 | 1.234 | 2.10 | 1.67 | 16.5 % | 23.9 % | 0.14 |

## Monte Carlo (2,000 draws, central scheme)

| Design | Project IRR P10 / P50 / P90 | Equity IRR P10 / P50 / P90 | min DSCR P10 / P50 / P90 | P(min DSCR < 1.25) | P(< 1.0) | P(equity IRR < 12 %) |
|---|---|---|---|---:|---:|---:|
| lit lead 2.9 ha 150 umol 2T | 8.3 % / 11.6 % / 14.7 % | 10.0 % / 15.2 % / 20.8 % | 0.93 / 1.28 / 1.53 | 45% | 14% | 23% |
| verified site_002 4.44 ha 232 umol 4T | 7.7 % / 11.4 % / 14.8 % | 9.0 % / 14.7 % / 20.8 % | 0.69 / 1.25 / 1.52 | 50% | 28% | 28% |
| verified site_028 4.61 ha 245 umol 4T | 5.8 % / 9.8 % / 13.2 % | 6.4 % / 12.0 % / 17.7 % | 0.34 / 0.95 / 1.40 | 75% | 55% | 50% |
| verified site_002 5.54 ha 219 umol 2T | 8.2 % / 12.2 % / 15.8 % | 9.7 % / 15.9 % / 22.5 % | 0.69 / 1.31 / 1.60 | 44% | 26% | 22% |

## Phasing to 10.2 ha (parity -10 %, central scheme per module)

| Start yr | ha | Capex GBP M | Debt GBP M | Equity GBP M | min DSCR | Equity IRR nom. |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2.9 | 11.45 | 8.12 | 4.34 | 1.56 | 21.8 % |
| 3 | 2.9 | 11.45 | 8.12 | 4.34 | 1.56 | 21.8 % |
| 6 | 4.4 | 15.87 | 11.32 | 5.99 | 1.70 | 24.7 % |

Total capex GBP 38.8 M, debt GBP 27.6 M. Peak external equity GBP 6.68 M (year 6): later phases are part-funded from phase-1 cash. Combined equity IRR 22.4 %, payback 8.2 yr.
