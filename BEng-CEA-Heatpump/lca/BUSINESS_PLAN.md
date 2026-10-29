> **Superseded 2026-10-07.** The business plan is now the Claude Doc https://claude.ai/code/artifact/cf65b986-f2ca-4a1a-a924-13c38a97152b (lead: GBP 10 M, 2.9 ha, CO2 GBP 0.25/kg). The numbers below are the 1 ha concept pack at CO2 GBP 0.20 and are kept as history.

# Business plan: preparation pack (started 2026-10-05)

Working document for the heat-pump glasshouse business plan. It holds the settled design, the verified numbers, the
figures and the diversification strategy. It is not yet the plan itself. Every number traces to a script and a results
file. Inputs follow the study rule: sourced or standard-based, or labelled as a placeholder.

Rebuild everything in this pack (from `lca/`):

```
python cashflow.py A B && python costing_report.py      # full costing (~10 min)
CEA_TRACK=B python bplan_perf.py; CEA_TRACK=A python bplan_perf.py   # monthly performance (~1 min)
python bplan_verify.py                                  # independent checks -> results/bplan/VERIFICATION.md
python bplan_diversify.py                               # diversification screen + thermal campus
python bplan_figures.py                                 # figures -> ../figures/business_plan/
```

## 1. Decisions (user, 2026-10-05)

- **Lead case: track B.** A standalone glasshouse with its own R717 heat pump and an owned 2.5 MW turbine, cucumber,
  at the Stranraer location. Track A (industrial waste heat) is the option.
  - Why B leads: B beats A on cash flow at every shortlisted site. The waste-heat pipe (£0.5 M) and the full-standby
    heat pump cost more than the cheap heat saves once own-wind power is available.
  - B also does not depend on one host operator.
- **Heat pump:** both rules are shown.
  - LP-sized + hot-water store, floored to the 2010 winter. This is the recommended central case.
  - Full standby at design load.
- **Audience:** investors and banks at 8 % (headline), and public funders at 3.5 % (Green Book), as a second section.
- **Diversification in scope:** multi-zone thermal campus, higher-value variants, winter soft fruit, citrus/avocado
  niche (section 6).

## 2. Settled design (lead and option)

| | Track B lead: cucumber | Track B: tomato | Track A option: cucumber |
|---|---|---|---|
| Location | Stranraer (The Creamery site, used as a location only) | Girvan | Stranraer (Creamery waste heat, 51 % of heat) |
| Area | 1.0 ha | 1.15 ha | 1.1 ha |
| Structure | 4 spans x 15.4 m, 162 m long, gutter 4.64 m, roof pitch 12.2°, 3 ridges per span | 2 spans x 18.2 m, gutter 4.98 m, pitch 16.2° | 2 spans x 17.2 m, gutter 4.76 m, pitch 15.7° |
| Glazing | double AR glass, ridges N-S, no insulated north wall | same | same |
| Heat pump | R717 air source, design load 1.25 MW; LP-sized 69 % + store | 1.36 MW; LP 61 % + store | 1.48 MW water source; LP 80 % + store |
| Climate | RH 90 %, heat-recovery dehumidification, CO2 enrichment | same | RH 85 % |
| Electricity | owned 2.5 MW turbine (89 % of greenhouse power), grid backup | same | same |
| Yield | 54.6 kg/m2 (546 t/yr) | 43.8 kg/m2 (504 t/yr) | 59.9 kg/m2 (661 t/yr) |
| Heat / electricity | 284 / 100 kWh/m2/yr, SCOP 3.21 | 172 / 60, SCOP 3.51 | 344 / 65, SCOP 3.23 |
| Capex (LP / standby) | £4.07 M (£407/m2) / £4.50 M | £4.65 M / £5.21 M | £5.48 M / £5.74 M |
| Carbon | 0.30 kg CO2e/kg (imports 0.81) | 0.36 (imports 1.30) | 0.26 |

Status: concept design (Gate B). Structural design, RFQ quotes (about 46 % of structure items are placeholders) and the
EN 13031-1 detailed check come at Gate C.

## 3. The numbers (verified)

Full tables: `results/costing/FULL_COSTING.md`. Checks: `results/bplan/VERIFICATION.md` (13 pass, 3 flagged; below).

**Headline (track B cucumber, Stranraer, LP heat pump):**

| | 8 % (commercial) | 3.5 % (Green Book) |
|---|---:|---:|
| Levelised cost | £1.58/kg | £1.32/kg |
| Price received (DEFRA UK wholesale, harvest-weighted) | £1.17/kg | £1.17/kg |
| Import parity (CIF + haul to RDC) | £1.57/kg | £1.57/kg |
| NPV, greenhouse alone, at DEFRA price | -£2.49 M | -£1.46 M |
| NPV at an import-parity contract price | -£0.2 M (IRR 7.5 %) | +£2.3 M |
| NPV with free CO2, yield +18 %, capex -20 % | +£0.2 M (IRR 8.7 %) | +£2.5 M |
| NPV with all of the above | +£3.0 M (IRR 16.5 %) | +£7.0 M |
| Turbine as its own business | -£1.47 M (IRR 4.9 %) | +£1.01 M |
| Greenhouse + turbine (capex £10.0 M) | -£3.96 M (IRR 3.1 %) | -£0.45 M |

**What the plan has to say plainly:**

1. **Not profitable at today's UK wholesale prices,** on either track, for either crop. Tomato is further off than
   cucumber, with a break-even of £1.96-1.98/kg at 8 % against a price of £1.23.
2. **The energy system is nearly optimised. The capital is where design can still cut cost.**
   - Energy is £0.10/kg of a £1.58/kg cost. Heat in total, including the heat pump's capital, is £0.31-0.36/kg. A
     peak-boiler test adds only about 1 p/kg over the LP-sized heat pump with store.
   - Capital recovery is £0.70/kg. The largest items are the residual systems lump (£0.15), the heat pump (£0.14) and
     the double AR glass (£0.13), and the design was optimised at 3.5 %, not 8 %.
   - Design-to-cost, labour and CO2 strategy (HANDOFF BP13) are estimated at £0.15-0.30/kg (to be proven).
   - Every design is below import parity at 3.5 % and beats imports on carbon by a factor of 2.5 to 4.
3. **The route to viability** (figure bp04) needs both of these:
   - a contract price near import parity (a "Scottish, low-carbon" supply contract rather than the wholesale market);
   - at least one of: free distillery CO2, supplier quotes about 20 % under the placeholders, or the GreenLight yield
     response.

   The evidence for each is the next research step (section 7).
4. **At 8 % the turbine does not pay for itself either.** Present it as the energy route, not as a profit centre.
   Private-wire PPA (+£0.04-0.06/kg) is the fallback.

**Verification summary** (`bplan_verify.py`, plus the regression tests, all PASS):
- Cash flow: NPV, IRR, capex totals, revenue and steady-year identities, and levelised cost are re-derived
  independently. Differences are below £1.
- Energy: heat-pump COP is 23-45 % of Carnot (winter 38-43 %), at a supply of 46-52 °C and a source of 5-13 °C.
  That is realistic to pessimistic, never optimistic. Unmet heat is 32-131 h/yr at design capacity.
- Heat demand is within ±15 % of GreenLight (0.95 and 1.15 in two independent checks; monthly r 0.98-1.00).
- **Defect found and fixed:** the winter tomato price had been back-filled from a single DEFRA March observation
  (£3.00/kg). It now uses the import CIF price for months with no UK market. Tomato revenue fell by £33-70k/yr and
  NPV by about £0.6-1.3 M. Cucumber is unchanged.
- **Flag (evidence needed):** modelled yields are 0.89-1.03 times the Dutch national average (CBS). They are
  physically consistent, but investors will ask for UK commercial evidence (AHDB, growers). Yield -15 % costs £0.9 M
  of NPV at 8 %.
- **Flag (do not quote):** the thesis README headline of a mean COP of 4.29 at an 80 °C supply is about 97 % of the
  Carnot limit (4.41), which is not physically achievable. Use the study's SCOP of 3.0-3.5. The thesis numbers need
  their own review.
- **Minor inconsistency:** the greenhouse buys turbine power at its 3.5 % levelised cost even in the 8 % case. The
  effect is below £0.02/kg.

## 4. Figures (`../figures/business_plan/`, repo visual standard)

| File | Shows |
|---|---|
| bp01_cost_vs_price | Levelised cost of every finalist at 8 % and 3.5 % (LP vs standby) against DEFRA price and import parity |
| bp02_cost_buildup_08 / _035 | What a kilo costs: capital, energy, labour, inputs, packing/haulage, overheads vs price |
| bp03_capex | Capex per m2 by component, both tracks, both heat-pump rules |
| bp04_cumulative_B_cucumber | Route to viability: cumulative discounted cash flow under the four price/lever scenarios |
| bp05_sensitivity_B_cucumber_008 / _0035 | NPV sensitivity |
| bp06_monthly_sales_price | Harvest by month against the UK and import price by month |
| bp07_energy_performance | Monthly heat supply, COP, inside/outside temperature, track B vs A |
| bp08_carbon | kg CO2e/kg of every finalist vs imports |
| bp09_diversify_margin_080 / _035 | Diversification screen: margin per m2 by product and structure |
| bp10_price_windows | UK supply windows vs import-priced months for berries, cherry tomato, salads |
| bp11_thermal_campus | Vertical-farm LED heat as the heat-pump source: heat share and COP |

## 5. What diversification can and cannot do

The screen (`bplan_diversify.py`, table `results/bplan/diversify_table.md`) prices each product per m2 on the same
basis as the cash flow, at the Stranraer location. It reproduces the lead cucumber cost within about 4 %, which is
its calibration check. It is a screen, not a design result.

| Product | Status of inputs | What the screen says |
|---|---|---|
| Cucumber, round tomato | model (verified) | the lead case; loses £29-39/m2/yr on new glass at 8 % |
| Vine tomato, cherry tomato | price sourced (DEFRA in season; winter months use the all-tomato CIF, HS 0702, which understates cherry); yield placeholder | £56-67/m2 revenue vs £48 for round; better, still negative on new glass |
| Sweet pepper | CBS yield scaled | worst: low yield at a mid price |
| Strawberry (two forced crops, unlit) | CBS yield (NL glass + tunnel), labour estimate | £55/m2 revenue; break-even on second-hand glass |
| Raspberry, blueberry | yields are estimates | high price, but 2-3 kg/m2 cannot pay for heated glass |
| Lettuce, baby leaf | estimates/placeholders | lettuce close to break-even on cheap structures; result hangs on head weight and cycles |
| Avocado, citrus | earlier study; import CIF £1.7-2.4/kg | about £2/m2 revenue against £30-80/m2 of cost: never viable as fruit |

Conclusions:

1. **Changing the crop moves the margin far less than the structure's capital does.** On the lead structure every
   product loses £14-44/m2/yr at 8 %. On second-hand or basic glass most products sit near break-even.
   - For diversification, the big lever is a cheaper second zone (basic glass, polycrub or second-hand glass, SAC/SRUC
     Table 11).
   - Cool crops also need a much smaller heat pump (berries about 20-60 kWh/m2 of heat against 284 for cucumber).
2. **Soft fruit: the money is in Oct-Jan, and the unlit schedule misses it.** Imported strawberry costs £6.0-7.9/kg CIF
   in Oct-Jan, against £3.2-3.8 in Mar-Apr (bp10). UK supply stops in December.
   - The unlit two-crop schedule (Apr-Jun and Sep-Nov) averages £5.26/kg. It breaks even only on second-hand glass.
   - A lit Oct-Jan crop is the one soft-fruit case worth modelling. It sells into a market priced at about £7/kg where
     UK growers are absent. Its LED capex and electricity at own-wind prices are the test. The earlier "LEDs never pay"
     finding was on vegetables, the older model and grid power.
   - Raspberry and blueberry imports (£7-8 and £5-6/kg) are cheaper than UK-grown in season (£10-14 and £10-12). The UK
     premium exists only in season, and yields of 2-3 kg/m2 cannot carry heated glass.
3. **Higher-value tomato is the cheapest change.** It uses the same house, heat pump and climate; only the variety,
   labour and packing differ. Its yield needs a source (KWIN-AGV) before it goes in the plan.
4. **The thermal campus is a modest bonus, not a driver** (bp11). A 500-1,000 m2 LED vertical farm per hectare of
   glass:
   - covers 23-38 % of the glasshouse heat;
   - raises the heat-pump COP from about 3.1 to 4.3 in winter;
   - but saves only 70-110 MWh/yr of heat-pump electricity, while its LEDs use 0.6-1.2 GWh/yr.
   
   Heating the whole glasshouse would need about 3,000 m2 of tiers and 3.5 GWh/yr of LED power. The real value runs the
   other way: the glasshouse is a free winter chiller for the farm or a cold store. So the campus is justified only if
   the vertical farm or cold store pays on its own.
5. **Citrus and avocado:** not a production line. At most a small showcase or retail line (potted citrus, yuzu or
   finger lime for chefs), with no sourced price yet. Include it only as a visitor or brand element, costed
   separately.

## 6. How to take diversification forward (proposed method)

Phase 1: screen (done today, first pass). Products x structures x discount rates, tiered inputs.

Phase 2: source the inputs that decide the ranking. These are cheap and come before any modelling.
- Cherry/vine tomato and mini-cucumber yields and labour (KWIN-AGV, AHDB).
- Strawberry: everbearer table-top yields under glass with and without LEDs, and picking rates (AHDB SF projects,
  NIAB, Dutch "teelt onder glas").
- Raspberry long-cane glasshouse yields per crop.
- Lettuce head weight and cycles per year, unlit, in Scotland.
- Winter import prices by month (Comtrade, being added: strawberry, raspberry, blueberry, lettuce, pepper, avocado).
- Contract prices for UK winter berries.

Phase 3: model the two candidates that survive phase 2, on the same verified toolchain.
- **Cool zone:** strawberry (and lettuce) with crop setpoints.
  - `crop_gh` crop parameters for strawberry.
  - `transp.py` coefficients for strawberry and lettuce.
  - Heat-pump sizing for the lower design lift.
  - Structure options from the SAC/SRUC anchors.
  - One sweep at the lead site only (big runs last).
- **Multi-zone campus:** warm house plus cool house on one heat pump with a shared hot-water store. Model
  simultaneous heating and cooling (cool-house summer cooling, packhouse cold store as the evaporator source) through
  the existing `finalist_lp.py` LP, which already sizes the heat pump and store.
- **Lit winter strawberry:** LED capex and electricity at turbine price vs the Dec-Mar import price. This is the one
  case with a plausible high-value window.

Phase 4: diversified cash flow in `cashflow.py`, with products as zones, to see whether a portfolio smooths the
monthly revenue (bp06 shows the summer trough) and the labour profile.

## 6b. Reducing initial expenditure (started 2026-10-05, HANDOFF BP13-BP17)

Day-one spend today: greenhouse £4.07M plus turbine £5.9M, a £10M project. First levers (lead design, design-search
basis; `results/bplan/capex_levers.log`):

| Option | Greenhouse capex (struct + heat) | Energy capex | £/kg at 8 % vs today |
|---|---:|---:|---:|
| Today: double AR glass, full-standby heat pump, owned turbine | £3.66M | £5.9M | 0 |
| Double AR, heat pump 69 % + electric peak boiler | £3.34M | £5.9M | -0.018 |
| **Single glass, heat pump 69 % + peak boiler** | £3.46M | £5.9M | **-0.055** (yield +14 %) |
| **Single glass, heat pump 69 % + peak boiler, private-wire PPA** | £3.46M | **£0** | +0.014 |

- Dropping the owned turbine for a private-wire PPA cuts day-one spend by about 64 % for about 1.4p/kg. It needs a
  wind farm next door: Girvan (16 large turbines within 3.1 km), not Stranraer.
- Glazing and heat-pump sizing have to be chosen together. Single glass lets in more light (yield +14 %) but needs
  74 % more heat, which only pays when a cheap peak boiler takes the top of the load.
- The boiler also replaces the expensive full-standby heat pump as the cold-year and outage backup.
- To be confirmed at the full costing basis. The capex scaling model (fixed / per-kW / per-m2 / per-perimeter, BP16)
  and the soil-to-shelf boundary (BP15) are next.

## 6c. Design under GBP 10 M (2026-10-05, `CAPEX_10M_DESIGN.md`)

2.9 ha, single glass, R717 heat pump 1.9 MW + 358 MWh store, 0.5 MVA import cap, third-party turbine on a private
wire, CO2 1,000 ppm, retailer collects. Capex GBP 9.90 M; cost GBP 0.995/kg (design-search basis); carbon 0.41 kg
CO2e/kg; payback 8.8 years at the import-parity contract (NPV 8 % +GBP 2.2 M, IRR 10.3 %). Opex GBP 1.45 M/yr against
a 10-year ceiling of GBP 1.64 M. Price -10 % or yield -10 % pushes payback to about 12 years; at wholesale prices it
does not pay back.

## 7. Evidence the plan still needs (in order of value)

1. **Sales price:** supermarket contract prices for UK glasshouse cucumber and tomato against DEFRA wholesale, and
   whether a Scottish low-carbon premium exists. This alone decides the headline.
2. **Supplier quotes (RFQ_SPEC.md):** the placeholders are about 46 % of structure capex; capex -20 % is worth £0.9 M
   at 8 %.
3. **Fermentation CO2 deal** with a distillery: £0.7 M at 8 % (CO2 is £0.12/kg).
4. **UK yield evidence** for cucumber and tomato (the verification flag).
5. **Export connection** and planning for the 2.5 MW turbine, or a private-wire PPA partner.
6. For diversification: phase 2 sourcing above.
