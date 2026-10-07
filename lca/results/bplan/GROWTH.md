# Growth model: when to expand from 2.9 ha

Inputs and triggers in the bplan_growth.py docstring. Central financing per module; prices real (today's money).

## Modules at GBP 1.40/kg

| Module | Capex GBP M | t/yr | Equity GBP M | Min price GBP/kg | Equity IRR nom. |
|---|---:|---:|---:|---:|---:|
| 2.9 ha | 11.45 | 2,698 | 4.34 | 1.237 | 21.9 % |
| 4.4 ha | 15.87 | 4,080 | 5.99 | 1.194 | 24.7 % |
| 2.9 ha (same site) | 11.04 | 2,698 | 3.93 | 1.237 | 23.7 % |
| 4.4 ha (same site) | 15.46 | 4,080 | 5.58 | 1.194 | 26.3 % |

## Yield phase 1 must prove before a lender funds the next phase (DSCR >= 1.25)

| Contract price GBP/kg | Minimum yield kg/m2 |
|---:|---:|
| 1.24 | 92.8 |
| 1.30 | 88.0 |
| 1.35 | 84.4 |
| 1.40 | 81.0 |
| 1.45 | 78.0 |
| 1.48 | 76.2 |

## Expansion paths

| Yield | Price | Funding | Steps (year: module) | ha operating yr 5 / 10 / 15 | Outside equity GBP M | Equity IRR nom. | Equity NPV 12 % GBP M |
|---|---:|---|---|---|---:|---:|---:|
| model 93 kg/m2 | 1.30 | self-funded | 0: 2.9, 8: 2.9, 12: 2.9 | 2.9 / 5.8 / 8.7 | 4.34 | 17.8 % | 4.6 |
| model 93 kg/m2 | 1.30 | new equity | 0: 2.9, 3: 4.4, 6: 2.9 | 7.3 / 10.2 / 10.2 | 8.23 | 18.9 % | 8.0 |
| model 93 kg/m2 | 1.40 | self-funded | 0: 2.9, 6: 2.9, 9: 2.9 | 2.9 / 8.7 / 8.7 | 4.34 | 22.4 % | 8.9 |
| model 93 kg/m2 | 1.40 | new equity | 0: 2.9, 3: 4.4, 6: 2.9 | 7.3 / 10.2 / 10.2 | 7.44 | 23.7 % | 13.1 |
| model 93 kg/m2 | 1.48 | self-funded | 0: 2.9, 5: 2.9, 8: 2.9 | 2.9 / 8.7 / 8.7 | 4.34 | 26.3 % | 12.5 |
| model 93 kg/m2 | 1.48 | new equity | 0: 2.9, 3: 4.4, 6: 2.9 | 7.3 / 10.2 / 10.2 | 6.81 | 27.6 % | 17.2 |
| lender case 79 kg/m2 | 1.30 | self-funded | 0: 2.9 | 2.9 / 2.9 / 2.9 | 4.33 | 10.1 % | -1.0 |
| lender case 79 kg/m2 | 1.30 | new equity | 0: 2.9 | 2.9 / 2.9 / 2.9 | 4.33 | 10.1 % | -1.0 |
| lender case 79 kg/m2 | 1.40 | self-funded | 0: 2.9 | 2.9 / 2.9 / 2.9 | 4.33 | 13.6 % | 0.8 |
| lender case 79 kg/m2 | 1.40 | new equity | 0: 2.9 | 2.9 / 2.9 / 2.9 | 4.33 | 13.6 % | 0.8 |
| lender case 79 kg/m2 | 1.48 | self-funded | 0: 2.9, 8: 2.9, 12: 2.9 | 2.9 / 5.8 / 8.7 | 4.33 | 16.8 % | 3.9 |
| lender case 79 kg/m2 | 1.48 | new equity | 0: 2.9, 3: 4.4, 6: 2.9 | 7.3 / 10.2 / 10.2 | 8.37 | 17.9 % | 6.9 |
