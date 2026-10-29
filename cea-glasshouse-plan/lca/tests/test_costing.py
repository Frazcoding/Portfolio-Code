"""Checks for sizing.py and costing.py. Run from lca/: python tests/test_costing.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))
import costing  # noqa: E402
import design as D  # noqa: E402
import sizing  # noqa: E402
from simcore import weather  # noqa: E402

V = [(0, 0), (0.25, 0.81), (0.5, 0), (0.75, 0.81), (1, 0)]
ok = True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(f"{'OK  ' if cond else 'FAIL'} {name} {detail}")


L = sizing.Loads()
# BS EN 1991-1-3 UK NA: s_k = 0.15 + (0.1 Z + 0.05) + (A - 100)/525, Z = 4, A = 10 m
check("snow s_k formula", abs(L.s_k - (0.15 + 0.45 + (10 - 100) / 525)) < 1e-9, f"{L.s_k:.3f}")
check("multi-span drift raises gutter snow above undrifted 0.8 s_k",
      sizing.size(D.Design(n_spans=12, span_w=8.0, profile=V))["snow_kN_m2"] > 0.8 * L.s_k)
s8 = sizing.size(D.Design(n_spans=12, span_w=8.0, profile=V, glazing="dbl_ar_lowe"))
s16 = sizing.size(D.Design(n_spans=6, span_w=16.0, profile=[(0, 0), (0.5, 1.6), (1, 0)], glazing="dbl_ar_lowe"))
check("primary steel per m2 grows with span", s16["primary_kg"] / 9600 > s8["primary_kg"] / 9600,
      f"{s8['primary_kg'] / 9600:.2f} -> {s16['primary_kg'] / 9600:.2f} kg/m2")
check("heavier glazing needs more steel",
      sizing.size(D.Design(n_spans=12, span_w=8.0, profile=V, glazing="dbl_ar_lowe"))["steel_kg"]
      > sizing.size(D.Design(n_spans=12, span_w=8.0, profile=V, glazing="pc_twin"))["steel_kg"])
check("steel in a plausible Venlo range (5-15 kg/m2)", 5 < s8["steel_kg_m2"] < 15, f"{s8['steel_kg_m2']:.1f}")

R = costing.rates()
check("every rate has a cost tier and life", all(r["cost_tier"] and (r["life_yr"] or 0) > 0 for r in R.values()))
check("every non-placeholder cost has a source",
      all(r["cost_source"] for r in R.values() if "placeholder" not in r["cost_tier"]))
weather.SITES.setdefault("perth_carse", (56.42, -3.20, 0, "Carse"))
wx = weather.load("perth_carse")
resid, ref = costing.calibration(wx, 56.42, -3.20)
d = costing.reference(wx, 56.42, -3.20)
a = D.analyse(d, wx, 56.42, -3.20)
e = costing.capex(d, a, resid)
check("reference design reproduces the SAC anchor (GBP 200/m2)", abs(e["capex_gbp_m2"] - 200.0) < 1e-6,
      f"{e['capex_gbp_m2']:.2f}")
dbl = D.Design(length=100, n_spans=12, span_w=8.0, gutter_h=6.0, profile=V, glazing="dbl_ar_lowe")
e2 = costing.capex(dbl, D.analyse(dbl, wx, 56.42, -3.20), resid)
check("double glazing costs more than single", e2["capex_gbp_m2"] > e["capex_gbp_m2"])
check("embodied carbon positive and below 10 kg/m2/yr", 0 < e["co2_kg_m2_yr"] < 10, f"{e['co2_kg_m2_yr']:.2f}")
print("PASS" if ok else "FAIL")
