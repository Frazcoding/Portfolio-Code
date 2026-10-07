"""R10: re-cost the refined finalists with waste heat switched off (availability 0, no connection pipe)."""
import json, sys, numpy as np
sys.path.insert(0, r'C:/Users/frase/kDrive/Code/BEng-CEA-Heatpump/lca')
import site_opt
site_opt.availability = lambda site, wx, planned=True, unplanned=True: np.zeros(8760)
SL = {s['site_key']: s for s in json.load(open(site_opt.HERE/'data/siting/shortlist.json'))}
imp = {'cucumber': 1.574, 'tomato': 1.77}
for crop in ['cucumber', 'tomato']:
    d = json.load(open(site_opt.OUT/f'refined_{crop}.json'))
    for e in d['sites']:
        b = e['best']; s = SL[b['site']]
        if s['grade'] == 'low': continue
        r = site_opt.evaluate(s, b['x'], crop, {'pipe_mult': 0.0})
        base = b['gbp_kg_ex_heat'] + 10/1000*b['heat_MWh_per_kg']*1000/1000*1000/1000  # placeholder
        print(f"{crop[:4]} {b['name'][:22]:22s} with-waste {b['gbp_kg_ex_heat']+0.010*b['heat_MWh_per_kg']*1000:.3f}  no-waste {r['gbp_kg_ex_heat']:.3f}  "
              f"kgCO2 {b['kg_kg']:.2f}->{r['kg_kg']:.2f}  heat {r['heat_kWh_m2']:.0f}  hpMWh {r['hp_MWh']:.0f} hp_elec {r['hp_elec_MWh']:.0f} "
              f"COP {r['hp_MWh']/max(r['hp_elec_MWh'],1):.2f}  elec_price {r['elec_price']:.3f} wind {r['wind_kW']:.0f} batt {r['batt_kWh']:.0f} "
              f"en_cost/kg {r['en_cost_gbp']/(r['Y']*r['area_ha']*1e4):.3f}  unmet {r['unmet_h']}  import {imp[crop]}")
