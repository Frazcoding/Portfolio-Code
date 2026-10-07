# Design constraints: year-round, low-carbon, investable (user, 2026-10-05)

Question: how can we grow crops in the UK year-round, as low-carbon and as cheaply as possible, to improve food
security and lower prices, while breaking even soon enough to attract investors?

Objective: minimise payback (equivalently, maximise margin per pound of capex) subject to the constraints below.
Optimiser variables: location, area (at most 5 ha), lighting (intensity, hours, daily light target), glazing,
screens, heat pump and store, grid cap, crop. Stage 1 crops: cucumber and tomato. Stage 2, once inputs are sourced
(BP10): leafy greens and strawberry.

Coupling, per m2 and year: yield x (price - cash cost per kg) >= ~1.1 x capex per m2 / payback years. So production
cost, opex and yield targets follow from price, capex and payback. They are derived and reported, not set
independently. The surrogate model (BP34) maps the design variables to all of them.

| # | Constraint | Value | Status |
|---|---|---|---|
| 1 | Carbon, soil to supermarket depot | <= 1.00 kg CO2e/kg search ceiling (user 2026-10-06, was 0.50); high-carbon designs are not taken, carbon reported with every ranking | set |
| 2 | Capex (incl. development, contingency, connection, lighting) | < GBP 20.0 M per phase (user 2026-10-06, was 10.0; owned turbines are a separate SPV, not in the cap); scale-up in phases funded from cash (user 2026-10-05); peak funding reported | set |
| 3 | Payback, simple | <= 10 yr at the evidence price: DEFRA wholesale of the product x farm-gate/wholesale 0.85 (cucumber GBP 1.01/kg). Target: Dutch farm-gate level GBP 0.86-1.03/kg (user 2026-10-06) | set |
| 4 | Full production cost, packed ex-farm (8 %) | derived from #3: reported with the margin to the price | derived |
| 5 | Cash opex | <= revenue - capex / 10, reported per design | derived |
| 6 | Year-round supply | no month below 60 % of the mean month's output | set |
| 7 | Yield | floor from #3 (reported); ceiling = best published commercial yield at the same lighting level | set (ceiling to source) |
| 8 | Downside | payback <= 12 yr with price -10 % and yield -10 % together | set |
| 9 | Heat security | 0 unmet hours in the 2010 winter; 48 h plant-failure cover | set |
| 10 | Placeholder share of capex | <= 25 % before the investor pack | set |
| 11 | Beat imports | ex-farm price below the import landed price in every month | set |
| 12 | Grid connection | LP choice, priced on the SPEN steps; <= 1 MVA preferred | set |
| 13 | Renewable electricity | >= 80 % of use from private-wire or owned renewables | set |
| 14 | Light spill | blackout screens on all lit area (also night insulation in the heat model) | set |
| 15 | Labour | hours per kg at a sourced benchmark; FTE reported | set |
| 16 | Water | model rain capture vs irrigation demand; aim for 100 % on-site | set (to model) |
| 17 | Location and area | unconstrained location (optimiser); area <= 5 ha | set |
| 18 | Debt | company-only, no personal guarantee | set |
| 19 | Control | founder keeps > 50 % of voting shares | set |
| 20 | Lender test | DSCR >= 1.30 every year, lender case | set |
| 21 | Outside equity | preference-share / minority return >= 12 % nominal post-tax | set |

## Lit-crop evidence for the yield ceiling (#7) and lighting inputs (2026-10-05)

| Item | Value | Source |
|---|---|---|
| Cucumber, unlit, NL average | 65 kg/m2 | CBS (crops.py; crop model anchor) |
| Cucumber, UK average (mostly unlit) | 50-52 kg/m2 | DEFRA Horticulture Statistics 2026, Table 17 |
| Cucumber, lit, top Dutch growers | 105-108 kg/m2/yr | WUR (F. Kempkes) via Hortidaily, 2018 Winter Light Greenhouse report |
| Cucumber, WUR Winter Light Greenhouse (research) | 122 kg/m2 (42 harvest weeks; 425 g fruit) | same |
| Cucumber, potential with 210 umol/m2/s for 3,000 h, 3 plantings | 147 kg/m2 | Wageningen PPO, 'Horticultural lighting in the Netherlands: new developments' (via ResearchGate) |
| Tomato, NL average unlit / lit | ~75 / > 90 kg/m2 | secondary trade summary: to confirm (KWIN) |
| Tomato, LED top 104 umol + 2 rows interlighting | > 100 kg/m2 | GreenQ Improvement Centre via Hortidaily |
| LED fixture efficacy | 2.5-2.8 umol/J (white+red), 3.0 (blue+red); limits 3.4 / 4.1; 2025-26 toplights 2.6-3.6 | Kusuma, Pattison & Bugbee (2020) Horticulture Research 7:56; Arize Element product data |
| LED fixture cost | USD 1,000-3,000 per kW (2014-19), since fallen; installed systems USD 50-200+/m2 | Kusuma et al. (2020); market summary (secondary): quote needed |

Working ceiling for #7: lit cucumber 105 kg/m2 (top commercial practice), unlit 65 kg/m2 scaled by site light.
Model results above the ceiling are capped.

Rough check before modelling (my arithmetic, not a result): 200 umol/m2/s at 3.0 umol/J is 67 W/m2. At ~3,000 h that
is 200 kWh/m2/yr, ~GBP 18/m2 at GBP 90/MWh. Capex is ~GBP 80-100/m2 with installation. Going from ~58 to ~100 kg/m2
adds ~GBP 42/m2 of revenue at GBP 1.01/kg, and the light heat offsets some heat-pump power. So lighting looks
plausibly positive at private-wire prices. The surrogate study (BP34) tests this properly.

## Levers built in for the planned run (2026-10-06, `bplan_yearround.py`)

- Products: cucumber; round, vine, plum and cherry tomato (DEFRA variety prices; yield/labour factors in PRODUCTS).
- Lighting: top + interlighting, light window, daily light target, and **wind-following** control (lights only while
  the turbine runs above 0.15 / 0.30 per unit). New `config.Lighting.allow_hourly`, in both simulators; tests PASS.
- LED rate GBP 515/kW (RVO EG 2026 cap GBP 900, practice ~GBP 310); was GBP 1,170 (2014-19).
- By-product CO2 at GBP 0.06/kg next to a fermentation/AD source (Stranraer Creamery, Girvan distilleries), vs bought
  GBP 0.20. This is Thanet-style recovery without combustion.
- Bulk packing x0.5 where the product allows it; pipe-rail 2.25 / 4.5 m/m2; water basin sized and costed.
- Phasing: modules added from cash, up to 10 ha; shared site costs 5 % (placeholder).
- Grid tariff re-basing dropped: the model already uses GBP 173/MWh (DESNZ Q1 2026 non-domestic average 24.1 p incl.
  CCL; manufacturing 17.5 p excl. CCL), so only ~1 p/kg was available.
