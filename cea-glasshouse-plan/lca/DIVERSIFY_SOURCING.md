# Diversification crops: sourcing (BP10, 2026-10-07)

Desk search through Firecrawl; every value below is from a search excerpt or a scraped page, tier given. Nothing here is
a UK commercial grower figure unless stated. KWIN-AGV is not obtainable (BP18 note), so the standard Dutch reference
values are missing. **No row replaces a placeholder in the model by itself:** `bplan_yearround.PRODUCTS` and
`bplan_diversify.py` keep their labelled placeholders until the primary sources below are read in full.

| Crop / item | Value | Basis | Source | Tier |
|---|---|---|---|---|
| Cherry tomato, yield | 27-30 kg/m2/yr (record 30) | high-tech Dutch-type glasshouse | Novagric project page | vendor, secondary |
| Cherry tomato, yield, trial | 12.9-14.4 kg/m2 | one trial crop (not annual) | MDPI Sensors 20(22):6430 (2020), intelligent greenhouse trial | peer-reviewed, partial year |
| Cherry tomato, labour | 281 h/week on 18,000 ft2 (1,672 m2), ~8.7 h/m2/yr | US medium-tech tunnel, cost-benefit | HortTechnology 36(1):124 (2026) | peer-reviewed, not comparable to Dutch high-tech |
| Mini cucumber, yield | "similar but somewhat lower" than standard European | cultivar trials, no number | UF/IFAS HS790/CV268 | extension, qualitative |
| Mini cucumber, labour | scales with pick interval, not weight; no figure | qualitative | DutchGreenhouses mini-cucumber page | vendor, no numbers |
| Strawberry, winter UK glass | planned 400 t over 3.6 ha of glass = 11 kg/m2 (derived) | The Summer Berry Company, winter crop | Fruitnet (Fresh Produce Journal) | trade press, derived |
| Strawberry, LED | average 1.1 kg/m2/week in January | dynamic LED, case study | Sollum Technologies | vendor |
| Strawberry, table-top polytunnel | 1.4-1.6 kg/plant Class 1 (Malling Ace, high-light years) | UK polytunnel | Frontiers in Horticulture 2025 (RDI study) | peer-reviewed |
| Strawberry, UK demand | 2.3 kg per person (2023) vs EU 2.6 | | CBI market potential | agency |
| Raspberry long cane, yield | 1.5-3.8 kg per cane (research); Ohio system 22,000-25,000 lb/acre (~25-28 t/ha) | | ResearchGate (long canes to 3 kg per cane); Ohioline ANR-0190 | research, extension |
| Lettuce, hydroponic greenhouse | 41 +/- 6.1 kg/m2/yr, 150 g head, 12 harvests/yr, 17 mol/m2/d | Arizona greenhouse unit (815 m2) | PMC4483736 (Barbosa et al. 2015); Cornell CEA Lettuce Handbook | peer-reviewed |
| Lettuce, vertical farm energy | typically 10-18 kWh/kg; technical floor 2.6-4.7 kWh/kg at LED efficiency 0.9-0.5 | review | ScienceDirect S2451904924007832 (2024) | peer-reviewed |
| Lettuce, greenhouse energy | 5.3-33.3 kWh/kg; ~3 kWh/kg in efficient heated greenhouses | review | same | peer-reviewed |
| Lettuce, vertical farm lighting load | 850-1,150 kWh/m2/yr per layer | | Univ. Manitoba thesis (PDF) | thesis, secondary |
| Lettuce, theoretical ceiling | up to 700 kg/m2/yr per layer at 500 umol/m2/s continuous light | | WUR publication (light use efficiency) | peer-reviewed |

## What this means for the model
1. **Cherry tomato factor.** The model uses yield_f 0.6 (27-30 kg/m2 vs CBS round 48, `bplan_yearround.PRODUCTS`). The
   Novagric 27-30 range supports the 0.6 only as a vendor claim; labour_f 1.5 stays a placeholder (the 8.7 h/m2/yr is a US
   medium-tech tunnel, not comparable).
2. **Mini / snack cucumber:** no usable number; keep the placeholder (yield_f below long cucumber, labour above).
3. **Strawberry winter on glass:** 11 kg/m2 (Summer Berry derived) is the only UK commercial figure, and it is a plan, not an
   audited result. LED weekly yield 1.1 kg/m2 would be ~57 kg/m2/yr if sustained, which is not credible as an annual figure:
   a January-only value. Do not annualise it.
4. **Lettuce:** the Arizona 41 kg/m2/yr (12 harvests of 150 g) is a transferable figure for a lit hydroponic house; UK
   light is the limit, so the crop needs lighting (BP11 lit case) before it is meaningful.
5. **Vertical farm (LED W/m2):** use energy per kg (10-18 kWh/kg) rather than W/m2 until a PPFD and photoperiod are chosen.

## Still not found (needs primary access or a grower)
- AHDB or named UK-grower yields for cherry/vine tomato, mini cucumber, everbearer strawberry under glass and baby leaf.
- Picking rates (kg per picker-hour) for strawberry and raspberry.
- Winter berry contract prices (UK supermarket). Only market commentary was found, no contract figure.
- KWIN-AGV 2026 (copyright; routes in HANDOFF BP18).
