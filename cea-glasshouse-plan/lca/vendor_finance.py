"""BP37 (user, 2026-10-07): supplier / asset finance instead of an 8 % all-investor discount rate.

The glasshouse builder and the heat-pump maker are paid over time: the glasshouse on export-credit-backed supplier credit
(a Dutch builder + Atradius Dutch State Business cover, OECD Arrangement terms), the heat pump, store and LEDs on asset
finance (hire purchase / lease), and equity pays the rest (down payments, development, contingency, connection).
Pre-tax, real terms, level annuities from year 1 (no construction grace): conservative on the first-year DSCR.

Inputs, tier and source:
  * Bank of England Bank Rate 3.75 % (sourced: held at 3.75 % through 2026, moneytothemasses.com / finder.com rate
    surveys, Oct 2026). Used only to anchor the asset-finance placeholder.
  * Supplier credit: OECD Arrangement (modernised 5 Jul 2023, Mayer Brown 8 Aug 2023): max repayment term up to 15 yr for
    all countries; 15 % minimum down payment, so at most 85 % of the export contract is financed (standard Arrangement
    rule). Rate 6.0 % = CIRR-style fixed rate, GBP gilt + ~1 % margin: PLACEHOLDER until the OECD monthly CIRR table for
    GBP is read (range 5.0-7.0 %). Tenor 10 yr central (PLACEHOLDER inside the 15 yr limit).
  * Asset finance on plant: Bank Rate + 3.0 % = 6.75 % fixed, 90 % advance, 7 yr (PLACEHOLDER; UK asset finance from ~4-5 %
    APR for strong credits, businessexpert.co.uk / expertsure.com 2026; plant margin 2-4 % to be quoted).
  * Equity hurdle 12 % (BP33 preference-share hurdle, PLACEHOLDER).
  * Lender test: minimum DSCR 1.25 (common UK project-finance covenant, PLACEHOLDER 1.20-1.35) on CFADS = EBITDA less a
    level major-maintenance reserve (the PV of all replacement capex at the supplier-credit rate, spread evenly over the
    life), the usual lender treatment of lumpy replacements (LEDs year 15, climate computer year 10, ...). Equity returns
    use the actual, lumpy cash flow.
"""
import numpy as np

import cashflow

BANK_RATE = 0.0375
STRUCT_KEYS = ("steel", "aluminium", "glass_single_m2", "glass_double_m2", "concrete", "pir_panel_m2", "heating_pipe_m",
               "energy_screen_m2", "residual (SAC-calibrated: install, climate computer, irrigation, vents ...)")
PLANT_KEYS = ("heat_pump", "hot_water_store", "led_lighting", "peak_boiler", "battery")

SCHEMES = {
    "all equity (8 % benchmark)": [],
    "supplier credit 10 yr + plant asset finance 7 yr": [
        dict(name="glasshouse supplier credit", keys=STRUCT_KEYS, advance=0.85, rate=0.060, tenor=10),
        dict(name="plant asset finance", keys=PLANT_KEYS, advance=0.90, rate=BANK_RATE + 0.030, tenor=7)],
    "supplier credit 15 yr + plant asset finance 10 yr": [
        dict(name="glasshouse supplier credit", keys=STRUCT_KEYS, advance=0.85, rate=0.060, tenor=15),
        dict(name="plant asset finance", keys=PLANT_KEYS, advance=0.90, rate=BANK_RATE + 0.030, tenor=10)],
    "supplier credit 15 yr @ 5 % + plant 10 yr @ 5.75 %": [
        dict(name="glasshouse supplier credit", keys=STRUCT_KEYS, advance=0.85, rate=0.050, tenor=15),
        dict(name="plant asset finance", keys=PLANT_KEYS, advance=0.90, rate=BANK_RATE + 0.020, tenor=10)],
}
EQUITY_HURDLE, DSCR_MIN = 0.12, 1.25


class VendorFinance:
    RESERVE_RATE = 0.06

    def __init__(self, cf, capex, kg_t, ebitda_t):
        """cf: unlevered project cash flow (year 0 = -capex); capex: cashflow.build capex dict; kg_t: kg sold per year;
        ebitda_t: revenue - opex per year (before replacements and residual value)."""
        self.cf, self.capex, self.kg_t = np.asarray(cf, float), capex, np.asarray(kg_t, float)
        self.ebitda = np.asarray(ebitda_t, float)
        n = len(self.cf) - 1
        rep = np.clip(self.ebitda[1:n] - self.cf[1:n], 0.0, None)          # final year carries the residual value
        pv = sum(c / (1 + self.RESERVE_RATE) ** t for t, c in enumerate(rep, start=1))
        self.reserve = pv * cashflow.annuity_at(self.RESERVE_RATE, n)

    def debt(self, tranches):
        n = len(self.cf)
        service, drawn, rows = np.zeros(n), 0.0, []
        for t in tranches:
            amt = sum(self.capex.get(k, 0.0) for k in t["keys"]) * t["advance"]
            pay = amt * cashflow.annuity_at(t["rate"], t["tenor"])
            service[1:t["tenor"] + 1] += pay
            drawn += amt
            rows.append(dict(name=t["name"], amount=amt, rate=t["rate"], tenor=t["tenor"], payment=pay))
        return drawn, service, rows

    def evaluate(self, tranches, dprice=0.0):
        cf = self.cf + dprice * self.kg_t
        drawn, service, rows = self.debt(tranches)
        eq = cf - service
        eq[0] = cf[0] + drawn                                   # equity pays what the loans do not
        cfads = self.ebitda[1:] + dprice * self.kg_t[1:] - self.reserve
        mask = service[1:] > 0
        dscr = cfads[mask] / service[1:][mask] if mask.any() else np.array([np.inf])
        return dict(reserve_yr=self.reserve, debt=drawn, equity=-eq[0], tranches=rows, debt_service_yr1=float(service[1]),
                    min_dscr=float(dscr.min()), equity_irr=cashflow.irr(eq.tolist()),
                    equity_npv_hurdle=cashflow.npv(eq, EQUITY_HURDLE), equity_payback=cashflow.payback(eq),
                    project_irr=cashflow.irr(cf.tolist()))

    def min_price_shift(self, tranches):
        """Smallest price change (GBP/kg) for equity IRR >= hurdle and min DSCR >= DSCR_MIN (for all-equity: NPV 8 % >= 0)."""
        def ok(dp):
            r = self.evaluate(tranches, dp)
            if not tranches:
                return cashflow.npv(self.cf + dp * self.kg_t, 0.08) >= 0
            return r["min_dscr"] >= DSCR_MIN and (r["equity_irr"] or -1) >= EQUITY_HURDLE
        lo, hi = -2.0, 3.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            lo, hi = (lo, mid) if ok(mid) else (mid, hi)
        return hi

    def run(self, price):
        out = {}
        for name, tr in SCHEMES.items():
            r = self.evaluate(tr)
            r["min_price"] = price + self.min_price_shift(tr)
            out[name] = r
        return out
