# BP36: financing on the verified designs, phasing and Monte Carlo

Central scheme: supplier credit + plant asset finance, 1-yr holiday. Nominal, post-tax (finance.py). Inputs in the bplan_finance_risk.py docstring.

## Designs at parity -10 % (central scheme)

| Design | Capex GBP M | kg/yr (t) | Min price GBP/kg | DSCR yr 1 | min DSCR | Project IRR real pre-tax | Equity IRR nom. | at GBP 1.02: min DSCR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| lit lead 2.9 ha 150 umol 2T | 11.45 | 2,698 | 1.243 | 2.07 | 1.55 | 15.2 % | 22.2 % | 0.48 |
| verified site_002 4.44 ha 232 umol 4T | 16.30 | 4,382 | 1.251 | 1.96 | 1.57 | 15.5 % | 22.5 % | 0.18 |
| verified site_028 4.61 ha 245 umol 4T | 16.96 | 4,550 | 1.321 | 1.62 | 1.46 | 13.9 % | 19.3 % | -0.16 |
| verified site_002 5.54 ha 219 umol 2T | 18.89 | 5,468 | 1.24 | 2.05 | 1.66 | 16.5 % | 24.3 % | 0.14 |

## Monte Carlo (2,000 draws, central scheme)

| Design | Project IRR P10 / P50 / P90 | Equity IRR P10 / P50 / P90 | min DSCR P10 / P50 / P90 | P(min DSCR < 1.25) | P(< 1.0) | P(equity IRR < 12 %) |
|---|---|---|---|---:|---:|---:|
| lit lead 2.9 ha 150 umol 2T | 8.3 % / 11.6 % / 14.7 % | 10.1 % / 15.4 % / 21.1 % | 0.92 / 1.27 / 1.53 | 47% | 16% | 21% |
| verified site_002 4.44 ha 232 umol 4T | 7.7 % / 11.4 % / 14.8 % | 9.1 % / 14.9 % / 21.2 % | 0.67 / 1.23 / 1.51 | 53% | 30% | 27% |
| verified site_028 4.61 ha 245 umol 4T | 5.8 % / 9.8 % / 13.2 % | 6.5 % / 12.1 % / 18.0 % | 0.33 / 0.93 / 1.39 | 77% | 57% | 49% |
| verified site_002 5.54 ha 219 umol 2T | 8.2 % / 12.2 % / 15.8 % | 9.8 % / 16.1 % / 22.8 % | 0.67 / 1.29 / 1.59 | 46% | 28% | 22% |

## Phasing to 10.2 ha (parity -10 %, central scheme per module)

| Start yr | ha | Capex GBP M | Debt GBP M | Equity GBP M | min DSCR | Equity IRR nom. |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2.9 | 11.45 | 8.12 | 4.22 | 1.55 | 22.2 % |
| 3 | 2.9 | 11.45 | 8.12 | 4.22 | 1.55 | 22.2 % |
| 6 | 4.4 | 15.87 | 11.32 | 5.82 | 1.69 | 25.2 % |

Total capex GBP 38.8 M, debt GBP 27.6 M. Peak external equity GBP 6.36 M (year 6): later phases are part-funded from phase-1 cash. Combined equity IRR 22.8 %, payback 8.1 yr.
