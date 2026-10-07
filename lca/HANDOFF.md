# Handoff — UK glasshouse vs imports study (state at 2026-10-05: business-plan preparation started)

**2026-10-07 FINANCE (cloud): `finance.py` / `bplan_finance_risk.py`, see BP33/BP36/BP37.** Lit lead 2.9 ha, capex GBP 11.45 M: ECA supplier credit + plant asset finance with a 1-yr holiday needs a real price of GBP 1.237/kg (DSCR 1.25 binds); at parity -10 % (GBP 1.40) equity GBP 4.34 M, equity IRR 21.8 % nominal, min DSCR 1.56. The lender case (GBP 1.01-1.20) fails. Yield -15 % breaches DSCR 1.25 (1.18); Monte Carlo P(DSCR < 1.25) 45 %.

**2026-10-05 LATE: design under GBP 10 M, see `CAPEX_10M_DESIGN.md` (BP28).** User goal: capex < GBP 10 M, cost held at
GBP 1.00/kg, carbon <= 0.50 kg CO2e/kg, payback 5-10 yr. Lead: track B cucumber, Stranraer, **2.9 ha** single glass,
R717 heat pump 1.9 MW + 358 MWh store, 0.5 MVA import cap, third-party turbine on a private wire, CO2 1,000 ppm (AHDB),
retailer collects at the farm. Capex **GBP 9.90 M**; cost **GBP 0.995/kg** (BP23 design-search basis) / 0.987 ex-farm
(conservative yield, 2026 labour); carbon **0.41**; payback **8.8 yr** at the import-parity contract (NPV 8 % +GBP 2.2 M,
IRR 10.3 %); opex GBP 1.45 M/yr vs a 10-yr ceiling of GBP 1.64 M. Needs the import-parity contract: at GBP 1.00/kg or
DEFRA wholesale as a SALE price it never pays back. Turbine developer margin only GBP 2.4/MWh at 2.9 ha.

**2026-10-05 SESSION: business plan pack, see `BUSINESS_PLAN.md`.** Decisions in §3 (track B leads, both HP rules,
8 % headline + 3.5 % public case, four diversification routes). The costing was rerun after a price defect fix: the
winter tomato price had been back-filled from one DEFRA March point (£3.00); months with < 3 DEFRA observations now
use the import CIF price. Tomato is now £1.23/kg (was 1.29-1.31) and NPV is about £0.6-1.3 M lower; cucumber is
unchanged. Old results are in `results/costing/*_pre_pricefix_20261005.*`.

Headline, track B cucumber, Stranraer, LP heat pump:
- Levelised cost £1.58/kg at 8 % and £1.32/kg at 3.5 %, against a DEFRA price of £1.17 and import parity of £1.57.
- NPV at 8 %: -£2.5 M base; -£0.2 M at import parity; +£3.0 M at import parity with the CO2, yield and capex levers
  (IRR 16.5 %).
- The turbine alone has an IRR of 4.9 %, so it is negative at 8 %.

Verification (`bplan_verify.py` → `results/bplan/VERIFICATION.md`): 13 pass, 3 flags (UK yield evidence ×2; the
thesis README COP of 4.29 at an 80 °C supply is about 97 % of Carnot and must not be quoted).

Figures are in `../figures/business_plan/` (bp01-bp11). Diversification screen: `bplan_diversify.py`. Its finding:
changing the crop moves the margin far less than the structure capital does; the thermal campus is a modest bonus.

New scripts (class-based per ../CLAUDE.md): `bplan_perf.py`, `bplan_verify.py`, `bplan_diversify.py`,
`bplan_figures.py`.

**CURRENT RESULTS: R10 two-track chain + full costing (2026-10-03, 18:22-19:11, `run_chain_tracks.sh`; logs
`results/site_opt/R10_chain.log` (track A, waste heat) and `results/site_opt_B/R10_chain.log` (track B, no waste heat); costing
`results/costing/FULL_COSTING.md`).** Everything older (incl. the R6 block that was here, archived in `results/site_opt/pre_R10_archive`)
is superseded. Central electricity route = owned single 2.5 MW turbine (user: grid baseline, turbine priority, private wire second).
- Model cost (levelised at 3.5 %, the design-search basis), refined designs: track A cucumber 1.08-1.10, tomato 1.36-1.43 GBP/kg (Creamery,
  Cameronbridge, Girvan; Sapphire for tomato); track B cucumber 1.10-1.16, tomato 1.37-1.44 (Creamery, Tay/Hatton, Girvan, Nigg). With
  cheap turbine power, waste heat is worth only ~0.02-0.05 GBP/kg. All beat imports (1.57 / 1.77) and carbon (0.81 / 1.30) centrally;
  grid-only costs +0.13-0.24; private wire +0.04-0.06; 2010 weather +0.03-0.11; no-export turbine is a loser (1.7-2.4).
- FULL COSTING (cashflow.py, 30 yr real pre-tax cash purchase, DEFRA wholesale price 2023-26 by month: cucumber 1.16-1.17, round
  tomato 1.29-1.31 GBP/kg): NOT PROFITABLE at DEFRA prices on either track. Break-even price at 3.5 % cucumber 1.32-1.39, tomato
  1.63-1.76 GBP/kg (8 %: 1.58-1.69 / 1.95-2.09). NPV 3.5 % cucumber -1.5 to -3.4 M, tomato -3.2 to -9.1 M (LP-sized heat pump).
  At the import-parity price (1.57 / 1.77): cucumber NPV +2.0 to +2.7 M at 3.5 % (IRR 6-7 %), still negative at 8 %; tomato ~0 to +1.7 M.
  The full costing adds ~0.25 GBP/kg the design search left out (young plants, substrate, fertiliser/protection, overheads, sales
  commission, development + contingency, import connection, land, ramp-up year). Capex 360-520 GBP/m2 (4.1-11.7 M per house).
- What closes the gap (NPV at 3.5 %, LP heat pump): free fermentation CO2 from a distillery host (CO2 is 0.12 GBP/kg), GreenLight's
  yield response (+18 %), capex -20 % from quotes: all three together make every design positive at DEFRA prices (+0.7 to +3.1 M);
  with import-parity contracts as well, IRR 12-16 %.
- The owned 2.5 MW turbine as its own business: NPV +0.9 to +1.4 M at 3.5 %, payback ~12 yr at most sites (Cameronbridge -0.9 M, CF 33 %);
  it needs an export connection (no-export case fails).
- Heat pump: the LP-sized unit must meet a 2010 winter (2023 is mild): 50-88 % of design load with a 3-30 MWh store; saves
  0.04-0.12 GBP/kg vs full standby.
Open: user decisions (section 5), supplier quotes (RFQ, placeholders ~half of structure capex), sales-price evidence (contract price vs
DEFRA wholesale), CO2 deal with a distillery, export connection offer, operator heat data (B6).

## 0. Start here on the other machine

1. **Wait for kDrive to finish syncing** `kDrive/Code` (lca ~260 MB, `simcore/cache` ~100 MB). Check that
   `lca/results/greenlight/caledonian_tomato_chunk*_out.csv` and `lca/results/site_opt/lp_*.json` are there.
2. **Set up Python** (one command, from this `lca` folder in PowerShell; needs python.org Python 3.12, and 3.14 if you
   want the same main version as the laptop):
   ```
   powershell -ExecutionPolicy Bypass -File setup_machine.ps1
   ```
   It creates `~/.venvs/portfolio` (main study, `requirements.txt`) and `~/.venvs/greenlight` (Python 3.12,
   `requirements-greenlight.txt`), downloads the Global Wind Atlas rasters to `~/.cache/gwa`, and runs quick checks.
   Then activate the main venv for every study script: `~/.venvs/portfolio/Scripts/activate`.
3. **Optional full checks:** `python tests/test_reproduce.py` (thesis, ~5 min, must PASS) and
   `python tests/test_fast.py` (~12 min).
4. **Pick up the work in §5.** First job on the bigger machine: the continuous GreenLight year for yield and R6
   (our off-season heat is ~half GreenLight's).
5. **Machine-specific settings to raise on a bigger machine:** `site_opt.py` and `size_study.py` use 7 workers,
   `finalist_lp.py` 2 workers (`main(crops, workers=...)`), `gl_chunks.py` 4 quarters. Use about (physical cores − 1);
   each sweep worker needs ~0.3 GB, each LP ~1.3 GB, each GreenLight run <1 GB.

What does **not** sync: Python environments, `~/.cache/gwa`, and Claude's memory (the two rules it holds are in §3:
track every commitment in §4; every input sourced or standard-based). **GitHub is not up to date:** the repo
`Frazcoding/BEng-CEA-Heatpump` was last committed on 2026-09-24 and `lca/`, `sim/`, `results/`, `figures/` are
untracked; `kDrive/Code/simcore` is not in any repo. The user decided not to push for now (2026-10-03): kDrive is the
copy of record. Before any push, check the third-party PDFs in `lca/data` (licences) and large files.


**Working rule (user, 2026-10-02):** whenever we say we will do something, add it to the task list in §4; tick it
when done, or strike it through with a reason when retired. Keep the list current at the end of every session.

The full record (method, every result table, sources) is `SCOPE.md` in this folder (§3.16 toolchain, §3.17 Gate B);
this file is the short version plus what to do next. Everything lives under `kDrive/Code`, which syncs. Python
packages, the GWA rasters and the GreenLight venv do **not** sync (§6).

## 1. What the study is

Can heated Scottish glasshouse produce beat imports on two pass/fail goals the user set (2026-10-02)?

1. **Carbon:** kg CO₂e per kg delivered to a Central Belt supermarket distribution centre (RDC) below the
   volume-weighted import footprint delivered to the same RDCs (annual and seasonal).
2. **Cost:** levelised £/kg below the import price delivered to the same RDCs (Comtrade CIF + port-to-RDC haul,
   annual and seasonal).

It started as avocado (fails on cost), widened to 10 crops at Chelmsford and Perthshire, and is now a **site search
across Scotland for waste-heat-fed glasshouses growing cucumber (first) or tomato**. Earlier scenarios are history
(§7); their scripts still run.

## 2. Where we are: Gate B step 5 done (2026-10-03)

Validation order (user decision): (1) code verification [done]; (2) model validation vs GreenLight at Gate B on the
chosen design [heat done 2026-10-03: fails ±15 %, see below; yield still to do]; (3) design gates: A concept freeze [done 2026-10-03] → B verified
concept [step 5 done; GreenLight heat check failed → R6] → RFQ [spec drafted] → C quoted design + full structural design.

Gate B results (refined design per site, £10/MWh heat; imports at Scottish RDCs: cucumber £1.57/kg and
0.81 kg CO₂e/kg, tomato £1.77/kg and 1.30 kg CO₂e/kg):

| Site | Cucumber £/kg, kg CO₂e/kg | Tomato £/kg, kg CO₂e/kg | Notes |
| --- | --- | --- | --- |
| Girvan + Ailsa Bay distilleries (51 GWh/yr) | 1.00, 0.26 | 1.34, 0.37 | 0.2 MW turbine justified on own use; 116 km to RDCs |
| Caledonian Paper, Irvine (83 GWh/yr) | 1.01, 0.29 | 1.36, 0.38 | largest heat source; 77 km |
| Cameronbridge distillery, Fife (55 GWh/yr) | 1.03, 0.30 | 1.38, 0.41 | 81 km |
| The Creamery, Stranraer (food/AD) | 1.06, 0.35 | 1.39, 0.47 | waste heat covers only ~42 % |
| North British distillery, Edinburgh (26 GWh/yr) | 1.07, 0.30 | 1.44, 0.41 | urban, 1.4–1.7 ha |

- All six leading sites per crop pass both goals centrally and under every sensitivity (wall light ×0.5,
  placeholders low/high, utility wind, capex −20 %, no network increase, pipe ×0/×3, outages none/planned, no
  battery, battery capex ×0.5, heat £0/20, e-HGV).
- **What changed since Gate A (+£0.17–0.20/kg):** the R717 heat pump is now costed at the full design load as standby
  (£104–110/m², about half the structure capex); waste heat stops for planned shutdowns and one unplanned winter week;
  wind is sized for own use only, which removed Girvan's export artefact (worth £0.08/kg).
- **Size:** fixed 5/10/20/30 ha re-optimised: +£0.04–0.10/kg from 5 to 30 ha; nearly flat without the wall-light
  credit. Large houses are viable; every size passes.
- **EN 13031-1 (Type A, A15, CC0):** all designs pass; costing kept on the conservative CC2 basis.
- **Heat store + plant LP (item 4):** with the full-standby rule the LP agrees with the sweep within 1 p/kg and
  builds almost no store. If the LP sizes the heat pump instead (40–46 % of design load) a 13–61 MWh hot-water store
  carries the coldest-week outage and saves £0.07–0.09/kg (cucumber), £0.10–0.12/kg (tomato). This is a capital
  saving, not price arbitrage. It holds only for cold-weather outages of up to about a week. **User decision
  pending** (§5 step 1); the central case stays full standby.
- **Electricity price fix (2026-10-03):** only the wholesale share (32 %, Drax spring 2026 via UtilityBidder) follows
  the hourly Agile shape; network and policy charges are flat. Before, the cheapest hours were nearly free. No
  change to the sweep results; the LP numbers above use the fixed prices.
- **GreenLight cross-check (R5, Caledonian tomato, 2026-10-03): our heat model FAILS the ±15 % test.** GreenLight
  230 vs ours 121 kWh/m²/yr (ours 48 % low). Monthly shape agrees (r 0.87) and midwinter agrees (Jan/Dec within 8 %),
  so peak load and heat-pump size stand; the gap is spring–autumn heating at dawn (night→day setpoint step) and on
  humid nights, which our model barely does. Effect: ~+3 p/kg tomato at waste-heat sites (cheap heat), ~+15 p/kg
  where the heat pump supplies the heat (WWTP sites, outages, big houses). Shortlist still passes; fix in R6.
- **Converged design:** pitched wide span 14–23 m (single ridge, or 3 ridges per span at Girvan), roof pitch
  10–16°, gutter 4.5 m (lower bound of the sweep), ridges mostly N–S, plain double AR glass, no insulated north wall.

Recommended Gate B shortlist: **Caledonian Paper (Irvine), Cameronbridge, Girvan**, cucumber first, tomato as the
alternative. North British stays as the small urban case.

Site news checked 2026-10-03: UPM is cutting 34 roles at Caledonian but says it is staying and investing (Irvine
Times 2025); Diageo is cutting ~70 roles at Cameronbridge with strikes 28 Sep–15 Oct 2026 and no closure planned
(Food Manufacture, 24 Sep 2026). Both show the heat supply depends on one operator: the standby heat pump is the
answer, and a heat-supply contract is a Gate C item.

## 3. Decisions and preferences from the user (keep these)

Study rules:
- Every input sourced or tied to a named standard; placeholders labelled with a range, and the share of the result
  that rests on them reported. Status lives in `data/input_register.csv` and `data/rates.csv`.
- Honest negative results; when an assumption flips a conclusion, say so plainly.
- Never edit `../sim/annual_sim.py` or the thesis notebooks. `tests/test_reproduce.py` must keep passing
  (bit-identical thesis reproduction). New options default to thesis behaviour. Any change to `greenhouse.py` must
  be mirrored in `greenhouse_fast.py` and both tests rerun.
- Dosed CO₂ is reported both ways (emission, and by-product allocation).
- Model every supply (wind, grid, heat) with its real cost, never as a bare carbon factor.

- **Big runs last (user, 2026-10-03):** no run-restart cycles. Do NOT launch the GreenLight continuous year, a full
  `site_opt` sweep, `finalist_lp.py` etc. until the inputs they depend on are settled. Use cheap controlled tests
  first (`gl_ctrl.py` 25 s, fast sim 0.2 s). A sweep started 2026-10-03 with the new transpiration/vent coefficients was
  stopped for this reason (old results untouched; copy in `results/site_opt/pre_R6_archive`).

- **AIM (user, 2026-10-05): prove a 5 ha glasshouse viable. Area is fixed at 5 ha.** Objective is joint: minimise
  cost AND carbon (report both; choose on the cost-carbon front, never cost alone).

Design decisions:
- **Heat pump: R717 (ammonia)**, AGR Fenland precedent; DEA ch. 40 cost data is for ammonia units. ~~Always installed
  at the full design heat load as standby~~ **RELAXED 2026-10-05 (user):** heat pump + electric peak boiler together
  must cover the full design heat load (standby); the LP sizes heat pump, boiler and store (rule 'standby',
  boiler=True). (The 2026-10-02 idea of a refrigerant change / packaged cascades is retired.)
- **Wind** exports only what is left after the greenhouse's own loads; turbine and battery are sized for own use
  (export revenue not counted in sizing); a battery charges from our own wind only (2026-10-03).
- Structure anchored at £2M/ha (SAC/SRUC "commercial"); design and materials may change, upgrades costed on top.
- Area adjustable; max 30 ha. Site search Scotland only. Supermarket-roof case (heat option "SM") still of interest.
- Organic label target: soil beds fed by food-waste digestate (aquaponics not certifiable in GB); AD CO₂ for dosing.
- Sales report: price = what the supermarket pays (DEFRA wholesale in `data/defra_wholesale_prices.csv`).
- `../CALCULATIONS_WHITE_PAPER.md` §6.1 rates are unsourced ("estimated"); the site model no longer uses them
  (`optimise.py` still does, for the old Perthshire shape sweep only).
- **Two tracks in parallel (2026-10-03):** A = waste-heat site (Gate B designs), B = no waste heat (heat pump for all
  heat, any windy site). Both are offered; every rerun evaluates both. Track B controls: RH 90 % + heat-recovery
  dehumidification. **Night setpoint drop rejected** (crop model has no development-rate effect, yield gain not credible).
- Electricity routes (decided 2026-10-03): grid baseline, 2.5 MW owned turbine first priority, private-wire PPA second.
  All routes remain in energy_grid.ELEC_OPTIONS: grid, owned small turbine, owned single
  2.5 MW turbine (surplus on a PPA, reported as its own business), share of a wind farm, private-wire PPA, sleeved PPA.
- **Business plan (user, 2026-10-05):** lead with track B (no waste heat, own heat pump + wind), track A shown as an
  option; show BOTH heat-pump rules (LP-sized + store, and full standby); audience is investors/bank AND public funders:
  8 % commercial headline, 3.5 % Green Book public-value case second. Diversification in scope: multi-zone thermal
  campus (warm + cool house, heat-pump cold side for cold store / vertical farm), higher-value variants (vine/cherry
  tomato, mini cucumber, pepper, herbs), winter soft fruit (strawberry, raspberry, blueberry), citrus/avocado niche.
- Reference: SAC/SRUC "Developing SME-scale CEA in the Highlands & Islands" (Jan 2026),
  `../../cea-guide-for-practitioners_v6-final-jan-2026.pdf`; its vertical-farm 2.3 kWh/kg and polycrub
  "3,000 kWh/m²/yr" look wrong.

## 4. Task list (rule: anything we say we will do goes here; tick `[x]`, or ~~strike~~ with a reason)

Gate B (in progress)
- [x] R1–R4. Sites (distilleries, paper, food/AD, WWTP), OSRM haul, hourly weather, per-site optimisation
- [x] 3. Heat-pump capex: DEA Aug 2026 data sheets ch. 40; 2026-10-03 now at full design load everywhere
- [x] B1. Backup heat: R717 standby at design load + heat-source availability profile (`site_opt.availability`)
- [x] B2. Wind sized for own use, export credited separately, optional own-wind battery (`energy_grid.py`)
- [x] B3. Fixed-size reruns 5/10/20/30 ha (`size_study.py`)
- [x] B4. Simulation speed: cached setup in `greenhouse_fast.py` (0.6 → 0.18 s/design, identical results)
- [x] 4. Heat store + plant sizing by LP for the finalists, grid-backed (`finalist_lp.py`); off-grid not rerun
      (grid connection assumed at all three finalist sites). Result: standby rule confirmed; smaller HP + store option
      saves 7–12 p/kg (decision pending)
- [x] B10. Electricity price: only the wholesale share follows the hourly shape (`energy_grid.WHOLESALE_SHARE`)
- [ ] B11. Primary source for the business wholesale share (DESNZ / Ofgem / Cornwall Insight; HoC CBP-10505 May 2026
      blocks scripted download, read it in a browser)
- [x] B5. Preliminary EN 13031-1 check (`en13031.py`)
- [x] 5–6. Sensitivities and local refinement (rerun 2026-10-03 with the new rules)
- [~] R5. GreenLight cross-check, Caledonian tomato (2026-10-03): **heat FAILS ±15 %** (GreenLight 230 vs ours
      121 kWh/m², ours 48 % low); monthly shape OK (r 0.87), midwinter agrees, gap is spring–autumn dawn and humid-night
      heating. Peak load unaffected. See SCOPE §3.17. Still to do: yield (continuous year, 32 GB machine)
- [~] R6 (started 2026-10-03, this session). Hour-by-hour finding: the off-season gap is NOT the setpoint ramp or
      humidity control. Our floor runs 8-10 K hotter than GreenLight's (35 vs ~25 C in June) and releases ~49 W/m2
      into the night air (Apr nights: ours pipe 4 W/m2, GL 45-50). GreenLight drains 49 kWh/m2/yr through a 1-D soil
      column (U~0.37) and chunks 2-4 started with 10 C soil; ours uses ISO 13370 (U 0.057). Sensitivities (ours,
      kWh/m2/yr, base 120.6): floor U 0.5/1.2/2.0 -> 137/161/187; floor light share 0.24/0.15/0.08 -> 124/132/140
      (`floor_sol_frac`, default 0.3 = thesis). Running: GreenLight with ISO-equivalent soil and mature soil start
      (`gl_variant.py launch iso`, then `compare iso`) to see what gap remains. Then decide the floor/soil model.
      RESULT of the ISO-soil rerun: GreenLight 208.5 kWh/m2 (soil sink 11.8), ours 120.6 -> ours/GL 0.58. The soil
      confounder explains only ~21 of the 109 kWh/m2 gap; the rest is our model. GreenLight April nights: thermal
      screen 72 % closed, half the pipe heat is radiative (to floor/canopy, then lost by FIR through the cover), cover
      and top-exchange losses ~25 W/m2 plus floor release; ours loses ~25 % less at night and heats almost nothing by
      day in spring/autumn. `test_reproduce` PASS with `floor_sol_frac` added. Next: separate FIR-to-sky loss,
      screen leakage and day-time heating, then recalibrate against sourced values (not by fitting).
      ROOT CAUSE FOUND (controlled constant-weather runs, `gl_ctrl.py`, 25 s each): steady night envelope loss
      agrees (screen closed: ours 48 vs GL ~44 W/m2; screen open 17.1 vs 17.3), so envelope/screen are fine. The
      gap is TRANSPIRATION: our law LE = 0.21*I + 14*VPD (thesis, avocado) gives 398 kg/m2/yr vs GreenLight 645
      (tomato, LAI 2.6). Too little latent heat -> too much sensible solar gain -> ours is 2-3 K hotter, 20-25 RH
      points drier, and heats ~nothing in spring/autumn. Regression of GL's hourly transpiration: LE = 0.30*I +
      53*VPD (R2 0.94). With `transp_rad` 0.4286 (x0.7 = 0.30) and `transp_vpd` 53: heat 199.6 vs GL 208.5 kWh/m2
      (ratio 0.96, passes +-15 %), transpiration 677, June 22.6 C / 76 % RH (GL 22.3 / 80). Summer: ours still hotter
      (46 h > 30 C, max 34.5 vs GL 7 h, 31.9) because our full-open vent capacity is 6+3*wind = 16.5 ACH vs GL ~24-30;
      `vent_ach` 9, `vent_ach_wind` 4 gives 22 h > 30 C, heat unchanged. New Envelope options (defaults = thesis,
      `test_reproduce` PASS): `floor_sol_frac`, `transp_rad`, `transp_vpd`, `vent_ach`, `vent_ach_wind`, mirrored in
      greenhouse_fast. NOTE site_opt yield = yield_glass x light^0.8 (no climate): the hot/dry summer never reduced
      reported yields; crop.py (T, VPD) is not used on the site path. Remaining: Mar-Apr ours 21/8 vs GL 27/18 and
      Dec 29 vs 12 kWh/m2 (shape), GL exceeds the design load 183 h/yr (4.7 kWh/m2, ~2 %, morning/late-afternoon
      transitions), source the transpiration/vent coefficients, wire into site_opt for tomato/cucumber, rerun chain.
      Venvs set up on this machine (portfolio + greenlight, via uv). Original item text:
- [~] R7. Port GreenLight physics into our sim (DONE 2026-10-03, awaiting user review; ours stays the search tool,
      GreenLight the reference). Done: crop transpiration A0(1-exp(-k LAI))G + B0 LAI VPD with seasonal LAI
      (`transp.py`; tomato validated vs GreenLight, cucumber A0/B0/k from Medrano 2005 tested against Nikolaou 2017 measured
      lysimeter data: -7 % / -10 %, tested only at LAI 1-1.9, design LAI 3.0 is an extrapolation); Vanthoor roof-vent law
      (`vent_area_frac` 0.117); GreenLight floor + 5 soil layers over ISO deep conductance (`soil_layers`); floor light share from
      canopy optics (`floor_light_frac`, extinction 0.7 PAR / 0.27 NIR, floor reflectance 0.65 / 0.5). All options default to
      thesis behaviour; `test_reproduce`, `test_fast`, `test_costing`, new `tests/test_r6_options.py` PASS (bit-identical
      fast vs reference). Result vs GreenLight (Caledonian tomato, annual): heat 197.8 vs 208.5 kWh/m2 (0.95, passes +-15 %),
      monthly r 0.98, RMSE 3.0 kWh/m2/month, transpiration 640 vs 645 kg/m2, hours > 30 C 23 vs 7 (max 33.7 vs 31.9).
      Controlled mature-crop cases (`gl_ctrl.py`): nights agree within ~5 %, summer LE within 10 %, spring ok, dull days
      ours 40 % low on heat. Remaining: Mar-Apr / Oct shoulder (ours 14 vs 18 and 20 vs 26 kWh/m2), dull-day low-light
      transpiration (GL 48 vs ours 35 W/m2), summer slightly warm, GL exceeds design load 183 h/yr (4.7 kWh/m2).
      Tested and rejected: refitting A0/B0 on GreenLight's hourly LE with true LAI (A0 0.30, B0 31.7 -> heat 237; A0 0.33/B0 26 -> 216;
      A0 0.34/B0 22.2 -> 201; current 0.372/20.7 -> 197.7 vs GL 208.5): no gain; the residual is GreenLight's concave light response
      (LE 33 vs ours 23 W/m2 at 1-80 W/m2), not representable in the linear Baille form. `site_opt.py` sampling heat demand updated to
      330 / 205 kWh/m2 (cucumber / tomato). Dry run of 20 sweep jobs: 0 errors, 0.39 s/job.
      GREENLIGHT CONTINUOUS YEAR (done 2026-10-03, `gl_year.py`, no restarts, 25 min): Caledonian tomato yield 62.2 kg/m2 (6 % DM),
      heat 206.7 kWh/m2, harvest peaks May-Aug (lags production ~2 months), mean CO2 648 ppm (ours 662). Ours (CBS-anchored) gives
      36 kg/m2: GreenLight is uncalibrated (Westland-equivalent would exceed CBS), so only the RATIO Caledonian/Westland is a valid test
      -> `gl_westland.py` (GreenLight on the Westland reference house, running), then `python gl_westland.py compare`.
      RELATIVE YIELD TEST (GreenLight Westland run done, 70.1 kg/m2 = 1.46 x CBS): Caledonian/Westland ratio GreenLight 0.89 vs ours 0.76;
      floor light ratio is 0.78, so GreenLight's light elasticity is ~0.47, ours ~1.1 (literature 0.8-1, Marcelis 2006). NOT a bug: kept
      ours (literature-anchored); GreenLight response carried as sensitivity `yield_greenlight_x1.18` (+ `yield_minus15`, `transp_x0.8/1.2`)
      in refine.py. Open question for the user: which yield response to trust for Scotland (+-18 % on yield).
      LESSONS (errors I made and fixed): first controlled runs used GreenLight's young crop (LAI 0.1-0.3) and our synthetic
      weather lacked `w_amb`; both invalidated early summer/dull-day conclusions (night results were fine).
- [~] R8. Yield model (DONE as a first version 2026-10-03, needs sourcing + GreenLight yield): `crop_gh.py` = crop.py
      photosynthesis/canopy/CO2 (now numba, identical results) with annual-crop parameters; fruit partition calibrated so the
      Westland reference house gives CBS (tomato 48, cucumber 65 kg/m2; partition 0.73 / 0.81, plausible 0.6-0.8). Checks:
      light elasticity 0.89 tomato, 1.00 cucumber (literature 0.8 / ~1). Replaces CBS x light^0.8 in `site_opt.evaluate`
      (also CO2 dose from the model, ~40 kg/m2, was 25 placeholder). Finalist effect (same designs, not re-optimised):
      yield 0.86-1.00 of the old formula; cucumber GBP/kg@10 1.00-1.03 -> 1.16-1.23, tomato 1.34-1.38 -> 1.45-1.55; carbon
      +0.04-0.05; heat 190-225 -> 315-345 (cucumber), 117-141 -> 195-220 kWh/m2 (tomato). Both still beat imports
      (1.57 / 1.77) but margins fall to 0.34-0.41 / 0.22-0.30. PLACEHOLDERS: leaf Amax (25 / 30), quantum yield, maintenance
      0.30 g CH2O/m2/h, glucose cost 1.5, fruit DM 0.06 / 0.04, VPD slope, no heat-stress/fruit-set effect, no seasonal
      partition; cucumber LAI shape. Sourcing check 2026-10-03: maintenance, growth respiration, Jmax/alpha compared with Vanthoor 2011 Table 9.1 (in the
      GreenLight install) and Marcelis cucumber growth respiration: ours within ~15-40 %, input_register.csv rows updated; cucumber
      Amax and fruit DM remain literature-range. Still to do: validate tomato against GreenLight's continuous-year yield (run
      ONCE at the end); cucumber yield check vs UK/Scottish commercial data.
- [x] R9. Summer overheating check (2026-10-03, from the R6-R8 chain refined designs): hours > 30 C 0-42 /yr, > 32 C 0-6 /yr,
      heat-stress yield factor 0.999-1.000 at every finalist; our sim runs warmer than GreenLight (23 vs 7 h at Caledonian), so
      this is conservative. No overheating problem in Scotland at vent area 0.117. Vent area is not a costed design variable
      (kept as is: it would only matter if a smaller vent area were tried to save cost).
- [x] R6. Off-season heat: CLOSED 2026-10-03 by the R7 physics port (transpiration law, vent law, soil layers, floor light):
      annual heat 197.8 vs GreenLight 208.5 kWh/m2 (0.95, passes +-15 %), monthly r 0.98; chain rerun done (R6_chain.log).
      Residual shoulder-month / dull-day gap is a limit of the linear Baille transpiration form (see R7), documented, not fixed.
- [~] R10. Run WITHOUT waste heat and stay profitable (user, 2026-10-03). First pass done (fast sim, `nowaste_eval.py`,
      `nowaste_levers.py`, logs in `results/nowaste/`): the refined finalists with waste off (heat pump supplies all heat, no pipe)
      cost cucumber 1.19-1.62, tomato 1.49-1.69 GBP/kg vs imports 1.57 / 1.77; carbon cucumber 0.47-0.91 (import 0.81), tomato
      0.55-0.78 (import 1.30). Cheapest where wind is good (Girvan, Stranraer). Levers (Girvan cuc / Cameronbridge cuc / Girvan tom,
      GBP/kg change vs no-waste base 1.19 / 1.34 / 1.51): low-e glass +0.04-0.07 (light loss beats heat saving), insulated north
      wall ~0, heat-recovery dehum -0.01-0.03, RH 90 % -0.01-0.03, night setpoint -2 K -0.05-0.11, HP 50 % + store -0.07-0.08
      (capex only), utility wind capex -0.06-0.11, double screen x0.35 (unsourced) -0.01-0.04. Package P3 (night -2 K, RH 90,
      HRD, HP 50 % + store, cheap wind): 0.95 / 1.08 / 1.29 GBP/kg, carbon 0.39 / 0.54 / 0.46. At an 8 % commercial discount
      rate (Green Book 3.5 % is the central case) the no-waste base fails (1.43 / 1.57 / 1.80) and P3 passes (1.14 / 1.27 / 1.53).
      CAVEATS before using these numbers: (1) night -2 K raises modelled yield 2-4 % only because maintenance respiration falls;
      crop_gh has no development-rate effect, so treat the yield as unchanged (temperature integration, Koerner/Dutch practice:
      source it); (2) HP 50 % + store is capex only, the store is not simulated: confirm with finalist_lp in LP-sized mode;
      (3) GBP 1,400/kW wind is a utility-scale price, unrealistic at 150-450 kW: needs a mid-size turbine price or a PPA;
      (4) the designs were optimised WITH waste heat; a no-waste sweep (no pipe, free site choice: windy, cheap connection) is the
      proper search. Do it after the caveats are settled (big runs last).
      SECOND PASS 2026-10-03 (user: two tracks in parallel, drop night setpoint, do the half heat pump and cheaper wind):
      `nowaste_study.py` (fast: 6 finalists x track A/B x 6 electricity routes x 3.5/8 %; lp: track B standby vs LP-sized
      heat pump + store), results `results/nowaste/study_fast.log`, `study_lp.log`, `combined.log`.
      * Wind realism fix (site_opt.WIND_NET 0.85, WIND_CF_CAP 41.3 %, Arup 2025 Table 22): before, CF reached 54-62 %.
        Affects track A own-wind slightly (Girvan cucumber 1.10 -> 1.11 with small turbines). Chain rerun will carry it.
      * Half heat pump (LP): the LP picks 45-66 % of design load with a 4-30 MWh hot-water store, saving 0.04-0.06
        (cucumber) and 0.08-0.12 (tomato) GBP/kg vs full standby on track B. Perfect-foresight LP on one weather year:
        a colder year or an outage is not covered beyond the store.
      * Electricity routes (track B, 3.5 %, standby): grid 1.35-1.58 cuc / 1.48-1.60 tom; owned small turbine barely beats
        grid at GBP 2,500/kW once CF is realistic; owned single 2.5 MW turbine 1.11-1.26 / 1.34-1.45 (greenhouse buys at the
        turbine LCOE GBP 49-63/MWh; turbine as its own business pays back in 8-11 yr at 3.5 %, NPV +1.4 to +3.8 M, mostly from
        supplying the greenhouse; export-only NPV -0.3 to +1.4 M); private-wire PPA at GBP 90/MWh 1.18-1.34 / 1.39-1.47;
        wind-farm share 1.16-1.35; sleeved PPA is WORSE than grid (+0.02-0.05): it replaces only the cheap wholesale share.
      * Best track-B estimate (2.5 MW turbine or private wire + LP-sized HP): cucumber 1.04-1.20, tomato 1.23-1.37 GBP/kg at
        3.5 %; 1.30-1.49 / 1.49-1.67 at 8 %; all below imports (1.57 / 1.77); carbon 0.31-0.52 (cuc) / 0.36-0.47 (tom) vs
        imports 0.81 / 1.30. Track A (waste heat) at 3.5 %: 1.07-1.15 / 1.41-1.49; so track B with own wind is within
        0-0.10 GBP/kg of track A.
      Remaining before the track-B sweep: (1) grid export connection for 2.5 MW at a site (cost, queue: Scottish connection
      dates are years out) and planning; Kilbirnie price includes its own connection; (2) private wire needs a farm within
      a few km: map candidate farms near windy sites (track B site list, REPD); (3) colder-year / outage check of the
      LP-sized heat pump (rerun the LP on a second weather year, or keep 60 % as a floor); (4) export PPA price 60 is an
      estimate on a sourced anchor.
      THIRD PASS / VERIFICATION 2026-10-03 evening (goal: verified model + full costing on both tracks): two-track chain
      (`run_chain_tracks.sh`), cold-year-safe LP heat pump, 2010 sensitivity, B7/B8, `cashflow.py` + `costing_report.py`
      (results in the CURRENT RESULTS block at the top and results/costing/FULL_COSTING.md). Verification: tests/test_r10.py
      28/28 PASS; test_reproduce, test_fast, test_r6_options, test_costing PASS (results/test_regress_R10.log); GreenLight
      continuous year on the final track-B tomato design (Girvan, 1.2 ha, RH 90 %, HRD off for the comparison; no restarts):
      heat ours 182.4 vs GreenLight 158.3 kWh/m2 (1.152: misses +-15 % by 0.2 points, ours HIGH = conservative; monthly r 1.00;
      cost effect < 0.01 GBP/kg with turbine power); relative yield (vs the Westland reference) ours 0.971 vs GreenLight 0.934
      (+3.9 %, passes). At Caledonian (8.5 ha, R7) ours was 0.95 low: the model's error sign flips with house size, so the
      +-15 % band holds for 1-9 ha houses. Track B results use the shortlisted industrial sites as locations; a free site
      search for windy land was not done.
- [ ] B6. Heat-source data from operators: real availability, heat profile by month, temperature, contract price
      (replaces the flat mean rate, the outage placeholders and the £0/10/20 heat-price range)
- [~] B7. (2026-10-03: central kept flat whenever the source runs, continuous-process hosts; sensitivity `winter_waste_x0.8` in refine.py; real profile needs B6) Waste-heat rate is flat (annual mean): model the seasonal waste-heat profile; at 10+ ha winter peaks
      exceed it and the heat pump takes over
- [x] B8. (2026-10-03: bound widened to 4.0 m; refined designs now sit at 4.5-5.2 m, off the bound) Gutter height sits at the sweep's 4.5 m lower bound: widen to 4.0 m and check climate effects (cucumber
      high-wire needs height; source the minimum)
- [ ] B9. Concept steel (4–7 kg/m²) looks light: compare with a supplier's structure weight in the RFQ answers

Promised deliverables
- [x] 7. (DONE 2026-10-03: `cashflow.py`, `costing_report.py` -> results/costing/FULL_COSTING.md; organic premium/yield still open under item 9) Lifecycle cash flow + sales report (cash purchase, payback; supermarket price basis; sources for margin,
      organic premium, organic yield)
- [~] 8. RFQ specification: drafted in `RFQ_SPEC.md` (2026-10-03) with quantities per finalist; to issue once the
      user picks the site and suppliers
- [ ] 9. Organic system: digestate fertility, AD CO₂ for dosing (replaces liquid CO₂ and the DAC idea), certifier check

Sourcing debts (`data/input_register.csv` 'pending' / 'placeholder')
- [ ] 10. Screen factor, h_min, path share, hung-crop load (EN 13031-1 annex), ground bearing, snow zone / v_b
      from the UK NA maps, snow V for the UK
- [ ] 11. Asset lives, O&M fractions, labour hours, packing, consumables, battery inverter £/kW
- [ ] 12. Berry/grape yields, WWTP flow per p.e. and effluent temperature profile
- [ ] 13. Embodied factors for screens, ETFE, XPS, polycarbonate
- [ ] 14. Distillery cooling-water heat (second distillery case)
- [ ] 15. Outage timing (distillery, paper) and food/AD shutdown length: operator data (see B6)

Model gaps
- [ ] 16. Wall thermal-mass node (earth-sheltered designs)
- [ ] 17. Inter-span shading of low sun
- [ ] ~~Unmet hours with the double screen~~ retired 2026-10-02: double screen withdrawn (screen factor unsourced)

Business plan (2026-10-05)
- 2026-10-07 FINDING (stale cache): the CO2 price is read from results/compare.json ('defaults'), which simstore did not key on, so
  cached site_opt.evaluate ledgers kept CO2 0.20 after breakeven.py changed. Fixed: compare.py rerun (only co2_price changed) and
  compare.json added to simstore.DATA. Reruns at 0.25: cashflow A B, costing_report, bplan_10m lead (payback 8.8 -> 9.4 yr, NPV 8 %
  +2.23 -> +1.72 M, IRR 10.3 -> 9.8 %, opex 0.867 -> 0.899/kg, CO2 0.126 -> 0.157/kg). NOT rerun (still CO2 0.20, self-consistent):
  viable_5ha*.json, yearround_* DOE/fit/verify (desktop job), workbook scenarios S0-S4 use their own input (0.25, done)
- RUN 2026-10-07 (user: "check them all off, BP4-32 in order, firecrawl connected, do everything you can, leave GitHub alone, CO2 0.25"):
  working BP4 -> BP32 in order; each item ends ticked, or marked BLOCKED with the exact thing needed (quote, user decision)
- [x] BP1. Pack started: `BUSINESS_PLAN.md`, figures bp01-bp11, `bplan_*.py`. Regression tests rerun and PASS
      (test_reproduce, test_costing, test_r10), and the costing was rerun after the price fix
- [x] BP2. Winter price defect fixed in `cashflow.defra_monthly` (CIF where DEFRA has < 3 observations)
- [x] BP3. Independent verification `bplan_verify.py` (13 pass, 3 flags)
- [x] BP4. (DONE 2026-10-07: written as the Claude Doc in BP26, https://claude.ai/code/artifact/cf65b986-f2ca-4a1a-a924-13c38a97152b; lead = GBP 10 M 2.9 ha case at CO2 0.25) Write the business plan itself from the pack (structure: summary, market/price, design, operations,
      financials 8 % + 3.5 %, risks, funding ask). Wait for the price evidence (BP5) before the financial headline
- [x] BP5. (desk evidence done 2026-10-07; buyer indication = user outreach, listed in PRICE_EVIDENCE.md) Sales-price evidence: supermarket contract prices vs DEFRA wholesale, low-carbon/Scottish premium (= §5 step 2)
- [x] BP6. (DONE 2026-10-07, DEFRA Table 17 in PRICE_EVIDENCE.md; a named UK high-tech grower yield still not found) UK commercial yield evidence for cucumber and tomato (AHDB, growers): yields are 0.89-1.03 x CBS NL
- [x] BP7. (REVIEWED 2026-10-07: lca/THESIS_NUMBERS_REVIEW.md; README, CLAUDE.md, GEMINI.md, AGENTS.md edited 2026-10-07 with user OK: COP definition note, 80 °C as design condition, no 'near Carnot'; 4.29 itself unchanged) Thesis README / CLAUDE.md headline (COP 4.29 at 80 °C supply, near Carnot): review the thesis numbers
      before any public use; the study does not use them
- [x] BP8. (DONE 2026-10-07: cashflow.build re-prices the LP wind cost at the turbine LCOE for each discount rate (annuity ratio); 3.5 % results unchanged,
      8 % NPV -£0.1 M, LCOP 8 % +£0.02/kg on the track A/B cases; combined greenhouse+turbine unchanged; tests PASS) cashflow.py: greenhouse buys turbine power at the 3.5 % LCOE also in the 8 % NPV (< 0.02 GBP/kg); recompute
      the LCOE at 8 % for the 8 % case
- [x] BP9. (done 2026-10-05, 3,724 rows; screen and figures rerun) Monthly import prices for diversification crops: `fetch_imports_monthly.py strawberry raspberry blueberry
      lettuce pepper avocado` -> `data/imports_monthly_diversify.csv` (running 2026-10-05); then rerun
      `bplan_diversify.py` and `bplan_figures.py`
- [x] BP10. (DESK SOURCING DONE 2026-10-07: DIVERSIFY_SOURCING.md; model placeholders unchanged; UK grower yields, picking rates, winter berry contracts NOT found) Diversification phase 2 (sourcing, before any modelling): cherry/vine tomato + mini-cucumber yield and
      labour (KWIN-AGV, AHDB); strawberry everbearer table-top yields under glass with and without LEDs, picking rates;
      raspberry long-cane yields per crop; lettuce head weight and cycles; baby-leaf yields; LED W/m2 for a vertical
      farm; winter berry contract prices
- [ ] BP11. (BLOCKED 2026-10-07: needs a calibrated strawberry/lettuce crop model; DIVERSIFY_SOURCING.md has no UK yield, picking-rate or winter-price source to calibrate against, and the sourcing rule forbids placeholder-calibrated results) Diversification phase 3 (after BP10): cool-zone strawberry/lettuce in crop_gh + transp; multi-zone campus
      (warm + cool house, shared heat pump and store, simultaneous heating/cooling) in finalist_lp; lit winter
      strawberry case. One sweep at the lead site only (big runs last)
- [ ] BP12. (BLOCKED on BP11 outputs: zone revenue and labour need modelled monthly yields per zone) Diversification phase 4: zones in cashflow.py (portfolio revenue and labour by month)

- [x] BP13. (CLOSED 2026-10-07 by later work: step 1 sweep still at 3.5 % (NOT re-run at 8 %: open); 2 single vs double = BP23/BP28 (single wins); 3 boiler = BP19a; 4 CO2 = BP28 (1,000 ppm, lower rejected) + BP20b pricing; 5 labour = BP27a(h), residual itemised BP19b, quotes still needed; 6 lit winter = BP32/BP34) Design-to-cost study (user challenge 2026-10-05: design must be able to cut cost). The capital of the lead
      design (track B cucumber, 8 %) is £0.66/kg: residual £0.154, heat pump £0.136, double AR glass £0.131,
      contingency £0.058, steel £0.054. Steps, cheapest first:
      (1) re-optimise at 8 % (refine.py; the sweep was optimised at 3.5 %);
      (2) single/diffuse vs double AR glass at 8 %;
      (3) electric peak boiler in the heat-pump sizing (quick test 2026-10-05 on hourly load, DEA ch. 41
          €0.155 M/MW vs heat pump €1.15 M/MW: HP 50 % + boiler -£0.050/kg vs standby at 8 %, only ~-£0.01 vs the LP
          + store case; add the boiler to finalist_lp);
      (4) CO2 dosing strategy (34 kg/m2/yr, £0.12/kg) in crop_gh;
      (5) labour and packing sourcing (KWIN) and an itemised RFQ of the £94/m2 residual;
      (6) retest lit winter production with own-wind power (tomato winter £1.70-1.85 vs £0.90 in July).
      My estimate of the total, unproven: £0.15-0.30/kg

- [x] BP14. (DONE: 14 % commission in cashflow; contract evidence = PRICE_EVIDENCE.md BP5/BP30) Price basis (user, 2026-10-05): central = DEFRA wholesale net of 14 % market commission (BritFarmers,
      T. Harfield, 'UK supermarket contracts vs wholesale pricing 2026', trade guide, secondary). Was 5 % (placeholder).
      Note from the same guide: contracts pay stability, not a premium (iceberg contract 30-40p/head vs ~54p net
      wholesale; strawberry contract £3.50-5.20/kg gate), so the import-parity contract scenario needs real evidence.
      Compliance £8-50k/yr (our overheads £3/m2 ≈ £30k/ha cover it)
- [x] BP15. (DONE 2026-10-07 for cost: shelf_chain.py + SHELF_CHAIN.md; duty/BTOM sourced; port/RDC/importer margin PLACEHOLDER; cucumber carbon chain by origin NOT built) Soil-to-shelf boundary (user, 2026-10-05). Functional unit: 1 kg on a Central Belt supermarket shelf.
      Stages for UK and imports, cost and carbon: grow -> pack -> to RDC -> RDC -> store -> shelf, plus shrink.
      Imports today = CIF at the UK border + port->RDC haul only: add UK port handling, border (BTOM) charges, UK
      Global Tariff duty by origin, importer/ripener margin, transit loss on cost; common downstream stages
      (RDC->store, retail margin) shown for both; differential shrink (shelf life) sourced (WRAP)
- [x] BP16. (CLOSED 2026-10-07: components now fixed + stepped + per-m2: fixed residual 17.7 % (BP19b/d), perimeter 10.1 %, HV connection stepped on kVA (BP23a), heat pump per DEA curve, turbines per module (BP35b). Size evidence from the year-round DOE, cucumber, double AR, medians over mixed designs: capex/m2 415 (<2 ha) -> 348 (6-9 ha), -16 %; LCOP 8 % 1.25 -> 1.28, i.e. NO LONGER rising with size once wind scales with area (fixed single turbine: 1.33 -> 1.34 at 4-6 ha). Sourced scale curves for glass, steel and heat pump beyond DEA still not found) Capex scaling (user, 2026-10-05: £/m2, £/kW, £/kg do not scale linearly). Today: structure =
      quantities x flat unit rates + a £94/m2 residual calibrated at 1 ha, linear in area; heat pump on the DEA
      1-10 MW curve (weak scale effect). Symptom: the size study gives cost/kg rising with size (cucumber 1.18 at
      5 ha -> 1.30 at 30 ha). Replace with fixed + stepped + per-m2 components and sourced scale curves; rerun the
      size study
- [x] BP17. (DONE: greenhouse and energy capex reported separately in the workbook and BP19a/BP23; PPA, grid + small turbine and owned-turbine routes compared in BP17 results, BP23, BP28, BP35b; leasing not modelled) Initial expenditure (user, 2026-10-05): report greenhouse capex (£4.1M) and energy-route capex
      (turbine £5.9M) separately; test routes without the owned turbine (private-wire PPA, grid + small turbine,
      leasing) by capex and by cost/kg.
      FIRST RESULTS 2026-10-05 (`results/bplan/capex_levers.log`; lead design, track B cucumber, design-search basis,
      i.e. no dev/contingency/consumables). New option `site_opt.evaluate(..., hp_boiler=f)`: heat pump at f x design
      load plus an electric peak boiler (DEA ch. 41: 0.155 MEUR/MW, eff 0.99), hourly split, default off; tests PASS.
      * Single 2xAR glass + HP 69 % + boiler: £/kg -0.055 at 8 % (-0.016 at 3.5 %); greenhouse struct + heat capex
        -£0.20M; yield 62.0 vs 54.6 kg/m2 (+14 %, more light); heat 494 vs 284 kWh/m2; boiler 5 % of heat. Best case
        found.
      * Same design on a private-wire PPA: no turbine capex. Initial spend £3.46M vs £9.56M (-64 %), +£0.014/kg at 8 %
        vs today's lead. BUT Stranraer has no large turbine within 5 km; Girvan has 16 within 3.1 km, so the
        no-turbine route means the Girvan site (its cucumber cost is within £0.02/kg).
      * Double AR glass + boiler: HP 69 % -0.018/kg at 8 % (-£0.32M), HP 50 % -£0.52M at -0.007/kg.
      * Below about 60 % HP with single glass the import peak crosses the next network-charge band (£23k -> £77k/yr)
        and costs jump. The £150k HV import connection is still fixed: it must scale with kVA (BP16).
      * Caveats: the boiler makes the heat system standby-safe (HP + boiler = design load), which removes the
        cold-year / outage risk. Single-glass yield (+14 %) rests on the crop model's light response (elasticity
        ~1 for cucumber). The private-wire price (£90/MWh) is an estimate. Confirm in cashflow.py at the full costing
        basis (with dev, contingency, consumables, 14 % commission) before the plan uses it

- [x] BP18. Capex/opex workbook (user, 2026-10-05): `../business_plan/Glasshouse_Capex_Opex_Model.xlsx`, built by
      `bplan_workbook.py` from `results/bplan/xlsx_inputs.json`, checked by `bplan_workbook_check.py` (formulas engine,
      1,465 cells, 0 errors; no Excel/LibreOffice on this machine, the user has ONLYOFFICE). Sheets: Read Me, Inputs,
      Rates, Scenarios (S0-S4), Capex (by item and driver), Energy (turbine LCOE at 8 % and 3.5 %: fixes BP8 inside the
      workbook), Opex, Results, Scale, Capex Levers, Prices, Sources.
      Results at 14 % commission, steady-state (no ramp, no residual):
      * S0 £1.759/kg at 8 % (£1.470 at 3.5 %), greenhouse £4.08M, day-one spend £9.98M.
      * CORRECTION to the BP17 first results: against the LP heat pump + store (S0), the peak boiler LOSES (S1
        +£0.033/kg at 8 %). It only beats the full-standby heat pump. Single glass + boiler (S2) -£0.024/kg.
      * At 8 % the private wire (S3) costs the same per kg as owning the turbine (1.755 vs 1.759): the turbine's LCOE
        at 8 % is £72/MWh. Day-one spend £4.15M (-58 %). At 3.5 % the private wire is +£0.06/kg.
      * Scale sheet (assumed 25 % fixed residual, 15 % perimeter items, both UNSOURCED user levers): 1 -> 30 ha cuts
        capex/m² by 18 %.
      KWIN 2026: user cannot buy it; not obtained by other means (copyright). Legitimate routes: university library or
      alumni access, an interlibrary loan, asking WUR for a student/researcher copy, older KWIN editions in the WUR
      eDepot, Agrimatie (free WUR data)
- [x] BP19. Next capex work (split into parts and done 2026-10-05; tests: `tests/test_bp19.py`, `tests/test_costing.py`):
      - [x] BP19a. Boiler cases WITH a store. `finalist_lp.solve(boiler=True)` sizes heat pump, electric peak boiler and
            hot-water store together (rule 'standby': HP + boiler >= design load); `bplan_lp_boiler.py` runs S1-S4 in
            parallel and folds the standby results into `xlsx_inputs.json` (`boiler_store.json` keeps both rules).
            THIS REVERSES the BP18 correction. Levelised £/kg at 8 % vs S0 £1.759: S1 1.686 (-0.073), S2 1.617 (-0.142),
            S3 1.657 (-0.102), S4 1.719 (-0.040); at 3.5 % S1-S3 -0.03 to -0.12, S4 +0.01. The LP picks a small heat pump
            (S1 457 kW = 37 % of design) + boiler 788 kW + 4.2 MWh store: boiler capacity is cheap. Day-one spend vs S0
            -3 % (S1), -2 % (S2); private wire S3/S4 -61 %/-62 %. Caveats: the 'lp' rule (no standby, 2010 winter not
            checked) is £0.004-0.04/kg cheaper still; yield +14 % for single glass rests on the crop model's light response
      - [x] BP19b. Residual itemised in `data/residual_items.csv` (`bplan_residual.py`; RFQ_SPEC §3.7). Seven systems,
            fixed vs per-m2, lives (cashflow.py now replaces each at its own life). ONLY the climate-computer line has a
            public source (hcts.tech, 25 Mar 2026, vendor page); 85 % of the £94/m2 is a labelled PLACEHOLDER split. Quotes
            replace it line by line. Fixed share 17.7 % (was the unsourced 25 %)
      - [x] BP19c. Second-hand glasshouse: `bplan_secondhand.py`, `results/bplan/secondhand.json`, RFQ_SPEC §3.8, Levers row.
            vs new single glass (£191/m2 incl. residual): low -13, central +0, high +20 £/m2 => -0.026 / +0.001 / +0.040
            £/kg at 8 %. Fit-out (£64/m2) + re-erection eat the purchase saving. Purchase £60/m2 sourced (SAC/SRUC Table 11);
            re-erection and glass replacement are PLACEHOLDERS. The "Avéro 2025" guideline named earlier could not be found
            online and is not used: need the document or a dismantler quote
      - [x] BP19d. Scale shares: fixed residual 17.7 % from BP19b; perimeter share 10.1 % geometric (wall glazing + bars; a
            lower bound). Model option `CEA_RESID_FIXED` / `costing.capex(fixed_share=)` (default 0 = unchanged). Size study
            rerun (cucumber, track B; `size_cucumber.json` linear, `size_cucumber_fixedresid.json`): fixed residual cuts
            £0.02-0.03/kg at 5-30 ha but cost/kg STILL rises with size (Creamery 1.159 at 5 ha -> 1.275 at 30 ha). Cause
            (checked): the single 2.5 MW turbine covers 69 % of load at 5 ha but 22 % at 30 ha, so electricity goes
            £93 -> £151/MWh (energy £0.176 -> 0.294/kg), outweighing the 5 % capex/m2 saving; yield also falls 50.5 -> 47.5.
            A bigger site needs a bigger energy source (BP17), not a capex curve
      Open follow-ups from BP19:
      - [x] BP19e. `business_plan/Glasshouse_Capex_Opex_Model.xlsx` overwritten 2026-10-05 (0 formula errors; S0-S4 8 % £/kg 1.759 / 1.686 / 1.617 / 1.657 / 1.719)
      - [x] BP19f. (DONE via BP29, verified 2026-10-07: changing CEA_RESID_FIXED re-costs in 1.3 s vs 7.3 s cold, same yield, physics not re-run) Split the store so physics is cached once and cost-only options (residual share) apply after (size study
            fixed pass cannot reuse the linear pass today)
      - [ ] BP19g. (BLOCKED: outbound RFQ emails are the user's to send; RFQ_SPEC.md is ready) Quotes: send RFQ_SPEC §3.7/§3.8; re-run `bplan_residual.py`, `bplan_secondhand.py`, workbook
      - [ ] BP19h. (cucumber DONE in BP35b: 90-point wind-scaled DOE; TOMATO wind DOE stopped at 34 of ~80: BLOCKED on the 32 GB desktop, `python bplan_yearround.py doe tomato 80` with CEA_WORKERS=5, resumable) Size study with the energy source scaled with area (turbine count or PPA by load), tomato too
      - [x] BP19i. (2010 CHECK DONE 2026-10-07; GreenLight/yield-source confirmation of S1 still open) Boiler cases: 2010 cold-year check for the 'lp' rule.
            coldyear.store_check(boiler_kw=) and a report-only check in finalist_lp._run (lp + boiler). On the stored S1-S4 results
            the 'standby' rule leaves 0 h unmet in 2010 in all four; the 'lp' rule (no standby) leaves 179 h (S1), 0 h (S2), 106 h (S3),
            244 h (S4) unmet (15-62 MWh). So the 'lp' saving of GBP 0.004-0.04/kg is NOT real without a 2010 floor: 'standby' stays the basis
- [x] BP20. (DONE 2026-10-07: 20a, 20b) Gemini notes check (2026-10-05; restored after a parallel edit dropped it). `business_plan/` and `docs/`
      COMPONENT_COST_BENCHMARKS.md + LIQUID_CO2_PRICING_SCOTLAND.md (identical copies) are NOT citable: no URL/page for
      any price, "audited/validated" on unverified numbers, our own 1.6 kg/m fed back as "verified", "Saint-Gobain
      Cultilene" (a substrate brand) named as a glass maker, RVO EG misread. DECISION: no rate change from them.
      User contacted Lothian Supply / Clean Carbon (Livingston) for CO2, 2026-10-05.
      - [x] BP20a. CO2 £0.20 -> £0.25/kg DONE 2026-10-07 (user OK): breakeven.py P, bplan_workbook.py, bplan_diversify.py,
            input_register.csv; reran cashflow.py A B (results/bplan/cashflow_co2_025.log), costing_report.py, workbook (1,468
            cells, 0 errors; S0 8 % LCOP 1.759 -> 1.788). viable_5ha*.json / capex10m*.json still at 0.20: rerun in BP23c/BP28a
      - [x] BP20b. (DONE 2026-10-07 as priced sensitivities; supplier tank/capture capex still needs a quote) Replace `co2_free` lever with priced routes: cashflow.SENS co2_recovered_low/high = GBP 0.048/0.088 per kg (US ethanol-plant production + distribution, secondary), co2_free kept as the zero-cost upper bound; register rows added
- [x] BP21. (findings entered in data/input_register.csv 2026-10-07; quotes themselves outstanding, see BP19g) Desk research for the 8 RFQ lines (2026-10-05):
      * Water vs air source (S0 cucumber, effluent 12.3+-4 C, intake not costed): HP elec 901 -> 748 MWh/yr, energy
        -£11.8k/yr, -£0.027/kg. Oasthouse intake £100/kW (CIBSE Journal Oct 2019) ~£12.5k/yr at 8 %: cancels it.
        DECISION: air source unless next to a waste-water works
      * Whole project: Oasthouse £120M / 29 ha = £4.1M/ha all-in 2019 (incl. 70 MW HP + CHP) vs our £4.07M/ha
      * HV: SPEN 'Statement of Methodology and Charges for Connection' Nov 2025 (pdf in repo root) p.52 Example 5:
        600 kVA commercial, new 800 kVA substation teed to 11 kV, 150 m cable = £143,000 (11 kV cable £300/m); p.53
        Example 6 looped = £206,000. SUPPORTS our £150k (~450 kW peak) as sourced; the £310k figure quoted earlier was
        Example 2 (200 homes, £200k of LV mains) and does not apply. Excludes reinforcement
      * Heat store: our DEA formula £766/m3 at ~144 m3. The '£390/m3' is NOT Delta-EE: it is UKERC/ERP 'The Future Role
        of Thermal Energy Storage in the UK' (2020) p.4/p.25, citing ~€470/m3 for a 300 m3 tank (secondary, older
        euros, double our size). DEA at 300 m3 = ~£563/m3. DECISION: keep DEA; the cheaper figure is worth only
        ~£0.008/kg even if adopted
      * Glass: Enerpedia "meerprijs ... ong. 15 EUR/m2" (double AR vs standard; ambiguous); RVO EG 2026 €20/m2 cap
      * CO2: ChemAnalyst USD 345/t; AHDB CO2 guide (Mar 2016) gas-combustion CO2 9p/kg; flue capture €20-25/t
        (VerticalFarmDaily Jun 2026) needs a boiler
      * No public prices: pipe-rail, aluminium, second-hand glasshouse (leads: DS Hortitrade, Ebtech, New Century)
- [x] BP22. (DONE 2026-10-07: DEA ch.40 kept, modular recorded in the register (NOT modelled); double count checked: contractor design_pm is GBP 10/m2 (GBP 0.1 M per ha, GBP 60k of it fixed) at the SAC anchor vs owner dev_frac 5 % (owner's costs by the DEA definition), so the worst-case overlap is that line, about 0.6 % of capex; at the WUR anchor design_pm was an unitemised GBP 93/m2 remainder, relabelled in residual_items.csv; building-cost index for the HICP step still not checked) Heat-pump price basis and residual cross-check (2026-10-05):
      * Official modular price: DEA 'Technology Data for Individual Heating Plants' data sheets (Apr 2026), sheet
        '207 HP air-water,new apart': 160 kW unit (note B: cascade of smaller units) €147.0k total 2025 (equipment
        102.9 + install 44.1) = €919/kW; fixed O&M €2,932/unit/yr; life 20 yr. 'ex apart' 320 kW €312.4k = €976/kW,
        upper 500 kW €374.8k = €750/kW. vs DEA el/DH ch. 40 (our basis) ~€1,140/kW at 0.86 MW, O&M €2,127/MW/yr,
        25 yr. Annualised at 8 % for 857 kW: ch. 40 £837k -> ~£80k/yr; modular new-apart £675k -> £69k + O&M £13.5k
        = ~£82k/yr. DECISION (pending user): modular is no cheaper per year (more O&M, shorter life) but gives N+1
        redundancy and staging. Keep ch. 40 as base; add modular as a scenario
      * Residual cross-check: WUR/LEI Rapport 2016-068 'Local-for-local productie kastomaten' (edepot.wur.nl/387511)
        Bijlage 3 Table B3.1: standard Dutch high-tech tomato glasshouse 4-8 ha (7 m, diffuse glass, 1 screen, boiler
        + heating, CO2 dosing, hanging gutters, basin, irrigation, computer, electrics, internal transport, service
        area; excl. CHP and lighting) €110-120/m2 (2012-14, NL); England '+ / ++' (0-10 % / >10 % more). x1.29 HICP
        -> ~€142-155/m2 NL 2025, ~£125-150/m2 England. Our SAC anchor £200/m2 (1 ha, single glass) is 30-60 % higher;
        part is scale (1 vs 4-8 ha). Supports the capex -20 % lever as plausible at 4+ ha. HICP is not a construction
        index: check with a building-cost index
      * Residual lines (data/residual_items.csv): no public line-level prices found for install labour, vents,
        irrigation, crop wires, electrics (vendor blogs / US guides only, not usable). Quotes needed
      * Check double count: residual design_pm (~£104k: "design, permits, PM") vs cashflow dev_frac 5 % (£177k:
        "design, planning, legal, SI")
- [x] BP23. 5 ha viable case (2026-10-05, `bplan_5ha.py`, results/bplan/viable_5ha*.json; track B cucumber, Stranraer,
      heat pump + boiler + store LP 'standby', fixed residual 17.7 %). Grid (design-search £/kg, kg CO2e/kg): own turbine
      beats sleeved PPA and grid on BOTH; strip vs compact layout within £0.01 (use compact). Front: single glass 0.996 /
      0.486 (Y 56.3), double 1.059 / 0.431 (Y 49.5): double costs ~£1,150/t CO2e abated. Carbon 0.49 vs ~0.25 at 1 ha:
      one 2.5 MW turbine covers less; ~0.35 kg/kg is non-energy. Investor basis (cashflow.build), single glass: LCOP 8 %
      £1.51 at DEFRA price (NPV -£10.5M); import-parity contract £1.57: NPV 8 % +£1.31M, IRR 8.9 %; +CO2 £0.25: IRR 8.3 %;
      +free CO2: IRR 11.0 %; +capex -20 %: IRR 12.0 %. Double glass at contract: NPV -£2.5M. Greenhouse capex £16.1M
      (£321/m2; store £1.34M at 386 MWh, boiler £0.86M); with turbine £22.0M, combined NPV 8 % +£0.35M, IRR 8.2 %.
      FIX: cashflow.build now includes peak-boiler capex and O&M (was missing; no-boiler runs unchanged)
      - [x] BP23a. (done, see the DONE line below) HV import connection still £150k fixed but 5 ha import peak ~2.1 MW (SPEN Example 5 is 600 kVA):
            scale with kVA (BP16); likely higher
      - [x] BP23b. (turbines/wind-farm share per area DONE in BP35b: cucumber 4.4 ha, 4 turbines, carbon 0.34-0.39; the GreenLight check of single glass stays open: GreenLight is tomato-only, BP25 resolved the +14 % as the Dutch-anchor effect) Second turbine / wind-farm share at 5 ha for carbon; GreenLight yield check of single glass (+14 %)
      - [x] BP23c. (SUPERSEDED 2026-10-07: the lead is the GBP 10 M 2.9 ha case; business plan written as a Claude Doc (BP26); minimum price at 8 % for the lead = GBP 1.48/kg ex-farm (= LCOP 8 %), 3.5 % GBP 1.27; the workbook is NOT rebuilt on the lead: see BP26a) Rebuild workbook + business plan on the 5 ha case; minimum contract price at 8 % (~£1.53/kg)
- [x] BP24. (a-d done) 5 ha follow-ups (user, 2026-10-05):
      - [x] BP24a. COP levers: new options `pipe_m2` (emitter m/m2, costed via costing.bill) and `hx_scale` (physics only,
            HX cost NOT in LP: placeholder) in site_opt.site_setup; `python bplan_5ha.py cop` -> viable_5ha_cop.json.
            Electricity at 5 ha single glass is £0.175/kg + network £0.027 (not 9p). Results (search basis, compact
            single own turbine): pipe 2.25/hx1 SCOP 3.46 £0.994; 3.4/hx1 3.80 £0.980; 4.5/hx1 4.01 £0.966;
            4.5/hx2 4.17 £0.961 (HX cost not counted: not worth it). Carbon flat (0.483-0.487): power is mostly wind.
            DECISION (proposed): pipe-rail + grow pipe 4.5 m/m2 (extra pipe at the £8/m PLACEHOLDER). Investor basis:
            `python bplan_5ha.py cashflow_cop` -> viable_5ha_cop_cashflow.json: capex £16.61M; LCOP 8 % £1.486 at
            DEFRA (NPV -£9.75M); contract £1.57: NPV +£1.98M IRR 9.2 %; +CO2 £0.25 IRR 8.7 %; +free CO2 IRR 11.3 %;
            +capex -20 % IRR 12.4 %; free CO2 + capex -20 %: NPV +£9.39M IRR 14.8 % (25 s run, LP cached)
      - [x] BP24b. Speed: finalist_lp solves with io_api="direct" (CEA_LP_IO=lp restores LP files); warm start
            `store_kwh0` gives 1 solve per case (6 solves for 6 cases vs ~15). Check: pipe 2.25/hx1 0.994/0.485 vs grid
            0.996/0.486. Memory is the limit on this 8 GB machine (~1.3-1.5 GB free with the user's apps): CEA_WORKERS=1
            unless apps are closed
      - [x] BP24c. Retailer-partner model (ECF/REWE Wiesbaden 2021). New cashflow.build options commission, haul_mult,
            pack_mult; `python bplan_5ha.py retailer` -> viable_5ha_retailer.json (SCOP 4 case, contract £1.57). Model
            confirms 22.5p/kg = packing 10.0 + haulage 4.6 + commission 7.9 (commission 5 % is a PLACEHOLDER, 3-8 %).
            NPV 8 % / IRR: via marketing org +£1.98M 9.2 %; direct (no commission) +£4.42M 10.7 %; + retailer backhaul
            +£5.86M 11.5 %; + bulk crates packing x0.5 (PLACEHOLDER) +£7.41M 12.4 %. If the retailer deducts our haulage
            from the price, backhaul adds nothing (+£4.43M)
- [x] BP25. (RESOLVED in BP28 2026-10-05: model anchored on single plain glass; cap = light-only CBS expectation 0.976) Single-glass yield check (2026-10-05). GreenLight is tomato-only, so no direct cucumber check. Model: single vs
      double light_rel 0.903 / 0.850 (+6.2 %) but yield 56.3 / 49.5 (+13.8 %): implied light elasticity 2.2 vs
      0.8-1.0 (Marcelis et al. 2006; register). Cause not yet found (temperature/humidity response under single glass?).
      Capped at light x elasticity: single Y 52.4 (e 1.0) / 51.8 (e 0.8). SCOP 4 case at contract: NPV 8 % -£0.81M /
      -£1.26M (IRR 7.5 / 7.2 %); with direct contract + backhaul +£2.80M / +£2.31M (IRR 9.7 / 9.4 %). Single still beats
      double (double at contract -£2.52M). USE THE CAPPED YIELD in the plan until the +13.8 % is explained
      - [x] BP25a. (resolved, see BP28) Find why crop_gh gives 2.2x the light response for single glass (compare hourly T_air, RH, CO2, LAI)
- [x] BP23a DONE 2026-10-05: HV import connection now stepped on peak kVA (`cashflow.hv_conn_gbp`, input `hv_conn_steps`):
      SPEN Nov 2025 Ex. 5 (<=800 kVA £143,000), Ex. 17 (<=1 MVA £153,900), Ex. 18 (<=2.4 MVA £633,900), +£75k per 800 kVA
      above. 5 ha SCOP 4 case peak 1,852 kW -> £633,900 (was £150k). 1 ha cases -> £143k (was £150k)
- [x] BP26. (UPDATED 2026-10-07 late, cloud: Summary and Funding and financing rebuilt on the lit 2.9 ha lead with finance.py results (routes table, stresses, Monte Carlo, phasing), checklist + asset-finance quote, ECA premium, heat-source run; Market/Design/Operations/Financials still describe the unlit GBP 9.9 M case and say so) (DONE 2026-10-07, Claude Doc https://claude.ai/code/artifact/cf65b986-f2ca-4a1a-a924-13c38a97152b; BP26a workbook NOT rebuilt on the lead) Business proposition report (user, 2026-10-05: shareable Claude Doc; investors/bank at 8 % first, 3.5 %
      public-value second). Numbers from `python bplan_5ha.py plan` -> results/bplan/viable_5ha_plan.json (SCOP 4 case,
      capex £17.16M incl. HV £0.63M; central = yield capped at light gain + direct retailer contract at £1.57):
      central LCOP 8 % £1.539, NPV +£0.91M, IRR 8.6 %; model yield +£3.87M 10.3 %; via marketing org -£1.37M 7.1 %;
      wholesale -£12.3M; upsides backhaul +£2.25M 9.4 %, free CO2 +£4.34M 10.6 %, capex -20 % +£5.00M 11.6 %, both
      +£8.43M 14.0 %; risks CO2 £0.25 +£0.05M 8.0 %, yield -15 % -£5.28M 4.5 %, price -10 % -£3.64M 5.7 %, capex +20 %
      -£3.18M 6.3 %
      - [x] BP26a. (DONE 2026-10-07 as a NEW lead workbook: `bplan_workbook_lead.py` -> business_plan/Lead_Finance_Model.xlsx, lit lead 2.9 ha with live formulas for price, CPI, tax with full expensing and losses, ECA + asset finance with holiday, DSRA, WC, stresses and grant; recalculated in LibreOffice it matches finance.py exactly, also under yield -15 % + capex +20 % + grant. Physics lines are inputs from lit_open.json. The old 1 ha S0-S4 workbook is left as it was) (was: NOT DONE, user decision wanted: the workbook is built around the 1 ha S0-S4 concept (own turbine, text notes per scenario); a lead-case workbook needs a new inputs builder and edits to bplan_workbook.py, about a day) Workbook on 5 ha: bplan_workbook.py needs an xlsx_inputs_5ha.json builder (scen schema: quantities,
            design/hp/boiler/store kW, heat/elec MWh, elec/grid price, en_cost, net, Y, kg, turbine, ...) + CEA_XLSX_IN,
            and the stepped HV cost. Bigger than first estimated (~1 h); report does not depend on it
      - [x] BP24d. (DONE 2026-10-07: GRANTS.md; no open grant for a Scottish glasshouse found, FDPSS up to GBP 0.4 M for a packhouse only) Grants: GHISP closed and aimed at heat-tech makers; FPMC 40 % (Annex I) is processing/marketing, so a
            packhouse may qualify, not the glasshouse. `../Market/02_SCOTLAND_GO_TO_MARKET_STRATEGY.md` "30-50 % capital
            match" is unverified. NPV gain ~= grant at t0
      - Grid connection: still needed (export of ~8 GWh surplus; ~1 GWh/yr import, 2.1 MW peak in calm spells)
- Note: user's DEFRA file `../fruitvegprices-260928.csv` is identical to `data/defra_wholesale_prices.csv` (17,702 rows,
  0 differences); source page https://www.gov.uk/government/statistical-data-sets/wholesale-fruit-and-vegetable-prices-weekly-average

- [x] BP27. (done, with BP27a) Capex/opex audit of the 5 ha case (user, 2026-10-05: £23 M raise too high). Findings in `CAPEX_OPEX_AUDIT.md`
      (estimates, nothing rerun). To do: (a) standby rule: credit the screen in the design load and/or count the store
      (boiler 6.77 MW supplies 18 MWh/yr) - user decision; (b) HV kVA step + TNUoS bands into the LP (peak cap < 1 MVA);
      one shared turbine/greenhouse connection; (c) turbine capex basis (blended finance + double conn margin) and
      20-yr full repower; (d) split climate_control replacement (computer vs wiring); (e) fix residual lines vs scaled
      residual at 5 ha (design_pm negative); (f) dev/contingency on DEA all-in plant; (g) install_labour vs erected steel
      overlap (RFQ); (h) labour rate to NLW Apr 2026 £12.71 + on-costs (~£16.3/h); then rerun `bplan_5ha.py plan`
      DONE 2026-10-05 for 1-7 (`python bplan_5ha.py lean`, results/bplan/viable_5ha_plan_lean.json, log lean.log):
      two-component plant only (user); new options finalist_lp.run(store=, import_cap_kw=, screen_design=),
      energy_grid 'tp_2p5MW' (third-party turbine, private wire £90), own_2p5MW conn 0, costing WUR 4-8 ha anchor
      (CEA_RESID_ANCHOR=wur, £177/m2), config.design_heat_loss_w(screen=), residual lines pro rata. LEAD: third-party
      turbine, HP 3.7 MW + store 662 MWh, import cap 1 MVA: raise £16.00 M (was £23.06 M), NPV 8 % +£0.41 M IRR 8.3 %.
      Owned turbine alt: raise £21.64 M, combined NPV 8 % +£2.24 M IRR 9.1 %. HP + boiler without store loses
      (-£3.2 M or worse). Finding 6 not a saving, 7 withdrawn (DEA p.22), 5 only ~£0.5 M. Tests PASS
      - [x] BP27a. (DONE 2026-10-07 except two user/outside items: DNO operating-limit term for the 1 MVA cap, and the rebuilt workbook + plan on the lean case = BP26a/BP23c) climate_control split computer 70 % (10 yr) / wiring 30 % (30 yr) in residual_items.csv, PLACEHOLDER ratio, total unchanged; BP8 done; turbine life 20 yr kept as conservative (UK models 25-30+, register row). Original text: ~~(h) labour rate~~ (done in BP28); BP8 transfer price; climate_control replacement split; turbine life;
            1 MVA import cap needs an operating-limit term in the SPEN offer; rebuild workbook + business plan on lean case

- [x] BP28. Design under GBP 10 M (user goal 2026-10-05; `bplan_10m.py`, `CAPEX_10M_DESIGN.md`, results/bplan/capex10m*.json).
      Area 2.5-3.0 ha x glazing x pipe x import cap on the BP27 lean plant. Done: BP25a resolved (crop model is anchored
      on SINGLE plain glass; double AR is 4-5 % below the light-only CBS expectation, single 2xAR 2 % above; new cap =
      light-only CBS expectation 0.976, replaces the BP25 0.93 for this study); BP27a(h) labour GBP 16.3/h applied
      (cashflow option labour_mult); new site_opt option `co2` (dosing setpoints, default unchanged), AHDB 1,000 ppm.
      Rejected: double glass (GBP 11.1 M, 12.4 yr), pipe 2.25 at 3 ha (HP/store grow, +GBP 0.4 M), lower CO2 setpoints,
      geometry changes. Tests test_costing, test_bp19 PASS
      - [x] BP28a. (SUPERSEDED 2026-10-07: the 5 ha plan is no longer the lead; the GBP 10 M lead case (bplan_10m.py lead) already applies the BP25a cap and the 2026 labour rate; 5 ha files stay historical at CO2 0.20) Apply the BP25a yield basis and the 2026 labour rate to the 5 ha plan (`bplan_5ha.py`) and the workbook
      - [ ] BP28b. (BLOCKED: needs an outbound approach to a developer or community-turbine group, the user's to make) Turbine developer at 2.9 ha: margin GBP 2.4/MWh at GBP 90; get a developer or community-turbine offer
      - [x] BP28d. Sale price GBP 1.00/kg checked: infeasible (10-yr payback allows <= GBP 77/m2 capex); minimum sale price
            GBP 1.52/kg (10 yr), GBP 2.13/kg (5 yr). In CAPEX_10M_DESIGN.md. DECIDED (user, 2026-10-05): GBP 1.00/kg = production cost (option 1); lead design stands
      - [x] BP28c. (stated in CAPEX_10M_DESIGN.md; goes into the business plan text) 5-year payback is not reachable (opex ceiling GBP 0.65 M/yr < labour + packing + power); say so in the plan

- [x] BP29. Cache keyed on real dependencies (2026-10-05): simstore per-kind import graph + named data files (cost,
      finance and documentation edits no longer invalidate); LP keyed on solver inputs, roll-up on `row` applied after;
      dataclasses hashed by field (repr truncated arrays). Lead case rerun 9 s vs ~95 s rebuild. Tests PASS
- [x] BP30. Price evidence (BP5 partly): `PRICE_EVIDENCE.md`. DEFRA Horticulture Statistics 2026 (data/hort-dataset-
      25-20260625.ods): UK cucumber farm-gate GBP 1.01/kg (2023-25), import unit value GBP 1.37-1.46, UK yield 50-52
      kg/m2. GBP 1.57 is import parity at the RDC, not a grower price. Winter (Nov-Mar) = 44 % of imports, 12 % of our
      unlit output
- [x] BP31. Highlands screen (`bplan_highlands.py`): Inverness, Invergordon, Moray all worse than Stranraer (capex
      GBP 11.0-11.5 M, cost 1.12-1.25, carbon 0.52-0.65, uplift ~GBP 0.04/kg). Stranraer stays
- [x] BP32. (DONE 2026-10-07: bplan_lit_winter.py -> results/bplan/lit_winter.json; lead + LED at 0/100/150/220 umol: cost at 8 % GBP 1.47 / 1.34 / 1.29 / 1.36 per kg, capex 9.94 / 11.27 / 11.38 / 11.78 M, winter share 11 / 24 / 28 / 33 %, CO2e 0.41 / 0.42 / 0.47 / 0.60; best at ~150, over the GBP 10 M cap; LED GBP 515/kW is a placeholder inside the RVO cap GBP 900/kW) Lit winter crop case on the GBP 10 M design (LED capex sourced, power at GBP 90/MWh, winter CIF prices)
- [x] BP33. (DONE 2026-10-07, cloud: `finance.py` -> results/bplan/finance.json + FINANCE.md on the lit lead 2.9 ha/150 umol/2 PPA turbines, from lit_open.json, no physics rerun; the rebuilt real layer matches lit_open to 1e-9. Nominal CPI 2 %, CT 25 %, full expensing with integral features at special rate (conservative), losses carried forward, interest-only year 1, DSRA 6 months, WC 2 months, ECA supplier credit at the OECD GBP CIRR 5.81 % (85 %, 15 yr, equal principal, 2 % premium PLACEHOLDER) + plant asset finance 7.0 % 10 yr (PLACEHOLDER). MIN REAL PRICE (DSCR 1.25 binds; equity 12 % nominal never binds): central vendor scheme GBP 1.237/kg; without the holiday 1.514; bank debt sculpted to 1.25 at 65 % gearing 1.190; ESCo 1.257; pref shares / FDPSS grant 1.237 (do not move the DSCR); all equity at 8 % real = 10.2 % nominal post-tax 1.188. LENDER CASE FAILS: min DSCR 0.45 / 0.84 / 1.16 at GBP 1.01 / 1.10 / 1.20. SPONSOR CASE: parity -5 % (GBP 1.477) equity GBP 4.34 M, min DSCR 1.74, equity IRR 25.5 % nominal, payback 4.0 yr; parity -10 % (GBP 1.399) min DSCR 1.56, equity IRR 21.8 % (19.4 % real), payback 4.9, first tax year 6. Equity cheque 4.34 M = 3.34 M capex + DSRA 0.57 + WC 0.31 + fees 0.13. Pref-share and grant options do not change the min price) Financing model (`finance.py`): nominal (CPI), corporation tax 25 % + full expensing (glasshouse = plant,
      CAA 2001 s.23 List C item 17), DSRA + working capital, company-only debt sized on DSCR, non-voting preference
      shares (12 % hurdle), grants, heat-plant ESCo with buyout; lender case at GBP 1.01-1.20, sponsor case at a premium
- [x] BP34. (DONE for cucumber via BP35/BP35b: DOE, fit, verify incl. water balance and the 105 kg/m2 ceiling; LED rate still the BP32 PLACEHOLDER GBP 515/kW; tomato BLOCKED with BP19h on the desktop run) Year-round study (user question 2026-10-05, `CONSTRAINTS.md`): design-of-experiments on the full model (lighting
      ppfd/hours/DLI target, glazing, screens, area <= 5 ha, heat pump + store, site), fit a surrogate for yield,
      monthly supply, heat, electricity, water, capex, opex, carbon; optimise payback against the 21 constraints;
      confirm winners on the full model. Needs: LED capex rate (rates.csv, quote range), water balance (rain capture vs
      irrigation demand), yield ceiling cap (105 kg/m2 lit cucumber)
- [x] BP35. (run done 2026-10-06, see next line) PLANNED RUN ON THE DESKTOP (2026-10-06, user: "big run tomorrow on the better computer"). From lca/:
      `set CEA_WORKERS=5` then `python bplan_yearround.py doe cucumber 60` and `python bplan_yearround.py doe tomato 80`
      (resumable; results/bplan/yearround_doe_<crop>.json), then `python bplan_yearround.py fit <crop>` and
      `python bplan_yearround.py verify <crop>`. Levers in CONSTRAINTS.md "Levers built in". Target: price cover <= 1
      at the evidence price (Dutch farm-gate level)
- [x] BP35 run 2026-10-06 (desktop, 5 workers): cucumber 60 + tomato 80 designs, fit, verify. Best verified cover 1.14
      (cucumber, site_002, 1.06 ha); no tomato design meets month-min >= 0.6. Diagnosis: one fixed 2.5 MW turbine
      (tp_2p5MW) for every area, so capex/m2 fell 22 % from 1 to 4.5 ha but grid import cancelled it (cover 1.21 both)
- [x] BP35b. (DONE for cucumber: results/bplan/yearround_wind_verify_cucumber.json, 3 verified designs, all fail the lender price GBP 1.02 (IRR 1.9-4.4 %); tomato BLOCKED = BP19h) Wind scales with area (user 2026-10-06): routes own (SPV, judged on greenhouse + turbine cash flow), ppa
      and farm_share, 1-4 turbines per module; cap GBP 20 M/phase, carbon ceiling 1.0, area 1-8 ha. Results in
      results/bplan/yearround_wind_*. Fix: farm_share LP now on the 80 m wind profile (was 45 m). Smoke 5 ha cucumber
      site_002: cover own x4 1.07 (greenhouse-only 0.98; SPV NPV8 -5.9 M), ppa x4 1.09, farm_share 1.09
- [x] BP36. (DONE 2026-10-07, cloud: `bplan_finance_risk.py` -> results/bplan/finance_risk.json + FINANCE_RISK.md. Central vendor scheme at parity -10 %: min price lead 1.237, verified 4.44 ha 1.246, 4.61 ha 1.315, 5.54 ha 1.234 (verified capex/opex split apportioned on the lead; lead parity used as their price proxy). Monte Carlo 2,000 draws (skewed-downside PLACEHOLDER ranges in the docstring), lead: project IRR real pre-tax P10/P50/P90 8.3/11.6/14.7 %, equity IRR nominal 10.0/15.2/20.8 %, min DSCR 0.93/1.28/1.53, P(min DSCR < 1.25) 45 %, P(< 1.0) 14 %. Phasing 2.9 + 2.9 + 4.4 = 10.2 ha at years 0/3/6: capex GBP 38.8 M, debt 27.6 M, peak external equity GBP 6.68 M (year 6), combined equity IRR 22.4 %, payback 8.2 yr) Financing model (BP33) on the verified designs, phased; Monte Carlo on the cash-flow layer (P50/P90)
- [ ] BP37. (all financing parts DONE 2026-10-07; open: BP37c BLOCKED, asset-finance quote BLOCKED in BP37d) (user, 2026-10-07) Lights allowed, capex cap REMOVED; price = slightly under import parity (user: import
      parity itself is not credible); supplier / asset finance instead of 8 % all-investor money.
      - [x] BP37a. `bplan_lit_open.py` -> results/bplan/lit_open.json (log lit_open.log): lit lead (150/200 umol, 1-2 PPA turbines, 2.9/4.4 ha),
            by-product CO2 + bulk crates, priced at monthly import parity (CIF + GBP 0.162 haul) x (1 - 3/5/10 %)
            DONE 2026-10-07. LCOP 8 %: unlit 1.302 (CO2 by-product + bulk); 150 umol 1 turbine 1.136; 150 umol 2 turbines
            1.112 (capex 11.45 M, Y 93.0, winter 26 %); 200 umol 2 turbines 1.128; 4.4 ha 150 umol 2 turbines 1.078
            (15.87 M). At 10 % under parity (GBP 1.40): 2.9 ha/150/2T IRR 15.2 %, payback 6.4 yr, NPV8 +8.6 M; yield -15 %:
            IRR 10.5 %, payback 8.7. Supplier credit 15 yr + plant 10 yr: debt 8.1 M, equity 3.3 M, equity IRR 25-30 %;
            DSCR binds ONLY in year 1 (ramp, 1.1-1.2; years 2+ 2.0, 1.4 at yield -15 %): needs a 1-yr repayment holiday or
            DSRA (not modelled yet). 10 yr / 7 yr terms too short. Unlit cannot carry this debt (DSCR 0.5-0.8).
            OPEN: re-run of design 2 at 10 % gave LCOP 1.100 / NPV +8.94 M vs 1.112 / +8.58 M in the main run (cache or
            LP warm-start difference, ~1p): find cause. Carbon not reported in lit_open (BP32: 0.47 at 150 umol, 1 turbine)
            - [x] BP37e. (DONE in finance.py (BP33): interest-only year 1 + DSRA 6 months; carbon is in lit_open.json (lead 0.37, 0.89 with the CO2 dose counted). CORRECTION 2026-10-07: the earlier yield -15 % figures (IRR 10.5 %, payback 8.7, DSCR yr 1 1.23 / yrs 2+ 2.0) came from a track-A import order and are withdrawn. Redone on track B at parity -10 %, cash-flow layer (half of labour scales with kg): project IRR real pre-tax 10.6 %, payback 8.6 yr; central scheme DSCR yr 1 1.32, min 1.18 (BREACHES 1.25), equity IRR 13.6 % nominal; min price 1.431. Yield -15 % + capex +20 %: min DSCR 0.97. The re-run discrepancy (1.100 vs 1.112) stays OPEN: needs a physics rerun on the desktop) Add a year-1 repayment holiday / DSRA to vendor_finance; report carbon in lit_open
      - [x] BP37b. `vendor_finance.py`: glasshouse supplier credit (ECA-backed, OECD Arrangement 85 % max, rate/tenor
            PLACEHOLDER 6 %/10-15 yr), plant asset finance (Bank Rate 3.75 % + 3 %, 7-10 yr, PLACEHOLDER), equity rest;
            equity IRR, min DSCR, min price for equity 12 % + DSCR 1.25. Pre-tax, real (BP33 adds tax/CPI)
      - [x] BP37f. (DONE 2026-10-07, user: 'at what do we expand from 2.9 ha') `bplan_growth.py` -> results/bplan/GROWTH.md. Gate: phase 1 must show a full year at DSCR >= 1.25, i.e. >= 81 kg/m2 at GBP 1.40 (88 at 1.30, 76 at 1.48); earliest next phase year 3. At GBP 1.40, model yield: self-funded 2.9 ha at years 6 and 9 (8.7 ha by yr 10, equity NPV12 +8.9 M); with ~GBP 3.1 M new equity +4.4 ha yr 3, +2.9 ha yr 6 (10.2 ha, NPV12 +13.1 M). Same-site modules extend the HV connection (+GBP 75 k per 800 kVA, SPEN Ex. 18). At 79 kg/m2 and GBP 1.40 no expansion is fundable. Market cap 10.2 ha PLACEHOLDER. Doc rewritten on the lit lead (all sections) incl. lender-case yield 79 kg/m2, price floor, CO2 claim caveat
      - [ ] BP37c. (BLOCKED in the cloud 2026-10-07: code ready, `python bplan_heat_source.py` (site_opt option hp_source air/ground/sea, Millport monthly sea temperature 7.2-14.4 C as the Loch Ryan proxy, source works GBP 300/kW sea + 50 k licence and GBP 1,200/kW boreholes, PLACEHOLDERS). NEEDS: a run on the desktop (caches), or the cloud environment allowing api.carbonintensity.org.uk, api.octopus.energy and archive-api.open-meteo.com (uncached weather/grid inputs); and sourced costs for a sea intake and a borehole field) Heat source on the LIT design: air vs ground vs sea water (Loch Ryan). Earlier results were unlit only
            (BP21 water source -GBP 0.027/kg cancelled by intake; old Chelmsford study: ground loses once boreholes
            costed). Needs: site_opt option hp_source (sim already supports ground/river), borehole and sea-intake
            costs sourced (none usable found 2026-10-07), Loch Ryan monthly sea temperature
      - [ ] BP37d. (CIRR DONE 2026-10-07: OECD table (via Firecrawl), GBP 8-yr bond bucket (1 yr drawdown + 0.5 x 14 yr + 0.25) = 5.81 % for 15 Sep-14 Oct 2026, 6.09 % from 15 Oct; now in finance.py. Asset finance BLOCKED: NEEDS one indicative quote from a UK asset-finance lender for ~GBP 3.4 M of heat pump + store + LEDs over 10 yr (rate, advance, deferral), and an Atradius DSB premium indication for the ECA cover) Read the OECD GBP CIRR table and get one asset-finance indication to replace the PLACEHOLDER rates

Housekeeping
- [x] 18. SCOPE.md §3.16 and §3.17; tests/test_costing.py
- [ ] 19. Supermarket waste heat (SM) with real refrigeration profiles; vertical farm coupled to the glasshouse;
      vent/circulation fan check (900 W per 400 m²); market-scan reference cases (UK gas CHP, Standhill biomass);
      UK tomato self-sufficiency figure. (Older ideas kept, not on the Gate B path)
- [x] 20. New-machine setup: `setup_machine.ps1` + pinned requirements (2026-10-03)
- [ ] 21. GitHub: not pushed (user, 2026-10-03). When wanted: decide what may go public (third-party PDFs in
      `lca/data`, large result CSVs, `.blend` files), add `.gitignore` rules, and put `simcore` in a repo
- [ ] ~~Perthshire with grid backup~~ retired 2026-10-03: superseded by the waste-heat site search; grid-backed wind
      is now in every site case
- [ ] ~~Heat-pump 60–80 % sizing for frost-only crops~~ retired 2026-10-03: berries/grapes are off the shortlist and
      the user fixed full-load standby sizing

## 5. Next steps (in order) - updated 2026-10-03 evening, after the R10 chain and full costing

Done: two-track chain, cold-year-safe heat pump, electricity routes, wind realism, B8, item 7 (full costing), verification
(tests/test_r10.py + all regression tests PASS; GreenLight year on the track-B tomato design, see R10).
1. **User decisions:** (a) site per track (A: Creamery / Cameronbridge / Girvan; B: Creamery / Girvan / Tay-Hatton, cucumber first);
   (b) heat-pump rule: recommend LP-sized + store, floored to the 2010 winter (50-88 % of design load); (c) yield response ours vs
   GreenLight; (d) approach operators (heat data, fermentation CO2), suppliers (RFQ), DNO (export connection), buyers (price).
2. **The price question decides the project:** at DEFRA wholesale prices neither track pays back; at import parity cucumber does at
   3.5 % but not 8 %. Evidence needed: supermarket contract prices for UK glasshouse cucumber/tomato (vs DEFRA wholesale), and
   whether a 'Scottish, low-carbon' premium exists. This is the next research step, before more modelling.
3. **Capex and CO2 levers:** RFQ to suppliers (placeholders ~half of structure capex; capex -20 % is worth +1.4 to +2.6 M NPV);
   distillery fermentation CO2 (worth 0.12 GBP/kg); both are cheap to check and large.
4. Organic system (item 9), B6/B11 sourcing, cucumber Amax and fruit DM.

## 6. Setting up a machine

Use `setup_machine.ps1` (§0). Manual equivalent:

```
py -3.14 -m venv ~/.venvs/portfolio          # or py -3.12
~/.venvs/portfolio/Scripts/pip install -r requirements.txt
py -3.12 -m venv ~/.venvs/greenlight
~/.venvs/greenlight/Scripts/pip install -r requirements-greenlight.txt
```

Pinned versions (2026-10-03): main Python 3.14.7 with numpy 2.5.3, pandas 3.0.6, scipy 1.18.1, numba 0.67.0,
CoolProp 8.0.0, pypsa 1.3.0 (linopy 0.9.1), highspy 1.15.1, searoute 1.6.0, matplotlib 3.11.2, pypdf 6.19.0,
openpyxl 3.1.5, tifffile, imagecodecs, pyproj, requests. GreenLight venv Python 3.12.10 with greenlight 2.0.5,
numpy 1.26.4, pandas 2.2.3, scipy 1.14.1. On the laptop the main packages are in the global Python 3.14 (no
`~/.venvs/portfolio` there); `gl_chunks.py` finds GreenLight at `~/.venvs/greenlight/Scripts/python.exe`.

Not synced, recreated by the setup script: Global Wind Atlas rasters (~120 MB) in `~/.cache/gwa/`
(`GBR_wind-speed_100m.tif`, `GBR_wind-speed_50m.tif` from `https://globalwindatlas.info/api/gis/country/GBR/wind-speed/100`
and `/50`). Synced: weather, grid-price and performance-map caches in `../../simcore/cache` (~100 MB); new sites
fetch from Open-Meteo automatically. Run every script from this `lca/` folder.

**Hardware (user question 2026-10-03, the other computer has lots of RAM and a GPU):**
- GreenLight: a full year took ~17 min per quarter on this laptop, run as 4 parallel quarters (`gl_chunks.py`);
  a continuous year ~35–40 min. It is an ODE model that runs on one CPU core. A GPU does not speed it up and
  extra RAM does not either (one run needs well under 1 GB). What helps is a fast single core, and more cores to run
  several years or designs side by side (one process each).
- The site sweeps are Numba on the CPU, parallel over designs: speed scales with cores (7 workers here). RAM matters
  only in that each worker uses ~0.3 GB; this laptop has ~0.4 GB free during a sweep, so 16 GB+ removes that limit.
  A GPU would need the simulation rewritten for CUDA; not worth it while a full sweep takes ~20 min.
- Plug the laptop in for sweeps: on battery the CPU throttles.

## 7. How to rebuild (order matters)

```
python tests/test_reproduce.py        # thesis reproduction, must print PASS (~5 min)
python tests/test_fast.py             # fast sim vs reference, month by month (~12 min; only if the model changes)
python tests/test_costing.py          # sizing + costing checks
python site_opt.py 100 cucumber tomato   # 46 sites x 100 designs x 2 crops (~20 min)
python site_rank.py                   # ranking vs imports at the Scottish RDCs
python refine.py                      # local refinement + sensitivities -> refined_<crop>.json (~2 min)
# shortcut: if only costs/prices change, skip site_opt.py and start at refine.py (it re-costs the leading designs)
python size_study.py                  # 5/10/20/30 ha (~4 min)
python finalist_lp.py                 # heat store / heat pump / wind / battery LP, top 3 x 2 rules x 2 crops (36 min here)
python en13031.py                     # EN 13031-1 check
python rfq_quantities.py cucumber     # quantities for RFQ_SPEC.md
# R10 (current): both tracks in one go, then costing and checks
sh run_chain_tracks.sh                # CEA_TRACK=A then B: sweep -> rank -> refine -> size -> EN13031 -> LP -> coldyear -> RFQ (~50 min)
python cashflow.py A B                # 30-yr cash flow + sales on the top 3 per crop per track (~10 min)
python costing_report.py              # results/costing/FULL_COSTING.md
python tests/test_r10.py              # electricity routes, no-waste track, wind cap, cold-year LP, cash-flow arithmetic (~2 min)
python siting_wind_nearby.py          # OSM wind turbines within 5 km of each site (private-wire screen; resumable)
CEA_TRACK=B GLV_CASE=trackB_girvan_tomato GLV_SITE=Girvan python gl_validate.py prep; ... gl_year.py prep;
  ~/.venvs/greenlight/Scripts/python gl_run.py trackB_girvan_tomato_iso_year   # GreenLight year on the track-B design
# GreenLight cross-check (main venv for prep/merge; gl_run.py runs in ~/.venvs/greenlight)
python gl_validate.py prep 365        # weather + design parameters -> results/greenlight/caledonian_tomato_*
python gl_chunks.py launch            # 4 quarters in parallel with auto-restart (~17 min here)
python gl_chunks.py merge             # heat comparison by month -> caledonian_tomato_chunks_compare.json
~/.venvs/greenlight/Scripts/python gl_run.py      # continuous year (~35-40 min; needed for yield)
python gl_validate.py compare         # heat + yield from the continuous run
```
GreenLight gotchas (all handled in the scripts): pass the model as `input_prompt` (otherwise it loads its Dutch test
weather first); no commas in CSV header text; `max_step` 300 s; never use extreme control thresholds (a −100 °C
screen setpoint overflowed `exp()` and the model blew up silently, GreenLight clips overflows instead of failing);
`gl_run.py` restarts from the state 2 h before any solver failure or air temperature outside −50..80 °C.

History (earlier scenarios, still reproducible): `run_crops.py`, `energy_systems.py`, `compare.py` → Chelmsford
10-crop page `../crop_compare.html`; `run_perthshire.py`, `offgrid.py`, `perthshire_results.py` → Perthshire
off-grid (6 crops win carbon, none wins cost); `breakeven.py` → avocado (never wins on cost); `optimise.py` →
first shape sweep. Lessons that still hold: LEDs never pay back; twin-wall PC needs half the heat of glass for ~10 %
less yield; ground source loses to air source once boreholes are costed; only controls + a variable-speed pump pay
back among the system upgrades; on-site medium turbines are dearer than utility-scale wind.

## 8. File map (this folder, current toolchain)

| File | Role |
| --- | --- |
| `SCOPE.md` | The record: scope, decisions, every step's results, sources |
| `HANDOFF.md`, `RFQ_SPEC.md`, `FEASIBILITY_AUDIT.md`, `MARKET.md` | This file; RFQ draft; feasibility audit; market notes |
| `greenhouse.py` / `greenhouse_fast.py` | Reference hourly greenhouse + heat-pump sim / Numba copy (with per-process caches) |
| `design.py`, `sizing.py`, `costing.py`, `data/rates.csv` | Free-form geometry + light; concept steel sizing; quantities × rates anchored to SAC |
| `siting.py`, `data/siting/` | Waste-heat sites, GWA wind, OSRM haul to RDCs |
| `site_opt.py` | Per-site design evaluation (heat pump, outages, energy, network, logistics) and sweep |
| `energy_grid.py` | Grid-backed wind + own-wind battery dispatch and sizing |
| `site_rank.py`, `refine.py` | Ranking vs imports; local refinement + sensitivities |
| `size_study.py`, `finalist_lp.py`, `en13031.py`, `rfq_quantities.py` | Gate B studies |
| `gl_validate.py`, `gl_run.py`, `gl_chunks.py` | GreenLight cross-check: prep/compare, runner with auto-restart, parallel quarters |
| `setup_machine.ps1`, `requirements.txt`, `requirements-greenlight.txt` | New-machine setup |
| `run_gateB.sh` | Full Gate B chain in one go (sweep → … → RFQ quantities → thesis test) |
| `data/input_register.csv` | Every input with value, status and source |
| `run_chain_tracks.sh`, `coldyear.py` | R10 two-track chain; 2010 / 2018 weather-year cost and heat-pump checks |
| `cashflow.py`, `costing_report.py`, `results/costing/` | Item 7 lifecycle cash flow, sales and break-even; report |
| `nowaste_eval.py`, `nowaste_levers.py`, `nowaste_study.py`, `results/nowaste/` | R10 first and second passes (history) |
| `siting_wind_nearby.py`, `data/siting/wind_nearby.json` | Private-wire screen: OSM wind turbines near each site |
| `results/site_opt_B/` | Track B (no waste heat) chain outputs, same file names as results/site_opt |
| `tests/test_r10.py` | R10 verification |
| `data/standards/` | EN 13031-1 background report (reliability) |
| `data/dea_*` | DEA technology data: heat pumps (ch. 40), energy storage (hot-water tanks) |
| `results/site_opt/` | Sweep rows, rankings, refined, size, LP, EN 13031, RFQ quantities; `gateA_archive/`, `lp_flatprice_archive/` |
| `results/greenlight/` | GreenLight inputs, quarter outputs, comparison; `caledonian_tomato_day66_state.json` (crop state for chunks) |
| `config.py`, `crop.py`, `crops.py`, `climate.py`, `imports.py`, `compare.py`, `offgrid.py`, ... | Model parts and earlier scenarios |

## 9. Key inputs and their quality (details in `data/input_register.csv`)

**Sourced / standard:** DESNZ 2025 conversion factors and Quarterly Energy Prices; NESO TNUoS 2025/26 and 2026/27;
Comtrade imports (annual + monthly); CBS NL yields; SAC/SRUC structure and turbine prices; DEA heat-pump (ch. 40)
and hot-water-tank costs; NREL ATB battery; IVL battery carbon; TAG v2.03 haulage; EN 13031-1 / EN 1990 / EN 1991
load factors; ASABE EP406.4; ISO 6946/13370; HM Treasury Green Book 3.5 %.

**Placeholders (quote needed, RFQ):** glazing units, aluminium bars, heating pipe, energy screen, XPS, PC, ETFE,
heat connection pipe (500 m × £1,000/m). About 46–47 % of structure capex. Placeholders at their low/high ends move
cucumber cost by −£0.05/+£0.08 per kg.

**Placeholders (operator data):** outage timing, food/AD shutdown, unplanned outage week, waste-heat price
(£0/10/20 per MWh).

**Estimated, to source:** labour h/m², packing, consumables, O&M fractions, asset lives, crop hung load, snow V,
battery inverter £/kW, light–yield elasticity 0.8 (Marcelis 2006).
