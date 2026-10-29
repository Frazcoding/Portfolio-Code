# Hydrogen microgrid: equipment and scale register

`hydrogen_microgrid.blend` places the terminal, ferry and a remote wind farm at real model scale. The viewer has Plant, Ferry and Wind camera presets because a 162 m rotor dwarfs a 6 m electrolyser container. The site layout and ferry conversion are conceptual. The repository does not contain a PyPSA result series for the generated viewer trajectories.

| Part | Requirement and calculation | Blender model |
| --- | --- | --- |
| PEM bank | 8 MW installed; [Nel documents standard 2 MW containerised PEM units](https://nelhydrogen.com/press-release/press-release-nel-launches-containerized-large-scale-pem-electrolyzer/) | Four 2 MW modules; each 6.1 × 2.45 × 2.9 m estimated container envelope |
| Hydrogen production | `MW × 1000 / 52.5 kWh/kg` gives 108.6 kg/h at initial 5.7 MW and 152.4 kg/h at full 8 MW | Module colour follows the same power series; terminal inventory integrates rate each minute |
| Terminal 350 bar storage | CoolProp hydrogen density at 350 bar, 15 °C ≈23.995 kg/m³; 4,500 kg needs 187.5 m³ | Ten horizontal cylinders, each internal diameter 2 m × 6 m straight length; 188.50 m³ total, approximately 4,523 kg at stated state; wall thickness and end-cap volume not designed |
| Ferry tankage | 1,200 kg fills the simulated 15%→100% interval, implying 1,412 kg total usable inventory. At 23.995 kg/m³, at least 58.8 m³ | Twelve 1 m internal diameter × 6.5 m straight cylinders, 61.26 m³ total; pressure-vessel wall thickness and safety integration unverified |
| Ferry hull analogue | [CMAL lists MV Loch Seaforth at 117.9 m length, 19.2 m breadth and 4.8 m draught](https://www.cmassets.co.uk/ferry/mv-loch-seaforth/) | 117.9 × 19.2 m simplified hull and estimated deck heights. The real vessel has diesel propulsion; the model depicts a **hypothetical hydrogen conversion**, not its actual machinery |
| Wind farm analogue | Peak illustrative wind generation is below 18.6 MW. [Vestas V162 has 6.2 MW rating, 162 m rotor and a 119 m hub option](https://www.vestas.com/en/energy-solutions/onshore-wind-turbines/enventus-platform/v162-6-2-mw) | Three 6.2 MW turbines, 119 m hub, 162 m rotor, 500 m spacing; turbine count and location are estimates |
| Interconnector | 5 MW stated export limit | Electrical cabinet envelope estimated; no cable route or conductor sizing supplied |

The 45 minute bunkering series now integrates 26.67 kg/min to exactly 1,200 kg at minute 45, with zero transfer thereafter. The 4.5 t terminal starts at 4,500 kg in that scenario and ends at 3,300 kg. The earlier fixed 22 kg/min accumulation and 55 minute flow window disagreed with the 45 minute claim. The gale-case terminal inventory now integrates the displayed H₂ production rather than adding a fixed 2.8 kg/min.

The displayed diesel litres are an energy-equivalent illustrative calculation using 3.54 L/kg H₂, not verified emissions or fuel savings for an actual ferry. Electrical dispatch and cost data also remain illustrative until replaced by timestamped PyPSA outputs.

Open `hydrogen_microgrid.blend` in Blender, preserve named meshes used by `hydrogen_scene.js`, export `hydrogen_microgrid.glb`, run `python build_all.py`, then inspect with `run_viewer.cmd`.
