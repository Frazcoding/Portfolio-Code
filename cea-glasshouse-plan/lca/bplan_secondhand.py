"""BP19c: second-hand glasshouse, re-erected. Bottom-up GBP/m2 against the new single-glass structure of workbook scenario S2
(a used Venlo house is single glazed, so the like-for-like new build is S2, not the double-glazed S0).
Sourced: purchase price (SAC/SRUC 2026 Table 11, ~GBP 600k/ha used structure). Everything else is a labelled placeholder
until quotes arrive (RFQ_SPEC.md 3.8); the Avero (2025) re-erection guideline named in earlier notes could not be found
online, so it is NOT used. Output: results/bplan/secondhand.json and a table; delta capex and delta GBP/kg at 8 % and 3.5 %
on the workbook's own basis (CRF 30 yr, O&M 2 %, development + contingency 15 %)."""
import json
from pathlib import Path

import bplan_residual

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "bplan" / "secondhand.json"
PURCHASE = 60.0                       # GBP/m2, SAC/SRUC 2026 Table 11 (sourced)
RE_ERECT = (25.0, 35.0, 50.0)         # dismantle + haul + re-erect, GBP/m2 (placeholder)
GLASS_REPLACE_FRAC = (0.05, 0.15, 0.30)   # glazed area replaced (breakage, seals), at new single-glass price


class SecondHandCase:
    def __init__(self, inputs):
        self.d = inputs
        self.s0, self.s2 = inputs["scen"][0], inputs["scen"][2]
        self.A = self.s2["area_m2"]
        self.rates = inputs["rates"]
        self.resid = bplan_residual.ResidualItems(inputs["resid_gbp_m2"])
        self.kg = self.s2["kg"]

    def new_structure_gbp_m2(self):
        q = self.s2["quantities"]
        return sum(q[k] * self.rates[k]["cost"] for k in q) / self.A + self.d["resid_gbp_m2"]

    def second_hand_gbp_m2(self, i):
        q = self.s2["quantities"]
        glass = q["glass_single_m2"] * self.rates["glass_single_m2"]["cost"] / self.A
        concrete = q["concrete"] * self.rates["concrete"]["cost"] / self.A
        pipe_screen = (q["heating_pipe_m"] * self.rates["heating_pipe_m"]["cost"] + q["energy_screen_m2"] * self.rates["energy_screen_m2"]["cost"]) / self.A
        fitout = self.d["resid_gbp_m2"] - self.resid.rows[0]["gbp_m2_central"]      # residual without erection labour
        return dict(purchase=PURCHASE, re_erect=RE_ERECT[i], foundations=concrete, glass_replacement=glass * GLASS_REPLACE_FRAC[i],
                    heating_pipe_screens=pipe_screen, fitout_residual=fitout)

    def delta_gbp_kg(self, dcap_m2, rate):
        crf = rate / (1 - (1 + rate) ** -30)
        return dcap_m2 * self.A * (1.15) * (crf + self.d["D"]["om_frac"]) / self.kg

    def run(self):
        new = self.new_structure_gbp_m2()
        out = dict(new_single_glass_gbp_m2=new, cases={})
        for name, i in (("low", 0), ("central", 1), ("high", 2)):
            parts = self.second_hand_gbp_m2(i)
            tot = sum(parts.values())
            out["cases"][name] = dict(parts=parts, total_gbp_m2=tot, dcap_gbp_m2=tot - new, dcap_gbp=(tot - new) * self.A * 1.15,
                                      dgbp_kg_8=self.delta_gbp_kg(tot - new, 0.08), dgbp_kg_35=self.delta_gbp_kg(tot - new, 0.035))
        OUT.write_text(json.dumps(out, indent=1))
        return out


if __name__ == "__main__":
    r = SecondHandCase(json.loads((HERE / "results" / "bplan" / "xlsx_inputs.json").read_text())).run()
    print(f"new single-glass structure incl. residual: GBP {r['new_single_glass_gbp_m2']:.0f}/m2")
    for k, c in r["cases"].items():
        print(f"{k:<8} {c['total_gbp_m2']:.0f}/m2  d capex {c['dcap_gbp_m2']:+.0f}/m2 ({c['dcap_gbp'] / 1e6:+.2f} M incl dev+cont)  GBP/kg 8% {c['dgbp_kg_8']:+.3f}  3.5% {c['dgbp_kg_35']:+.3f}")
        print("   ", {a: round(b, 1) for a, b in c["parts"].items()})
