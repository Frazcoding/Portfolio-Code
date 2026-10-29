# Industrial heat pump: dimension and energy register

`industrial_hthp.blend` holds two **alternative** plant layouts. The viewer shows the dairy row for the 95 °C hot-water case and the steam row for the 130 °C case. Both share a 24 × 12 m display plinth; this is an estimated access envelope, not a surveyed factory foundation. The viewer trajectories remain illustrative.

| Item | Calculation or known simulation value | Model geometry and confidence |
| --- | --- | --- |
| Dairy heat balance | 650 kW delivered − 175 kWe = 475 kW effluent uptake | Source and condenser exchangers shown |
| Dairy effluent outlet | 28.5 m³/h × 1000 kg/m³ × 4.18 kJ/(kg K) = 33.1 kW/K; 475/33.1 = 14.36 K drop, 45 → 30.6 °C | Calculated with water-property assumptions; exposed as viewer telemetry |
| Dairy effluent pipe | At 1.5 m/s design velocity, 28.5 m³/h requires 82 mm inside diameter | 100 mm outside diameter visual pipe, estimated wall thickness |
| Dairy compressor | 175 kWe input | 2.8 × 1.45 × 1.35 m housing with 1.04 m diameter motor case, estimates; no duty-point selection |
| Steam source balance | 520 kW delivered − 188 kWe = 332 kW flue-gas uptake | Flue exchanger shown |
| Flue gas outlet | 14.2 kg/s × assumed 1.05 kJ/(kg K) ≈ 14.91 kW/K; 332/14.91 = 22.3 K drop, 65 → 42.7 °C | Calculated assumption; exposed as viewer telemetry |
| Flue duct | 14.2 kg/s at assumed 1.1 kg/m³ and 20 m/s requires ≈0.645 m² flow area | 0.90 m diameter display duct (0.636 m²), estimated |
| Steam outlet | Water saturation at 130 °C: 2.703 bar absolute. With 20 °C feedwater, 520 kW yields approximately 0.197 kg/s steam | Separator shell 1.36 m diameter × 2.7 m high, estimated; no steam quality or hold-up time specified |
| Steam compressor | 188 kWe input | 2.8 × 1.45 × 1.35 m housing, estimated |
| Plate exchangers | Duty specified, but no temperatures on both sides, pressure drop or plate specification | Frames 1.3 × 1.4 × 2.0–2.4 m, estimated |

The [BITZER CSH2T high-temperature series](https://www.bitzer.de/mv/en/products/screw-compressors/csh2t/) is an R1233zd(E) steam-case technology analogue. Its [technical data sheet](https://www.bitzer.de/shared_media/documentation/2024_chillventa_productsheets/sp-170-9-en.pdf) lists a 649 kW heating capacity at 70/120 °C for one model; that is **a different duty point** from this 520 kW at 130 °C case and does not validate product selection or the depicted housing size. A specific dairy-case refrigerant and compressor have not been resolved from simulation inputs. The dairy case is represented as a capacity-sized generic package.

The former viewer stated that 28.5 m³/h effluent cooled from 45 to 25 °C while providing only 475 kW. The 20 K drop would yield approximately 662 kW. The outlet was corrected to the duty-consistent 30.6 °C, with the assumed density and heat capacity above.

Open `industrial_hthp.blend` in Blender. Preserve the `Dairy_` and `Steam_` prefixes and the named parts used by `industrial_scene.js`, export to `industrial_hthp.glb`, then run `python build_all.py` and inspect with `run_viewer.cmd`.
