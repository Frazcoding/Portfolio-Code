# Plantpost model dimensions

All lengths in metres unless stated. The documented values come from `CALCULATIONS_WHITE_PAPER.md`, section 8. Geometry estimates are explicitly separate from those model inputs.

| Part | Model dimension | Basis | Geometry in `create_plantpost_asset.py` |
| --- | ---: | --- | --- |
| Total post height | 4.50 | Documented `height_post_m` | Canopy top at 4.50 |
| PV canopy outside diameter | 2.00 | Documented `diameter_canopy_m` | Radius 1.00 |
| Planter drip elevations | 1.0, 2.0, 3.0, 4.0 | Documented `tier_heights_m` | Four named tiers |
| Reservoir capacity | 150 L | Documented `volume_tank_max_l` | 0.150 m³ |
| Reservoir cross section | 0.15 m² | Documented `area_tank_m2` | Radius `sqrt(0.15/pi)` = 0.2185 |
| Reservoir usable height | 1.00 | Calculated 0.150 m³ / 0.15 m² | 1.00 |
| Irrigation tubing bore | 8 mm | Documented `pipe_int_diameter_m` | 8 mm ID; 12 mm OD estimated |
| Luminaire power | 47.1 W | Documented `power_light_w` | Named `Luminaire` mesh |
| Battery capacity | 1.28 kWh / 100 Ah | Documented `battery_nominal_kwh` | Housing 0.30 × 0.20 × 0.18 estimated |
| Structural pole outside diameter | 0.15 | Estimate for display; no structural sizing given | 0.075 radius |
| Planter outside diameter | 1.26 | Estimate; no planter diameter given | 0.63 radius |
| PV dish rise | 0.14 | Estimate; projected aperture is fixed at 2 m diameter | Shallow conical mesh |

The real system should not be fabricated from these estimates. Replacing an estimate with a surveyed or manufacturer dimension requires updating this register and the Blender script, then checking the `.blend` and `.glb` exports. The reservoir mesh uses `v_tank` to show water level; the lamp uses `p_light` or `light_state` to show on/off state. Other colours and foliage geometry are illustrative.
