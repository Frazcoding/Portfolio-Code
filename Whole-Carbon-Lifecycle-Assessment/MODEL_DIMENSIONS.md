# Whole-life carbon office: dimensional basis

The source of record is `src/config.py` and `src/inventory.py`. This viewer regenerates its annual values from `src/carbon_calculator.py`; the old hand-written 5,000 m² trajectory was removed.

| Element | Value | Status | Basis |
| --- | ---: | --- | --- |
| Gross internal area | 7,500 m² | Calculated model input | 5 × 1,500 m² in `BuildingArchetype` |
| Plan dimensions | 50 × 30 m | Documented | `CALCULATIONS_WHITE_PAPER.md` §2 |
| Storeys / floor-to-floor | 5 / 3.8 m | Calculated model input | `BuildingArchetype` |
| Total building height | 19.0 m | Calculated model input | 5 × 3.8 m |
| Window-to-wall ratio | 45% | Calculated model input | `BuildingArchetype` |
| Retrofit installed thermal capacity | 215.6 kW | Calculated | `BuildingInventory.calculate_peak_thermal_load`, scenario 2 |
| Baseline installed thermal load | 590.5 kW | Calculated | Same sizing method, scenario 1; rendered as a gas boiler analogue |
| Retrofit rooftop plant | 2 × 85 + 1 × 50 = 220 kW | Capacity estimate | Nearest modular combination of Daikin R290 units, 2.0% over calculated load |
| 85 kW module enclosure | 3.516 × 0.816 × 1.878 m | Manufacturer analogue | [Daikin EWA(Y)K-CZ product catalogue](https://www.daikin.eu/content/dam/internet-denv/catalogues_brochures/industrial/EWA%28Y%29K-CZ_Product%20catalogue_ECPEN26-431_English.pdf) |
| 50 kW module enclosure | 2.516 × 0.816 × 1.878 m | Manufacturer analogue | Same catalogue |
| Scroll compressor cans | 0.38 m diameter × 0.85 m high | Visual estimate | External module dimensions and compressor count are sourced; internal can dimensions are not published in the cited catalogue |
| Baseline boiler enclosure | 4.0 × 1.7 × 2.0 m | Visual estimate | No boiler make or model specified by the simulation |
| PV panel layout | 40 panels, 1.9 × 1.2 m each | Visual estimate | Project specifies PV generation, not panel count or physical array |

The module envelopes are **equipment analogues**, not an assertion that the WLC study selected those products. The R32 new-build scenario currently reuses the same envelope as an explicit sizing surrogate; its actual R32 unit dimensions still require product selection. The internal scroll compressor dimensions, boiler housing, roof PV count, column and mullion cross sections remain estimates. Do not use those dimensions for procurement or fabrication.

The Blender file `wlc_office.blend` is editable. `wlc_office.glb` is the browser asset. Keep node names beginning `Frame`, `FloorSlab`, `HeatPump`, `PVPanel`, and `BaselineBoiler`: the viewer uses them for material and scenario switching. After manual edits, run:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' wlc_office.blend --background --python export_wlc_asset.py
```
