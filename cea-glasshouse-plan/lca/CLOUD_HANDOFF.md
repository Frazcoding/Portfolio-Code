# Cloud handoff (2026-10-07)

Read this first, then `HANDOFF.md`.

## Repo rules
- Private repo `Frazcoding/cea-glasshouse-plan`. NEVER push to remote `public` (`Frazcoding/BEng-CEA-Heatpump` is PUBLIC; its push URL is disabled).
- `simcore` is vendored at the repo root; lca scripts put the repo root first on `sys.path`.
- Caches are not in git (`lca/results/store`, `simcore/cache`, `lca/results/greenlight`): first runs rebuild them (minutes per lit case).
- Always import `bplan_5ha` before `site_opt` (track B is set at import time; `bplan_lit_open.py` asserts it). Run from `lca/` with `CEA_RESID_ANCHOR=wur`.

## User decisions (2026-10-07)
Lights allowed, NO capex cap. Price slightly UNDER import parity (not at parity). Supplier / asset finance preferred to 8 % all-investor money. Goal: finish the financial modelling until every HANDOFF item is ticked or marked BLOCKED with the exact outside need.

## Done
- `bplan_lit_open.py` -> `results/bplan/lit_open.json` (carbon, cashflow, costs, harvest share, monthly parity). Lead 2.9 ha, 150 umol, 2 PPA turbines: capex GBP 11.45 M, Y 93 kg/m2, LCOP 8 % GBP 1.112/kg, 0.37 kg CO2e/kg (0.89 dose counted); at 10 % under parity (GBP 1.40): IRR 15.2 %, payback 6.4 yr. 4.4 ha: LCOP 1.078.
- `vendor_finance.py` (real, pre-tax, maintenance-reserve DSCR).
- Tests `test_costing`, `test_bp19`, `test_fast` PASS after the simcore move.

## Correction owed to the user
The yield -15 % stress results and "DSCR year 1 1.23 / years 2+ 2.0" given earlier came from a script that imported `site_opt` first (track A, waste heat). They are INVALID: redo them.

## To do, in order
1. `finance.py` (BP33 + BP37e): nominal CPI 2 % (BoE target); CT 25 % with full expensing (CAA 2001 s.23 List C item 17) and loss carry-forward; 1-yr repayment holiday; DSRA 6 months; working capital 2 months opex; supplier credit (ECA, 85 % max, 15 yr; rate = 15-yr gilt 5.09 % Apr 2026 + ~1 %, PLACEHOLDER) + plant asset finance (Bank Rate 3.75 % + 3-3.5 %, PLACEHOLDER); alternative bank debt sculpted to DSCR 1.25; pref shares 12 %; grants option; heat-plant ESCo with buyout; lender case GBP 1.01-1.20, sponsor case parity -5/-10 %; min-price solver. Read `lit_open.json`, no physics rerun.
2. BP36: same on the 3 verified designs (`results/bplan/yearround_wind_verify_cucumber.json`, `cashflow_lender`); levered phasing to 10 ha; Monte Carlo P10/P50/P90 (yield, price, capex, power, CO2 GBP 0.03-0.10/kg, labour; half of labour scales with kg, `site_opt.LABOUR_KG_SHARE`).
3. BP37d: OECD CIRR table returned 403; mark BLOCKED on one asset-finance quote if still unavailable.
4. BP37c: heat source on the lit design (air vs ground vs Loch Ryan sea water, ~7 C in Feb per the Millport record); costs unsourced, label placeholders.
5. Tick BP33/34/35/35b/36/37 as appropriate; mark outside-dependent items BLOCKED with the exact need. Re-read HANDOFF before every edit (other agents edit it).
6. Rebuild the business plan (Claude Doc from BP26) and the workbook (BP26a) on the lit 2.9 ha lead with the new finance. Commit as you go; the user pushes.

## Progress (cloud session, 2026-10-07 late)
- Items 1-3, 5, 6 DONE: `finance.py` (BP33/BP37e), `bplan_finance_risk.py` (BP36), CIRR 5.81 % (BP37d), HANDOFF ticked,
  `bplan_workbook_lead.py` -> business_plan/Lead_Finance_Model.xlsx (matches finance.py exactly), Claude Doc Summary +
  Funding rebuilt on the lit lead. Correction owed: done (BP37e line in HANDOFF).
- Item 4 (BP37c) BLOCKED here: code ready (`bplan_heat_source.py`, site_opt `hp_source`), but this container's network
  policy blocks api.carbonintensity.org.uk, api.octopus.energy and archive-api.open-meteo.com, so the uncached inputs
  cannot be rebuilt. Run it on the desktop.
- BLOCKED on outside parties: an asset-finance quote and the Atradius premium (BP37d).
- Not done: the Market/Design/Operations/Financials sections of the Doc and the old S0-S4 workbook still show the unlit case.

## Goal session (2026-10-07, later): viable design end to end
- Lead is now 8 ha lit cucumber (see HANDOFF top). All new numbers come from cloud physics runs on ERA5 open-data weather and
  a proxy grid price shape; re-run on the desktop with the API inputs to confirm (commands in HANDOFF).
- New modules: simcore/era5_open.py, simcore/grid_proxy.py, lca/staffing.py, bplan_viable.py, bplan_plan.py,
  bplan_report_figures.py, PlanGrowth in bplan_growth.py, PlanWorkbook in bplan_workbook_lead.py; pepper in crop_gh/transp.
- Path fix: greenhouse.py and sim/annual_sim.py looked for simcore one level above the repo.
