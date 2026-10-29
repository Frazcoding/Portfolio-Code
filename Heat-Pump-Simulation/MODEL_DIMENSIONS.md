# Two-stage heat pump rig: dimensional assumptions

`heatpump_rig.blend` is an editable plant layout for the illustrative 45.2 kW London case. The repository has climate CSV processing, but no validated refrigerant cycle output for these viewer trajectories. The 6 × 3 m skid and heat-exchanger/receiver envelopes are estimates, not fabrication drawings.

| Item | Basis | Blender model |
| --- | --- | --- |
| Working fluid | R290 assumed for this rig; the prior R1233zd(E)/R290 mixed label could not describe one set of pressures | R290 labels and pressure state |
| LP suction | 0.182 kg/s at 3.2 bar absolute and 5 K superheat; CoolProp R290 density ≈6.925 kg/m³ | 2 scroll cans, each 0.46 m diameter × 0.95 m high, envelope estimate |
| LP swept volume | `0.182 / 6.925 / 0.8 × 3600 = 118.3 m³/h`, assuming volumetric efficiency 0.8 | Two nominal 77.2 m³/h analogue scrolls, 154.4 m³/h total |
| HP minimum swept volume | At geometric mean intermediate pressure 8.24 bar, R290 vapour density ≈17.29 kg/m³ at 5 K superheat: 47.4 m³/h before injection | One nominal 77.2 m³/h analogue scroll, 0.54 m diameter × 1.02 m high envelope estimate |
| Flash receiver | No refrigerant charge, residence time or injection fraction given | 0.72 m diameter × 1.65 m straight shell; ≈0.672 m³, estimated |
| Exchangers | Heating duty ≈45 kW; no approach temperatures, plate design, pressure drop or water flow given | 0.8 × 0.9 × 1.3 m frame each, estimated |
| Tubing | Refrigerant flow given for London; pressure loss, velocity and routing limits missing | 50–90 mm outside diameters, layout estimates |

The [BITZER ORBIT PRO R290 range](https://www.prod.bitzer.de/sg/en/products/scroll-compressors/orbit-pro/) lists 19.8–77.2 m³/h at 50 Hz; the model uses its upper swept-volume figure as a **capacity analogue**, not a verified compressor selection. The cans' physical envelopes are estimates because the required CAD drawings have not been matched to a specific product code. The single HP compressor is provisional because flash injection adds to HP mass flow and the injection ratio is absent.

The original illustrative London 16.8 bar condensing pressure corresponds to about 49 °C saturation with R290, below the stated 55 °C water supply. The displayed London pressure was adjusted to approximately 21.2 bar (60 °C saturation). The Glasgow pressure was adjusted from 21.5 to approximately 25.9 bar (70 °C saturation for 65 °C water). These are consistency assumptions, **not measured or solver-calculated points**. COP, discharge temperature, economiser heat and other traces remain illustrative and require a thermodynamic model for validation.

Open `heatpump_rig.blend` in Blender and preserve the names in `heatpump_scene.js` when editing. After an edit, export the visible meshes as `heatpump_rig.glb` and run `python build_all.py`; use `run_viewer.cmd` to inspect the web view.
