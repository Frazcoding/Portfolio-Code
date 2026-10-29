# Review of the thesis headline numbers (BP7, 2026-10-07)

Scope: `README.md` / `CLAUDE.md` state a mean COP of 4.29 (water source), 4.06 (air), 4.11 (ground) at an "80 °C supply",
"near Carnot". The business-plan study does not use these numbers (it uses `lca/` R717 models), so nothing downstream breaks.
This note says what can and cannot be defended before any public use.

## What I checked
`results/{air,ground,water}_hourly.csv.gz` are the re-run thesis engine (`sim/annual_sim.py`, 2018 weather). Over the hours
with heat delivered (Q_c > 1 kW):

| Source | Active hours | Mean COP | Mean Tc, degC (range) | Mean Te, degC | Mean Carnot COP | COP / Carnot | Mean pipe supply, degC |
|---|---:|---:|---|---:|---:|---:|---:|
| Air | 3,649 | 3.47 | 51.5 (33-71) | -5.2 | 5.90 | 0.58 | 44.7 |
| Ground | 3,576 | 3.64 | 52.4 (33-75) | -1.5 | 6.21 | 0.59 | 44.8 |
| Water | 3,462 | 3.65 | 53.2 (33-76) | 1.7 | 6.56 | 0.56 | 45.1 |

(Carnot = (Tc + 273.15) / (Tc - Te), taken hour by hour.) The thesis KPI file (`results/thesis_kpis.json`) quotes annual COP
4.14 / 4.21 / 4.41 for the same runs, so the COP definition differs (weighting and what counts as an active hour).

## Findings
1. **"80 °C supply" is not what the engine runs at.** The controller asks for 22-72 °C pipe supply (`annual_sim.py` l.118);
   the condensing temperature averages 51-53 °C. 80 °C is a design condition, not an operating mean.
2. **"Near Carnot" is not supported.** At the operating point above the engine reaches 56-59 % of Carnot, a normal figure for
   a real two-stage ammonia machine. At a true 80 °C condensing temperature and a +1.7 °C source the Carnot limit is 4.51, so
   a COP of 4.29 would be 95 % of Carnot, which no real cycle reaches.
3. **The three mean COPs are not on one definition.** README 4.29 is an unweighted mean over active hours of the
   original notebook outputs; the re-run engine gives other numbers (table). Quote one definition (seasonal, energy-weighted:
   total heat / total compressor and auxiliary electricity) and say it.
4. The original outputs (`data/outputs/*.csv`) have no temperature columns, so the 80 °C claim cannot be checked from them.
   The BEng thesis PDF (`docs/Fraser_Mclellan_2550305M_individual_project_BEng.pdf`) is the authority for the cycle
   assumptions: the condensing temperature, approach temperatures and isentropic efficiency must be read from there.

## Recommendation (user decision)
Before any public use: (a) replace "near Carnot" with the measured fraction (about 0.56-0.59), (b) state the COP definition,
(c) replace "80 °C supply" with the actual condensing-temperature range, (d) reconcile 4.29 against the thesis PDF.
README, CLAUDE.md, GEMINI.md and AGENTS.md updated on 2026-10-07 with the user's OK (definition note, design vs operating temperature, no near-Carnot claim); the 4.29 figure itself is unchanged.
