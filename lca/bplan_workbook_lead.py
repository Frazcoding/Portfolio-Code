"""BP26a: finance workbook on the lit lead (2.9 ha, 150 umol, 2 PPA turbines), live formulas.

The physics stays in Python: kg, capex lines, opex lines and the real replacement schedule are written as inputs from
results/bplan/lit_open.json (design 2). Everything after that is a formula a reader can flex: price, CPI, tax, stresses,
the ECA supplier credit and plant asset finance terms, holiday, DSRA, working capital. Central scheme of finance.py
(BP33); a Check sheet holds finance.py's own results for the default inputs.

    python bplan_workbook_lead.py   -> ../business_plan/Lead_Finance_Model.xlsx
"""
import json
import os
from pathlib import Path

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

import finance as F
from bplan_workbook import Style

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("CEA_XLSX_LEAD") or HERE.parent / "business_plan" / "Lead_Finance_Model.xlsx")
N = F.YEARS
C0 = 3                                                  # column of year 0 on the Cashflow sheet


class Names:
    def __init__(self):
        self.ref = {}

    def __getitem__(self, k):
        return self.ref[k]


class LeadWorkbook:
    TRANCHES = ("eca", "af")
    TITLE = "Lead finance model"
    NOTE = "Supplier credit (ECA) + plant asset finance, 1-yr holiday, DSRA (finance.py central scheme). Change blue cells on Inputs."
    OUT = OUT

    def __init__(self, undercut=0.10):
        self.p, self.case = F.Project.from_lit_open(2)
        self.price = self.p.parity * (1 - undercut)
        self.scheme = next(sc for sc in F.SCHEMES if sc.name == F.CENTRAL)
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.n = Names()

    # ---- Inputs ----------------------------------------------------------------------------------------------------
    def scalar(self, ws, r, name, label, value, fmt, note=""):
        ws.cell(r, 1, label).font = Style.CALC
        c = ws.cell(r, 3, value)
        c.font, c.number_format = Style.INPUT, fmt
        ws.cell(r, 4, note).font = Style.NOTE
        self.n.ref[name] = f"Inputs!$C${r}"

    def debt_inputs(self):
        tr_eca, tr_af = F.ECA, F.PLANT_AF
        return [
            ("eca_adv", "ECA supplier credit: advance on structure", tr_eca.advance, Style.PCT, "OECD Arrangement max 85 %"),
            ("eca_rate", "ECA supplier credit: fixed rate", tr_eca.rate, Style.PCT, "OECD GBP CIRR, 8-yr bucket, 15 Sep-14 Oct 2026"),
            ("eca_ten", "ECA supplier credit: tenor (yr)", tr_eca.tenor, Style.NUM, "max 15"),
            ("eca_gr", "ECA supplier credit: interest-only years", tr_eca.grace, Style.NUM, "needs the ECA's agreement"),
            ("eca_fee", "ECA premium, up front", tr_eca.upfront_fee, Style.PCT, "PLACEHOLDER"),
            ("af_adv", "Plant asset finance: advance", tr_af.advance, Style.PCT, "PLACEHOLDER"),
            ("af_rate", "Plant asset finance: rate", tr_af.rate, Style.PCT, "Bank Rate 3.75 % + 3.25 %, PLACEHOLDER"),
            ("af_ten", "Plant asset finance: tenor (yr)", tr_af.tenor, Style.NUM, ""),
            ("af_gr", "Plant asset finance: interest-only years", tr_af.grace, Style.NUM, ""),
            ("af_fee", "Plant asset finance: arrangement fee", tr_af.upfront_fee, Style.PCT, "PLACEHOLDER"),
        ]

    def inputs(self):
        ws = self.wb.create_sheet("Inputs")
        for col, w in zip("ABCD", (44, 4, 16, 110)):
            ws.column_dimensions[col].width = w
        ws.cell(1, 1, "Lead finance model: inputs (blue = input)").font = Style.TITLE
        d = self.case["design"]
        ws.cell(2, 1, f"Lit lead {d['ha']} ha, {d['ppfd']:.0f} umol, {d['turbines']} PPA turbines, Stranraer; physics from "
                      "lit_open.json; terms and tiers in finance.py").font = Style.NOTE
        rows = [
            ("price", "Contract price, real (year-0 GBP/kg)", self.price, Style.GBP3, f"default = import parity {self.p.parity:.3f} x 0.90; CPI-indexed"),
            ("parity", "Import parity (GBP/kg)", self.p.parity, Style.GBP3, "monthly CIF + GBP 0.162 haul, weighted by own harvest"),
            ("cpi", "CPI", F.CPI, Style.PCT, "Bank of England target"),
            ("ct", "Corporation tax", F.CT, Style.PCT, "main rate"),
            ("kg", "Output at full yield (kg/yr)", self.p.kg, Style.NUM, "model, before stresses"),
            ("ramp", "Year-1 output share", self.p.ramp, Style.PCT, "first-crop establishment"),
            ("ym", "Stress: yield x", 1.0, Style.NUM2, ""),
            ("cm", "Stress: capex x (incl. replacements)", 1.0, Style.NUM2, ""),
            ("pm", "Stress: power cost x", 1.0, Style.NUM2, ""),
            ("co2", "CO2 price (GBP/kg)", F.CO2_BASE, Style.GBP3, "by-product CO2 (PLACEHOLDER); model base 0.06"),
            ("lm", "Stress: labour x", 1.0, Style.NUM2, ""),
            ("lks", "Share of labour that scales with kg", F.LABOUR_KG_SHARE, Style.PCT, "PLACEHOLDER"),
            *self.debt_inputs(),
            ("grant", "Capital grant (GBP)", 0.0, Style.GBP, "FDPSS up to GBP 0.4 M, packhouse only (GRANTS.md)"),
            ("dscr", "Lender minimum DSCR", F.DSCR_MIN, Style.NUM2, "PLACEHOLDER 1.20-1.35"),
            ("hurdle", "Equity hurdle, nominal post-tax", F.EQUITY_HURDLE, Style.PCT, "PLACEHOLDER"),
            ("wc_m", "Working capital (months of opex)", F.Finance.WC_MONTHS, Style.NUM, ""),
            ("dsra_m", "DSRA (months of next year's debt service)", F.Finance.DSRA_MONTHS, Style.NUM, ""),
            ("res_r", "Maintenance-reserve rate (real)", F.Finance.RESERVE_RATE, Style.PCT, "levels the lumpy replacements for CFADS"),
            ("fya", "Special-rate first-year allowance", F.Finance.SPECIAL_FYA, Style.PCT, "CAA 2001 s.45S"),
            ("wda", "Special-rate writing-down allowance", F.Finance.SPECIAL_WDA, Style.PCT, ""),
        ]
        r = 4
        for name, label, val, fmt, note in rows:
            self.scalar(ws, r, name, label, val, fmt, note)
            r += 1
        r += 1
        ws.cell(r, 1, "Capex lines (GBP, year 0)").font = Style.BOLD
        ws.cell(r, 3, "GBP").font = Style.BOLD
        ws.cell(r, 4, "Finance / allowance class").font = Style.BOLD
        r += 1
        first = r
        for k, v in self.p.capex0.items():
            ws.cell(r, 1, k)
            c = ws.cell(r, 3, v)
            c.font, c.number_format = Style.INPUT, Style.GBP
            fin = "ECA" if k in F.STRUCT_KEYS else "AF" if k in F.PLANT_KEYS else "-"
            allow = "none" if k in F.NO_ALLOWANCE_KEYS else "special" if k in F.SPECIAL_KEYS else "contingency" if k == "contingency" else "main"
            ws.cell(r, 2, fin)
            ws.cell(r, 4, allow)
            r += 1
        self.n.ref.update(capex=f"Inputs!$C${first}:$C${r - 1}", capex_fin=f"Inputs!$B${first}:$B${r - 1}",
                          capex_cls=f"Inputs!$D${first}:$D${r - 1}")
        r += 1
        ws.cell(r, 1, "Opex lines at full yield (real GBP/yr)").font = Style.BOLD
        r += 1
        first = r
        for k, v in self.p.costs.items():
            cls = "elec" if k in F.ELEC_KEYS else "per_kg" if k in F.PER_KG_KEYS else k if k in ("labour", "co2_purchased", "sales_commission") else "fixed"
            ws.cell(r, 1, k)
            c = ws.cell(r, 3, v)
            c.font, c.number_format = Style.INPUT, Style.GBP
            ws.cell(r, 4, cls)
            r += 1
        self.n.ref.update(opex=f"Inputs!$C${first}:$C${r - 1}", opex_cls=f"Inputs!$D${first}:$D${r - 1}")
        r += 1
        self.scalar(ws, r, "resid", "Residual value at year 30 (real GBP)", self.p.resid, Style.GBP, "replaced items, straight line")
        self.scalar(ws, r + 1, "rev0", "Revenue the commission line was set on (GBP/yr)", self.p.price0 * self.p.kg, Style.GBP, "")
        r += 3
        ws.cell(r, 1, "Replacement capex (real GBP) by year").font = Style.BOLD
        ws.cell(r + 1, 1, "year")
        ws.cell(r + 2, 1, "GBP")
        for t in range(N + 1):
            ws.cell(r + 1, 5 + t, t)
            c = ws.cell(r + 2, 5 + t, float(self.p.rep[t]))
            c.font, c.number_format = Style.INPUT, Style.NUM
        self.rep_row = r + 2

    # ---- Cashflow ----------------------------------------------------------------------------------------------------
    def debt_spec(self, rows, n, col, cap_fin):
        return [
            ("eca_bal", "ECA supplier credit, closing balance", lambda t: (f"={cap_fin('ECA')}*{n['eca_adv']}" if t == 0 else
             f"={col(t - 1)}{rows['eca_bal']}-{col(t)}{rows['eca_p']}")),
            ("eca_i", "ECA interest", lambda t: 0 if t == 0 else f"=IF({t}<={n['eca_ten']},{col(t - 1)}{rows['eca_bal']}*{n['eca_rate']},0)"),
            ("eca_p", "ECA principal (equal instalments)", lambda t: 0 if t == 0 else
             f"=IF(AND({t}>{n['eca_gr']},{t}<={n['eca_ten']}),MIN($B{rows['eca_bal']}/({n['eca_ten']}-{n['eca_gr']}),{col(t - 1)}{rows['eca_bal']}),0)"),
            ("af_bal", "Plant asset finance, closing balance", lambda t: (f"={cap_fin('AF')}*{n['af_adv']}" if t == 0 else
             f"={col(t - 1)}{rows['af_bal']}-{col(t)}{rows['af_p']}")),
            ("af_i", "Asset finance interest", lambda t: 0 if t == 0 else f"=IF({t}<={n['af_ten']},{col(t - 1)}{rows['af_bal']}*{n['af_rate']},0)"),
            ("af_p", "Asset finance principal (annuity)", lambda t: 0 if t == 0 else
             f"=IF(AND({t}>{n['af_gr']},{t}<={n['af_ten']}),MIN($B{rows['af_bal']}*{n['af_rate']}/(1-(1+{n['af_rate']})^-({n['af_ten']}-{n['af_gr']}))"
             f"-{col(t)}{rows['af_i']},{col(t - 1)}{rows['af_bal']}),0)"),
        ]

    def cashflow(self):
        ws = self.wb.create_sheet("Cashflow")
        ws.column_dimensions["A"].width = 46
        ws.column_dimensions["B"].width = 14
        n = self.n
        col = lambda t: get_column_letter(C0 + t)  # noqa: E731
        rows = {}

        def cap_fin(tag):
            return f'SUMIF({n["capex_fin"]},"{tag}",{n["capex"]})*{n["cm"]}'

        cap = lambda cls: f'SUMIF({n["capex_cls"]},"{cls}",{n["capex"]})*{n["cm"]}'  # noqa: E731
        opx = lambda cls: f'SUMIF({n["opex_cls"]},"{cls}",{n["opex"]})'  # noqa: E731
        q_sum = f'({cap("main")}+{cap("special")}+{cap("contingency")})'
        gshare = f'(1-{n["grant"]}/{q_sum})'
        special0 = f'{cap("special")}*(1+{cap("contingency")}/({cap("main")}+{cap("special")}))*{gshare}'
        spec = [
            ("year", "", lambda t: t),
            ("idx", "CPI index", lambda t: f"=(1+{n['cpi']})^{col(t)}{rows['year']}"),
            ("f", "Output share", lambda t: 0 if t == 0 else f"={n['ramp']}" if t == 1 else 1),
            ("kg", "kg sold", lambda t: f"={n['kg']}*{n['ym']}*{col(t)}{rows['f']}"),
            ("rev_r", "Revenue, real", lambda t: f"={n['price']}*{col(t)}{rows['kg']}"),
            ("opex_r", "Opex, real", lambda t: 0 if t == 0 else
             f"={opx('fixed')}+{opx('labour')}*{n['lm']}*((1-{n['lks']})+{n['lks']}*{n['ym']})+{opx('elec')}*{n['pm']}"
             f"+{opx('co2_purchased')}*{n['co2']}/{F.CO2_BASE}+{opx('per_kg')}/{n['kg']}*{col(t)}{rows['kg']}"
             f"+{opx('sales_commission')}/{n['rev0']}*{col(t)}{rows['rev_r']}"),
            ("rep_r", "Replacement capex, real", lambda t: f"=Inputs!{get_column_letter(5 + t)}{self.rep_row}*{n['cm']}"),
            ("unlev", "Unlevered cash flow, real pre-tax", lambda t: f"=-SUM({n['capex']})*{n['cm']}" if t == 0 else
             f"={col(t)}{rows['rev_r']}-{col(t)}{rows['opex_r']}-{col(t)}{rows['rep_r']}" + (f"+{n['resid']}*{n['cm']}" if t == N else "")),
            ("ebitda", "EBITDA, nominal", lambda t: f"=({col(t)}{rows['rev_r']}-{col(t)}{rows['opex_r']})*{col(t)}{rows['idx']}"),
            ("opex", "Opex, nominal", lambda t: f"={col(t)}{rows['opex_r']}*{col(t)}{rows['idx']}"),
            ("rep", "Replacements, nominal", lambda t: f"={col(t)}{rows['rep_r']}*{col(t)}{rows['idx']}"),
            ("resid", "Residual value, nominal", lambda t: f"={n['resid']}*{n['cm']}*{col(t)}{rows['idx']}" if t == N else 0),
            ("sp_add", "Special-rate pool additions", lambda t: f"={special0}" if t == 0 else f"={col(t)}{rows['rep']}"),
            ("fya", "First-year allowance (special)", lambda t: f"={n['fya']}*{col(t)}{rows['sp_add']}"),
            ("wda", "Writing-down allowance (special)", lambda t: f"={n['wda']}*({'0' if t == 0 else f'{col(t - 1)}{rows['sp_bal']}'}"
             f"+{col(t)}{rows['sp_add']}-{col(t)}{rows['fya']})"),
            ("sp_bal", "Special-rate pool, closing", lambda t: f"={'0' if t == 0 else f'{col(t - 1)}{rows['sp_bal']}'}+{col(t)}{rows['sp_add']}"
             f"-{col(t)}{rows['fya']}-{col(t)}{rows['wda']}"),
            ("ca", "Capital allowances", lambda t: (f"={q_sum}*{gshare}-{col(t)}{rows['sp_add']}+{col(t)}{rows['fya']}+{col(t)}{rows['wda']}"
                                                  if t == 0 else f"={col(t)}{rows['fya']}+{col(t)}{rows['wda']}"
                                                  + (f"+{col(t)}{rows['sp_bal']}-{col(t)}{rows['resid']}" if t == N else ""))),
            *self.debt_spec(rows, n, col, cap_fin),
            ("service", "Debt service", lambda t: "=" + "+".join(f"{col(t)}{rows[f'{q}_i']}+{col(t)}{rows[f'{q}_p']}" for q in self.TRANCHES)),
            ("profit", "Taxable profit before losses", lambda t: f"={col(t)}{rows['ebitda']}-{col(t)}{rows['ca']}"
             + "".join(f"-{col(t)}{rows[f'{q}_i']}" for q in self.TRANCHES)),
            ("loss_used", "Losses used", lambda t: 0 if t == 0 else f"=MIN({col(t - 1)}{rows['loss_cf']},MAX({col(t)}{rows['profit']},0))"),
            ("loss_cf", "Losses carried forward", lambda t: f"={'0' if t == 0 else f'{col(t - 1)}{rows['loss_cf']}'}-{col(t)}{rows['loss_used']}+MAX(-{col(t)}{rows['profit']},0)"),
            ("tax", "Corporation tax paid", lambda t: f"={n['ct']}*(MAX({col(t)}{rows['profit']},0)-{col(t)}{rows['loss_used']})"),
            ("wc", "Working capital balance", lambda t: 0 if t == N else f"={n['wc_m']}/12*{col(t + 1)}{rows['opex']}"),
            ("dwc", "Working-capital build", lambda t: f"={col(t)}{rows['wc']}-{'0' if t == 0 else f'{col(t - 1)}{rows['wc']}'}"),
            ("reserve", "Maintenance reserve", lambda t: 0 if t == 0 else
             f"=NPV({n['res_r']},${col(1)}${rows['rep_r']}:${col(N)}${rows['rep_r']})*{n['res_r']}/(1-(1+{n['res_r']})^-{N})*{col(t)}{rows['idx']}"),
            ("cfads", "CFADS", lambda t: 0 if t == 0 else f"={col(t)}{rows['ebitda']}-{col(t)}{rows['tax']}-{col(t)}{rows['reserve']}-{col(t)}{rows['dwc']}"),
            ("dscr", "DSCR", lambda t: "" if t == 0 else f'=IF({col(t)}{rows["service"]}>0,{col(t)}{rows["cfads"]}/{col(t)}{rows["service"]},"")'),
            ("dsra", "DSRA balance", lambda t: (f"={n['dsra_m']}/12*MAX({col(1)}{rows['service']},{col(2)}{rows['service']})" if t == 0 else
                                               0 if t == N else f"={n['dsra_m']}/12*{col(t + 1)}{rows['service']}")),
            ("ddsra", "DSRA build", lambda t: f"={col(t)}{rows['dsra']}-{'0' if t == 0 else f'{col(t - 1)}{rows['dsra']}'}"),
            ("equity", "Cash flow to equity", lambda t: (
                f"=-(SUM({n['capex']})*{n['cm']}" + "".join(f"-{col(0)}{rows[f'{q}_bal']}" for q in self.TRANCHES)
                + f"-{n['grant']})-{col(0)}{rows['dwc']}-{col(0)}{rows['ddsra']}"
                + "".join(f"-{col(0)}{rows[f'{q}_bal']}*{n[f'{q}_fee']}" for q in self.TRANCHES) if t == 0 else
                f"={col(t)}{rows['ebitda']}-{col(t)}{rows['rep']}-{col(t)}{rows['tax']}-{col(t)}{rows['service']}-{col(t)}{rows['dwc']}"
                f"-{col(t)}{rows['ddsra']}+{col(t)}{rows['resid']}")),
            ("cum", "Cumulative equity cash", lambda t: f"={'0' if t == 0 else f'{col(t - 1)}{rows['cum']}'}+{col(t)}{rows['equity']}"),
        ]

        for i, (key, _, _) in enumerate(spec):
            rows[key] = 3 + i
        ws.cell(1, 1, f"{self.TITLE}: annual cash flow (nominal GBP unless marked real)").font = Style.TITLE
        for key, label, fn in spec:
            r = rows[key]
            ws.cell(r, 1, label).font = Style.BOLD if key in ("equity", "cfads", "dscr", "ebitda") else Style.CALC
            for t in range(N + 1):
                c = ws.cell(r, C0 + t, fn(t))
                c.number_format = Style.NUM if key not in ("idx", "f", "dscr", "year") else Style.NUM2
                ws.column_dimensions[col(t)].width = 12
            if key in tuple(f"{q}_bal" for q in self.TRANCHES):
                ws.cell(r, 2, f"={col(0)}{r}").number_format = Style.NUM
        ws.freeze_panes = "C3"
        self.rows = rows

    # ---- Results ----------------------------------------------------------------------------------------------------
    def results(self):
        ws = self.wb.create_sheet("Results", 0)
        ws.column_dimensions["A"].width = 46
        ws.column_dimensions["B"].width = 16
        ws.column_dimensions["C"].width = 16
        ws.column_dimensions["D"].width = 60
        r, last = self.rows, get_column_letter(C0 + N)
        rng = lambda k, a=0: f"Cashflow!{get_column_letter(C0 + a)}{r[k]}:{last}{r[k]}"  # noqa: E731
        ws.cell(1, 1, f"{self.TITLE}: results").font = Style.TITLE
        ws.cell(2, 1, self.NOTE).font = Style.NOTE
        ref = F.Finance(self.p, self.scheme).run(self.price)
        ws.cell(4, 1, "Output").font = Style.BOLD
        ws.cell(4, 2, "Workbook").font = Style.BOLD
        ws.cell(4, 3, "finance.py (default inputs)").font = Style.BOLD
        out = [
            ("Capex (GBP)", f"=SUM({self.n['capex']})*{self.n['cm']}", sum(self.p.capex0.values()), Style.GBP),
            ("Debt drawn (GBP)", "=" + "+".join(f"Cashflow!{get_column_letter(C0)}{r[f'{q}_bal']}" for q in self.TRANCHES), ref["debt"], Style.GBP),
            ("Equity at close (GBP)", f"=-Cashflow!{get_column_letter(C0)}{r['equity']}", ref["equity"], Style.GBP),
            ("Project IRR, real pre-tax", f"=IRR({rng('unlev')})", ref["project_irr_real_pretax"], Style.PCT),
            ("Equity IRR, nominal post-tax", f"=IRR({rng('equity')})", ref["equity_irr"], Style.PCT),
            ("Equity IRR, real", f"=(1+B9)/(1+{self.n['cpi']})-1", ref["equity_irr_real"], Style.PCT),
            ("DSCR year 1", f"=Cashflow!{get_column_letter(C0 + 1)}{r['dscr']}", ref["dscr_yr1"], Style.NUM2),
            ("Minimum DSCR", f"=MIN({rng('dscr', 1)})", ref["min_dscr"], Style.NUM2),
            ("Tax paid over 30 yr (GBP)", f"=SUM({rng('tax')})", ref["tax_total"], Style.GBP),
            ("Equity NPV at the hurdle (GBP)", f"=NPV({self.n['hurdle']},{rng('equity', 1)})+Cashflow!{get_column_letter(C0)}{r['equity']}",
             ref["equity_npv_hurdle"], Style.GBP),
            ("Lender test met (min DSCR >= target)", f'=IF(B12>={self.n["dscr"]},"yes","NO")', "", Style.NUM),
        ]
        for i, (label, f, v, fmt) in enumerate(out):
            ws.cell(5 + i, 1, label)
            c = ws.cell(5 + i, 2, f)
            c.number_format, c.font = fmt, Style.BOLD
            c = ws.cell(5 + i, 3, v)
            c.number_format, c.font = fmt, Style.NOTE
        label, mp = self.min_price()
        ws.cell(17, 1, label).font = Style.NOTE
        ws.cell(18, 1, "Minimum price (GBP/kg)")
        ws.cell(18, 3, mp).number_format = Style.GBP3

    def min_price(self):
        return ("Minimum real price for DSCR 1.25 (finance.py solver): flex Inputs!price until 'Lender test met' turns yes.",
                F.Finance(self.p, self.scheme).min_price())

    def build(self):
        self.inputs()
        self.cashflow()
        self.results()
        self.OUT.parent.mkdir(parents=True, exist_ok=True)
        self.wb.save(self.OUT)
        return self.OUT


class PlanWorkbook(LeadWorkbook):
    """The viable plan design (results/bplan/plan.json pick, 8 ha): full staffing in opex, senior debt sized on the lender
    case (bplan_plan.LenderSizing). The debt service schedule is an input row from that sizing; interest, balance, tax,
    cover and equity follow by formula."""
    TRANCHES = ("sen",)
    TITLE = "Plan finance model (8 ha)"
    NOTE = ("Senior debt sized to DSCR 1.25 on the yield -15 % case (bplan_plan.LenderSizing), year-1 interest rolled up, "
            "full team in opex. Change blue cells on Inputs; the service schedule row is the sizing at the default inputs.")
    OUT = HERE.parent / "business_plan" / "Plan_8ha_Finance_Model.xlsx"

    def __init__(self):
        import bplan_plan as PL
        plan = json.loads((HERE / "results" / "bplan" / "plan.json").read_text())["pick"]
        rows = json.loads((HERE / "results" / "bplan" / "viable_lit.json").read_text())
        row = next(r for r in rows if r["crop"] == plan["crop"] and r["design"]["ha"] == plan["ha"]
                   and r["design"]["product"] == plan["product"])
        d = PL.Design(row)
        self.p, self.case, self.price = d.project, {"design": d.d}, d.price
        self.ls = PL.LenderSizing(self.p)
        self.scheme = self.ls.scheme(self.price)
        self.tr = self.scheme.tranches[0]
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.n = Names()

    def debt_inputs(self):
        tr = self.tr
        return [("sen_amt", "Senior debt drawn at close (GBP)", tr.fixed_amount, Style.GBP, "sized to DSCR 1.25 on the yield -15 % case"),
                ("sen_rate", "Senior debt rate", tr.rate, Style.PCT, "blend of GBP CIRR 5.81 % and bank 6.75 %, PLACEHOLDER"),
                ("sen_ten", "Senior debt tenor (yr)", tr.tenor, Style.NUM, "year-1 interest rolled into the loan"),
                ("sen_fee", "Lender fees, up front", tr.upfront_fee, Style.PCT, "PLACEHOLDER")]

    def inputs(self):
        super().inputs()
        ws = self.wb["Inputs"]
        r = self.rep_row + 2
        ws.cell(r, 1, "Senior debt service schedule (nominal GBP) by year, from the lender sizing").font = Style.BOLD
        svc = F.Finance(self.p, self.scheme).run(self.price)["service"]
        for t in range(N + 1):
            c = ws.cell(r + 1, 5 + t, float(svc[t]))
            c.font, c.number_format = Style.INPUT, Style.NUM
        self.sched_row = r + 1

    def debt_spec(self, rows, n, col, cap_fin):
        sched = lambda t: f"Inputs!{get_column_letter(5 + t)}{self.sched_row}"  # noqa: E731
        return [
            ("sen_bal", "Senior debt, closing balance", lambda t: f"={n['sen_amt']}" if t == 0 else
             f"={col(0)}{rows['sen_bal']}*(1+{n['sen_rate']})" if t == 1 else f"={col(t - 1)}{rows['sen_bal']}-{col(t)}{rows['sen_p']}"),
            ("sen_i", "Senior debt interest (year 1 rolled up)", lambda t: 0 if t <= 1 else
             f"=IF({t}<={n['sen_ten']},{col(t - 1)}{rows['sen_bal']}*{n['sen_rate']},0)"),
            ("sen_p", "Senior debt principal (service schedule less interest)", lambda t: 0 if t <= 1 else
             f"=MAX(MIN({sched(t)}-{col(t)}{rows['sen_i']},{col(t - 1)}{rows['sen_bal']}),0)"),
        ]

    def min_price(self):
        return ("Price for a 12 % nominal equity return with the debt re-sized at each price (bplan_plan.LenderSizing).",
                self.ls.min_price())


if __name__ == "__main__":
    print(LeadWorkbook().build())
    print(PlanWorkbook().build())
