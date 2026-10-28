# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 01 Model: hub sizing (sheet port) and the operating day
#
# Thin notebook: the relations live in `src/ember_hub_simulator/model.py` (`HubModel`, `DaySimulation`); this notebook
# writes each one out with its sheet cell and evaluates it for the baseline (S1 Temple Works). Units in the text are
# the sheet's (km, min, kWh, kW, kVA); the model is SI internally. See `docs/THEORY.md`.

# %%
import matplotlib.pyplot as plt
from IPython.display import Markdown, display

from ember_hub_simulator import Config, HubModel, Params, ProjectPaths, Simulation, SiteCase
from ember_hub_simulator.model import H_S, MIN_S, SubstationSizes
from ember_hub_simulator.plotting import PlotStyle
from ember_hub_simulator.runner import Runner, SiteCatalogue

PlotStyle.apply()
paths = ProjectPaths.discover()
cfg = Config.from_toml(paths.baseline)
p = Params.from_config(cfg)
site = SiteCase.from_config(cfg)
model = HubModel(p)

# %% [markdown]
# ## Energy per rotation (Site Selection I13)
#
# $$ E_\mathrm{rot} = 2\,d_\mathrm{route}\,e + 2\,d_\mathrm{dead}\,e $$
#
# route distance $d_\mathrm{route}$ (one way), dead run $d_\mathrm{dead}$, consumption $e$ (kWh/km).

# %%
E_rot_kWh = model.energy_rotation_J(site) / 3.6e6
display(Markdown(f"$E_\\mathrm{{rot}}$ = **{E_rot_kWh:.1f} kWh**, SOC at plug-in **{1 - model.energy_rotation_J(site) / p.battery_J:.1%}**"))

# %% [markdown]
# ## Return cycle and fleet (I16 to I18)
#
# $$ t_\mathrm{charge} = \frac{E_\mathrm{rot}}{P_\mathrm{charger}}, \qquad
#    t_\mathrm{cycle} = 2 t_\mathrm{drive} + t_\mathrm{turn} + t_\mathrm{break} + 2 t_\mathrm{dead} + t_\mathrm{charge}, \qquad
#    N_\mathrm{fleet} = \left\lceil \frac{t_\mathrm{cycle}}{h} \right\rceil $$

# %%
r = model.evaluate(site)
display(Markdown(f"charge **{r.charge_s / MIN_S:.1f} min**, cycle **{r.cycle_s / H_S:.2f} h**, fleet **{r.fleet}**, "
                 f"slack **{r.slack_s / MIN_S:.1f} min**"))

# %% [markdown]
# ## Chargers and grid (I20 to I23)
#
# $$ N_\mathrm{active} = \left\lceil \frac{t_\mathrm{charge} / h}{u_\mathrm{max}} \right\rceil, \quad
#    S_\mathrm{peak} = N_\mathrm{total} \frac{P_\mathrm{charger}}{\eta\,\mathrm{PF}} + S_\mathrm{aux}, \quad
#    S_\mathrm{substation} = \min\{S_k \ge S_\mathrm{peak} / u_\mathrm{max}\} $$
#
# with the BS EN 60076 ratings $S_k$ of the sheet's Lookups tab.

# %%
display(Markdown(f"{r.active_chargers} active + {p.backup_chargers} backup chargers, peak **{r.peak_VA / 1e3:,.0f} kVA**, "
                 f"substation **{r.substation_VA / 1e3:,.0f} kVA** (ratings {SubstationSizes.SIZES_kVA})"))

# %% [markdown]
# ## Drivers (I24 to I29)
#
# $$ t_\mathrm{shift} = 2 t_\mathrm{drive} + 2 t_\mathrm{dead} + t_\mathrm{checks} + t_\mathrm{break}, \quad
#    n_\mathrm{shifts} = \min\left(d_\mathrm{max}, \left\lfloor \frac{T_\mathrm{week}}{t_\mathrm{shift}} \right\rfloor\right), \quad
#    N_\mathrm{drivers} = \left\lceil \frac{\mathrm{trips/week}}{n_\mathrm{shifts}} (1 + c) \right\rceil $$

# %%
display(Markdown(f"shift **{r.shift_s / H_S:.2f} h**, {r.shifts_per_driver_week} shifts per driver per week, "
                 f"**{r.drivers} drivers**, EU hours {'OK' if r.eu_ok else 'FAIL'}"))

# %% [markdown]
# ## Site comparison (3.4)
#
# Capital items are annualised, $A = PV\,r / (1 - (1 + r)^{-n})$; the feasible site with the lowest annual cost ranks 1.

# %%
sites = Runner.alternatives(SiteCatalogue(paths.data).listed())
for res in model.compare(sites):
    print(f"{res.site.id}  fleet {res.fleet_total}  drivers {res.drivers}  £{res.total_gbp_yr:,.0f}/yr  "
          f"£{res.gbp_per_trip:,.0f}/trip  rank {res.rank}")

# %% [markdown]
# ## Operating day
#
# The day simulation runs the timetable with the sized fleet and the active chargers, at 1 min steps after a warm-up day.

# %%
out = Simulation(p, site, sites).run()
f = out.frame
fig, ax = plt.subplots(figsize=(PlotStyle.FULL_W, 6 * PlotStyle.CM))
ax.step(f["t_h"], f["grid_kVA"], where="post")
ax.set(xlabel="Time (h)", ylabel="Grid load $S$ (kVA)", xlim=(0, f["t_h"].iloc[-1]))
plt.show()
print({k: round(v, 2) for k, v in out.kpis.items() if k.startswith("sim_")})
