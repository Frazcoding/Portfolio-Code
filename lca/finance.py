"""BP33 + BP37e: nominal, post-tax financing model on the lit lead (results/bplan/lit_open.json, no physics rerun).

The real, pre-tax project layer of cashflow.build (kg, opex lines, replacement capex, residual value) is rebuilt from the
saved lit_open entry, then put into money of the day and financed. User decisions 2026-10-07: lights allowed, no capex
cap, price slightly UNDER import parity, supplier / asset finance preferred to 8 % all-investor money.

Inputs, tier and source:
  * CPI 2.0 %/yr on prices, opex, replacements and residual value (sourced: Bank of England inflation target). The
    contract price is assumed CPI-indexed (PLACEHOLDER: needs the retailer's indexation clause); debt rates are fixed
    nominal, so inflation erodes the real debt service.
  * Corporation tax 25 % main rate (sourced: CTA 2010, rate from 1 Apr 2023). Full expensing: 100 % first-year allowance
    on new main-pool plant (CAA 2001 s.45S); the glasshouse is plant (CAA 2001 s.23 List C item 17: glasshouse whose
    air, heat, light, irrigation and temperature are provided automatically by devices forming part of its structure).
    Conservative split: heat pump, store, boiler, battery, LEDs and heating pipe treated as special-rate integral
    features (50 % first-year allowance s.45S, then 6 % writing-down allowance on the balance) unless HMRC accepts
    them as part of the List C glasshouse; replacements at special rate too; HV connection contribution and development
    costs get no allowance (not owned plant / planning costs). Capital grants reduce qualifying cost (CAA 2001 s.532).
    Trading losses carried forward without limit (profits below the GBP 5 M deductions allowance, CTA 2010 s.269ZR).
    Disposal at year 30: pool balance less residual value (balancing allowance or charge). Tax paid in the year.
  * Repayment holiday: interest only in year 1 (the crop-establishment ramp year). Under the OECD Arrangement the first
    ECA instalment is due 6 months after the starting point (acceptance of the plant): a 1-yr holiday needs the ECA to
    set the starting point at the end of year 1 (PLACEHOLDER, needs the ECA's agreement).
  * DSRA = 6 months of the next year's debt service, funded at close, moved to target every year, released at the end.
    Working capital = 2 months of opex, funded at close, grows with CPI, released in year 30.
  * Supplier credit (ECA-backed Dutch builder, OECD Arrangement): 85 % of the export contract (15 % minimum down
    payment), 15 yr max; fixed rate = GBP CIRR 5.81 % (sourced: OECD CIRR table, valid 15 Sep - 14 Oct 2026, bond
    maturity = drawdown 1 yr + 0.5 x repayment 14 yr + 0.5 x 0.5 yr frequency = 8.25 -> 8 yr; the 15 Oct - 14 Nov 2026
    table gives 6.09 %); equal-principal instalments (Arrangement standard repayment). ECA premium 2 % of the credit
    paid up front (PLACEHOLDER: Atradius DSB premium depends on the buyer's rating and tenor; needs an indication).
    Lender arrangement fee 1 % on asset finance and bank debt (PLACEHOLDER).
  * Plant asset finance (heat pump, store, LEDs, battery): 90 % advance, Bank Rate 3.75 % + 3.25 % = 7.0 %, 10 yr,
    annuity (PLACEHOLDER, margin range 3.0-3.5 % to be quoted).
  * Alternative bank term debt: sculpted to DSCR 1.25 on CFADS, 15 yr, Bank Rate + 3.0 % = 6.75 %, gearing cap 65 %
    (PLACEHOLDER: needs an indicative term sheet).
  * Non-voting cumulative preference shares, 12 % coupon, 50 % of the equity cheque; paid ahead of ordinary dividends,
    then 50 % of the remaining distributable cash redeems them (PLACEHOLDER terms).
  * Grant option: GBP 400 k FDPSS (GRANTS.md: packhouse only, eligibility unconfirmed; the glasshouse has no open grant).
  * Heat-plant ESCo: owns heat pump + store + boiler, charges a level fee = annuity at 9 % nominal over 15 yr
    (PLACEHOLDER: infrastructure-fund hurdle 8-10 %); the farm buys the plant out at year 10 for the ESCo's outstanding
    balance; second-hand plant gets 18 % writing-down allowance (no full expensing for used plant).
  * Lender test: CFADS = EBITDA - tax - maintenance reserve - working-capital build; minimum DSCR 1.25 (PLACEHOLDER
    1.20-1.35). Ordinary equity hurdle 12 % nominal post-tax (PLACEHOLDER); all-equity benchmark 10.2 % nominal post-tax
    (= 8 % real at 2 % CPI).

    python finance.py            -> results/bplan/finance.json, results/bplan/FINANCE.md
"""
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cashflow  # noqa: E402

OUT = HERE / "results" / "bplan"
YEARS = cashflow.YEARS
CPI, CT = 0.02, 0.25
BANK_RATE, CIRR_GBP_8Y = 0.0375, 0.0581
DSCR_MIN, EQUITY_HURDLE, ALL_EQUITY_HURDLE = 1.25, 0.12, 1.08 * (1 + CPI) - 1
CO2_BASE = 0.06
LABOUR_KG_SHARE = 0.5                       # site_opt.LABOUR_KG_SHARE (placeholder): half of labour scales with kg
RESID_KEY = "residual (SAC-calibrated: install, climate computer, irrigation, vents ...)"
STRUCT_KEYS = ("steel", "aluminium", "glass_single_m2", "glass_double_m2", "concrete", "pir_panel_m2", "heating_pipe_m",
               "energy_screen_m2", RESID_KEY)
PLANT_KEYS = ("heat_pump", "hot_water_store", "led_lighting", "peak_boiler", "battery")
SPECIAL_KEYS = ("heat_pump", "hot_water_store", "peak_boiler", "battery", "led_lighting", "heating_pipe_m")
NO_ALLOWANCE_KEYS = ("hv_import_connection", "development", "waste_heat_pipe")
ESCO_KEYS = ("heat_pump", "hot_water_store", "peak_boiler")
ELEC_KEYS = ("electricity_grid", "electricity_wind_from_turbine", "network_charge_increase")
PER_KG_KEYS = ("packing", "haulage_to_rdc")


def irr(cf, lo=-0.95, hi=5.0):
    f = lambda r: cashflow.npv(cf, r)  # noqa: E731
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(100):
        m = 0.5 * (lo + hi)
        lo, hi = (lo, m) if f(lo) * f(m) <= 0 else (m, hi)
    return 0.5 * (lo + hi)


@dataclass(frozen=True)
class Tranche:
    name: str
    keys: tuple
    advance: float
    rate: float
    tenor: int
    grace: int = 1
    profile: str = "annuity"                 # annuity | equal | sculpt
    gearing_cap: float = 1.0
    upfront_fee: float = 0.01


@dataclass(frozen=True)
class Scheme:
    name: str
    tranches: tuple = ()
    pref_frac: float = 0.0
    grant: float = 0.0
    esco: bool = False


@dataclass(frozen=True)
class Stress:
    yield_mult: float = 1.0
    capex_mult: float = 1.0
    power_mult: float = 1.0
    co2_gbp_kg: float = CO2_BASE
    labour_mult: float = 1.0


ECA = Tranche("glasshouse supplier credit (ECA)", STRUCT_KEYS, 0.85, CIRR_GBP_8Y, 15, profile="equal", upfront_fee=0.02)
PLANT_AF = Tranche("plant asset finance", PLANT_KEYS, 0.90, BANK_RATE + 0.0325, 10)
BANK = Tranche("bank term debt, sculpted", (), 1.0, BANK_RATE + 0.030, 15, profile="sculpt", gearing_cap=0.65)
SCHEMES = (
    Scheme("all equity (benchmark)"),
    Scheme("supplier credit + plant asset finance, 1-yr holiday", (ECA, PLANT_AF)),
    Scheme("supplier credit + plant asset finance, no holiday", (replace(ECA, grace=0), replace(PLANT_AF, grace=0))),
    Scheme("bank debt sculpted to DSCR 1.25", (BANK,)),
    Scheme("vendor finance + preference shares 12 %", (ECA, PLANT_AF), pref_frac=0.5),
    Scheme("vendor finance + FDPSS grant GBP 0.4 M", (ECA, PLANT_AF), grant=400e3),
    Scheme("vendor finance + heat-plant ESCo (buyout yr 10)", (ECA, replace(PLANT_AF, keys=("led_lighting", "battery"))),
           esco=True),
)
CENTRAL = SCHEMES[1].name


class Project:
    """Real, pre-tax annual layer rebuilt from one lit_open price entry."""

    def __init__(self, entry, parity):
        self.parity, self.price0 = parity, entry["price"]
        self.capex0, self.costs = dict(entry["capex"]), dict(entry["costs"])
        self.kg, self.ramp = entry["kg_yr"], entry["ramp"]
        self.comm_frac = self.costs.get("sales_commission", 0.0) / entry["revenue"]
        self.per_kg = sum(self.costs[k] for k in PER_KG_KEYS) / self.kg
        cf = np.asarray(entry["cashflow"], float)
        ebitda0 = self.real(Stress(), self.price0, rep=False)["ebitda"]
        self.rep = np.clip(ebitda0 - cf, 0.0, None)
        self.rep[0] = self.rep[YEARS] = 0.0
        self.resid = cf[YEARS] - ebitda0[YEARS]

    @classmethod
    def from_lit_open(cls, design=2, undercut="undercut 3%"):
        c = json.loads((OUT / "lit_open.json").read_text())[design]
        return cls(c["prices"][undercut], c["parity_gbp_kg"]), c

    def capex(self, s):
        return {k: v * s.capex_mult for k, v in self.capex0.items()}

    def real(self, s, price, rep=True):
        t = np.arange(YEARS + 1)
        f = np.where(t == 1, self.ramp, 1.0) * (t > 0)
        kg = self.kg * s.yield_mult * f
        rev = price * kg
        c = self.costs
        fixed = sum(v for k, v in c.items() if k not in ELEC_KEYS + PER_KG_KEYS + ("labour", "co2_purchased", "sales_commission"))
        labour = c["labour"] * s.labour_mult * ((1 - LABOUR_KG_SHARE) + LABOUR_KG_SHARE * s.yield_mult)
        opex = (fixed + labour + sum(c[k] for k in ELEC_KEYS) * s.power_mult + c["co2_purchased"] * s.co2_gbp_kg / CO2_BASE
                + self.per_kg * kg + self.comm_frac * rev) * (t > 0)
        out = dict(kg=kg, revenue=rev, opex=opex, ebitda=rev - opex)
        if rep:
            out["rep"], out["resid"] = self.rep * s.capex_mult, self.resid * s.capex_mult
        return out


class Debt:
    """Schedule of one tranche: interest-only grace, then annuity, equal principal or sculpted service."""

    def __init__(self, tr, amount, cfads=None):
        self.tr, n = tr, YEARS + 1
        self.interest, self.principal = np.zeros(n), np.zeros(n)
        g, r, m = tr.grace, tr.rate, tr.tenor - tr.grace
        if tr.profile == "sculpt":
            d = np.array([(1 + r) ** -(k - g) for k in range(g + 1, tr.tenor + 1)])
            target = np.clip(cfads[g + 1:tr.tenor + 1], 0.0, None) / DSCR_MIN
            amount = min(float(target @ d), amount)
            service = target * amount / max(float(target @ d), 1e-9)
        self.amount = amount
        bal = amount
        for t in range(1, tr.tenor + 1):
            self.interest[t] = bal * r
            if t <= g:
                continue
            if tr.profile == "annuity":
                p = amount * cashflow.annuity_at(r, m) - self.interest[t]
            elif tr.profile == "equal":
                p = amount / m
            else:
                p = service[t - g - 1] - self.interest[t]
            p = min(max(p, 0.0), bal)
            self.principal[t], bal = p, bal - p

    @property
    def service(self):
        return self.interest + self.principal


class Finance:
    RESERVE_RATE, WC_MONTHS, DSRA_MONTHS = 0.06, 2, 6
    ESCO_RATE, ESCO_TERM, ESCO_BUYOUT = 0.09, 15, 10
    PREF_RATE, PREF_SWEEP = 0.12, 0.5
    SPECIAL_FYA, SPECIAL_WDA, USED_WDA = 0.5, 0.06, 0.18

    def __init__(self, project, scheme, stress=Stress(), cpi=CPI):
        self.p, self.sc, self.s, self.cpi = project, scheme, stress, cpi
        self.t = np.arange(YEARS + 1)
        self.idx = (1 + cpi) ** self.t

    def reserve(self, rep):
        pv = sum(c / (1 + self.RESERVE_RATE) ** t for t, c in enumerate(rep) if t)
        return np.where(self.t > 0, pv * cashflow.annuity_at(self.RESERVE_RATE, YEARS), 0.0) * self.idx

    def esco(self, capex):
        amount = sum(capex.get(k, 0.0) for k in ESCO_KEYS) if self.sc.esco else 0.0
        fee, buyout = np.zeros(YEARS + 1), np.zeros(YEARS + 1)
        if amount:
            pay = amount * cashflow.annuity_at(self.ESCO_RATE, self.ESCO_TERM)
            bal = amount
            for t in range(1, self.ESCO_BUYOUT + 1):
                fee[t] = pay
                bal = bal * (1 + self.ESCO_RATE) - pay
            buyout[self.ESCO_BUYOUT] = bal
        return amount, fee, buyout

    def allowances(self, capex, esco_amount, rep, resid, buyout):
        """Capital allowances by year (CAA 2001): main pool 100 %, special rate 50 % + 6 % WDA, used plant 18 % WDA."""
        grant_share = self.sc.grant / max(sum(v for k, v in capex.items() if k not in NO_ALLOWANCE_KEYS), 1.0)
        q = {k: v * (1 - grant_share) for k, v in capex.items() if k not in NO_ALLOWANCE_KEYS}
        if self.sc.esco:
            q = {k: v for k, v in q.items() if k not in ESCO_KEYS}
        lump = capex["contingency"] * (1 - grant_share)
        base = sum(v for k, v in q.items() if k != "contingency")
        special_in = np.zeros(YEARS + 1)
        special_in[0] = sum(q.get(k, 0.0) for k in SPECIAL_KEYS) * (1 + lump / max(base, 1.0))
        special_in += rep
        main0 = sum(q.values()) - special_in[0]
        ca, sp, used = np.zeros(YEARS + 1), 0.0, 0.0
        for t in range(YEARS + 1):
            fya = self.SPECIAL_FYA * special_in[t]
            sp += special_in[t] - fya
            wda = self.SPECIAL_WDA * sp
            sp -= wda
            used += buyout[t]
            uw = self.USED_WDA * used
            used -= uw
            ca[t] = fya + wda + uw + (main0 if t == 0 else 0.0)
        ca[YEARS] += sp + used - resid
        return ca

    def tax(self, ebitda, interest, ca):
        tax, loss = np.zeros(YEARS + 1), 0.0
        for t in range(YEARS + 1):
            profit = ebitda[t] - interest[t] - ca[t]
            if profit < 0:
                loss -= profit
                continue
            used = min(loss, profit)
            loss -= used
            tax[t] = CT * (profit - used)
        return tax

    def pref(self, dist, amount):
        out, bal, arrears = np.zeros(YEARS + 1), amount, 0.0
        out[0] = -amount
        for t in range(1, YEARS + 1):
            arrears += bal * self.PREF_RATE
            pay = min(max(dist[t], 0.0), arrears)
            arrears -= pay
            red = min(max(dist[t] - pay, 0.0) * self.PREF_SWEEP, bal)
            if t == YEARS:
                red, pay = bal, pay + arrears
            bal -= red
            out[t] = pay + red
        return out

    def run(self, price):
        s, sc, idx = self.s, self.sc, self.idx
        real = self.p.real(s, price)
        capex = self.p.capex(s)
        esco_amount, fee, buyout = self.esco(capex)
        ebitda = real["ebitda"] * idx - fee
        opex = real["opex"] * idx + fee
        rep, resid = real["rep"] * idx, real["resid"] * idx[YEARS]
        reserve = self.reserve(real["rep"])
        wc = np.where(self.t < YEARS, self.WC_MONTHS / 12 * np.append(opex[1:], opex[-1]), 0.0)
        dwc = np.diff(np.concatenate([[0.0], wc]))
        ca = self.allowances(capex, esco_amount, rep, resid, buyout)
        project_capex = sum(capex.values()) - esco_amount
        tax = self.tax(ebitda, np.zeros(YEARS + 1), ca)
        for _ in range(6):
            cfads = ebitda - tax - reserve - np.where(self.t > 0, dwc, 0.0)
            debts = [Debt(tr, (sum(capex.get(k, 0.0) for k in tr.keys) * tr.advance if tr.keys else
                               tr.gearing_cap * project_capex), cfads) for tr in sc.tranches]
            interest = sum((d.interest for d in debts), np.zeros(YEARS + 1))
            tax = self.tax(ebitda, interest, ca)
        service = sum((d.service for d in debts), np.zeros(YEARS + 1))
        debt = sum(d.amount for d in debts)
        dsra = np.append(self.DSRA_MONTHS / 12 * service[1:], 0.0)
        dsra[0] = max(dsra[0], dsra[1])
        ddsra = np.diff(np.concatenate([[0.0], dsra]))
        eq = ebitda - rep - tax - service - dwc - ddsra - buyout
        eq[YEARS] += resid
        fees = sum(d.amount * d.tr.upfront_fee for d in debts)
        eq[0] = -(project_capex - debt - sc.grant) - dwc[0] - ddsra[0] - fees
        pref = self.pref(eq, -eq[0] * sc.pref_frac) if sc.pref_frac else np.zeros(YEARS + 1)
        ordinary = eq - pref
        mask = service > 0
        dscr = cfads[mask] / service[mask] if mask.any() else np.array([np.inf])
        eq_irr = irr(ordinary)
        unlev = real["ebitda"] - real["rep"]
        unlev[0], unlev[YEARS] = -sum(capex.values()), unlev[YEARS] + real["resid"]
        return dict(price=price, debt=debt, gearing=debt / sum(capex.values()), equity=-ordinary[0], pref=-pref[0],
                    esco_capex=esco_amount, grant=sc.grant, dsra0=dsra[0], wc0=wc[0], fees0=fees,
                    tranches=[dict(name=d.tr.name, amount=d.amount, rate=d.tr.rate, tenor=d.tr.tenor, grace=d.tr.grace,
                                   profile=d.tr.profile) for d in debts],
                    service_yr1=float(service[1]), service_yr2=float(service[2]),
                    dscr_yr1=float(cfads[1] / service[1]) if service[1] else None,
                    min_dscr=float(dscr.min()), min_dscr_yr2on=float((cfads[2:][mask[2:]] / service[2:][mask[2:]]).min())
                    if mask[2:].any() else None,
                    equity_irr=eq_irr, equity_irr_real=eq_irr and (1 + eq_irr) / (1 + self.cpi) - 1,
                    project_irr_real_pretax=irr(unlev), project_payback_real=cashflow.payback(unlev),
                    equity_npv_hurdle=cashflow.npv(ordinary, EQUITY_HURDLE), equity_payback=cashflow.payback(ordinary),
                    pref_irr=irr(pref) if sc.pref_frac else None,
                    tax_total=float(tax.sum()), first_tax_year=int(np.argmax(tax > 0)) if (tax > 0).any() else None,
                    negative_equity_years=[int(t) for t in self.t[1:] if ordinary[t] < 0],
                    equity_cf=ordinary.tolist(), cfads=cfads.tolist(), service=service.tolist(), tax=tax.tolist())

    def ok(self, r, lender_only=False):
        dscr_ok = not self.sc.tranches or r["min_dscr"] >= DSCR_MIN - 1e-9
        if lender_only:
            return dscr_ok
        hurdle = EQUITY_HURDLE if self.sc.tranches else ALL_EQUITY_HURDLE
        return dscr_ok and (r["equity_irr"] or -1) >= hurdle

    def min_price(self, lender_only=False):
        lo, hi = 0.3, 4.0
        if not self.ok(self.run(hi), lender_only):
            return None
        for _ in range(36):
            mid = 0.5 * (lo + hi)
            lo, hi = (lo, mid) if self.ok(self.run(mid), lender_only) else (mid, hi)
        return hi


class Study:
    LENDER_PRICES = (1.01, 1.10, 1.20)
    SPONSOR_UNDERCUTS = (0.05, 0.10)
    STRESSES = {"yield -15 %": Stress(yield_mult=0.85), "capex +20 %": Stress(capex_mult=1.2),
                "power +30 %": Stress(power_mult=1.3), "labour +20 %": Stress(labour_mult=1.2),
                "CO2 GBP 0.10/kg": Stress(co2_gbp_kg=0.10),
                "yield -15 % + capex +20 %": Stress(yield_mult=0.85, capex_mult=1.2)}

    def __init__(self, design=2):
        self.project, self.case = Project.from_lit_open(design)
        self.prices = {f"lender GBP {p:.2f}": p for p in self.LENDER_PRICES} | {
            f"sponsor parity -{u:.0%}": self.project.parity * (1 - u) for u in self.SPONSOR_UNDERCUTS}

    @staticmethod
    def brief(r):
        return {k: v for k, v in r.items() if k not in ("equity_cf", "cfads", "service", "tax")}

    def run(self):
        out = dict(design=self.case["design"], Y=self.case["Y"], carbon=self.case["carbon"],
                   carbon_dose_counted=self.case["carbon_dose_counted"], parity=self.project.parity,
                   capex=sum(self.project.capex0.values()), schemes={}, stresses={})
        for sc in SCHEMES:
            f = Finance(self.project, sc)
            out["schemes"][sc.name] = dict(prices={k: self.brief(f.run(p)) for k, p in self.prices.items()},
                                           min_price=f.min_price(), min_price_lender=f.min_price(lender_only=True))
        central = next(sc for sc in SCHEMES if sc.name == CENTRAL)
        sponsor = self.prices["sponsor parity -10%"]
        for k, s in {"none": Stress(), **self.STRESSES}.items():
            f = Finance(self.project, central, s)
            out["stresses"][k] = dict(at_sponsor_10=self.brief(f.run(sponsor)), min_price=f.min_price(),
                                      min_price_lender=f.min_price(lender_only=True))
        out["central_cashflow"] = {k: v for k, v in Finance(self.project, central).run(sponsor).items()
                                   if k in ("equity_cf", "cfads", "service", "tax")}
        return out


class Report:
    @staticmethod
    def pct(x):
        return "n/a" if x is None else f"{x * 100:.1f} %"

    @classmethod
    def markdown(cls, res):
        d = res["design"]
        L = [f"# Financing model (BP33/BP37e), lit lead {d['ha']} ha, {d['ppfd']:.0f} umol, {d['turbines']} PPA turbines",
             "", f"Capex GBP {res['capex'] / 1e6:.2f} M, yield {res['Y']:.1f} kg/m2, carbon {res['carbon']:.2f} kg CO2e/kg "
             f"({res['carbon_dose_counted']:.2f} with the CO2 dose counted), import parity GBP {res['parity']:.3f}/kg. "
             "Nominal (CPI 2 %), post-tax (CT 25 %, full expensing). Prices are real (year-0 money), CPI-indexed. "
             "Inputs and tiers in the finance.py docstring.", "",
             "## Minimum real price (GBP/kg)", "",
             "| Scheme | Lender (DSCR >= 1.25) | Lender + equity 12 % nominal |", "|---|---:|---:|"]
        for n, s in res["schemes"].items():
            ml = "-" if s["min_price_lender"] is None or n.startswith("all equity") else f"{s['min_price_lender']:.3f}"
            L.append(f"| {n} | {ml} | {s['min_price'] and round(s['min_price'], 3)} |")
        L += ["", "All-equity row: equity hurdle 10.2 % nominal post-tax (8 % real).", ""]
        for pk in next(iter(res["schemes"].values()))["prices"]:
            L += [f"## Price: {pk}", "", "| Scheme | Debt GBP M | Equity GBP M | DSCR yr 1 | min DSCR | min DSCR yr 2+ | "
                  "Equity IRR nom. | real | Payback yr | Negative equity years |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
            for n, s in res["schemes"].items():
                r = s["prices"][pk]
                L.append(f"| {n} | {r['debt'] / 1e6:.2f} | {r['equity'] / 1e6:.2f} | "
                         f"{'-' if r['dscr_yr1'] is None else round(r['dscr_yr1'], 2)} | "
                         f"{'-' if not r['debt'] else round(r['min_dscr'], 2)} | "
                         f"{'-' if r['min_dscr_yr2on'] is None else round(r['min_dscr_yr2on'], 2)} | "
                         f"{cls.pct(r['equity_irr'])} | {cls.pct(r['equity_irr_real'])} | "
                         f"{r['equity_payback'] and round(r['equity_payback'], 1)} | "
                         f"{','.join(map(str, r['negative_equity_years'])) or '-'} |")
            L.append("")
        L += [f"## Stresses on the central scheme ({CENTRAL}) at parity -10 %", "",
              "| Stress | Project IRR real pre-tax | Project payback yr | DSCR yr 1 | min DSCR | Equity IRR nom. | "
              "Equity payback yr | Min price lender | Min price lender + equity |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for k, s in res["stresses"].items():
            r = s["at_sponsor_10"]
            L.append(f"| {k} | {cls.pct(r['project_irr_real_pretax'])} | {r['project_payback_real']:.1f} | {r['dscr_yr1']:.2f} | {r['min_dscr']:.2f} | {cls.pct(r['equity_irr'])} | "
                     f"{r['equity_payback'] and round(r['equity_payback'], 1)} | {s['min_price_lender']:.3f} | "
                     f"{s['min_price'] and round(s['min_price'], 3)} |")
        return "\n".join(L) + "\n"


if __name__ == "__main__":
    res = Study().run()
    (OUT / "finance.json").write_text(json.dumps(res, indent=1, default=float))
    md = Report.markdown(res)
    (OUT / "FINANCE.md").write_text(md)
    print(md)
