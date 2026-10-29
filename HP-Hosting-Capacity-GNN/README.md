# Heat-pump hosting capacity with a GNN power-flow surrogate

**Status: paused (2026-10-09).** `gridgnn.py` is an untested first draft written by a builder agent that was stopped before it ran anything. No dataset, model or results exist yet.

## Idea
Use a graph neural network as a fast surrogate for low-voltage power flow, then run large Monte-Carlo studies of how much heat-pump adoption a feeder can take before voltage or thermal limits are breached.

```
scenario generator ──► pandapower runpp (~30 ms each) ──► dataset (~6000 cases)
        │                                                    │
        │                                         train edge-aware GNN (GPU)
        ▼                                                    ▼
adoption 0–100 %  ──► GNN Monte-Carlo (2000 / step) ──► P(violation) vs adoption
                       validated against power flow on a subset
```

## Design (as briefed)
- **Network:** `pandapower.networks.create_kerber_dorfnetz()` — German LV village feeder after Kerber (2011), 116 buses, 114 lines. Synthetic but representative; not a real network of ours. `mv_oberrhein` (179 buses) also solves.
- **Scenario (cold-winter-evening peak, −10 °C):** heat-pump adoption a ~ U(0, 1) per scenario; each household gets a HP with probability a. Household base load U(0.5, 2.5) kW at cos φ 0.95; HP electrical = thermal design load U(5, 12) kW ÷ COP U(2.0, 3.0), cos φ 0.97; simultaneity 1.0.
- **Labels:** bus vm_pu, line loading %, transformer loading.
- **Model:** nodes = buses (P, Q, has_hp, base kW, slack/trafo flag, distance from trafo); edges = lines + trafo with (r, x, length, max_i_ka); GINEConv/TransformerConv, 4–6 layers, hidden 128; node head → voltage, edge head → loading. 80/10/10 split by scenario.
- **Evaluation:** voltage MAE (pu) and max error, loading MAE (pp), violation-classification accuracy (bus < 0.94 pu, line > 100 %), GNN vs power-flow speed.
- **Output:** hosting-capacity curve P(violation) and P(overload) vs adoption, GNN vs power flow, with the 10 % crossing point.

## Known limitations
Synthetic feeder, peak-only snapshot, no PV/storage/EVs, balanced three-phase power flow.

## To resume
Dependencies already exist in `Code\localml` (torch cu126, torch_geometric, pandapower 3.1.2 with numba, **pandas < 3** — pandapower breaks on pandas 3). Simplest: move `gridgnn.py` back to `Code\localml\src\localml\` (it imports `localml.gpu` for `gpu_lock`, `DEVICE`, `outputs`), then
`Code\localml\.venv\Scripts\python.exe -m localml.gridgnn --net kerber_dorfnetz --generate 6000 --train --hosting`.
Review the draft first: it has never been run.
