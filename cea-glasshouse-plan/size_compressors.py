"""Estimate annual R717 two-stage swept-volume requirements from calibrated CSVs.

The candidate filter uses a rounded-temperature suction-density proxy, then
evaluates the strongest LP and HP candidates with the white-paper compressor map.
The selected nominal machine count includes margin beyond candidate ranking error.
"""
from pathlib import Path
import csv
import heapq
import json
import math
from CoolProp.CoolProp import PropsSI

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'outputs'
FLUID='Ammonia'
PC=PropsSI('P','T',85+273.15,'Q',0,FLUID)
cache={}
candidates=[]
with (DATA/'calibrated_v2_heat_load.csv').open() as fh_a,(DATA/'calibrated_v2_results_air_source.csv').open() as fh_b:
    for a,b in zip(csv.DictReader(fh_a),csv.DictReader(fh_b)):
        m1=float(b['m_dot_1_kg_s']);m2=float(b['m_dot_2_kg_s'])
        if m2<=0:continue
        te=float(a['external_temp_C'])-5
        rounded=round(te*5)/5
        if rounded not in cache:
            pe=PropsSI('P','T',rounded+273.15,'Q',1,FLUID)
            pi=math.sqrt(pe*PC)
            rho1=PropsSI('D','T',rounded+276.15,'P',pe,FLUID)
            rho2=PropsSI('D','P',pi,'Q',1,FLUID)
            cache[rounded]=(rho1,rho2)
        rho1,rho2=cache[rounded]
        candidates.append({'hour':int(b['hour']),'te':te,'m1':m1,'m2':m2,
                           'heat_kw':float(b['Q_c_W'])/1000,
                           'lp_proxy':m1/rho1,'hp_proxy':m2/rho2})

selected={r['hour']:r for r in heapq.nlargest(500,candidates,key=lambda x:x['lp_proxy'])}
selected.update({r['hour']:r for r in heapq.nlargest(500,candidates,key=lambda x:x['hp_proxy'])})

def swept(r):
    te=r['te']; pe=PropsSI('P','T',te+273.15,'Q',1,FLUID);pi=math.sqrt(pe*PC)
    ratio=pi/pe
    t1=te+276.15
    h1=PropsSI('H','T',t1,'P',pe,FLUID)
    s1=PropsSI('S','T',t1,'P',pe,FLUID)
    h2s=PropsSI('H','S',s1,'P',pi,FLUID)
    h2=h1+(h2s-h1)/(.874-.0135*ratio)
    h3=PropsSI('H','P',pi,'Q',1,FLUID)
    hmix=(r['m1']*h2+(r['m2']-r['m1'])*h3)/r['m2']
    rho1=PropsSI('D','T',t1,'P',pe,FLUID)
    rho2=PropsSI('D','P',pi,'H',hmix,FLUID)
    return {'hour':r['hour'],'heat_kw':r['heat_kw'],'evap_C':te,
            'p_evap_bar':pe/1e5,'p_int_bar':pi/1e5,'p_cond_bar':PC/1e5,
            'm_dot_lp_kg_s':r['m1'],'m_dot_hp_kg_s':r['m2'],
            'lp_required_m3h':r['m1']/rho1/(.95-.025*ratio)*3600,
            'hp_required_m3h':r['m2']/rho2/(.95-.025*(PC/pi))*3600}

calculated=[swept(r) for r in selected.values()]
lp=max(calculated,key=lambda x:x['lp_required_m3h'])
hp=max(calculated,key=lambda x:x['hp_required_m3h'])
result={'basis':'Annual calibrated air-source CSV; 80 C sink + 5 K condenser pinch; white-paper eta_v map',
        'rows_checked':len(candidates),'candidate_rows_exact':len(calculated),
        'lp_peak':lp,'hp_peak':hp,
        'analogue':'Three 50 bar NH3 reciprocating cores, each nominal 193 m3/h: two LP, one HP',
        'lp_installed_m3h':386,'hp_installed_m3h':193,
        'analogue_core_dimensions_m':[.84,.785,.685]}
(ROOT/'compressor_sizing.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
