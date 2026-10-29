# Business-plan dashboard (Evidence)

A local, read-only view of the study results. It runs on open-source Evidence 40 (CSV source, DuckDB in the browser),
so no data leaves this machine. Do not publish it to Evidence Cloud or any public host.

## Refresh after a model run

```
cd lca && python evidence_export.py      # results -> dashboard/sources/cea/*.csv
cd ../dashboard && npm run sources       # CSV -> Evidence data cache
npm run dev                              # http://localhost:3000
```

First time on a machine: `npm install` in `dashboard/` (Node 18+).

## Pages

| Page | Source |
|---|---|
| Lead case | `lca/results/bplan/lit_open.json` (BP37a) |
| Cash flow and finance | `lit_open.json` finance cases (`vendor_finance.py`, pre-tax, real; BP33 replaces it) |
| Prices and harvest | `lit_open.json` monthly parity, `lca/data/defra_wholesale_prices.csv`, `imports_monthly.csv` |
| Design study | `yearround_wind_{doe,verify}_{crop}.json` (BP35b) |
| Status and evidence gaps | `lca/HANDOFF.md`, `lca/data/input_register.csv`, `residual_items.csv` |

## Chart standard

Legends sit below each chart, and all chart text is black (theme token `base-content-muted` in
`evidence.config.yaml`). Do not pass `xAxis`, `yAxis` or `animation` through `echartsOptions`: Evidence applies them
on top of its own axis setup and the charts plot wrong values.
