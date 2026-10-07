# Price evidence: UK glasshouse cucumber (BP5, started 2026-10-05)

Question: what price per kg can a Scottish glasshouse cucumber grower expect from a supermarket contract? The plan's
central case is GBP 1.57/kg (import parity: Comtrade CIF + haul to the RDC). The lead design needs at least
GBP 1.52/kg for a 10-year payback (`CAPEX_10M_DESIGN.md`).

Conversion: a standard UK cucumber weighs 0.30-0.40 kg; 0.375 kg is used, so 1p each = GBP 0.0267/kg. The weight
sources found are consumer guides; the EU/UNECE marketing-standard size classes are still to be cited.

## Official UK statistics (strongest evidence)

DEFRA Horticulture Statistics dataset, 25 Jun 2026 (`data/hort-dataset-25-20260625.ods`), Tables 17-20, cucumbers:

| | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| Average farm-gate price, GBP/t (Table 18) | 879 | 1,146 | 937 | 1,146 | 955 |
| Marketed yield, t/ha (Table 17) | 522 | 500 | 500 | 500 | 510 |
| Planted area, ha | 111 | 90 | 103 | 106 | 100 |
| Home production marketed, kt | 57.9 | 45.0 | 51.5 | 53.0 | 51.0 |
| Imports, kt / GBP M (Tables 19-20) | 169 / 156 | 201 / 247 | 181 / 250 | 191 / 263 | 203 / 295 |
| Import unit value, GBP/kg | 0.92 | 1.23 | 1.38 | 1.37 | 1.46 |

- **UK growers were paid GBP 1.01/kg on average in 2023-25** (GBP 1.01 over 2021-25 too). This is the number a lender
  will use.
- **Imports land at GBP 1.37-1.46/kg** before UK haulage; the study's GBP 1.57 adds haul to the RDC.
- UK production is about 20 % of supply (51 of ~254 kt). Consumption is about 3.7 kg per person per year (254 kt over
  ~69 M people).
- UK average marketed yield is 50-52 kg/m2 (BP6 evidence). The model's 57.7 kg/m2 at Stranraer is 11-15 % above the
  UK average. Modern high-wire houses beat the older Lea Valley stock, but a lender will test it.

## Evidence found (other public sources)

| Level | Value | Per kg (0.375 kg) | Date | Source |
|---|---|---:|---|---|
| UK retail shelf, standard cucumber | 99p each (Tesco, Sainsbury's); small 70p | 2.64 | May 2026 | price comparison sites (allsupers.co.uk, trolley.co.uk), secondary |
| UK retail shelf, own label | 80p each average | 2.13 | May 2023 | The Grocer KVI tracker (15 May 2023) |
| UK wholesale, normal season | ~40p each | 1.07 | 2023 | Lee Stiles, Lea Valley Growers Association, in The Grocer (15 May 2023) |
| UK wholesale, glut | 16p each ("not even worth the transport") | 0.43 | May 2023 | same |
| UK cost of production (Lea Valley) | ~30p each | 0.80 | 2023 | same |
| UK cost of production (British Growers) | 25p each (2021), heading for 70p at 2022 gas prices | 0.67 / 1.87 | Mar 2022 | British Growers via Reuters (31 Mar 2022) |
| UK wholesale (DEFRA weekly, harvest-weighted) | GBP 1.17/kg | 1.17 | 2023-26 | DEFRA wholesale prices (`data/defra_wholesale_prices.csv`) |
| UK wholesale, trade guide | GBP 1.20-2.00/kg | 1.20-2.00 | 2026 | BritFarmers 'UK Route to Market 2026' (trade guide, secondary) |
| Spain, producer (paid to grower at the packhouse) | EUR 1.11/kg, highest ever; retail EUR 1.95/kg | 0.95 | 2025/26 season | Andalusian Prices and Markets Observatory, via Hortidaily (24 Sep 2026) |
| Netherlands, producer | EUR 1.00-1.20/kg, peaks > EUR 1.70; Nov 2025 EUR 0.65 | 0.86-1.03 | 2025 | Hortidaily / Rabobank market reviews (secondary summary; primary auction series to fetch) |
| Import parity (plan) | CIF + haul to Central Belt RDC | 1.57 | 2023-25 | Comtrade, `data/imports_monthly.csv` |

Contract terms: supermarket contracts set price by formula (fixed, index-linked or cost-plus) with 14-60-day payment
terms (BritFarmers 2026). Lea Valley growers report costs up 23 % while returns rose 0.8 % (FPJ). Retailers did not
pass lower 2024 gas prices back to growers (FPJ, 26 Jan 2024).

## What it says

1. **Grower-gate prices cluster at GBP 0.9-1.2/kg.** UK wholesale is GBP 1.07-1.17 in a normal season. Spanish and
   Dutch producer prices are GBP 0.86-1.03, and the Spanish figure was a record high.
2. **GBP 1.57/kg is not a grower price.** It is what an imported cucumber costs the UK *at the RDC*: farm price plus
   packing, freight, exporter and importer margin. The plan assumes that a direct contract captures all of that. No
   public source shows a UK grower being paid it.
3. **Retail-to-grower ratio.** In Spain the grower gets 57 % of retail (1.11 / 1.95). Applied to the UK shelf price of
   GBP 2.64/kg, that gives about GBP 1.50/kg. It is an analogy across markets, not evidence, but it shows a
   GBP 1.4-1.5 contract is not out of reach for a premium, local, low-carbon line. It needs a buyer's word.
4. **Bank base case.** On this evidence a lender would underwrite about **GBP 1.00-1.20/kg**: the official UK
   farm-gate average (GBP 1.01, DEFRA 2023-25) up to the wholesale level, with a contract above that as upside. At that price the lead design does not pay back (minimum
   GBP 1.52 for 10 years). The economics have to change, through cost, scale, a regional premium or grants, before a
   bank deal works on a defensible price.

## Still to get

- Dutch auction price series (primary), and Companies House accounts of UK salad growers (turnover / tonnes).
- A buyer's indication: a short request to retailers or packers for a 5-10-year Scottish low-carbon cucumber contract.

## Seasonality (2026-10-05)

DEFRA wholesale (2023-26) vs import CIF (Comtrade 2023-25) by month, against the lead design's harvest share (light-led,
one-month lag):

- Imports run at 14-19 kt a month all year; **44 % arrive Nov-Mar**, when DEFRA has only 2-7 UK price observations a
  month (vs 12-14 in summer).
- Winter CIF is GBP 1.46-1.55/kg against GBP 1.26-1.44 in summer, a premium of about GBP 0.10-0.25/kg.
- The unlit lead design sells only **12 % of its output Nov-Mar**. Its harvest-weighted UK price (GBP 1.17) is slightly
  below the simple annual mean (GBP 1.19).
- Taking the winter window needs supplementary lighting: BP13 step 6, a lit winter crop case.

## Highlands screen (2026-10-05, `bplan_highlands.py`, results/bplan/highlands.json)

The same 2.9 ha design, with heat pump and store re-sized by the LP at each site (track B, location only):

| Site | Lat | Yield kg/m2 | Heat kWh/m2 | Capex GBP M | Cost GBP/kg | kg CO2e/kg | Uplift GBP/kg | Payback at premium | Turbine developer margin GBP/MWh |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Stranraer | 54.9 | 57.7 | 467 | 9.90 | 0.987 | 0.41 | 0 | 8.8 | +2.4 |
| Moray coast (Roseisle) | 57.7 | 54.4 | 525 | 11.02 | 1.116 | 0.52 | 0.039 | 11.7 | -0.3 |
| Invergordon | 57.7 | 52.6 | 538 | 11.30 | 1.186 | 0.63 | 0.040 | 13.5 | -21.1 |
| Inverness (Allanfearn) | 57.5 | 49.3 | 558 | 11.47 | 1.253 | 0.65 | 0.035 | 16.4 | -3.2 |

The Highland sites lose on every target.
- Less light means 6-15 % less yield.
- Colder winters mean 12-19 % more heat, so a bigger heat pump and store, and capex over GBP 10 M.
- The wind at these points (6.8-7.9 m/s) is lower than at Stranraer (8.5 m/s).
- The regional price uplift is only about GBP 0.04/kg, even capturing half the retailer's haul and the whole Highland
  market (~1.7 kt/yr).
- Carbon goes over 0.5.

Exposed far-north or island sites would have more wind, but the light and heat penalties would be larger still.
Stranraer stays the lead location. The south-west's mild, bright climate is worth more than cheaper land or a
regional uplift.

## Premium for local / low-carbon (BP5, 2026-10-07, desk search; excerpts only)

Question: does a Scottish, low-carbon label lift the price a grower is paid? Evidence found is consumer willingness-to-pay
(WTP), not grower contract prices, and mostly not UK:

| Finding | Value | Source |
|---|---|---|
| Stated WTP for locally grown produce, South Carolina survey | +27 % (animal products +23 %) | ageconsearch.umn.edu/record/6815 (survey, US) |
| WTP for locally grown, review in HortScience | 29.5 % | journals.ashs.org HortScience 60(12) (2025), review figure |
| Sustainable goods, 2024 global consumer survey | +9.7 % average | PwC Voice of the Consumer 2024 |
| WTP for healthier food, 26 experiments | +5.6 % to +91.5 % (mean 30.7 %) | PMC10909406 (review) |
| Field experiment, local label | no positive effect on WTP | Univ. Delaware working paper (udspace.udel.edu), null result |

Reading: stated premiums of 10-30 % are common in surveys and do not hold in a revealed-preference field test. None of it
shows what a UK supermarket pays a grower. BritFarmers (2026) says contracts pay stability, not a premium (see BP14).
**Decision for the plan:** no regional or low-carbon price premium in the central case. It stays a labelled upside
scenario, and the only valid evidence is a buyer's written indication (outstanding, needs the user to contact retailers).
Still open from this file: Dutch auction primary series, Companies House accounts, a buyer's indication.

## UK commercial yield evidence (BP6, 2026-10-07)

DEFRA Horticulture Statistics 25 Jun 2026, Table 17 (marketed yield per planted ha), Table 18 (farm-gate price), both
read from `data/hort-dataset-25-20260625.ods`:

| | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cucumber yield, kg/m2 | 54.0 | 52.0 | 53.1 | 52.2 | 50.0 | 50.0 | 50.0 | 51.0 |
| Tomato (all types, heated) yield, kg/m2 | 36.4 | 35.5 | 34.6 | 35.3 | 37.3 | 36.5 | 36.0 | 35.0 |
| Tomato farm-gate, GBP/kg | 1.09 | 1.38 | 1.35 | 1.82 | 1.41 | 1.74 | 1.77 | 1.69 |

(Column years checked against the ODS header, 1985-2025.)

- UK average cucumber yield is 50-54 kg/m2, flat for eight years. The model's 57.7 kg/m2 at Stranraer (unlit) is 11-15 %
  above it; the capped basis used in the plan (CBS light-anchor correction) is lower.
- UK average tomato yield is 35-37 kg/m2, an average over round, vine, plum and cherry on mixed-age glass. It is not a
  test of a new high-wire house. The crop model's round-tomato yield (CBS NL basis) sits far above this, so a lender will
  want a grower reference (AHDB, a named UK high-tech grower) before accepting it. Not found online yet.
- Tomato farm-gate is GBP 1.4-1.8/kg, well above cucumber's GBP 1.0, which is why tomato looks attractive on price and why the
  mix matters (see BP34 results).
