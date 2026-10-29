# Building heat pump retrofit: dimensional model

The editable `retrofit_plant.blend` represents the plant equipment. The simulation does not supply the served building's geometry, so the 30 × 24 m slab is a display plinth, not the building footprint.

| Part | Model size and basis | Status |
| --- | --- | --- |
| Two TES vessels | Each straight shell is 5.000 m high with radius `sqrt(100/(π×5)) = 2.523 m`, giving 100 m³; 200 m³ total | Volume fixed by simulation; height estimated |
| ASHP A and B | 85 kW nominal each, 3.516 × 0.816 × 1.878 m enclosure each | Vendor analogue; 170 kW installed for 160 kW TES dispatch |
| ASHP C | 85 kW nominal, same enclosure | Added for 280 kW direct dispatch |
| ASHP D | 50 kW nominal, 2.516 × 0.816 × 1.878 m enclosure | Direct mode total 305 kW installed |
| Grid transformer | 60 kWe connection limit; 2.2 × 1.7 × 2.5 m envelope | Rating from simulation; housing estimated |
| ASHP scroll cans | 0.36 m diameter × 0.85 m high | Internal visual estimate, not manufacturer geometry |
| Hydronic manifolds | 0.20 m diameter | Visual estimate; flow and pressure drop unspecified |

The enclosure analogue is the [Daikin EWA(Y)K-CZ R290 catalogue](https://www.daikin.eu/content/dam/internet-denv/catalogues_brochures/industrial/EWA%28Y%29K-CZ_Product%20catalogue_ECPEN26-431_English.pdf). This is a capacity and cabinet-size analogue, not a product selection for the simulated duty.

The viewer selects the TES or direct equipment bank for each scenario. Tank shell colour encodes thermal state of charge without lowering a water level. The transformer changes colour when simulated electrical demand exceeds 60 kWe. The chart trajectories remain illustrative scenarios.

Open `retrofit_plant.blend` in Blender, preserve the named parts in `retrofit_scene.js`, then export and regenerate:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b 'Building-Heatpump-Retrofit\retrofit_plant.blend' --python 'Building-Heatpump-Retrofit\export_retrofit_asset.py'
python build_all.py
```

Use `run_viewer.cmd` to inspect the `.glb` through the local server.
