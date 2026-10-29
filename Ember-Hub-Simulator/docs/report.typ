// Report wired to the latest run: `uv run ember-hub-simulator report` writes docs/kpis.json and docs/figures/*, then compiles this file.
#import "style/fraser.typ": *

#let k = json("kpis.json")

#show: report.with(
  title: k.project + " — hub sizing and operation",
  subtitle: k.origin + " to " + k.dest + ", hub at " + k.site,
  meta: (
    "Run": k.run + " · commit " + k.commit,
    "simcore": k.simcore,
    "Simulated": str(k.horizon_h) + " h at 1 min steps, after one warm-up day",
  ),
  abstract: [A #k.distance_km km route (#calc.round(k.drive_time_min) min one way) every #k.headway_min min needs
    #k.fmt.fleet_total coaches (#k.battery_kWh kWh), #k.fmt.total_chargers chargers of #k.charge_power_kW kW, a
    #k.fmt.substation_kVA kVA substation and #k.fmt.drivers drivers. The hub costs £#k.fmt.total_gbp_yr a year,
    £#k.fmt.gbp_per_trip per return trip. In the minute-by-minute simulation #k.fmt.sim_on_time_pct % of departures
    leave on time and the lowest state of charge at plug-in is #k.fmt.sim_min_soc_plug_in_pct %.],
)

= Method
Sizing, feasibility and costs are a line-by-line port of the Ember Google Sheet (tabs "Inputs & Variables" and
"Site Selection"); `tests/test_sheet_parity.py` pins the sheet values for the three listed sites. The coach return cycle
is two drives, the turnaround, two dead runs and the recharge at full charger power,

$ t_"cycle" = 2 t_"drive" + t_"turn" + t_"break" + 2 t_"dead" + E_"rot" / P_"charger", quad
  N_"fleet" = ceil(t_"cycle" / h) $ <eq-cycle>

with headway $h$. Capital items are annualised at the discount rate over the asset life. The operating-day simulation
dispatches the coach with the most charge at each departure, runs the legs, queues returning coaches for the active
chargers and charges them at constant power; see `docs/THEORY.md`.

= Results
#figure(image("figures/day.svg", width: 100%),
  caption: [Grid load and coach state of charge over the simulated period.]) <fig-day>

#figure(image("figures/blocks.svg", width: 100%), caption: [Coach states (operating blocks).]) <fig-blocks>

#figure(image("figures/sites.svg", width: 100%), caption: [Annual cost per return trip by candidate site.]) <fig-sites>

#grid(columns: (1fr, 1fr, 1fr, 1fr), column-gutter: 8pt,
  kpi(k.fmt.fleet_total, "Coaches"),
  kpi(k.fmt.total_chargers, "Chargers"),
  kpi(k.fmt.drivers, "Drivers"),
  kpi(k.fmt.gbp_per_trip, "Cost per trip", unit: "£"))

#figure(caption: [Key performance indicators of run #raw(k.run).],
  table(columns: 3,
    [Indicator], [Value], [Unit],
    ..for (key, label) in k.labels {
      if key in k.fmt { (label, k.fmt.at(key), k.units.at(key)) }
    },
  )) <tab-kpi>

= Limits
Placeholder costs from the sheet (electricity, wages, capex, grid) and unconfirmed site figures (rent, spare grid
capacity) carry through every result. Swept paths use an assumed wheelbase; confirm with AutoTURN and the
manufacturer's vehicle file.
