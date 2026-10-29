"""Staffing and organisation of the farm company (user goal 2026-10-07: control, harvesting, HR, everything a mid-size
engineering / farming company needs).

The cost model (cashflow.build) already carries crop work + harvest hours (site_opt labour: Dutch norms, half scaling with
kg) at GBP 16.3/h and GBP 3/m2 of overheads. Dutch labour norms leave out the grower-owner and the office, so this module
adds the salaried team, the packhouse and the 24/7 climate-alarm rota, and works out headcount by department and month.

Inputs, tier and source:
  * National Living Wage GBP 12.71/h from 1 Apr 2026 (sourced: Crossland Solicitors / DavidsonMorris NMW-NLW Apr 2026).
    Crop and harvest staff are paid NLW + 10 % (PLACEHOLDER) - the model's GBP 16.3/h is this plus on-costs.
  * Employer on-costs: NIC 15 % above GBP 5,000/yr per employee (sourced: rates from 6 Apr 2025), workplace pension 3 % of
    salary (auto-enrolment minimum), recruitment/training/PPE 3 % (PLACEHOLDER).
  * Worked hours per FTE: 39 h x 52 wk = 2,028 paid, less 5.6 weeks statutory holiday and 2 % sickness = 1,773 h.
  * Salaries (PLACEHOLDER unless noted): general manager 75 k, head grower 55 k, assistant grower / IPM 38 k, energy & controls
    engineer 45 k (multi-skilled engineer GBP 38-45 k, hvacrecruitment.com 2026 salary guide, sourced range), maintenance
    technician 36 k (maintenance engineer GBP 32-40 k, same source), QA & compliance 36 k, packhouse & logistics supervisor
    33 k, harvest team leader 30 k, HR & admin 30 k, finance controller 55 k (0.5 FTE), account manager 45 k (0.5 FTE).
  * On-call: 4-person weekly rota for climate, heat-pump and power alarms, GBP 3,000/yr allowance each (PLACEHOLDER).
  * Packhouse: grading into bulk crates + cold store 2.5 h per tonne (PLACEHOLDER; retailer collects from the farm).
  * Fixed roles step with area: second assistant grower and technician from 6 ha, a second QA from 8 ha (PLACEHOLDER).
  * Seasonal peak: monthly harvest hours follow the harvest share; months above the annual mean are filled by seasonal
    staff (Seasonal Worker visa route or agency), the base is permanent.
"""
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

NLW = 12.71
CROP_PAY = NLW * 1.10
WORK_H = 39 * 52 * (1 - 5.6 / 52) * 0.98
NIC_RATE, NIC_THRESHOLD, PENSION, RECRUIT = 0.15, 5000.0, 0.03, 0.03
PACK_H_PER_T = 2.5
ON_CALL = (4, 3000.0)
MODEL_RATE = 16.3


@dataclass(frozen=True)
class Role:
    dept: str
    title: str
    salary: float
    fte: tuple                     # ((area_ha_from, fte), ...) stepping with total area


ROLES = (
    Role("Management", "General manager", 75e3, ((0, 1.0),)),
    Role("Growing", "Head grower", 55e3, ((0, 1.0),)),
    Role("Growing", "Assistant grower / IPM and crop registration", 38e3, ((0, 1.0), (6, 2.0))),
    Role("Engineering", "Energy and controls engineer (heat pump, LEDs, climate computer, HV)", 45e3, ((0, 1.0),)),
    Role("Engineering", "Maintenance technician", 36e3, ((0, 1.0), (6, 2.0))),
    Role("Quality", "QA and compliance (BRCGS, GLOBALG.A.P., food safety)", 36e3, ((0, 1.0), (8, 2.0))),
    Role("Packhouse", "Packhouse and logistics supervisor", 33e3, ((0, 1.0),)),
    Role("Harvest", "Harvest team leader", 30e3, ((0, 2.0), (6, 3.0), (9, 4.0))),
    Role("Office", "HR and administration", 30e3, ((0, 1.0), (8, 1.5))),
    Role("Office", "Finance controller", 55e3, ((0, 0.5), (6, 1.0))),
    Role("Sales", "Account manager (retailer contract, forecasting)", 45e3, ((0, 0.5), (6, 1.0))),
)


class Employer:
    @staticmethod
    def loaded(salary, heads=1.0):
        nic = NIC_RATE * max(salary - NIC_THRESHOLD, 0.0)
        return heads * (salary * (1 + PENSION + RECRUIT) + nic)


class Staffing:
    def __init__(self, area_ha, kg_yr, crop_labour_gbp, harvest_share):
        self.ha, self.kg = area_ha, kg_yr
        self.crop_h = crop_labour_gbp / MODEL_RATE
        self.share = np.asarray(harvest_share, float)

    def salaried(self):
        rows = []
        for r in ROLES:
            fte = [f for a, f in r.fte if self.ha >= a - 1e-9][-1]
            rows.append(dict(dept=r.dept, title=r.title, fte=fte, salary=r.salary, cost=Employer.loaded(r.salary, fte)))
        return rows

    def hourly(self):
        pack_h = PACK_H_PER_T * self.kg / 1e3
        crop_fte, pack_fte = self.crop_h / WORK_H, pack_h / WORK_H
        crop_month = self.crop_h * (0.5 / 12 + 0.5 * self.share) / (WORK_H / 12)       # half the hours follow harvest
        base = float(crop_month.mean()) * 0.85
        seasonal = np.clip(crop_month - base, 0, None)
        pay = Employer.loaded(CROP_PAY * WORK_H)
        return dict(crop_fte=crop_fte, pack_fte=pack_fte, crop_month_fte=crop_month.tolist(), permanent_crop_fte=base,
                    seasonal_fte_month=seasonal.tolist(), crop_cost=crop_fte * pay, pack_cost=pack_fte * pay,
                    pay_per_fte=pay)

    def summary(self):
        sal, hr = self.salaried(), self.hourly()
        on_call = ON_CALL[0] * ON_CALL[1] * (1 + NIC_RATE + PENSION)
        salaried_cost = sum(r["cost"] for r in sal) + on_call
        depts = {}
        for r in sal:
            depts[r["dept"]] = depts.get(r["dept"], 0.0) + r["fte"]
        depts["Harvest"] = depts.get("Harvest", 0.0) + hr["crop_fte"]
        depts["Packhouse"] = depts.get("Packhouse", 0.0) + hr["pack_fte"]
        return dict(area_ha=self.ha, kg_yr=self.kg, roles=sal, hourly=hr, departments=depts,
                    fte_total=sum(depts.values()), salaried_fte=sum(r["fte"] for r in sal),
                    salaried_cost=salaried_cost, packhouse_cost=hr["pack_cost"], crop_cost_check=hr["crop_cost"],
                    added_cost=salaried_cost + hr["pack_cost"], added_gbp_kg=(salaried_cost + hr["pack_cost"]) / self.kg,
                    peak_month_fte=float(np.max(hr["crop_month_fte"])) + hr["pack_fte"] + sum(r["fte"] for r in sal))


class Study:
    AREAS = (2.9, 4.4, 5.8, 7.3, 10.2)

    def __init__(self):
        lit = json.loads((HERE / "results" / "bplan" / "lit_open.json").read_text())[2]
        e = lit["prices"]["undercut 3%"]
        self.lead = lit
        self.kg_m2, self.lab_m2 = e["kg_yr"] / 29000.0, e["costs"]["labour"] / 29000.0
        self.share = lit["harvest_share"]

    def at(self, ha):
        return Staffing(ha, self.kg_m2 * ha * 1e4, self.lab_m2 * ha * 1e4, self.share).summary()

    def run(self):
        return {f"{ha}": self.at(ha) for ha in self.AREAS}

    @staticmethod
    def markdown(res):
        lead = res["2.9"]
        L = ["# Staffing and organisation", "", "Inputs and tiers in the staffing.py docstring.", "",
             "## Lead 2.9 ha: roles", "", "| Department | Role | FTE | Salary GBP k | Loaded cost GBP k/yr |", "|---|---|---:|---:|---:|"]
        for r in lead["roles"]:
            L.append(f"| {r['dept']} | {r['title']} | {r['fte']:.1f} | {r['salary'] / 1e3:.0f} | {r['cost'] / 1e3:.0f} |")
        h = lead["hourly"]
        L += [f"| Harvest | Crop work and harvest staff (NLW + 10 %) | {h['crop_fte']:.1f} | {CROP_PAY * WORK_H / 1e3:.1f} | "
              f"{h['crop_cost'] / 1e3:.0f} (already in the model's labour line) |",
              f"| Packhouse | Grading and cold store operatives | {h['pack_fte']:.1f} | {CROP_PAY * WORK_H / 1e3:.1f} | {h['pack_cost'] / 1e3:.0f} |",
              "", f"Total {lead['fte_total']:.1f} FTE; peak month {lead['peak_month_fte']:.1f} FTE. Added to the cost model: salaried team "
              f"GBP {lead['salaried_cost'] / 1e3:.0f} k incl. on-call, packhouse GBP {lead['packhouse_cost'] / 1e3:.0f} k = "
              f"GBP {lead['added_gbp_kg']:.3f}/kg.", "", "## Scaling with area", "",
              "| Area ha | FTE total | Salaried FTE | Added cost GBP k/yr | Added GBP/kg |", "|---:|---:|---:|---:|---:|"]
        for k, s in res.items():
            L.append(f"| {k} | {s['fte_total']:.1f} | {s['salaried_fte']:.1f} | {s['added_cost'] / 1e3:.0f} | {s['added_gbp_kg']:.3f} |")
        return "\n".join(L) + "\n"


if __name__ == "__main__":
    out = HERE / "results" / "bplan"
    res = Study().run()
    (out / "staffing.json").write_text(json.dumps(res, indent=1, default=float))
    md = Study.markdown(res)
    (out / "STAFFING.md").write_text(md)
    print(md)
