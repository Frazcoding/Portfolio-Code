"""make_index_hub.py
Generates the portfolio hub (index.html): one card per project with its rendered Blender preview, a description and
headline KPIs read from the project's annual simulation results (results/<scenario>_kpis.json).
"""
import html
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

PROJECTS = [
    ("Heat-Pump-Simulation", "heatpump_rig_preview.png", "london", "Thermodynamics",
     "Two-stage R290 air-source heat pump",
     "Inverter LP pair + HP scroll with flash economiser serving a 12-flat block: 10 refrigerant state points, frost/defrost, "
     "stratified buffer and DHW cylinder, Agile-aware control.",
     ["SCOP (H2: compressors + fans)", "Electricity cost (Agile)", "Reverse-cycle defrosts", "Annual exergy efficiency"]),
    ("High-Temp-Waste-Heat-Recovery", "industrial_hthp_preview.png", "dairy_butane", "Industrial heat",
     "Industrial high-temperature heat pumps",
     "Dairy effluent and spray-dryer exhaust recovered by screw heat pumps with economiser + IHX to 95 °C water or 2.7 bar steam.",
     ["Seasonal system COP (incl. aux)", "Heat pump heat delivered", "CO₂ avoided", "Electricity / gas price ratio"]),
    ("Building-Heatpump-Retrofit", "retrofit_plant_preview.png", "tes_smart", "Building services",
     "Commercial retrofit under a 60 kWe cap",
     "Four 40 kW R290 modules, 2 x 100 m³ stratified stores and grid-capped dispatch for a 6,000 m² Edinburgh office.",
     ["System SPF (all plant electricity)", "Peak 10-min demand", "Electricity cost (Agile)", "Unmet occupied hours (<20 °C)"]),
    ("BEng-CEA-Heatpump", "greenhouse_preview.png", "ground", "Controlled-environment agriculture",
     "Greenhouse + two-stage ammonia heat pump",
     "Dynamic Venlo glasshouse with tomato crop, screen and vents, heated by an R717 open-intercooler heat pump on air, ground or river.",
     ["Seasonal COP (unit)", "Pipe-rail heat to greenhouse", "Hours below 17 °C", "Operational CO₂"]),
    ("Plantpost-Urban-Infrastructure-Modelling", "plantpost_preview.png", "london", "Urban infrastructure",
     "Plantpost autonomous street post",
     "PV canopy, LiFePO4 microgrid with adaptive dimming, rain-fed drip irrigation of four planted tiers, particulate capture.",
     ["PV energy to battery", "Lighting availability", "Rain harvested", "PM10 captured"]),
    ("PyPsa-Green-Hydrogen-Microgrid", "hydrogen_microgrid_preview.png", "base", "Energy systems",
     "Island wind–hydrogen microgrid",
     "Three 6.2 MW turbines, electrochemical PEM model, real-gas 350 bar storage and nightly ferry bunkering on Lewis.",
     ["Hydrogen produced", "Mean specific energy", "Ferry demand met by H₂", "LCOH (8 % WACC, 20 yr, £45/MWh)"]),
    ("UniBoat-Powertrain-Cooling", "uniboat_cooling_preview.png", "season", "Electric marine",
     "UniBoat electric hydrofoil cooling",
     "Monaco Energy Class catamaran: foil hydrodynamics, powertrain losses and a pumped two-phase R1233zd(E) cooling loop.",
     ["Sessions", "Energy drawn", "Max battery temperature", "Peak battery heat"]),
    ("Whole-Carbon-Lifecycle-Assessment", "wlc_office_preview.png", "lifecycle", "Whole-life carbon",
     "Whole-life carbon of a 7,500 m² office",
     "Baseline, deep retrofit, standard and timber new build: hourly operation in 2023 and 60-year A1–C4 carbon.",
     ["Deep Retrofit · 60-yr WLC (DESNZ central)", "Timber New Build · 60-yr WLC (DESNZ central)",
      "Standard New Build · 60-yr WLC (DESNZ central)", "Baseline (Gas) · 60-yr WLC (DESNZ central)"]),
]


def kpis_for(project, scenario, labels):
    f = BASE_DIR / project / "results" / f"{scenario}_kpis.json"
    if not f.exists():
        return []
    data = {k["label"].strip(): k for k in json.loads(f.read_text(encoding="utf-8"))}
    out = []
    for lab in labels:
        k = data.get(lab)
        if k and k["value"] is not None:
            v = k["value"]
            d = k.get("dec", 1)
            txt = f"{v:,.{d}f}" if abs(v) < 1e5 else f"{v:,.0f}"
            out.append((lab.replace(" (DESNZ central)", "").replace(" (incl. aux)", ""), txt, k["unit"]))
    return out


# Extra pages linked from a project's card: {project: [(href relative to project, label)]}
EXTRA_LINKS = {"BEng-CEA-Heatpump": [("crop_compare.html", "Compare crops vs imports →")]}


def card(project, img, scen, tag, title, desc, labels):
    ks = kpis_for(project, scen, labels)
    n_ch = 0
    scen_count = len(list((BASE_DIR / project / "viewer_data").glob("*.json"))) if (BASE_DIR / project / "viewer_data").exists() else 0
    man = BASE_DIR / project / "viewer_data" / f"{scen}.json"
    if man.exists():
        n_ch = len(json.loads(man.read_text(encoding="utf-8"))["channels"])
    kp = "".join(f'<div class="k"><span>{html.escape(l)}</span><b>{html.escape(v)}<small> {html.escape(u)}</small></b></div>' for l, v, u in ks)
    extra = "".join(f'<a class="btn alt" href="{project}/{h}">{html.escape(l)}</a>' for h, l in EXTRA_LINKS.get(project, []))
    return f"""
    <article class="card">
      <a class="shot" href="{project}/viewer.html"><img src="{project}/{img}" alt="Rendered 3D model: {html.escape(title)}" loading="lazy"></a>
      <div class="body">
        <div class="tagrow"><span class="tag">{html.escape(tag)}</span><span class="meta">{scen_count} scenarios · {n_ch} channels × 8,760 h</span></div>
        <h2>{html.escape(title)}</h2>
        <p>{html.escape(desc)}</p>
        <div class="kpis">{kp}</div>
        <div class="btnrow"><a class="btn" href="{project}/viewer.html">Open simulation viewer →</a>{extra}</div>
      </div>
    </article>"""


def generate():
    cards = "".join(card(*p) for p in PROJECTS)
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Engineering Simulation Portfolio</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Semi+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root {{ color-scheme: light; --ground:#eef1f4; --panel:#f9fbfc; --line:#d5dce3; --ink:#15202b; --muted:#5d6b78; --faint:#8a97a3; --model:#2f5bd3;
  --sans:"Barlow","Segoe UI",system-ui,sans-serif; --cond:"Barlow Semi Condensed","Barlow",system-ui,sans-serif; --mono:"IBM Plex Mono",ui-monospace,monospace; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ color-scheme: dark; --ground:#0e1318; --panel:#151c23; --line:#28323d; --ink:#e4e9ee; --muted:#9aa7b3; --faint:#6c7a87; --model:#7c9cff; }} }}
:root[data-theme="dark"] {{ color-scheme: dark; --ground:#0e1318; --panel:#151c23; --line:#28323d; --ink:#e4e9ee; --muted:#9aa7b3; --faint:#6c7a87; --model:#7c9cff; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--ground); color: var(--ink); font: 14.5px/1.5 var(--sans); }}
.wrap {{ max-width: 1280px; margin: 0 auto; padding: 32px 16px 56px; }}
header {{ border-bottom: 1px solid var(--line); padding-bottom: 18px; margin-bottom: 24px; }}
h1 {{ font: 700 30px/1.1 var(--cond); margin: 0 0 8px; text-wrap: balance; }}
.lead {{ color: var(--muted); max-width: 900px; margin: 0; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 380px), 1fr)); gap: 18px; }}
.card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; }}
.shot {{ display: block; aspect-ratio: 16 / 10; overflow: hidden; background: #c8d2da; }}
.shot img {{ width: 100%; height: 100%; object-fit: cover; display: block; transition: transform .3s; }}
.card:hover .shot img {{ transform: scale(1.03); }}
.body {{ padding: 14px 16px 16px; display: flex; flex-direction: column; flex: 1; }}
.tagrow {{ display: flex; justify-content: space-between; gap: 8px; align-items: center; flex-wrap: wrap; }}
.tag {{ font: 600 10.5px var(--cond); text-transform: uppercase; letter-spacing: .07em; color: var(--model); background: color-mix(in srgb, var(--model) 12%, transparent); padding: 2px 7px; border-radius: 3px; }}
.meta {{ font: 500 11px var(--mono); color: var(--faint); }}
h2 {{ font: 700 18px/1.2 var(--cond); margin: 8px 0 4px; }}
p {{ color: var(--muted); font-size: 13px; margin: 0 0 12px; }}
.kpis {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 14px; flex: 1; align-content: start; }}
.k {{ background: color-mix(in srgb, var(--ground) 70%, transparent); border-radius: 4px; padding: 5px 8px; min-width: 0; }}
.k span {{ display: block; font: 600 9.5px var(--cond); text-transform: uppercase; letter-spacing: .05em; color: var(--muted); overflow-wrap: anywhere; }}
.k b {{ font: 600 14px var(--mono); }}
.k small {{ font: 500 11px var(--sans); color: var(--muted); }}
.btn {{ align-self: flex-start; font: 600 13px var(--cond); text-transform: uppercase; letter-spacing: .04em; color: var(--ground); background: var(--ink); text-decoration: none; padding: 8px 14px; border-radius: 4px; }}
.btn:hover {{ background: var(--model); }}
.btnrow {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.btn.alt {{ background: transparent; color: var(--ink); box-shadow: inset 0 0 0 1px var(--ink); }}
.btn.alt:hover {{ background: var(--model); color: var(--ground); box-shadow: none; }}
footer {{ margin-top: 34px; color: var(--faint); font-size: 12px; border-top: 1px solid var(--line); padding-top: 14px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Engineering Simulation Portfolio</h1>
    <p class="lead">Eight annual (8,760-hour) simulations on real 2023 weather (ERA5), GB grid carbon and Agile prices, each with full
    thermodynamic state points, energy and exergy balances and annual KPIs, shown on detailed, physically-based 3D models.
    Open via <code>run_suite.cmd</code> or <code>python serve_viewers.py</code> (the viewers load their data from local files).</p>
  </header>
  <div class="grid">{cards}
  </div>
  <footer>Rebuild everything with <code>python build_all.py</code> (add <code>--force</code> to re-run all simulations). Textures and HDRI: CC0 (Poly Haven, ambientCG).</footer>
</div>
</body>
</html>
"""
    (BASE_DIR / "index.html").write_text(page, encoding="utf-8")
    print("Generated", BASE_DIR / "index.html")


if __name__ == "__main__":
    generate()
