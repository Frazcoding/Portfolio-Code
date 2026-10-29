# Capex / opex audit: 5 ha lead case (2026-10-05)

Case audited: `results/bplan/viable_5ha_plan.json`, central scenario (track B cucumber, Stranraer, 5 ha single glass,
pipe 4.5 m/m2, heat pump + peak boiler + store, own 2.5 MW turbine). Investor raise **£23.06 M** = greenhouse £17.16 M
+ turbine £5.90 M. The findings below were first estimates. Items 1-7 are now implemented and rerun: see **Results after the fixes** at
the end (`python bplan_5ha.py lean`, `results/bplan/viable_5ha_plan_lean.json`, grid in `viable_5ha_lean_grid.json`).

## Capex as modelled (greenhouse, £M)

| Item | £M | £/m2 | Note |
|---|---:|---:|---|
| Residual lump (install, climate, vents, irrigation, wires, electrics) | 4.05 | 81 | 85 % placeholder |
| Heat pump 3.39 MWth | 2.96 | 59 | DEA ch. 40 |
| Heating pipe 4.5 m/m2 at £8/m | 1.80 | 36 | placeholder rate |
| Contingency 10 % + development 5 % | 2.24 | 45 | on everything incl. DEA all-in and SPEN figures |
| Glass, steel, aluminium, concrete, screen | 3.44 | 69 | glass/Al/screen placeholders |
| Hot-water store 350 MWh | 1.14 | 23 | DEA formula |
| Peak boiler 6.77 MWth | 0.90 | 18 | supplies 18 MWh/yr |
| HV import connection | 0.63 | 13 | SPEN Ex. 18 step (1.95 MVA) |
| **Total** | **17.16** | **343** | |

## Findings, largest first

### Capex

1. **The turbine is £5.9 M of the raise and loses money at 8 %.** Greenhouse NPV 8 % is +£0.91 M; with the turbine
   it is -£0.22 M, so the turbine is about -£1.13 M at 8 %. Options: third-party ownership with a private-wire PPA at
   our site, or the Girvan private-wire route (S3: same £/kg at 8 %, BP18). Either takes **-£5.9 M** off the raise.
2. **The heating plant has three layers of redundancy.** The rule is heat pump + boiler ≥ the design load, and the
   350 MWh store does not count towards it. The result is a 6.77 MW boiler (£0.90 M, about £1.03 M with development
   and contingency) that supplies 18 MWh/yr (0.08 % of heat), about £5,000 per MWh at 8 %.
   - The design load (10.16 MW, 203 W/m2) is a steady loss with **no energy screen** (`config.design_heat_loss_w`).
     The screen is bought (£0.3 M) and closes at night below 15 °C. At design night the roof U would be ×0.55.
     - Estimate: design load about 6.6 MW, boiler about 3.2 MW, **-£0.5 M**.
   - Counting the store (it can cover the 6.8 MW gap for about 50 h) or using a modular N+1 heat pump removes the
     boiler: **-£1.0 M**. This needs a user decision on the standby rule.
3. **The HV import connection jumps a step the LP cannot see.** `hv_conn_gbp` and the TNUoS bands are applied after
   the LP (`finalist_lp.py` docstring), so the LP has no reason to shave the 1.85 MW import peak. Below 1 MVA the
   connection costs £153.9 k instead of £633.9 k: **-£0.48 M** (-£0.55 M with development and contingency). With
   350 MWh of store, a peak cap looks cheap to meet; that has to be checked in the LP.
   - The turbine also carries its own £0.3 M connection allowance. A turbine and a greenhouse on one site would
     normally share one point of connection, so one of the two allowances is probably double-counted.
4. **The turbine capex basis is high.** £2,240/kW is Kilbirnie's £5.6 M *blended finance* package, which may include
   finance and reserve costs. The model adds the £0.3 M connection margin on top, although the source note says
   Kilbirnie's connection is already inside the £5.6 M. Arup/DESNZ utility capex is £1,715/kW. Range **-£0.3 M to
   -£1.3 M** (a single turbine costs more than a farm; get a quote).
5. **Structure and fit-out are 25-50 % above the scale benchmark.**
   - Ours: £186/m2 (structure + residual), excluding heat plant, development and contingency.
   - WUR 2016-068: £125-150/m2 for England at 4-8 ha, including boiler and heating (BP22).
   - The residual was calibrated at **1 ha** (SAC £200/m2). At 5 ha only the 17.7 % fixed share scales.
   - Supplier quotes (RFQ) are the route. **-£1.8 M to -£3.0 M** if quotes land on the benchmark.
6. **Installation labour may be counted twice.** `install_labour` is a £30/m2 placeholder (£1.5 M at 5 ha) that
   covers "frame, glazing, pipe-rail, screens". The steel rate (£4,890/t, BCIS) is already an *erected* frame cost,
   so frame erection appears in both. Overlap is roughly a third of the steel line, about **-£0.3 to -0.5 M**
   (estimate; settle it with the structure quote).
7. **Development and contingency are charged on figures that already include them.**
   - DEA heat-pump, boiler and store costs are total-investment figures that already include project costs.
   - The SPEN connection is a worked-example price.
   - Using 5 % contingency and no development charge on those £5.6 M: about **-£0.5 M**.
8. **Model defect (no saving):** at 5 ha the residual lines (`bplan_residual.ResidualItems`) stay at £84/m2, while the
   scaled residual is £81/m2. The `design_pm` line therefore goes negative (-£149 k), and replacements use lines that
   do not reconcile with the capex. Note: the design/PM vs development double count (BP22) only exists at 1 ha.

### Lifecycle (replacements)

9. **The climate-control line is replaced in full every 10 years** (£700 k at years 10 and 20). Only the computer
   and sensors have a 10-year life; the wiring lasts 30. Splitting the line saves about **£0.35 M NPV at 8 %**.
10. **The turbine is rebought in full at year 20 (£5.9 M).** IEC 61400-1 sets 20 years as a *minimum* design life.
    A 25-30-year life with a mid-life overhaul is worth about **£0.7 M NPV at 8 %**.

### Opex (£2.34 M/yr)

11. **Labour is not overstated. It is slightly understated.**
    - Model: £564 k/yr (£0.215/kg) = 0.8 h/m2 × £15/h × usable area (about 22 FTE at 5 ha).
    - The £15/h is built on the **April 2025** National Living Wage (£12.21). The April 2026 rate is £12.71.
    - Add employer NI (15 % above £5 k), 3 % pension and 12 % holiday, and a productive hour costs about **£16.3**:
      **+£45 k/yr (+£0.017/kg)**.
    - The 0.8 h/m2 is still unsourced (register "pending", KWIN not obtained).
    - Check whether the hours include grading. If they do, the £0.10/kg packing charge partly double-counts it.
12. **The turbine power price flatters the greenhouse (BP8).** The greenhouse buys turbine power at its 3.5 % LCOE
    (about £52/MWh) even in the 8 % case, where it should be about £72/MWh. That understates opex by about
    **£110 k/yr**. The combined result is unaffected.
13. **CO2 at £305 k/yr (£0.116/kg) is the largest consumable you can control.** The levers are a dosing strategy
    (BP13 step 4) and distillery CO2. Price risk: £0.25/kg would add £76 k/yr.
14. **Unsourced percentage inputs carry real money.**
    - Structure O&M + insurance at 2 % of capex = £186 k/yr; each 0.5 % is about £46 k/yr.
    - Overheads at £3/m2 = £150 k/yr, which is light for a 5 ha business with a head grower.

## What the cuts add up to (estimates, not yet modelled)

| Step | Raise £M |
|---|---:|
| Today (greenhouse + owned turbine) | 23.06 |
| Turbine owned by a third party or private wire (1) | 17.16 |
| + boiler removed or screen-credited (2), import peak < 1 MVA (3), development/contingency basis (7) | about 15.1-15.6 |
| + quotes at the WUR scale benchmark and the erection overlap (5, 6) | about 12.5-13.5 |

Accuracy fixes that go the other way: labour +£45 k/yr, turbine transfer price +£110 k/yr (greenhouse view).

## Results after the fixes (BP27, 2026-10-05, `bplan_5ha.py lean`)

The user decided that the plant has two components, never heat pump + boiler + store together. The study ran
2 plants x 4 grid-import caps x 2 turbine routes, using the WUR 4-8 ha structure anchor, and ranked them on project NPV
at 8 % in the central scenario (capped yield, direct retailer contract at £1.57/kg).

| | Old plan | Third-party turbine (lead) | Owned turbine |
|---|---:|---:|---:|
| Plant | HP 3.4 MW + boiler 6.8 MW + store 350 MWh | HP 3.7 MW + store 662 MWh | HP 3.6 MW + store 776 MWh |
| Grid import cap | none (peak 1.85 MW) | 1.0 MVA (peak 950 kW) | 0.8 MVA (peak 760 kW) |
| HV connection | £634 k | £154 k | £143 k |
| Greenhouse capex | £17.16 M | £16.00 M | £16.04 M |
| **Investor raise** | **£23.06 M** | **£16.00 M (-31 %)** | **£21.64 M** |
| Cost per kg at 8 % (LCOP) | £1.539 | £1.556 | £1.466 |
| Project NPV 8 % (IRR) | -£0.22 M (7.9 %) | +£0.41 M (8.3 %) | +£2.24 M (9.1 %) |

- **Heat pump + boiler with no store loses on every route:** NPV -£3.2 M or worse.
  - Without a store, all the heat must be made at the moment it is needed, so the import peak reaches 5.6 MW.
  - Capping the import then forces batteries, up to £134 M of capex.
  - The store is the component that earns its place; the boiler is not.
- **Capping grid import at 1 MVA is worth about £1.2 M of NPV.** A larger store keeps the import peak under the
  SPEN step, which cuts the connection cost (£634 k to £154 k) and the electricity bill.
- **Third-party turbine developer check.**
  - Generation 9,045 MWh/yr, of which the greenhouse takes 5,647 MWh at £90 and 3,398 MWh is exported at £60.
  - Average revenue £78.7/MWh against an LCOE at 8 % of £68.9/MWh. The margin of £9.8/MWh makes the deal plausible
    for a developer.
- **The owned turbine is now value-positive in combination** (turbine business -£0.78 M at 8 %; greenhouse NPV rises
  to +£3.02 M because it buys power at the 3.5 % LCOE, BP8). It costs £5.6 M more of raise for +£1.8 M of NPV.
- **Scenarios, third-party lead** (NPV 8 %, IRR):

  | Scenario | NPV 8 % | IRR |
  |---|---:|---:|
  | Capex -20 % | +£4.22 M | 11.3 % |
  | Free CO2 | +£3.84 M | 10.4 % |
  | Capex +20 % | -£3.39 M | 6.1 % |
  | Price -10 % | -£4.14 M | 5.1 % |
  | Yield -15 % | -£5.78 M | 3.9 % |
  | Wholesale price | -£12.8 M | |

- **Lead greenhouse capex £16.00 M:**

  | Item | £M |
  |---|---:|
  | Residual (now WUR-anchored) | 3.58 |
  | Heat pump | 3.24 |
  | Heating pipe | 1.80 |
  | Store | 1.70 |
  | Glass | 1.40 |
  | Contingency | 1.39 |
  | Steel | 1.31 |
  | Development | 0.70 |
  | Aluminium | 0.32 |
  | Screen | 0.30 |
  | HV connection | 0.15 |
  | Concrete | 0.10 |

Corrections to the findings above, from the sources:
- **5:** indexed with the Eurostat construction index rather than consumer prices, the WUR anchor is £177/m2, not
  £125-150. Ours was about 5 % above it, so the saving is about £0.5 M, not £1.8-3.0 M. The anchor still includes a
  boiler we no longer buy, so it is conservative.
- **6:** the residual is a calibration remainder (anchored total minus the itemised list), so it cannot double-count
  in total. The line is relabelled, and the 5 ha lines now reconcile pro rata (no negative design/PM line).
- **7:** withdrawn. DEA's methodology (p.22) excludes owners' predevelopment costs, so the 5 % development charge on
  DEA plant is correct.

Not done (outside 1-7): labour rate to the April 2026 NLW (+£45 k/yr), the BP8 transfer price, climate-control
replacement split, turbine life. The capped (1 MVA) store strategy needs an operating-limit agreement in the SPEN
connection offer.

## Under GBP 10 M (BP28, 2026-10-05)

The GBP 10 M cap cannot be met at 5 ha on sourced anchors (WUR GBP 177/m2 before development, contingency and heat
plant). It is met at 2.9 ha: GBP 9.90 M, payback 8.8 years, cost GBP 0.995/kg, 0.41 kg CO2e/kg. Labour (finding 11)
is now at GBP 16.3/h in that case. Full write-up: `CAPEX_10M_DESIGN.md`.
