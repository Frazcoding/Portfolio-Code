# Financing model (BP33/BP37e), lit lead 2.9 ha, 150 umol, 2 PPA turbines

Capex GBP 11.45 M, yield 93.0 kg/m2, carbon 0.37 kg CO2e/kg (0.89 with the CO2 dose counted), import parity GBP 1.555/kg. Nominal (CPI 2 %), post-tax (CT 25 %, full expensing). Prices are real (year-0 money), CPI-indexed. Inputs and tiers in the finance.py docstring.

## Minimum real price (GBP/kg)

| Scheme | Lender (DSCR >= 1.25) | Lender + equity 12 % nominal |
|---|---:|---:|
| all equity (benchmark) | - | 1.188 |
| supplier credit + plant asset finance, 1-yr holiday | 1.237 | 1.237 |
| supplier credit + plant asset finance, no holiday | 1.514 | 1.514 |
| bank debt sculpted to DSCR 1.25 | 1.190 | 1.19 |
| vendor finance + preference shares 12 % | 1.237 | 1.237 |
| vendor finance + FDPSS grant GBP 0.4 M | 1.237 | 1.237 |
| vendor finance + heat-plant ESCo (buyout yr 10) | 1.257 | 1.257 |

All-equity row: equity hurdle 10.2 % nominal post-tax (8 % real).

## Price: lender GBP 1.01

| Scheme | Debt GBP M | Equity GBP M | DSCR yr 1 | min DSCR | min DSCR yr 2+ | Equity IRR nom. | real | Payback yr | Negative equity years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| all equity (benchmark) | 0.00 | 11.77 | - | - | - | 5.7 % | 3.7 % | 13.8 | 15,20,25 |
| supplier credit + plant asset finance, 1-yr holiday | 8.12 | 4.34 | 0.45 | 0.45 | 0.69 | 5.6 % | 3.5 % | 18.4 | 1,2,3,4,5,6,7,8,10,15,20,25 |
| supplier credit + plant asset finance, no holiday | 8.12 | 4.31 | 0.22 | 0.22 | 0.74 | 5.6 % | 3.5 % | 18.3 | 1,2,3,4,5,6,10,15,20,25 |
| bank debt sculpted to DSCR 1.25 | 6.18 | 5.96 | 0.55 | 0.55 | 1.25 | 5.5 % | 3.5 % | 18.6 | 1,10,15,20,25 |
| vendor finance + preference shares 12 % | 8.12 | 2.17 | 0.45 | 0.45 | 0.69 | 4.2 % | 2.1 % | 27.7 | 1,2,3,4,5,6,7,8,10,15,20,25 |
| vendor finance + FDPSS grant GBP 0.4 M | 8.12 | 3.94 | 0.45 | 0.45 | 0.69 | 6.0 % | 3.9 % | 18.1 | 1,2,3,4,5,6,7,8,10,15,20,25 |
| vendor finance + heat-plant ESCo (buyout yr 10) | 5.42 | 3.87 | -0.43 | -0.43 | 0.57 | 5.3 % | 3.3 % | 20.2 | 1,2,3,4,5,6,10,15,20,25 |

## Price: lender GBP 1.10

| Scheme | Debt GBP M | Equity GBP M | DSCR yr 1 | min DSCR | min DSCR yr 2+ | Equity IRR nom. | real | Payback yr | Negative equity years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| all equity (benchmark) | 0.00 | 11.77 | - | - | - | 8.1 % | 5.9 % | 11.2 | 15,25 |
| supplier credit + plant asset finance, 1-yr holiday | 8.12 | 4.34 | 0.84 | 0.84 | 0.91 | 9.1 % | 7.0 % | 13.7 | 15,25 |
| supplier credit + plant asset finance, no holiday | 8.12 | 4.31 | 0.4 | 0.4 | 0.98 | 9.0 % | 6.9 % | 13.5 | 1,15,25 |
| bank debt sculpted to DSCR 1.25 | 7.44 | 4.79 | 0.85 | 0.85 | 1.32 | 9.2 % | 7.0 % | 15.6 | 10,15,25 |
| vendor finance + preference shares 12 % | 8.12 | 2.17 | 0.84 | 0.84 | 0.91 | 8.9 % | 6.7 % | 18.6 | 15,25 |
| vendor finance + FDPSS grant GBP 0.4 M | 8.12 | 3.94 | 0.84 | 0.84 | 0.91 | 9.7 % | 7.5 % | 13.3 | 15,25 |
| vendor finance + heat-plant ESCo (buyout yr 10) | 5.42 | 3.87 | 0.18 | 0.18 | 0.92 | 9.0 % | 6.9 % | 15.6 | 1,10,15,25 |

## Price: lender GBP 1.20

| Scheme | Debt GBP M | Equity GBP M | DSCR yr 1 | min DSCR | min DSCR yr 2+ | Equity IRR nom. | real | Payback yr | Negative equity years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| all equity (benchmark) | 0.00 | 11.77 | - | - | - | 10.4 % | 8.3 % | 8.8 | 25 |
| supplier credit + plant asset finance, 1-yr holiday | 8.12 | 4.34 | 1.27 | 1.16 | 1.16 | 13.1 % | 10.9 % | 10.4 | 25 |
| supplier credit + plant asset finance, no holiday | 8.12 | 4.31 | 0.61 | 0.61 | 1.24 | 12.9 % | 10.7 % | 10.3 | 1,25 |
| bank debt sculpted to DSCR 1.25 | 7.44 | 4.80 | 1.29 | 1.29 | 1.61 | 13.3 % | 11.1 % | 8.0 | 15,25 |
| vendor finance + preference shares 12 % | 8.12 | 2.17 | 1.27 | 1.16 | 1.16 | 13.5 % | 11.3 % | 13.1 | 25 |
| vendor finance + FDPSS grant GBP 0.4 M | 8.12 | 3.94 | 1.27 | 1.16 | 1.16 | 14.0 % | 11.8 % | 10.1 | 25 |
| vendor finance + heat-plant ESCo (buyout yr 10) | 5.42 | 3.87 | 0.86 | 0.86 | 1.31 | 13.4 % | 11.2 % | 8.7 | 10,25 |

## Price: sponsor parity -5%

| Scheme | Debt GBP M | Equity GBP M | DSCR yr 1 | min DSCR | min DSCR yr 2+ | Equity IRR nom. | real | Payback yr | Negative equity years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| all equity (benchmark) | 0.00 | 11.77 | - | - | - | 16.3 % | 14.0 % | 6.0 | 25 |
| supplier credit + plant asset finance, 1-yr holiday | 8.12 | 4.34 | 2.46 | 1.74 | 1.74 | 25.5 % | 23.0 % | 4.0 | 25 |
| supplier credit + plant asset finance, no holiday | 8.12 | 4.31 | 1.17 | 1.17 | 1.85 | 24.4 % | 22.0 % | 4.3 | 25 |
| bank debt sculpted to DSCR 1.25 | 7.44 | 4.83 | 2.51 | 2.4 | 2.4 | 25.5 % | 23.0 % | 3.9 | 25 |
| vendor finance + preference shares 12 % | 8.12 | 2.17 | 2.46 | 1.74 | 1.74 | 29.7 % | 27.1 % | 4.5 | 25 |
| vendor finance + FDPSS grant GBP 0.4 M | 8.12 | 3.94 | 2.46 | 1.68 | 1.68 | 27.6 % | 25.1 % | 3.7 | 25 |
| vendor finance + heat-plant ESCo (buyout yr 10) | 5.42 | 3.87 | 2.75 | 2.27 | 2.27 | 27.0 % | 24.6 % | 3.7 | 10,25 |

## Price: sponsor parity -10%

| Scheme | Debt GBP M | Equity GBP M | DSCR yr 1 | min DSCR | min DSCR yr 2+ | Equity IRR nom. | real | Payback yr | Negative equity years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| all equity (benchmark) | 0.00 | 11.77 | - | - | - | 14.7 % | 12.5 % | 6.6 | 25 |
| supplier credit + plant asset finance, 1-yr holiday | 8.12 | 4.34 | 2.13 | 1.56 | 1.56 | 21.8 % | 19.4 % | 4.9 | 25 |
| supplier credit + plant asset finance, no holiday | 8.12 | 4.31 | 1.01 | 1.01 | 1.67 | 21.1 % | 18.7 % | 5.1 | 25 |
| bank debt sculpted to DSCR 1.25 | 7.44 | 4.82 | 2.17 | 2.17 | 2.18 | 22.0 % | 19.6 % | 4.6 | 25 |
| vendor finance + preference shares 12 % | 8.12 | 2.17 | 2.13 | 1.56 | 1.56 | 24.8 % | 22.3 % | 5.7 | 25 |
| vendor finance + FDPSS grant GBP 0.4 M | 8.12 | 3.94 | 2.13 | 1.56 | 1.56 | 23.6 % | 21.1 % | 4.5 | 25 |
| vendor finance + heat-plant ESCo (buyout yr 10) | 5.42 | 3.87 | 2.22 | 2.09 | 2.09 | 23.0 % | 20.6 % | 4.4 | 10,25 |

## Stresses on the central scheme (supplier credit + plant asset finance, 1-yr holiday) at parity -10 %

| Stress | Project IRR real pre-tax | Project payback yr | DSCR yr 1 | min DSCR | Equity IRR nom. | Equity payback yr | Min price lender | Min price lender + equity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 15.2 % | 6.4 | 2.13 | 1.56 | 21.8 % | 4.9 | 1.237 | 1.237 |
| yield -15 % | 10.6 % | 8.6 | 1.32 | 1.18 | 13.6 % | 10.1 | 1.431 | 1.431 |
| capex +20 % | 12.4 % | 7.6 | 1.73 | 1.36 | 16.9 % | 6.8 | 1.346 | 1.346 |
| power +30 % | 13.0 % | 7.3 | 1.64 | 1.40 | 17.5 % | 6.4 | 1.327 | 1.327 |
| labour +20 % | 14.4 % | 6.7 | 1.94 | 1.53 | 20.2 % | 5.3 | 1.271 | 1.271 |
| CO2 GBP 0.10/kg | 14.7 % | 6.5 | 2.01 | 1.52 | 20.8 % | 5.1 | 1.258 | 1.258 |
| yield -15 % + capex +20 % | 8.3 % | 10.6 | 1.07 | 0.97 | 10.2 % | 12.6 | 1.560 | 1.56 |
