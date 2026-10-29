"""Preliminary EN 13031-1:2019 check of the Gate B design(s): reliability class, load reduction, member resizing.

What this checks (concept stage, same member model as sizing.py):
  * Classification: glass cladding on glazing bars is not tolerant to frame displacement -> Type A; a commercial
    production greenhouse clad in glass should have a design working life of at least 15 years -> class A15,
    consequence class CC0; Type A needs both ULS and SLS checks (EN 13031-1 Table 1 as reproduced in Pertermann &
    Puthli (2022) Background Report Reliability Part 1 to EN 13031-1:2019, Table 1; saved in data/standards/).
  * Partial factors: EN 13031-1 gives no normative partial factors, only K_FI recommendations applied to the
    EN 1990 CC2 values gamma_G = 1.35, gamma_Q = 1.5 (Background Report Table 10): CC0 K_FI,G = K_FI,Q = 0.8;
    K_FI,G = 0.9 where the permanent action dominates. The UK National Annex may set other values (to confirm).
  * Snow for a 15-year reference period: EN 1991-1-3 Annex D (D.1), Gumbel,
    s_n = s_k [1 - V sqrt(6)/pi (ln(-ln(1 - p)) + 0.57722)] / (1 + 2.5923 V), p = 1/n with n = 15 (Background
    Report sec. 3: Pn ~ 1/n). V = 0.2 is the low end of the usual range and gives the smallest reduction
    (conservative choice until the UK NA / site data give V).
  * Wind for a 15-year reference period: EN 1991-1-4 4.2(2)P Note 4, c_prob = [(1 - K ln(-ln(1 - p))) /
    (1 - K ln(-ln(0.98)))]^n, K = 0.2, n = 0.5 (recommended values); peak pressure scales with c_prob^2.
Not checked here (needs the full structural design at Gate C): connections, bracing, uplift on the cover, glazing
panes (EN 16612), gutters as drainage, crop-load values from EN 13031-1 Annex (sizing.Loads.crop_kN_m2 is still a
placeholder), site snow zone / basic wind speed from the UK NA maps (input register item 10).
Usage: python en13031.py [crop ...] -> results/site_opt/en13031_<crop>.json
"""
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import costing  # noqa: E402
import optimise  # noqa: E402
import sizing  # noqa: E402
import site_opt  # noqa: E402

DESIGN_LIFE = 15
V_SNOW = 0.2
K_FI = 0.8
K_FI_G_DOMINANT = 0.9


def snow_factor(n=DESIGN_LIFE, V=V_SNOW):
    p = 1.0 / n
    return (1 - V * math.sqrt(6) / math.pi * (math.log(-math.log(1 - p)) + 0.57722)) / (1 + 2.5923 * V)


def c_prob(n=DESIGN_LIFE, K=0.2, ex=0.5):
    p = 1.0 / n
    return ((1 - K * math.log(-math.log(1 - p))) / (1 - K * math.log(-math.log(0.98)))) ** ex


def loads_a15(base=sizing.Loads(), dominant_permanent=False):
    return replace(base, gamma_G=1.35 * (K_FI_G_DOMINANT if dominant_permanent else K_FI), gamma_Q=1.5 * K_FI,
                   snow_factor=snow_factor(), wind_factor=c_prob() ** 2)


def check(x):
    d = optimise.build(x)
    base = sizing.size(d)
    a15 = sizing.size(d, loads_a15())
    a15g = sizing.size(d, loads_a15(dominant_permanent=True))
    R = costing.rates()
    steel_gbp_t = R["steel"]["cost_central"]
    worst = max(a15["steel_kg"], a15g["steel_kg"])
    return dict(x=x, floor_m2=d.floor, snow_factor=snow_factor(), c_prob=c_prob(),
                gamma_G=1.35 * K_FI, gamma_Q=1.5 * K_FI,
                steel_kg_m2_cc2_50yr=base["steel_kg_m2"], steel_kg_m2_a15=worst / d.floor,
                steel_saving_kg_m2=(base["steel_kg"] - worst) / d.floor,
                steel_saving_gbp_m2=(base["steel_kg"] - worst) / 1e3 * steel_gbp_t / d.floor,
                snow_kN_m2_cc2=base["snow_kN_m2"], snow_kN_m2_a15=a15["snow_kN_m2"], q_p_cc2=base["q_p"],
                q_p_a15=a15["q_p"], passes=bool(worst <= base["steel_kg"] * 1.0001))


def main(crop):
    R = json.loads((site_opt.OUT / f"refined_{crop}.json").read_text())
    out = []
    print(f"== {crop}: EN 13031-1 A15/CC0 vs EN 1990 CC2 50-yr (current costing basis); snow x{snow_factor():.3f}, "
          f"wind pressure x{c_prob() ** 2:.3f}, gamma_G {1.35 * K_FI:.2f} / gamma_Q {1.5 * K_FI:.2f}")
    for s in R["sites"][:6]:
        c = check(s["best"]["x"])
        c.update(site=s["site"], name=s["name"])
        out.append(c)
        print(f"{s['name'][:32]:<33} steel {c['steel_kg_m2_cc2_50yr']:.1f} -> {c['steel_kg_m2_a15']:.1f} kg/m2 "
              f"(saves GBP {c['steel_saving_gbp_m2']:.1f}/m2); the CC2 design satisfies A15: {c['passes']}")
    (site_opt.OUT / f"en13031_{crop}.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    for c in sys.argv[1:] or ["cucumber", "tomato"]:
        main(c)
