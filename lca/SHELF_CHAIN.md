# Soil-to-shelf boundary (BP15, 2026-10-07)

Functional unit: 1 kg of cucumber on a Central Belt supermarket shelf. Code: `shelf_chain.py` (run `python shelf_chain.py`).
Every stage has a tier; PLACEHOLDER rows need a quote.

| Chain | Stage | GBP/kg | Tier |
|---|---|---:|---|
| Import | CIF at the UK border (Spain 55 %, Netherlands 41 %, Morocco 4 % by tonnage, 2023-25) | 1.400 | sourced (Comtrade) |
| Import | Duty (EU 0 %, Morocco 0 %; third-country 12 %) | 0.000 | sourced (UK Trade Tariff 0707000520, queried 2026-10-07) |
| Import | Border SPS checks (BTOM low-risk) | 0.000 | secondary (GOV.UK BTOM Aug 2023); cucumber category to confirm |
| Import | Port, customs agent, haul to RDC (balance to the plan's 1.57) | 0.170 | derived, placeholder split |
| Import | Importer margin | 0 | placeholder (no figure found) |
| Import | Transit loss 3 % | 0.043 | proxy (Blaauw 2024, avocado) |
| **Import at the RDC** | | **1.613** | |
| UK | Ex-farm DEFRA wholesale (harvest-weighted) | 1.170 | sourced |
| UK | Packing | 0.100 | model |
| UK | Own haulage to RDC | 0.046 | model |
| UK | Marketing commission 14 % | 0.164 | secondary (BritFarmers) |
| **UK at the RDC** | | **1.480** | |
| Both | RDC to store and handling | 0.100 | placeholder |
| Both | Retail shrink | 0 | UK cucumber figure not found (US produce 4-6 %, IFPA 2023) |

Observed shelf price GBP 2.64/kg (99p per 0.375 kg cucumber, May 2026, secondary). Shelf minus RDC price is the downstream
retail margin plus store logistics: 2.64 - 1.61 = GBP 1.03/kg for the import, 2.64 - 1.48 = 1.16 for UK supply at wholesale.

## What it says
1. A UK grower paid the DEFRA wholesale price lands at the RDC at about GBP 1.48/kg, GBP 0.13 below the import at 1.61. The
   plan's GBP 1.57 contract price is the import at the RDC before transit loss, so a direct contract at 1.57 would sit
   inside the import's cost and above the UK wholesale chain.
2. Duty and border charges are zero for the origins that matter (EU, Morocco), so the import's disadvantage is freight and
   handling, not tariff. The 12 % third-country rate only matters for a new origin.
3. The differential-shrink case (shelf life) is not quantified: found WRAP/ECRLoss material says +1 day shelf life cuts
   retail waste by 42.8 % (ECRLoss) and shrink-wrap cuts cucumber retail spoilage by about 4.8 % (Trellis summary).
   Neither gives a UK local-versus-import difference. Left at zero, which favours the import.
4. Carbon by stage exists only for avocado (`data/chain_stages.csv`); a cucumber carbon chain by origin is not built.
   The farm-side carbon (0.41 kg CO2e/kg) is the study's value.

## Still needed
Forwarder quote for port + customs + haul; RDC to store haul; UK retailer shrink for cucumber (WRAP report); importer margin;
cucumber BTOM risk category (check the GB plant-health risk register).
