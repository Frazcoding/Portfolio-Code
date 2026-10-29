# Design under GBP 10 M (2026-10-05)

User goal: capex under GBP 10 M; cost held at GBP 1.00/kg; carbon at or below 0.50 kg CO2e/kg; opex low enough to pay
back within 5-10 years.

Rebuild (from `lca/`):

```
python bplan_10m.py one 2.9,single_2ar,4.5,500     # one design case -> results/bplan/capex10m.json (~12 min)
python bplan_10m.py lead                           # lead case + sensitivities -> results/bplan/capex10m_lead.json
```

## Result

All four targets are met by the lead design on the bases stated below.

| Target | Lead design | Pass |
|---|---|---|
| Capex under GBP 10 M | **GBP 9.90 M** (incl. 5 % development and 10 % contingency; no turbine capex) | yes |
| Cost at GBP 1.00/kg | **GBP 0.995/kg** on the design-search basis of the BP23 GBP 0.996 figure; **GBP 0.987/kg** ex-farm with the conservative yield and the 2026 labour rate | yes |
| Carbon at or below 0.50 kg CO2e/kg | **0.41 kg CO2e/kg** (was 0.49 at 5 ha) | yes |
| Payback 5-10 years | **8.8 years** simple at the import-parity contract (9.9 with our own haulage); NPV at 8 % +GBP 2.2 M, IRR 10.3 % | yes |

Opex ceiling for a 10-year payback: **GBP 1.64 M/yr (GBP 0.98/kg)**. Opex is GBP 1.45 M/yr (GBP 0.87/kg), so the margin
is GBP 0.19 M/yr. A 5-year payback would need opex below GBP 0.65 M/yr. That is less than labour, packing and power
together, so 5 years cannot be reached with any design in the study.

## The design

Track B cucumber at the Stranraer location. The changes from the BP27 5 ha lean case are in bold.

| | 5 ha lean (BP27) | Lead under GBP 10 M |
|---|---|---|
| Area | 5.0 ha | **2.9 ha** (compact block, 11 spans x 15.7 m, ~168 m long) |
| Structure | single 2xAR glass, 3 ridges per span, gutter 4.64 m, pitch 15° | same (checked: lower gutter, other pitch and span are no better) |
| Heat pump | R717 air source 3.7 MW | **R717 air source 1.90 MW** (32 % of the 6.0 MW design load), 2010 winter met (0 h unmet) |
| Store | 662 MWh | **358 MWh** hot-water store |
| Grid import cap | 1.0 MVA (SPEN GBP 153.9 k) | **0.5 MVA** (peak 475 kW; SPEN Ex. 5 GBP 143 k; lowest TNUoS band) |
| Emitters | pipe-rail + grow pipe 4.5 m/m2 | same (2.25 m/m2 tested at 3 ha: the lower COP makes the heat pump and store larger, capex +GBP 0.4 M) |
| CO2 dosing | 800 ppm vents closed | **1,000 ppm vents closed** (AHDB, below) |
| Electricity | third-party 2.5 MW turbine on site, private wire GBP 90/MWh | same |
| Sales | direct retailer contract at import parity GBP 1.57/kg | same; **retailer collects at the farm** (ECF/REWE retailer-partner model, BP24c) |
| Output | 2.62 kt/yr | 1.67 kt/yr (57.7 kg/m2) |

Capex (GBP k): residual systems 2,420; heat pump 1,714; store 1,230; heating pipe 1,044; glass 833; steel 794;
aluminium 192; screen 174; concrete 66; HV connection 143; development 431; contingency 861. Total 9,902.

Opex (GBP/kg): labour 0.213; electricity 0.200; CO2 0.126; packing 0.100; structure O&M and insurance 0.066; young
plants 0.057; overheads 0.052; fertiliser and protection 0.033; substrate 0.012; other 0.008. Total 0.867.

## What the audit changed, and why

1. **Area is the capex lever.** On the study's own sourced anchors a 5 ha house cannot be built for GBP 10 M. The WUR
   4-8 ha benchmark is GBP 177/m2 before development and contingency, about GBP 10.2 M at 5 ha before any heat pump.
   Payback depends on margin per m2 against capex per m2, which barely changes with area. So the area is set to the
   largest that fits under the cap.
2. **Yield cap corrected (BP25a).** The crop model is calibrated to CBS 65 kg/m2 on the Westland reference house,
   which is glazed with *single plain* glass (`crop_gh.reference_house`). Scale that anchor by light alone (elasticity
   1, the upper end of Marcelis et al. 2006). Single 2xAR glass at Stranraer is then 2 % above the expectation, and
   double AR is 4-5 % below it. So the BP25 anomaly is mostly a double-glass shortfall. The old cap (single = double
   x light ratio, 0.93) penalised the anchored case. The new cap is the light-only CBS expectation (0.976), applied
   at the 800 ppm calibration condition. The single-glass yield is never raised above the model.
3. **Double glass loses under the cap.** At 3 ha it costs GBP 11.1 M with a 12.4-year payback, because glass costs
   more and the 2010 floor keeps the heat pump near 2.1 MW. Its carbon is lower (0.39).
4. **The 0.5 MVA import cap is better than 1 MVA at 3 ha.** The LP builds a smaller heat pump and a larger store.
   That costs GBP 0.24 M more capex but saves GBP 0.014/kg in opex and lowers carbon (0.40 vs 0.43).
5. **CO2 at 1,000 ppm.** AHDB, 'CO2 best practice guide: how much to use': "On sunny days when the vents are closed,
   supplement with 1,000 ppm CO2"; for cucumber, 800-1000 ppm in spring and summer. In the model, yield rises 2.9 %
   for 18 % more CO2. Going lower loses: 600 ppm costs more per kg and adds carbon.
6. **Labour corrected to April 2026 (BP27a h, against the goal).** The NLW is GBP 12.71/h; with holiday 12.07 %,
   employer NI 15 % above GBP 5 k and a 3 % pension, a productive hour costs GBP 16.3. That is +GBP 0.018/kg, applied
   throughout.
7. **The geometry stays.** Gutter 4.0-4.3 m loses yield; pitch 12/20° and span 12.8/19.2 m are within GBP 0.006/kg.

## Bases, stated plainly

- "GBP 1.00/kg" is read as the **production cost**, on the design-search basis that produced BP23's GBP 0.996/kg
  (3.5 %, structure and heat pump annuities, energy, labour, CO2, packing). It is **not** a sale price. Selling at
  GBP 1.00/kg never pays back (EBITDA GBP 0.22 M/yr). Selling at the DEFRA wholesale price (GBP 1.17) takes about 30
  years.
- Full investor cost (development, contingency, all consumables, ramp-up, replacements) is GBP 1.45/kg at 8 % and
  GBP 1.24/kg at 3.5 %. That is below import parity (GBP 1.57) but above DEFRA wholesale.
- Delivered to the RDC by our own lorries, the conservative design-search cost is GBP 1.033/kg. It meets GBP 1.00 only
  with retailer collection.

## Risks (lead case, payback in years)

| Case | Payback | NPV 8 % | IRR |
|---|---:|---:|---:|
| Central | 8.8 | +2.23 M | 10.3 % |
| Own haulage | 9.9 | +1.38 M | 9.4 % |
| PPA GBP 100/MWh | 9.2 | +1.85 M | 9.9 % |
| Capex +10 % | 10.3 | +1.05 M | 9.0 % |
| Yield -10 % | 11.7 | -0.49 M | 7.5 % |
| Price -10 % | 12.0 | -0.68 M | 7.3 % |
| DEFRA wholesale price | 29.9 | -6.21 M | 0.1 % |

- **The sale price decides it.** The design pays back only on a contract near import parity, and BP14 says contracts
  pay for stability, not a premium. Evidence for that price is still the first item in the plan (BP5).
- **The turbine developer is marginal.** At 2.9 ha the greenhouse takes 3.4 of the turbine's 9.0 GWh. The developer
  earns GBP 71.2/MWh against an LCOE at 8 % of GBP 68.9, a margin of GBP 2.4/MWh. The developer may ask for about
  GBP 95-100/MWh; at GBP 100 the payback is still 9.2 years. A community or blended-finance owner (the Kilbirnie model
  behind the capex) could do it for less.
- Placeholders unchanged: residual systems, heating pipe rate, glass, aluminium, packing, labour hours, structure O&M.
  The year-10 replacements (climate computer, screen; GBP 0.58 M) fall inside the payback window.
- The 0.5 MVA import cap needs an operating-limit term in the SPEN connection offer.

## If GBP 1.00/kg is the sale price (checked 2026-10-05)

No design in the study can pay back in 5-10 years selling at GBP 1.00/kg.
- Revenue at GBP 1.00 is GBP 57.7/m2/yr.
- Cash opex is GBP 50.0/m2/yr: GBP 31.1 before energy and CO2, plus GBP 18.9 for energy and CO2. The GBP 31.1 is
  labour, packing, plants, consumables, overheads and O&M.
- That leaves GBP 7.7/m2/yr, so a 10-year payback allows **at most GBP 77/m2 of capex**.
- The heat pump and store alone are GBP 101/m2; the cheapest structure in SAC/SRUC Table 11 is GBP 60-100/m2.
- Even with free energy and CO2 the limit is GBP 266/m2, below the lead design's GBP 341/m2.
- Lead design with every upside at once (free CO2, bulk packing x0.5, capex -20 %) and a GBP 1.00 sale price:
  payback 16.5 years.
- Minimum sale price for the lead design (retailer collects): **GBP 1.52/kg for a 10-year payback**, GBP 2.13/kg for
  5 years. Import parity (GBP 1.57) is above the first.
