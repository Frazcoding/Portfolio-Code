# Financing model (BP33/BP37e), lit lead 2.9 ha, 150 umol, 2 PPA turbines

Capex GBP 11.45 M, yield 93.0 kg/m2, carbon 0.37 kg CO2e/kg (0.89 with the CO2 dose counted), import parity GBP 1.555/kg. Nominal (CPI 2 %), post-tax (CT 25 %, full expensing). Prices are real (year-0 money), CPI-indexed. Inputs and tiers in the finance.py docstring.

## Minimum real price (GBP/kg)

| Scheme | Lender (DSCR >= 1.25) | Lender + equity 12 % nominal |
|---|---:|---:|
| all equity (benchmark) | - | 1.188 |
| supplier credit + plant asset finance, 1-yr holiday | 1.243 | 1.243 |
| supplier credit + plant asset finance, no holiday | 1.522 | 1.522 |
| bank debt sculpted to DSCR 1.25 | 1.190 | 1.19 |
| vendor finance + preference shares 12 % | 1.243 | 1.243 |
| vendor finance + FDPSS grant GBP 0.4 M | 1.243 | 1.243 |
| vendor finance + heat-plant ESCo (buyout yr 10) | 1.265 | 1.265 |

All-equity row: equity hurdle 10.2 % nominal post-tax (8 % real).

## Price: lender GBP 1.01

| Scheme | Debt GBP M | Equity GBP M | DSCR yr 1 | min DSCR | min DSCR yr 2+ | Equity IRR nom. | real | Payback yr | Negative equity years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| all equity (benchmark) | 0.00 | 11.77 | - | - | - | 5.7 % | 3.7 % | 13.8 | 15,20,25 |
| supplier credit + plant asset finance, 1-yr holiday | 8.12 | 4.22 | 0.44 | 0.44 | 0.68 | 5.6 % | 3.6 % | 18.4 | 1,2,3,4,5,6,7,8,10,15,20,25 |
| supplier credit + plant asset finance, no holiday | 8.12 | 4.19 | 0.21 | 0.21 | 0.73 | 5.7 % | 3.6 % | 18.2 | 1,2,3,4,5,6,10,15,20,25 |
| bank debt sculpted to DSCR 1.25 | 6.18 | 5.90 | 0.55 | 0.55 | 1.25 | 5.6 % | 3.5 % | 18.6 | 1,10,15,20,25 |
| vendor finance + preference shares 12 % | 8.12 | 2.11 | 0.44 | 0.44 | 0.68 | 4.3 % | 2.3 % | 27.5 | 1,2,3,4,5,6,7,8,10,15,20,25 |
| vendor finance + FDPSS grant GBP 0.4 M | 8.12 | 3.82 | 0.44 | 0.44 | 0.68 | 6.0 % | 3.9 % | 18.1 | 1,2,3,4,5,6,7,8,10,15,20,25 |
| vendor finance + heat-plant ESCo (buyout yr 10) | 5.42 | 3.78 | -0.42 | -0.42 | 0.56 | 5.4 % | 3.3 % | 20.2 | 1,2,3,4,5,6,7,10,15,20,25 |

## Price: lender GBP 1.10

| Scheme | Debt GBP M | Equity GBP M | DSCR yr 1 | min DSCR | min DSCR yr 2+ | Equity IRR nom. | real | Payback yr | Negative equity years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| all equity (benchmark) | 0.00 | 11.77 | - | - | - | 8.1 % | 5.9 % | 11.2 | 15,25 |
| supplier credit + plant asset finance, 1-yr holiday | 8.12 | 4.22 | 0.82 | 0.82 | 0.9 | 9.2 % | 7.0 % | 13.6 | 15,25 |
| supplier credit + plant asset finance, no holiday | 8.12 | 4.19 | 0.4 | 0.4 | 0.97 | 9.1 % | 7.0 % | 13.4 | 1,15,25 |
| bank debt sculpted to DSCR 1.25 | 7.44 | 4.71 | 0.85 | 0.85 | 1.32 | 9.3 % | 7.2 % | 15.6 | 10,15,25 |
| vendor finance + preference shares 12 % | 8.12 | 2.11 | 0.82 | 0.82 | 0.9 | 9.1 % | 6.9 % | 18.4 | 15,25 |
| vendor finance + FDPSS grant GBP 0.4 M | 8.12 | 3.82 | 0.82 | 0.82 | 0.9 | 9.8 % | 7.6 % | 13.2 | 15,25 |
| vendor finance + heat-plant ESCo (buyout yr 10) | 5.42 | 3.78 | 0.17 | 0.17 | 0.9 | 9.1 % | 7.0 % | 15.6 | 1,10,15,25 |

## Price: lender GBP 1.20

| Scheme | Debt GBP M | Equity GBP M | DSCR yr 1 | min DSCR | min DSCR yr 2+ | Equity IRR nom. | real | Payback yr | Negative equity years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| all equity (benchmark) | 0.00 | 11.77 | - | - | - | 10.4 % | 8.3 % | 8.8 | 25 |
| supplier credit + plant asset finance, 1-yr holiday | 8.12 | 4.22 | 1.24 | 1.15 | 1.15 | 13.3 % | 11.1 % | 10.3 | 25 |
| supplier credit + plant asset finance, no holiday | 8.12 | 4.19 | 0.6 | 0.6 | 1.23 | 13.0 % | 10.8 % | 10.3 | 1,25 |
| bank debt sculpted to DSCR 1.25 | 7.44 | 4.73 | 1.29 | 1.29 | 1.61 | 13.5 % | 11.3 % | 7.9 | 15,25 |
| vendor finance + preference shares 12 % | 8.12 | 2.11 | 1.24 | 1.15 | 1.15 | 13.7 % | 11.5 % | 13.0 | 25 |
| vendor finance + FDPSS grant GBP 0.4 M | 8.12 | 3.82 | 1.24 | 1.15 | 1.15 | 14.2 % | 12.0 % | 10.0 | 25 |
| vendor finance + heat-plant ESCo (buyout yr 10) | 5.42 | 3.78 | 0.83 | 0.83 | 1.28 | 13.5 % | 11.3 % | 8.7 | 10,25 |

## Price: sponsor parity -5%

| Scheme | Debt GBP M | Equity GBP M | DSCR yr 1 | min DSCR | min DSCR yr 2+ | Equity IRR nom. | real | Payback yr | Negative equity years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| all equity (benchmark) | 0.00 | 11.77 | - | - | - | 16.3 % | 14.0 % | 6.0 | 25 |
| supplier credit + plant asset finance, 1-yr holiday | 8.12 | 4.22 | 2.4 | 1.72 | 1.72 | 25.9 % | 23.5 % | 4.0 | 25 |
| supplier credit + plant asset finance, no holiday | 8.12 | 4.19 | 1.16 | 1.16 | 1.85 | 24.9 % | 22.4 % | 4.2 | 25 |
| bank debt sculpted to DSCR 1.25 | 7.44 | 4.76 | 2.51 | 2.4 | 2.4 | 25.9 % | 23.4 % | 3.9 | 25 |
| vendor finance + preference shares 12 % | 8.12 | 2.11 | 2.4 | 1.72 | 1.72 | 30.3 % | 27.7 % | 4.4 | 25 |
| vendor finance + FDPSS grant GBP 0.4 M | 8.12 | 3.82 | 2.4 | 1.68 | 1.68 | 28.2 % | 25.7 % | 3.6 | 25 |
| vendor finance + heat-plant ESCo (buyout yr 10) | 5.42 | 3.78 | 2.64 | 2.24 | 2.24 | 27.4 % | 24.9 % | 3.7 | 10,25 |

## Price: sponsor parity -10%

| Scheme | Debt GBP M | Equity GBP M | DSCR yr 1 | min DSCR | min DSCR yr 2+ | Equity IRR nom. | real | Payback yr | Negative equity years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| all equity (benchmark) | 0.00 | 11.77 | - | - | - | 14.7 % | 12.5 % | 6.6 | 25 |
| supplier credit + plant asset finance, 1-yr holiday | 8.12 | 4.22 | 2.07 | 1.55 | 1.55 | 22.2 % | 19.8 % | 4.8 | 25 |
| supplier credit + plant asset finance, no holiday | 8.12 | 4.19 | 1.0 | 1.0 | 1.66 | 21.4 % | 19.0 % | 5.0 | 25 |
| bank debt sculpted to DSCR 1.25 | 7.44 | 4.75 | 2.17 | 2.17 | 2.18 | 22.3 % | 19.9 % | 4.5 | 25 |
| vendor finance + preference shares 12 % | 8.12 | 2.11 | 2.07 | 1.55 | 1.55 | 25.3 % | 22.8 % | 5.5 | 25 |
| vendor finance + FDPSS grant GBP 0.4 M | 8.12 | 3.82 | 2.07 | 1.55 | 1.55 | 24.0 % | 21.6 % | 4.4 | 25 |
| vendor finance + heat-plant ESCo (buyout yr 10) | 5.42 | 3.78 | 2.13 | 2.05 | 2.05 | 23.3 % | 20.9 % | 4.4 | 10,25 |

## Stresses on the central scheme (supplier credit + plant asset finance, 1-yr holiday) at parity -10 %

| Stress | Project IRR real pre-tax | Project payback yr | DSCR yr 1 | min DSCR | Equity IRR nom. | Equity payback yr | Min price lender | Min price lender + equity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 15.2 % | 6.4 | 2.07 | 1.55 | 22.2 % | 4.8 | 1.243 | 1.243 |
| yield -15 % | 10.6 % | 8.6 | 1.29 | 1.17 | 13.7 % | 10.1 | 1.438 | 1.438 |
| capex +20 % | 12.4 % | 7.6 | 1.69 | 1.34 | 17.1 % | 6.7 | 1.353 | 1.353 |
| power +30 % | 13.0 % | 7.3 | 1.60 | 1.39 | 17.8 % | 6.4 | 1.333 | 1.333 |
| labour +20 % | 14.4 % | 6.7 | 1.89 | 1.52 | 20.5 % | 5.3 | 1.277 | 1.277 |
| CO2 GBP 0.10/kg | 14.7 % | 6.5 | 1.96 | 1.53 | 21.2 % | 5.1 | 1.263 | 1.263 |
| yield -15 % + capex +20 % | 8.3 % | 10.6 | 1.04 | 0.96 | 10.3 % | 12.6 | 1.568 | 1.568 |
