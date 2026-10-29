"""No-waste-heat lever tests on finalist designs (R10, 2026-10-03): waste heat off, heat pump supplies all heat. Fast sim, ~1 min.
P2+ hp_frac 0.5 is capex only (store not simulated: check with finalist_lp). * double screen factor unsourced."""
import json, sys, copy, numpy as np
from dataclasses import replace
sys.path.insert(0, r'C:/Users/frase/kDrive/Code/BEng-CEA-Heatpump/lca')
import site_opt, config
site_opt.availability = lambda site, wx, planned=True, unplanned=True: np.zeros(8760)
_orig = site_opt.site_setup
MOD = {}
def patched(site, x, crop, o=None):
    r = _orig(site, x, crop, o)
    if r is None or not MOD: return r
    d, a, cfg, low, avail, wk = r
    m = MOD
    env, cl = cfg.envelope, cfg.climate
    if 'screen_u' in m: env = replace(env, screen_u_factor=m['screen_u'])
    if 'screen_below' in m: env = replace(env, screen_below_C=m['screen_below'])
    if 'night_dK' in m:
        cl = replace(cl, periods=[replace(p, heat_night=p.heat_night + m['night_dK']) for p in cl.periods])
    if 'rh_vent' in m: cl = replace(cl, rh_vent_start=m['rh_vent'])
    cfg = replace(cfg, envelope=env, climate=cl)
    if m.get('hrd'): cfg = replace(cfg, hrd=config.HeatRecoveryDehum(enabled=True), hum=replace(cfg.hum, enabled=True))
    if 'hum_rh' in m: cfg = replace(cfg, hum=replace(cfg.hum, rh_set=m['hum_rh']))
    return d, a, cfg, low, avail, wk
site_opt.site_setup = patched
SL = {s['site_key']: s for s in json.load(open(site_opt.HERE/'data/siting/shortlist.json'))}
cases = [('cucumber', 'Girvan'), ('cucumber', 'Cameronbridge'), ('tomato', 'Girvan')]
PKG = {'night_dK': -2.0, 'hum_rh': 90.0, 'rh_vent': 90.0, 'hrd': True}
LEVERS = [
    ('base (no waste)', {}, {}, {}),
    ('heat-recovery dehum', {}, {}, {'hrd': True}),
    ('P1 controls: night-2K, RH90, HRD', {}, {}, PKG),
    ('P2 = P1 + HP50%+store', {}, {'hp_frac': 0.5}, PKG),
    ('P3 = P2 + utility wind', {}, {'hp_frac': 0.5, 'wind_capex': 1400.0}, PKG),
    ('P4 = P3 + double screen*', {}, {'hp_frac': 0.5, 'wind_capex': 1400.0}, dict(PKG, screen_u=0.35, screen_below=20.0)),
    ('P3 at 8% discount', {}, {'hp_frac': 0.5, 'wind_capex': 1400.0, '_rate': 0.08}, PKG),
    ('base at 8% discount', {}, {'_rate': 0.08}, {}),
]
for crop, nm in cases:
    d = json.load(open(site_opt.OUT/f'refined_{crop}.json'))
    b = next(e['best'] for e in d['sites'] if e['best']['name'].startswith(nm)); s = SL[b['site']]
    print(f"\n== {crop} {b['name']}  {b['area_ha']:.1f} ha  (with waste: {b['gbp_kg_ex_heat']+0.01*b['heat_MWh_per_kg']*1000:.3f})")
    base = None
    for name, dx, opts, mod in LEVERS:
        MOD.clear(); MOD.update(mod)
        x = dict(b['x'], **dx); o = dict({'pipe_mult': 0.0}, **opts)
        G = site_opt.optimise._state(); r0 = G['D']['rate']; G['D']['rate'] = o.pop('_rate', r0)
        r = site_opt.evaluate(s, x, crop, o); G['D']['rate'] = r0
        c = r['gbp_kg_ex_heat']; base = base or c
        print(f"  {name:30s} GBP/kg {c:.3f} ({c-base:+.3f})  kgCO2/kg {r['kg_kg']:.2f}  heat {r['heat_kWh_m2']:4.0f}  Y {r['Y']:.1f}  "
              f"elec {r['elec_kWh_m2']+0:.0f}  unmet {r['unmet_h']}  wind {r['wind_kW']:.0f}")
