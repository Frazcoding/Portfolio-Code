"""Business plan (2026-10-05): capex / opex workbook for exploring capital-cost reductions.

Builds ../business_plan/Glasshouse_Capex_Opex_Model.xlsx with live formulas: inputs and unit rates (sourced, tiered),
five design scenarios (physical quantities from the model), capital cost by item and by cost driver, annual running
costs, results at 8 % and 3.5 %, a size-scaling explorer, a capex-lever register, prices and sources.

Model outputs per scenario come from results/bplan/xlsx_inputs.json (site_opt.evaluate on the track-B lead design).

    python bplan_workbook.py
"""
import os
import json
import sys
from pathlib import Path

import numpy as np
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = Path(os.environ.get("CEA_XLSX_OUT") or HERE.parent / "business_plan" / "Glasshouse_Capex_Opex_Model.xlsx")
DEFRA_URL = "https://www.gov.uk/government/statistical-data-sets/wholesale-fruit-and-vegetable-prices-weekly-average"


class Style:
    FONT = "Arial"
    INPUT = Font(name=FONT, size=10, color="0000FF")
    CALC = Font(name=FONT, size=10, color="000000")
    LINK = Font(name=FONT, size=10, color="008000")
    BOLD = Font(name=FONT, size=10, bold=True)
    TITLE = Font(name=FONT, size=14, bold=True)
    H2 = Font(name=FONT, size=11, bold=True, color="FFFFFF")
    NOTE = Font(name=FONT, size=9, italic=True, color="555555")
    HEAD_FILL = PatternFill("solid", fgColor="1F4E78")
    SUB_FILL = PatternFill("solid", fgColor="DDEBF7")
    KEY_FILL = PatternFill("solid", fgColor="FFFF00")
    TOTAL_FILL = PatternFill("solid", fgColor="F2F2F2")
    THIN = Side(style="thin", color="BFBFBF")
    BOX = Border(top=THIN, bottom=THIN)
    GBP = '£#,##0;(£#,##0);"-"'
    GBP2 = '£#,##0.00;(£#,##0.00);"-"'
    GBP3 = '£#,##0.000;(£#,##0.000);"-"'
    NUM = '#,##0;(#,##0);"-"'
    NUM1 = '#,##0.0;(#,##0.0);"-"'
    NUM2 = '#,##0.00;(#,##0.00);"-"'
    PCT = '0.0%;(0.0%);"-"'


class Sheet:
    """Row-by-row writer that remembers named cells so formulas can refer to them by name."""

    def __init__(self, wb, title, widths):
        self.ws = wb.create_sheet(title)
        self.wb = wb
        self.row = 1
        for i, w in enumerate(widths, start=1):
            self.ws.column_dimensions[get_column_letter(i)].width = w
        self.ws.sheet_view.showGridLines = False

    def ref(self, col, row=None, absolute=True, sheet=True):
        r = self.row if row is None else row
        c = get_column_letter(col) if isinstance(col, int) else col
        a = f"${c}${r}" if absolute else f"{c}{r}"
        return f"'{self.ws.title}'!{a}" if sheet else a

    def name(self, nm, col, row=None):
        self.wb.defined_names[nm] = DefinedName(nm, attr_text=self.ref(col, row))

    def title(self, text, sub=None):
        self.ws.cell(self.row, 1, text).font = Style.TITLE
        self.row += 1
        if sub:
            self.ws.cell(self.row, 1, sub).font = Style.NOTE
            self.row += 1
        self.row += 1

    def header(self, labels, fill=Style.HEAD_FILL, font=Style.H2):
        for i, t in enumerate(labels, start=1):
            c = self.ws.cell(self.row, i, t)
            c.fill, c.font = fill, font
            c.alignment = Alignment(wrap_text=True, vertical="center")
        self.ws.row_dimensions[self.row].height = 30
        self.row += 1

    def section(self, text, ncols):
        for i in range(1, ncols + 1):
            self.ws.cell(self.row, i).fill = Style.SUB_FILL
        self.ws.cell(self.row, 1, text).font = Style.BOLD
        self.row += 1

    def put(self, col, value, fmt=None, font=None, fill=None, comment=None, wrap=False):
        c = self.ws.cell(self.row, col, value)
        if font is None:
            font = Style.CALC if isinstance(value, str) and value.startswith("=") else (
                Style.INPUT if isinstance(value, (int, float)) else Style.CALC)
        c.font = font
        if fmt:
            c.number_format = fmt
        if fill:
            c.fill = fill
        if comment:
            c.comment = Comment(comment, "model")
        if wrap:
            c.alignment = Alignment(wrap_text=True, vertical="top")
        return c

    def next(self, n=1):
        self.row += n


SC_COLS = [3, 4, 5, 6, 7]          # scenario columns C..G on every scenario sheet
SC_L = [get_column_letter(c) for c in SC_COLS]


class Workbook_:
    def __init__(self, data):
        self.d = data
        self.S = data["scen"]
        self.wb = Workbook()
        self.wb.remove(self.wb.active)

    # ---- Read Me ---------------------------------------------------------------------------------------------------
    def readme(self):
        s = Sheet(self.wb, "Read Me", [3, 110])
        s.title("Glasshouse capex / opex model: track B lead design (1 ha cucumber, Scotland)",
                "Built 2026-10-05 by lca/bplan_workbook.py from the verified BEng-CEA-Heatpump/lca model. Edit blue cells.")
        lines = [
            ("What this is", None),
            ("", "Every capital and running cost of the lead glasshouse design, item by item, for five design scenarios side "
                 "by side, so you can see where the money goes and test ways to cut the initial spend."),
            ("", "Results are computed live: change a blue input or a unit rate and every total, £/kg and NPV updates."),
            ("How to use", None),
            ("", "1. 'Inputs': discount rates, prices, labour rate, commission and other global assumptions."),
            ("", "2. 'Rates': unit costs (£/t steel, £/m² glass, £/kW heat pump ...). Try supplier quotes here."),
            ("", "3. 'Scenarios': the physical design of each option (areas, quantities, kW, MWh, yield) from the simulation."),
            ("", "4. 'Capex': initial expenditure by item and by cost driver (per m², per kW, fixed). 'Opex': annual costs."),
            ("", "5. 'Results': initial spend, cost per kg, margin and NPV at 8 % (commercial) and 3.5 % (Green Book)."),
            ("", "6. 'Scale': how cost per m² changes with greenhouse size when fixed costs are separated from per-m² costs."),
            ("", "7. 'Capex Levers': every capex-reduction idea, its status, evidence and next step."),
            ("Colour code", None),
            ("", "Blue text = input you can change. Black = formula. Green = link to another sheet. Yellow fill = key "
                 "assumption. Grey fill = totals."),
            ("Scenarios", None),
        ]
        lines += [("", f"{sc['key']}: {sc['label']}") for sc in self.S]
        lines += [
            ("Boundaries and basis", None),
            ("", "Cost boundary: farm gate to the supermarket regional distribution centre (RDC): growing, packing and haulage "
                 "to the RDC are included; RDC-to-shelf is not (soil-to-shelf ledger is task BP15)."),
            ("", "Price: DEFRA UK wholesale (weekly averages, 2023-26) weighted by the harvest month, less 14 % market "
                 "commission (user decision 2026-10-05). Contract prices are not assumed to carry a premium."),
            ("", "Levelised costs use equivalent annual cost per item (capex x capital recovery factor at the item's life). "
                 "NPV = (revenue - running costs - equivalent annual capital costs) x 30-year annuity factor. This is a "
                 "steady-state shortcut: it omits the 80 % ramp-up year and the residual value that cashflow.py includes "
                 "(the 'Results' sheet shows the check against cashflow.py)."),
            ("", "The owned 2.5 MW turbine is a separate business: the greenhouse buys its power at the turbine's levelised "
                 "cost, computed here at each discount rate. Its capex is reported as 'energy route' initial spend, not in "
                 "the greenhouse cost per kg."),
            ("Status", None),
            ("", "Concept stage (Gate B). About 46 % of structure items are supplier placeholders (RFQ_SPEC.md). Yields are "
                 "model results (0.89-1.03 x the Dutch average) awaiting UK evidence. See the 'Sources' sheet."),
        ]
        for a, b in lines:
            if b is None:
                s.put(1, a, font=Style.BOLD)
            else:
                s.put(2, b, wrap=True)
                s.ws.row_dimensions[s.row].height = 15 * max(1, len(b) // 105 + 1)
            s.next()

    # ---- Inputs ----------------------------------------------------------------------------------------------------
    def inputs(self):
        C = self.d["cashflow_inputs"]
        s = Sheet(self.wb, "Inputs", [46, 14, 14, 18, 90])
        s.title("Global inputs", "Blue = editable. Tier: sourced / standard / model / estimate / placeholder.")
        s.header(["Input", "Value", "Unit", "Tier", "Source / note"])
        rows = [
            ("Finance", None),
            ("rate_commercial", "Discount rate, commercial (headline)", 0.08, "/yr real", "choice", "Investor/bank basis (user decision 2026-10-05)", Style.PCT),
            ("rate_public", "Discount rate, public (Green Book)", 0.035, "/yr real", "standard", "HM Treasury Green Book (2022) Annex 6: 3.5 % years 0-30", Style.PCT),
            ("years", "Study period", 30, "yr", "standard", "SCOPE §2; Green Book appraisal period", Style.NUM),
            ("eur_gbp", "EUR to GBP", 0.8567, "GBP/EUR", "sourced", "ECB reference rates via api.frankfurter.dev, 2025 mean", "0.0000"),
            ("Sales", None),
            ("price_cucumber", "Cucumber price, harvest-weighted (link to 'Prices')", "='Prices'!$D$17", "GBP/kg", "sourced",
             f"DEFRA wholesale fruit and vegetable prices, weekly average, 2023-26, months with < 3 UK observations use the UK "
             f"import CIF price (Comtrade 2023-25). {DEFRA_URL}", Style.GBP3),
            ("commission", "Market commission (wholesale route)", 0.14, "of revenue", "sourced (secondary)",
             "BritFarmers, T. Harfield, 'UK supermarket contracts vs wholesale pricing 2026' (trade guide, June 2026): 14 % "
             "commission plus transport. Was 5 % placeholder in cashflow.py", Style.PCT),
            ("import_parity", "Import parity price at the RDC (reference only)", 1.574, "GBP/kg", "sourced",
             "Comtrade CIF 2023-25 at the UK border + port-to-RDC haul (site_rank.py). Excludes port fees, border checks, "
             "importer margin (BP15)", Style.GBP3),
            ("Operations", None),
            ("labour_rate", "Labour rate incl. on-costs", 15.0, "GBP/h", "estimate", "UK National Living Wage £12.21/h (Apr 2025) + ~20 % on-costs (input_register: pending)", Style.GBP2),
            ("labour_h_m2", "Labour per m² growing area", 0.8, "h/m²/yr", "estimate", "Glasshouse fruit veg 0.75-1.0 h/m²/yr; KWIN/AHDB to source. Flat per m² with scale (RaboResearch 2025 fig. 6: Dutch m² per work unit stable)", Style.NUM2),
            ("co2_price", "CO2 (bulk liquid, delivered)", 0.25, "GBP/kg", "sourced (secondary)", "breakeven.py; distillery fermentation CO2 could be ~free (lever)", Style.GBP2),
            ("plants_m2", "Young plants", C["plants_m2"]["cucumber"], "GBP/m²/yr", "sourced (range)", "cashflow.py: three crops/yr; tomato GBP 1.61-6.4/m² range (J. Cleaner Prod. 2022; KWIN 2023)", Style.GBP2),
            ("substrate_m2", "Substrate", C["substrate_m2"], "GBP/m²/yr", "sourced", "KWIN 2023 growing media EUR 0.86/m²", Style.GBP2),
            ("materials_m2", "Fertiliser, crop protection, strings, water", C["materials_m2"]["cucumber"], "GBP/m²/yr", "sourced (secondary)", "J. Cleaner Production 2022 UK tomato GBP 2.27-2.48/m²; cucumber without bumblebees", Style.GBP2),
            ("pack_gbp_kg", "Packing", 0.10, "GBP/kg", "estimate", "Packhouse, film, carton (crops.py); to source", Style.GBP3),
            ("om_frac", "Structure O&M + insurance", 0.02, "of structure capex /yr", "estimate", "breakeven.py", Style.PCT),
            ("overheads_m2", "Overheads (management, certification, accounts)", C["overheads_m2"], "GBP/m²/yr", "placeholder",
             "No UK source; BritFarmers 2026 puts retailer compliance at £8-50k/yr, inside this", Style.GBP2),
            ("land_rent_ha", "Land rent", C["land_gbp_ha"], "GBP/ha/yr", "placeholder", "Scottish arable ~£250-500/ha; industrial land more", Style.GBP),
            ("land_extra", "Extra land for access, packhouse, plant", 0.30, "of glass area", "estimate", "cashflow.py", Style.PCT),
            ("Project", None),
            ("dev_frac", "Development (design, planning, legal, site investigation)", C["dev_frac"], "of capex", "estimate", "Feasibility-stage allowance", Style.PCT),
            ("contingency", "Contingency", C["contingency"], "of capex", "estimate", "Class 4 estimate (±30 %)", Style.PCT),
            ("hv_conn", "HV import connection (11 kV)", C["import_conn_gbp"], "GBP", "sourced (range)", "£50-150k near a substation (solargridcheck.co.uk G99 guide 2026); upper end. Should scale with kVA (BP16)", Style.GBP),
        ]
        for r in rows:
            if r[1] is None:
                s.section(r[0], 5)
                continue
            nm, label, val, unit, tier, src, fmt = r
            s.put(1, label)
            s.put(2, val, fmt=fmt, font=Style.LINK if isinstance(val, str) else Style.INPUT,
                  fill=Style.KEY_FILL if nm in ("rate_commercial", "commission", "price_cucumber") else None)
            s.put(3, unit)
            s.put(4, tier)
            s.put(5, src, wrap=True)
            s.name(nm, 2)
            s.next()

    # ---- Rates -----------------------------------------------------------------------------------------------------
    def rates(self):
        R = self.d["rates"]
        s = Sheet(self.wb, "Rates", [40, 12, 12, 12, 12, 10, 16, 22, 80])
        s.title("Unit rates", "Central rate drives the model; low/high are the quote range. Replace with supplier quotes.")
        s.header(["Item", "Unit", "Low", "Central", "High", "Life (yr)", "Cost driver", "Tier", "Source"])
        s.section("Structure (quantities x rate)", 9)
        names = {"steel": "Steel frame, erected", "aluminium": "Aluminium glazing bars", "glass_single_m2": "Glass, single 4 mm 2xAR",
                 "glass_dbl_ar_m2": "Glass, double AR sealed unit", "glass_dbl_lowe_m2": "Glass, double AR + low-e",
                 "concrete": "Concrete (pads, edge beam, paths)", "heating_pipe_m": "Heating pipe-rail (51 mm)",
                 "energy_screen_m2": "Energy screen incl. drive"}
        driver = {"steel": "per t (from frame sizing)", "aluminium": "per kg (per m of bar)", "concrete": "per m³",
                  "heating_pipe_m": "per m (2.25 m per m²)", "energy_screen_m2": "per m² floor"}
        low_high = {"aluminium": (4, 9), "glass_single_m2": (15, 40), "glass_dbl_ar_m2": (45, 100), "glass_dbl_lowe_m2": (50, 120)}
        self.rate_row = {}
        for k, label in names.items():
            r = R[k]
            lo, hi = low_high.get(k, (None, None))
            s.put(1, label)
            s.put(2, {"steel": "t", "aluminium": "kg", "concrete": "m³", "heating_pipe_m": "m"}.get(k, "m²"))
            s.put(3, lo, fmt=Style.GBP2)
            s.put(4, r["cost"], fmt=Style.GBP2, fill=Style.KEY_FILL if "glass" in k else None)
            s.put(5, hi, fmt=Style.GBP2)
            s.put(6, r["life"], fmt=Style.NUM)
            s.put(7, driver.get(k, "per m² glazed"))
            s.put(8, r["tier"])
            s.put(9, r["src"][:300], wrap=True)
            s.name(f"r_{k}", 4)
            s.name(f"life_{k}", 6)
            self.rate_row[k] = s.row
            s.next()
        s.put(1, "Installation, climate computer, irrigation, vents, wires, design (residual)")
        s.put(2, "m²")
        s.put(4, round(self.d["resid_gbp_m2"], 2), fmt=Style.GBP2, fill=Style.KEY_FILL)
        s.put(6, 30, fmt=Style.NUM)
        s.put(7, "per m² floor (see 'Scale')")
        s.put(8, "calibrated")
        s.put(9, "SAC/SRUC (2026) 'Developing SME-scale CEA' Table 11: commercial glasshouse £2M/ha minus the itemised list for "
                 "a 1 ha Venlo reference (costing.py). Not itemised: the biggest single capex item, the first target for an "
                 "itemised RFQ.", wrap=True)
        s.name("r_resid", 4)
        s.name("life_resid", 6)
        s.next(2)
        s.section("Heat system", 9)
        s.put(1, "Heat pump (R717, air source), DEA cost curve")
        s.put(2, "MEUR/MW at 1 / 3 / 10 MW")
        for i, (mw, v) in enumerate([(1, 1.15), (3, 1.10), (10, 1.02)]):
            s.put(3 + i, v, fmt="0.000")
            s.name(f"dea_hp_{mw}", 3 + i)
        s.put(6, 25, fmt=Style.NUM)
        s.name("life_hp", 6)
        s.put(7, "per kW, log-interpolated by size")
        s.put(8, "sourced")
        s.put(9, "Danish Energy Agency, Technology Data for Generation of Electricity and District Heating, ch. 40 'Comp. hp, "
                 "airsource 1/3/10 MW', Aug 2026 data sheets, total investment (2030 column used by site_opt.py). Note P: "
                 "+15 % for 40-80 °C supply temperatures (not applied)", wrap=True)
        s.next()
        s.put(1, "Heat pump fixed O&M")
        s.put(2, "EUR/MW/yr")
        s.put(4, 2126.745, fmt=Style.NUM)
        s.name("om_hp", 4)
        s.put(8, "sourced")
        s.put(9, "DEA ch. 40 airsource 1 MW, fixed O&M")
        s.next()
        s.put(1, "Electric peak boiler")
        s.put(2, "MEUR/MW")
        s.put(4, 0.15457, fmt="0.00000")
        s.name("r_boiler", 4)
        s.put(6, 25, fmt=Style.NUM)
        s.name("life_boiler", 6)
        s.put(7, "per kW")
        s.put(8, "sourced")
        s.put(9, "DEA ch. 41 'Electric boiler, small': total investment 0.155 MEUR/MW (equipment 0.087 + installation 0.067), "
                 "efficiency 0.99. About 7x cheaper per kW than the heat pump: the cheap way to cover the few peak hours "
                 "(Stanghellini et al. 2019/2023, Greenhouse Horticulture, §8.9 eq. 8.14 and fig. 8.14)", wrap=True)
        s.next()
        s.put(1, "Electric boiler fixed O&M")
        s.put(2, "EUR/MW/yr")
        s.put(4, 1137.8, fmt=Style.NUM)
        s.name("om_boiler", 4)
        s.put(8, "sourced")
        s.put(9, "DEA ch. 41")
        s.next()
        s.put(1, "Hot-water store (buffer tank)")
        s.put(2, "GBP/kWh stored")
        s.put(4, round(self.d["lp"]["store_gbp_kwh"], 2), fmt=Style.GBP2)
        s.name("r_store", 4)
        s.put(6, 40, fmt=Style.NUM)
        s.name("life_store", 6)
        s.put(7, "per kWh capacity")
        s.put(8, "sourced")
        s.put(9, "DEA Technology Data for Energy Storage, hot-water tank, at 4.2 MWh (finalist_lp.py; size-dependent). Buffer "
                 "lowers peak plant: Stanghellini et al. §8.8 (25 W/m² store + 50 W/m² boiler = 75 W/m²)", wrap=True)
        s.next()
        s.put(1, "Hot-water store O&M")
        s.put(2, "EUR2015/MWh/yr")
        s.put(4, 8.6, fmt=Style.NUM1)
        s.name("om_store", 4)
        s.put(8, "sourced")
        s.put(9, "DEA storage; x1.2876 to 2025 EUR (finalist_lp.py)")
        s.next(2)
        s.section("Energy route", 9)
        T = self.S[0]["turbine"]
        items = [("turb_kw", "Owned turbine size", 2500, "kW", "Single 2.5 MW turbine (energy_grid own_2p5MW)", Style.NUM),
                 ("turb_gbp_kw", "Turbine capex", 2240, "GBP/kW", "Kilbirnie 2.5 MW community turbine, N. Ayrshire, £5.6M (Envirotec, 5 Mar 2026)", Style.GBP),
                 ("turb_conn", "Turbine export connection allowance", 300000, "GBP", "33 kV £0.3-1.0M, 11 kV £50-150k (solargridcheck.co.uk 2026)", Style.GBP),
                 ("turb_om_kw", "Turbine O&M", 19.5 * 1.08, "GBP/kW/yr", "Arup (2025) for DESNZ, Table 18: £19.5k/MW/a (2023 £) x1.08", Style.NUM1),
                 ("turb_gen", "Turbine generation", round(T["gen_MWh"], 1), "MWh/yr", "Model: Global Wind Atlas at the site, capacity factor capped at 41.3 % (Arup 2025 Table 22)", Style.NUM),
                 ("turb_life", "Turbine life (repowered once in 30 yr)", 20, "yr", "Arup (2025)", Style.NUM),
                 ("export_price", "Export PPA price for surplus", 60, "GBP/MWh", "~£70/MWh fair value (Veyt 2025) less ~£10 route-to-market (estimate)", Style.GBP),
                 ("pw_price", "Private-wire PPA price", 90, "GBP/MWh", "Savills 2025: £80-120/MWh delivered; low end (energy_grid private_wire). Needs a wind farm within a few km (Girvan: 16 large turbines within 3.1 km)", Style.GBP),
                 ("pw_capex", "Private-wire connection capex (if paid by us)", 0, "GBP", "Not costed in the model (placeholder 0); typically a few £100k per km", Style.GBP)]
        for nm, label, val, unit, src, fmt in items:
            s.put(1, label)
            s.put(2, unit)
            s.put(4, val, fmt=fmt, fill=Style.KEY_FILL if nm == "pw_price" else None)
            s.put(9, src, wrap=True)
            s.name(nm, 4)
            s.next()

    # ---- Scenarios -------------------------------------------------------------------------------------------------
    def scenarios(self):
        s = Sheet(self.wb, "Scenarios", [44, 12] + [17] * 5 + [70])
        s.title("Design scenarios: physical quantities from the simulation",
                "Blue values are model outputs (site_opt.evaluate, track B lead design, Stranraer location, 2023 weather).")
        s.header(["Quantity", "Unit"] + [sc["key"] for sc in self.S] + ["Note"])
        s.put(1, "Description")
        for c, sc in zip(SC_COLS, self.S):
            s.put(c, sc["label"], wrap=True)
        s.ws.row_dimensions[s.row].height = 64
        s.next()
        self.sc_row = {}

        def row(key, label, unit, vals, fmt, note=""):
            s.put(1, label)
            s.put(2, unit)
            for c, v in zip(SC_COLS, vals):
                s.put(c, v, fmt=fmt)
            s.put(8, note, wrap=True)
            self.sc_row[key] = s.row
            s.next()
        S = self.S
        gk = {"dbl_ar": "glass_dbl_ar_m2", "single_2ar": "glass_single_m2"}
        s.section("Design", 8)
        row("glazing", "Glazing", "-", [("Double AR" if x["glazing"] == "dbl_ar" else "Single 2xAR") for x in S], None)
        row("turbine", "Owns the 2.5 MW turbine (1 = yes)", "flag", [1 if x["elec"] == "own_2p5MW" else 0 for x in S], Style.NUM)
        row("area", "Glasshouse floor area", "m²", [x["area_m2"] for x in S], Style.NUM, "4 spans x 15.4 m x 162 m, gutter 4.64 m")
        row("usable", "Growing share of floor (paths excluded)", "-", [x["usable"] for x in S], Style.PCT)
        row("perimeter", "Perimeter", "m", [x["perimeter"] for x in S], Style.NUM)
        row("glazed", "Glazed area (roof + walls)", "m²", [x["glazed_m2"] for x in S], Style.NUM)
        s.section("Bill of quantities (costing.bill)", 8)
        row("q_steel", "Steel", "t", [x["quantities"]["steel"] for x in S], Style.NUM1, "Concept frame sizing (sizing.py, EN 13031-1 loads)")
        row("q_al", "Aluminium", "kg", [x["quantities"]["aluminium"] for x in S], Style.NUM)
        row("q_glass", "Glass", "m²", [x["quantities"][gk[x["glazing"]]] for x in S], Style.NUM)
        row("q_conc", "Concrete", "m³", [x["quantities"]["concrete"] for x in S], Style.NUM1)
        row("q_pipe", "Heating pipe", "m", [x["quantities"]["heating_pipe_m"] for x in S], Style.NUM)
        row("q_screen", "Energy screen", "m²", [x["quantities"]["energy_screen_m2"] for x in S], Style.NUM)
        s.section("Heat system", 8)
        row("design_kw", "Design heat load (-3.1 °C outside)", "kW", [x["design_kW"] for x in S], Style.NUM, "Single glass loses ~75 % more heat")
        row("hp_kw", "Heat pump capacity", "kW", [x["hp_kW"] for x in S], Style.NUM, "S0: LP-sized, floored to meet the 2010 winter with the store")
        row("boiler_kw", "Electric peak boiler", "kW", [x["boiler_kW"] for x in S], Style.NUM, "LP-sized with the heat pump and store (BP19a); boiler + heat pump = design load, so it is also the standby")
        row("store_kwh", "Hot-water store", "kWh", [x["store_kWh"] for x in S], Style.NUM, "LP-sized in every scenario (BP19a re-ran S1-S4 with the store)")
        row("heat_mwh", "Heat delivered", "MWh/yr", [x["heat_MWh"] for x in S], Style.NUM)
        row("boiler_mwh", "  of which from the boiler", "MWh/yr", [x["boiler_MWh"] for x in S], Style.NUM)
        s.section("Electricity", 8)
        row("elec_mwh", "Electricity use (heat pump, boiler, fans, pumps)", "MWh/yr", [x["elec_MWh"] for x in S], Style.NUM)
        row("self_share", "Share met by wind (own turbine or private wire)", "-", [x["self_share"] for x in S], Style.PCT, "Hourly dispatch (energy_grid.py)")
        row("grid_price", "Grid top-up price (delivered, all charges)", "GBP/MWh", [x["grid_price"] * 1e3 for x in S], Style.GBP, "DESNZ business price, wholesale share on the Agile shape")
        row("net_gbp", "Network charge increase (peak import band)", "GBP/yr", [x["net_gbp_yr"] for x in S], Style.GBP, "NESO TNUoS 2026/27 bands; jumps with peak kVA")
        s.section("Crop", 8)
        row("yield", "Yield per m² floor", "kg/m²/yr", [x["Y"] for x in S], Style.NUM1, "crop_gh, calibrated to CBS NL; single glass +14 % from more light (elasticity ~1)")
        row("co2_dose", "CO2 dosed", "kg/m²/yr", [x["co2_kg_m2"] for x in S], Style.NUM1)
        row("haul", "Haulage to RDCs", "GBP/kg", [x["logistics_gbp_kg"] for x in S], Style.GBP3, "Stranraer 165 km; Girvan would be £0.032/kg")
        row("co2e", "Carbon delivered to RDC", "kg CO2e/kg", [x["kg_co2e_kg"] for x in S], Style.NUM2, "Imports 0.81")
        self.scs = s

    def sc(self, key, col):
        return f"'Scenarios'!{get_column_letter(col)}{self.sc_row[key]}"

    # ---- Capex -----------------------------------------------------------------------------------------------------
    def capex(self):
        s = Sheet(self.wb, "Capex", [52, 22] + [16] * 5 + [12, 60])
        s.title("Initial expenditure by item (GBP)", "Quantity (Scenarios) x unit rate (Rates). Grey rows are totals.")
        s.header(["Item", "Cost driver"] + [sc["key"] for sc in self.S] + ["Life (yr)", "Note"])
        self.cx = {}

        def line(key, label, drv, f, life, note=""):
            s.put(1, label)
            s.put(2, drv)
            for c in SC_COLS:
                s.put(c, f(c), fmt=Style.GBP)
            s.put(8, life, fmt=Style.NUM, font=Style.LINK if isinstance(life, str) else Style.INPUT)
            s.put(9, note, wrap=True)
            self.cx[key] = s.row
            s.next()

        def total(key, label, keys, fill=Style.TOTAL_FILL):
            s.put(1, label, font=Style.BOLD, fill=fill)
            s.put(2, "", fill=fill)
            for c in SC_COLS:
                L = get_column_letter(c)
                s.put(c, "=" + "+".join(f"{L}{self.cx[k]}" for k in keys), fmt=Style.GBP, font=Style.BOLD, fill=fill)
            self.cx[key] = s.row
            s.next()
        sc = self.sc
        s.section("Structure", 9)
        line("steel", "Steel frame", "per t", lambda c: f"={sc('q_steel', c)}*r_steel", "=life_steel")
        line("al", "Aluminium glazing bars", "per kg", lambda c: f"={sc('q_al', c)}*r_aluminium", "=life_aluminium")
        line("glass", "Glass", "per m² glazed", lambda c: f'=IF({sc("glazing", c)}="Double AR",r_glass_dbl_ar_m2,r_glass_single_m2)*{sc("q_glass", c)}',
             "=life_glass_dbl_ar_m2", "Rate switches with the glazing choice")
        line("conc", "Concrete foundations and paths", "per m³", lambda c: f"={sc('q_conc', c)}*r_concrete", "=life_concrete")
        line("pipe", "Heating pipe-rail", "per m", lambda c: f"={sc('q_pipe', c)}*r_heating_pipe_m", "=life_heating_pipe_m")
        line("screen", "Energy screen", "per m² floor", lambda c: f"={sc('q_screen', c)}*r_energy_screen_m2", "=life_energy_screen_m2",
             "10-yr life: replaced twice in 30 yr")
        line("resid", "Installation, climate computer, irrigation, vents, wires (residual)", "per m² floor",
             lambda c: f"={sc('area', c)}*r_resid", "=life_resid", "SAC-calibrated lump: itemise with an RFQ")
        total("struct", "Structure total", ["steel", "al", "glass", "conc", "pipe", "screen", "resid"])
        s.section("Heat system", 9)

        def hp_gbp_kw(c):
            mw = f"({sc('hp_kw', c)}/1000)"
            return (f"IF({mw}<=1,dea_hp_1,IF({mw}<=3,dea_hp_1+LN({mw})/LN(3)*(dea_hp_3-dea_hp_1),"
                    f"IF({mw}<=10,dea_hp_3+LN({mw}/3)/LN(10/3)*(dea_hp_10-dea_hp_3),dea_hp_10)))*1000*eur_gbp")
        line("hp", "Heat pump", "per kW (DEA size curve)", lambda c: f"={sc('hp_kw', c)}*{hp_gbp_kw(c)}", "=life_hp")
        line("boiler", "Electric peak boiler", "per kW", lambda c: f"={sc('boiler_kw', c)}*r_boiler*1000*eur_gbp", "=life_boiler")
        line("store", "Hot-water store", "per kWh", lambda c: f"={sc('store_kwh', c)}*r_store", "=life_store")
        total("heat", "Heat system total", ["hp", "boiler", "store"])
        s.section("Site and connection", 9)
        line("hv", "HV import connection", "fixed per site", lambda c: "=hv_conn", 30, "Fixed: does not grow with m²")
        s.section("Project costs", 9)
        line("dev", "Development (design, planning, legal, SI)", "% of the above",
             lambda c: f"=dev_frac*({get_column_letter(c)}{self.cx['struct']}+{get_column_letter(c)}{self.cx['heat']}+{get_column_letter(c)}{self.cx['hv']})", 30)
        line("cont", "Contingency", "% of the above",
             lambda c: f"=contingency*({get_column_letter(c)}{self.cx['struct']}+{get_column_letter(c)}{self.cx['heat']}+{get_column_letter(c)}{self.cx['hv']})", 30)
        total("gh", "GREENHOUSE INITIAL EXPENDITURE", ["struct", "heat", "hv", "dev", "cont"], fill=Style.KEY_FILL)
        s.section("Energy route (separate business)", 9)
        line("turb", "Owned 2.5 MW turbine + export connection", "fixed (one turbine)",
             lambda c: f"={sc('turbine', c)}*(turb_kw*turb_gbp_kw+turb_conn)", "=turb_life", "Zero on the private-wire PPA route")
        line("pw", "Private-wire connection (if ours)", "fixed", lambda c: f"=(1-{sc('turbine', c)})*pw_capex", 30, "Placeholder 0")
        total("energy", "ENERGY-ROUTE INITIAL EXPENDITURE", ["turb", "pw"], fill=Style.KEY_FILL)
        total("all", "TOTAL DAY-ONE SPEND", ["gh", "energy"], fill=Style.KEY_FILL)
        s.next()
        s.section("Per m² and by cost driver", 9)
        for key, label, keys in [("gh", "Greenhouse capex per m²", ["gh"]), ("all", "Total day-one spend per m²", ["all"])]:
            s.put(1, label)
            for c in SC_COLS:
                L = get_column_letter(c)
                s.put(c, f"={L}{self.cx[key]}/{sc('area', c)}", fmt=Style.GBP)
            s.next()
        for label, keys in [("  per m² items (glass, frame, screen, pipe, residual)", ["steel", "al", "glass", "conc", "pipe", "screen", "resid"]),
                            ("  per kW items (heat pump, boiler, store)", ["hp", "boiler", "store"]),
                            ("  fixed items (HV connection)", ["hv"]),
                            ("  % add-ons (development, contingency)", ["dev", "cont"])]:
            s.put(1, label)
            for c in SC_COLS:
                L = get_column_letter(c)
                s.put(c, f"=({'+'.join(f'{L}{self.cx[k]}' for k in keys)})/{L}{self.cx['gh']}", fmt=Style.PCT)
            s.next()
        s.put(1, "Change in greenhouse capex vs S0")
        for c in SC_COLS:
            L = get_column_letter(c)
            s.put(c, f"={L}{self.cx['gh']}-$C${self.cx['gh']}", fmt=Style.GBP)
        s.next()
        s.put(1, "Change in total day-one spend vs S0")
        for c in SC_COLS:
            L = get_column_letter(c)
            s.put(c, f"={L}{self.cx['all']}-$C${self.cx['all']}", fmt=Style.GBP)
        s.next()

    def cxr(self, key, col):
        return f"'Capex'!{get_column_letter(col)}{self.cx[key]}"

    # ---- Energy price ----------------------------------------------------------------------------------------------
    def energy(self):
        s = Sheet(self.wb, "Energy", [56, 12] + [16] * 5 + [60])
        s.title("Electricity price paid by the greenhouse, and the turbine as its own business",
                "Turbine route: wind share at the turbine's levelised cost, the rest from the grid. PPA route: wind share at the PPA price.")
        s.header(["Item", "Unit"] + [sc["key"] for sc in self.S] + ["Note"])
        self.en = {}
        for tag, rate in (("8", "rate_commercial"), ("35", "rate_public")):
            s.section(f"At the {'commercial' if tag == '8' else 'Green Book'} discount rate", 8)
            s.put(1, "Turbine levelised cost of energy (LCOE)")
            s.put(2, "GBP/MWh")
            for c in SC_COLS:
                s.put(c, f"=(( turb_kw*turb_gbp_kw+turb_conn)*{rate}/(1-(1+{rate})^-turb_life)+turb_kw*turb_om_kw)/turb_gen".replace("( ", "("),
                      fmt=Style.GBP2)
            s.put(8, "capex x CRF(rate, 20 yr) + O&M, over generation")
            self.en[f"lcoe{tag}"] = s.row
            s.next()
            s.put(1, "Blended electricity price to the greenhouse")
            s.put(2, "GBP/MWh")
            for c in SC_COLS:
                L = get_column_letter(c)
                s.put(c, f"={self.sc('self_share', c)}*IF({self.sc('turbine', c)}=1,{L}{self.en[f'lcoe{tag}']},pw_price)"
                         f"+(1-{self.sc('self_share', c)})*{self.sc('grid_price', c)}", fmt=Style.GBP2)
            s.put(8, "Model check at 3.5 %: S0 £66.6, S3 £99.5/MWh (hourly dispatch)")
            self.en[f"price{tag}"] = s.row
            s.next()
            s.put(1, "Turbine business NPV (sales to greenhouse at LCOE + export)")
            s.put(2, "GBP")
            for c in SC_COLS:
                L = get_column_letter(c)
                af = f"((1-(1+{rate})^-years)/{rate})"
                sales = f"{self.sc('elec_mwh', c)}*{self.sc('self_share', c)}*{L}{self.en[f'lcoe{tag}']}"
                exp = f"MAX(turb_gen-{self.sc('elec_mwh', c)}*{self.sc('self_share', c)},0)*export_price"
                eac = f"(turb_kw*turb_gbp_kw+turb_conn)*{rate}/(1-(1+{rate})^-turb_life)"
                s.put(c, f"={self.sc('turbine', c)}*({sales}+{exp}-turb_kw*turb_om_kw-{eac})*{af}", fmt=Style.GBP)
            s.put(8, "Steady-state: equivalent annual cost of the turbine over 30 yr")
            self.en[f"tnpv{tag}"] = s.row
            s.next()

    # ---- Opex ------------------------------------------------------------------------------------------------------
    def opex(self):
        s = Sheet(self.wb, "Opex", [50, 26] + [16] * 5 + [50])
        s.title("Annual running costs (GBP/yr) at the commercial rate",
                "Electricity at the 8 % turbine LCOE; the 3.5 % case only changes the electricity line (see Results).")
        s.header(["Item", "Driver"] + [sc["key"] for sc in self.S] + ["Note"])
        self.ox = {}
        sc = self.sc
        A = lambda c: sc("area", c)  # noqa: E731
        U = lambda c: sc("usable", c)  # noqa: E731
        KG = lambda c: f"({sc('yield', c)}*{sc('area', c)})"  # noqa: E731
        items = [
            ("rev", "Revenue (before commission)", "kg x price", lambda c: f"={KG(c)}*price_cucumber", "Not a cost: used for commission"),
            ("elec", "Electricity", "MWh x blended price", lambda c: f"={sc('elec_mwh', c)}*'Energy'!{get_column_letter(c)}{self.en['price8']}", ""),
            ("net", "Network charge increase", "peak import band", lambda c: f"={sc('net_gbp', c)}", ""),
            ("labour", "Labour", "h/m² x rate x growing m²", lambda c: f"=labour_h_m2*labour_rate*{U(c)}*{A(c)}", ""),
            ("co2", "CO2", "kg/m² x price x growing m²", lambda c: f"={sc('co2_dose', c)}*co2_price*{U(c)}*{A(c)}", "Free distillery CO2 removes this"),
            ("plants", "Young plants", "per growing m²", lambda c: f"=plants_m2*{U(c)}*{A(c)}", ""),
            ("subs", "Substrate", "per growing m²", lambda c: f"=substrate_m2*{U(c)}*{A(c)}", ""),
            ("mat", "Fertiliser, protection, strings, water", "per growing m²", lambda c: f"=materials_m2*{U(c)}*{A(c)}", ""),
            ("pack", "Packing", "per kg", lambda c: f"=pack_gbp_kg*{KG(c)}", ""),
            ("haul", "Haulage to RDCs", "per kg", lambda c: f"={sc('haul', c)}*{KG(c)}", ""),
            ("om", "Structure O&M + insurance", "% of structure capex", lambda c: f"=om_frac*'Capex'!{get_column_letter(c)}{self.cx['struct']}", ""),
            ("hpom", "Heat pump, boiler, store O&M", "per MW / MWh", lambda c: f"=({sc('hp_kw', c)}/1000*om_hp+{sc('boiler_kw', c)}/1000*om_boiler)*eur_gbp+{sc('store_kwh', c)}/1000*om_store*1.2876*eur_gbp", "DEA"),
            ("ovh", "Overheads", "per m² floor", lambda c: f"=overheads_m2*{A(c)}", ""),
            ("land", "Land rent", "per ha incl. 30 % extra", lambda c: f"=land_rent_ha*{A(c)}/10000*(1+land_extra)", ""),
            ("comm", "Market commission", "% of revenue", lambda c: f"=commission*{get_column_letter(c)}{self.ox['rev']}", "14 % (BritFarmers 2026)"),
        ]
        for key, label, drv, f, note in items:
            s.put(1, label, font=Style.BOLD if key == "rev" else None)
            s.put(2, drv)
            for c in SC_COLS:
                s.put(c, f(c), fmt=Style.GBP)
            s.put(8, note)
            self.ox[key] = s.row
            s.next()
            if key == "rev":
                s.section("Running costs", 8)
        s.put(1, "TOTAL RUNNING COSTS", font=Style.BOLD, fill=Style.TOTAL_FILL)
        cost_keys = [k for k, *_ in items if k != "rev"]
        for c in SC_COLS:
            L = get_column_letter(c)
            s.put(c, "=" + "+".join(f"{L}{self.ox[k]}" for k in cost_keys), fmt=Style.GBP, font=Style.BOLD, fill=Style.TOTAL_FILL)
        self.ox["total"] = s.row
        s.next()
        s.put(1, "Running cost per kg")
        for c in SC_COLS:
            L = get_column_letter(c)
            s.put(c, f"={L}{self.ox['total']}/({sc('yield', c)}*{sc('area', c)})", fmt=Style.GBP3)
        self.ox["perkg"] = s.row
        s.next()

    # ---- Results ---------------------------------------------------------------------------------------------------
    def results(self):
        s = Sheet(self.wb, "Results", [58, 12] + [16] * 5 + [56])
        s.title("Results: initial spend, cost per kg, margin and NPV",
                "Equivalent annual capital cost = capex x CRF(rate, item life); covers replacements of shorter-lived items.")
        s.header(["Result", "Unit"] + [sc["key"] for sc in self.S] + ["Note"])
        self.rs = {}
        cx = lambda k, c: self.cxr(k, c)  # noqa: E731
        s.section("Initial expenditure", 8)
        for key, label in (("gh", "Greenhouse"), ("energy", "Energy route (turbine)"), ("all", "Total day-one spend")):
            s.put(1, label, font=Style.BOLD if key == "all" else None)
            s.put(2, "GBP")
            for c in SC_COLS:
                s.put(c, f"={cx(key, c)}", fmt=Style.GBP, font=Style.LINK, fill=Style.KEY_FILL if key == "all" else None)
            self.rs[key] = s.row
            s.next()
        s.put(1, "Reduction in day-one spend vs S0")
        s.put(2, "%")
        for c in SC_COLS:
            L = get_column_letter(c)
            s.put(c, f"=1-{L}{self.rs['all']}/$C${self.rs['all']}", fmt=Style.PCT)
        s.next()
        lives = [("steel", "life_steel"), ("al", "life_aluminium"), ("glass", "life_glass_dbl_ar_m2"), ("conc", "life_concrete"),
                 ("pipe", "life_heating_pipe_m"), ("screen", "life_energy_screen_m2"), ("resid", "life_resid"), ("hp", "life_hp"),
                 ("boiler", "life_boiler"), ("store", "life_store"), ("hv", "years"), ("dev", "years"), ("cont", "years")]
        for tag, rate, name in (("8", "rate_commercial", "commercial"), ("35", "rate_public", "Green Book")):
            s.section(f"At the {name} discount rate", 8)
            s.put(1, "Equivalent annual capital cost (greenhouse)")
            s.put(2, "GBP/yr")
            for c in SC_COLS:
                terms = "+".join(f"{cx(k, c)}*{rate}/(1-(1+{rate})^-{lf})" for k, lf in lives)
                s.put(c, "=" + terms, fmt=Style.GBP)
            self.rs[f"eac{tag}"] = s.row
            s.next()
            s.put(1, "Running costs (electricity at this rate's turbine LCOE)")
            s.put(2, "GBP/yr")
            for c in SC_COLS:
                L = get_column_letter(c)
                s.put(c, f"='Opex'!{L}{self.ox['total']}-'Opex'!{L}{self.ox['elec']}+{self.sc('elec_mwh', c)}*'Energy'!{L}{self.en[f'price{tag}']}",
                      fmt=Style.GBP)
            self.rs[f"opex{tag}"] = s.row
            s.next()
            s.put(1, "Production", font=None)
            s.put(2, "kg/yr")
            for c in SC_COLS:
                s.put(c, f"={self.sc('yield', c)}*{self.sc('area', c)}", fmt=Style.NUM)
            self.rs[f"kg{tag}"] = s.row
            s.next()
            s.put(1, "LEVELISED COST OF PRODUCTION", font=Style.BOLD)
            s.put(2, "GBP/kg")
            for c in SC_COLS:
                L = get_column_letter(c)
                s.put(c, f"=({L}{self.rs[f'eac{tag}']}+{L}{self.rs[f'opex{tag}']})/{L}{self.rs[f'kg{tag}']}", fmt=Style.GBP3,
                      font=Style.BOLD, fill=Style.KEY_FILL)
            self.rs[f"lcop{tag}"] = s.row
            s.next()
            s.put(1, "  of which capital")
            s.put(2, "GBP/kg")
            for c in SC_COLS:
                L = get_column_letter(c)
                s.put(c, f"={L}{self.rs[f'eac{tag}']}/{L}{self.rs[f'kg{tag}']}", fmt=Style.GBP3)
            s.next()
            s.put(1, "Price received (DEFRA wholesale, harvest-weighted)")
            s.put(2, "GBP/kg")
            for c in SC_COLS:
                s.put(c, "=price_cucumber", fmt=Style.GBP3, font=Style.LINK)
            s.next()
            s.put(1, "Margin per kg (price - cost)")
            s.put(2, "GBP/kg")
            for c in SC_COLS:
                L = get_column_letter(c)
                s.put(c, f"=price_cucumber-{L}{self.rs[f'lcop{tag}']}", fmt=Style.GBP3)
            self.rs[f"margin{tag}"] = s.row
            s.next()
            s.put(1, "Break-even price (covers commission)")
            s.put(2, "GBP/kg")
            for c in SC_COLS:
                L = get_column_letter(c)
                comm = f"'Opex'!{L}{self.ox['comm']}"
                s.put(c, f"=({L}{self.rs[f'eac{tag}']}+{L}{self.rs[f'opex{tag}']}-{comm})/({L}{self.rs[f'kg{tag}']}*(1-commission))",
                      fmt=Style.GBP3)
            s.next()
            s.put(1, "Greenhouse NPV (steady-state, 30 yr)", font=Style.BOLD)
            s.put(2, "GBP")
            for c in SC_COLS:
                L = get_column_letter(c)
                af = f"((1-(1+{rate})^-years)/{rate})"
                s.put(c, f"=({L}{self.rs[f'kg{tag}']}*price_cucumber-{L}{self.rs[f'opex{tag}']}-{L}{self.rs[f'eac{tag}']})*{af}",
                      fmt=Style.GBP, font=Style.BOLD)
            self.rs[f"npv{tag}"] = s.row
            s.next()
            s.put(1, "Turbine business NPV (link to Energy)")
            s.put(2, "GBP")
            for c in SC_COLS:
                L = get_column_letter(c)
                s.put(c, f"='Energy'!{L}{self.en[f'tnpv{tag}']}", fmt=Style.GBP, font=Style.LINK)
            s.next()
        s.next()
        cf = self.d["cashflow_S0"]
        s.section("Check against the full cash-flow model (cashflow.py, S0, 5 % commission, with ramp-up and residual value)", 8)
        checks = [("Levelised cost at 8 % (cashflow.py)", cf["lcop_0.08"], "lcop8"),
                  ("Levelised cost at 3.5 % (cashflow.py)", cf["lcop_0.035"], "lcop35")]
        for label, val, key in checks:
            s.put(1, label)
            s.put(2, "GBP/kg")
            s.put(3, round(val, 3), fmt=Style.GBP3)
            s.put(8, f"This sheet uses 14 % commission and the 8 %-rate turbine LCOE; set Inputs commission to 5 % to compare "
                     f"like for like (expect within a few pence: no ramp-up year, no residual value here)", wrap=True)
            s.next()
        s.put(1, "Greenhouse capex, S0 (cashflow.py)")
        s.put(2, "GBP")
        s.put(3, round(cf["capex_total"]), fmt=Style.GBP)
        s.next()

    # ---- Scale explorer --------------------------------------------------------------------------------------------
    def scale(self):
        s = Sheet(self.wb, "Scale", [46, 14, 14, 14, 14, 14, 14, 14, 60])
        s.title("Scale explorer: how cost per m² changes with size",
                "Today's model scales everything per m² except the HV connection. Here each cost has its own driver; "
                "fixed and perimeter shares come from residual_items.csv and the geometry (BP19b/d); quotes will replace them.")
        import bplan_residual
        res_items = bplan_residual.ResidualItems(self.d["resid_gbp_m2"])
        perim = bplan_residual.PerimeterShare(self.d)
        s.put(1, "Fixed share of the residual (climate computer core, design, plant room, water basin)")
        s.put(2, round(res_items.fixed_share, 3), fmt=Style.PCT, fill=Style.KEY_FILL,
              comment="From data/residual_items.csv (BP19b): fixed per-site lines / the £94/m² residual at 1 ha. Only the climate "
                      f"computer line is priced from a public source; {res_items.placeholder_share:.0%} of the residual is still "
                      "placeholder split, so the share is a labelled estimate until the RFQ returns. 0 % reproduces the linear model.")
        s.name("fixed_resid_share", 2)
        s.next()
        s.put(1, "Perimeter items: share of structure that is walls / edge foundations")
        s.put(2, round(perim.share, 3), fmt=Style.PCT, fill=Style.KEY_FILL,
              comment=f"Geometric (bplan_residual.PerimeterShare): wall glazing and bars, {perim.wall_frac:.1%} of the glazed area "
                      "(perimeter x gutter height), over the priced structure. Edge foundations and gable framing are not included "
                      "(no quantities yet), so this is a lower bound.")
        s.name("perim_share", 2)
        s.next()
        s.put(1, "Heat pump design load per m² (from S0)")
        s.put(2, f"={self.sc('design_kw', 3)}/{self.sc('area', 3)}*1000", fmt=Style.NUM1)
        s.put(3, "W/m²")
        s.name("hp_load_w_per_m2", 2)
        s.next()
        s.put(1, "Heat pump share of design load (S0 rule)")
        s.put(2, f"={self.sc('hp_kw', 3)}/{self.sc('design_kw', 3)}", fmt=Style.PCT)
        s.name("hp_share", 2)
        s.next(2)
        s.header(["Item (GBP per m²)", "1 ha", "2 ha", "5 ha", "10 ha", "20 ha", "30 ha", "", "Driver"])
        has = [1, 2, 5, 10, 20, 30]
        s.put(1, "Area (m²)")
        for i, h in enumerate(has):
            s.put(2 + i, h * 10000, fmt=Style.NUM)
        r_area = s.row
        s.next()
        struct_m2 = f"('Capex'!$C${self.cx['struct']}-'Capex'!$C${self.cx['resid']})/{self.sc('area', 3)}"
        rows = [
            ("Structure, area items", lambda L: f"={struct_m2}*(1-perim_share)", "per m² (flat rate; volume discounts need quotes)"),
            ("Structure, perimeter items", lambda L: f"={struct_m2}*perim_share*SQRT({self.sc('area', 3)}/{L}{r_area})", "per m of perimeter: falls as 1/sqrt(area)"),
            ("Residual, variable part", lambda L: "=r_resid*(1-fixed_resid_share)", "per m²"),
            ("Residual, fixed part", lambda L: f"=r_resid*fixed_resid_share*{self.sc('area', 3)}/{L}{r_area}", "fixed per site: falls as 1/area"),
            ("Heat pump (DEA curve)", lambda L: (f"=hp_load_w_per_m2/1000*hp_share*IF(hp_load_w_per_m2*hp_share*{L}{r_area}/1000000<=1,dea_hp_1,IF(hp_load_w_per_m2*hp_share*{L}{r_area}/1000000<=3,"
                                                 f"dea_hp_1+LN(hp_load_w_per_m2*hp_share*{L}{r_area}/1000000)/LN(3)*(dea_hp_3-dea_hp_1),IF(hp_load_w_per_m2*hp_share*{L}{r_area}/1000000<=10,"
                                                 f"dea_hp_3+LN(hp_load_w_per_m2*hp_share*{L}{r_area}/1000000/3)/LN(10/3)*(dea_hp_10-dea_hp_3),dea_hp_10)))*1000*eur_gbp"),
             "per kW, cheaper per kW above 1 MW"),
            ("Hot-water store", lambda L: f"='Capex'!$C${self.cx['store']}/{self.sc('area', 3)}", "per kWh (flat here; DEA tanks get cheaper with size)"),
            ("HV import connection", lambda L: f"=hv_conn/{L}{r_area}", "fixed per site (BP16: should step with kVA)"),
        ]
        first = s.row
        for label, f, drv in rows:
            s.put(1, label)
            for i in range(len(has)):
                s.put(2 + i, f(get_column_letter(2 + i)), fmt=Style.GBP2)
            s.put(9, drv)
            s.next()
        last = s.row - 1
        s.put(1, "Subtotal", font=Style.BOLD, fill=Style.TOTAL_FILL)
        for i in range(len(has)):
            L = get_column_letter(2 + i)
            s.put(2 + i, f"=SUM({L}{first}:{L}{last})", fmt=Style.GBP2, font=Style.BOLD, fill=Style.TOTAL_FILL)
        r_sub = s.row
        s.next()
        s.put(1, "Greenhouse capex per m² incl. development + contingency", font=Style.BOLD, fill=Style.KEY_FILL)
        for i in range(len(has)):
            L = get_column_letter(2 + i)
            s.put(2 + i, f"={L}{r_sub}*(1+dev_frac+contingency)", fmt=Style.GBP2, font=Style.BOLD, fill=Style.KEY_FILL)
        r_tot = s.row
        s.next()
        s.put(1, "Change vs 1 ha")
        for i in range(len(has)):
            L = get_column_letter(2 + i)
            s.put(2 + i, f"={L}{r_tot}/$B${r_tot}-1", fmt=Style.PCT)
        s.next(2)
        notes = ["Read: at 0 % fixed residual and 0 % perimeter share this reproduces today's model, where only the HV connection "
                 "and the heat pump curve give any economy of scale, which is why the size study found bigger houses no cheaper.",
                 "Evidence so far: Dutch growers consolidate onto 50-500 ha businesses for economies of scale (RaboResearch 2025, p. 6), "
                 "but no free source quantifies capex vs size. KWIN-AGV gives model-nursery investments by size (paywalled).",
                 "Labour stays per m² (RaboResearch 2025 fig. 6: Dutch m² per annual work unit stable 2000-2023)."]
        for n in notes:
            s.put(1, n, font=Style.NOTE)
            s.ws.merge_cells(start_row=s.row, start_column=1, end_row=s.row, end_column=9)
            s.ws.cell(s.row, 1).alignment = Alignment(wrap_text=True)
            s.ws.row_dimensions[s.row].height = 30
            s.next()

    # ---- Levers ----------------------------------------------------------------------------------------------------
    def levers(self):
        s = Sheet(self.wb, "Capex Levers", [40, 16, 18, 18, 22, 70])
        s.title("Capex-reduction levers", "Modelled values link to Results. 'To test' rows are the work plan (HANDOFF BP13-BP19).")
        s.header(["Lever", "Status", "Change in day-one spend", "Change in £/kg at 8 %", "Evidence", "Next step / caveat"])
        R = self.rs
        L = lambda c, k: f"='Results'!{c}{R[k]}"  # noqa: E731
        sh = json.loads((HERE / "results" / "bplan" / "secondhand.json").read_text())["cases"]
        rows = [
            ("LP-sized heat pump + electric peak boiler + store (double glass)", "modelled", f"='Results'!D{R['all']}-'Results'!C{R['all']}",
             f"='Results'!D{R['lcop8']}-'Results'!C{R['lcop8']}", "DEA ch. 40/41; Stanghellini §8.9",
             "Boiler also replaces the full-standby heat pump as cold-year / outage backup"),
            ("Single glass + LP-sized heat pump + boiler + store", "modelled", f"='Results'!E{R['all']}-'Results'!C{R['all']}",
             f"='Results'!E{R['lcop8']}-'Results'!C{R['lcop8']}", "Model: yield +14 %, heat +74 %",
             "Rests on the crop model's light response; check with GreenLight / grower data"),
            ("Private-wire PPA instead of owning the turbine", "modelled", f"='Results'!F{R['all']}-'Results'!E{R['all']}",
             f"='Results'!F{R['lcop8']}-'Results'!E{R['lcop8']}", "Savills 2025 PPA £80-120/MWh",
             "Needs an adjacent wind farm: Girvan (16 large turbines within 3.1 km), not Stranraer"),
            ("Supplier quotes for placeholder items (glass, aluminium, pipe, screen)", "to test", None, None,
             "Placeholders ~46 % of structure", "Issue RFQ_SPEC.md; try quotes in 'Rates' (low column)"),
            ("Itemise the £94/m² residual (climate computer, irrigation, install)", "itemised, unquoted", None, None, "data/residual_items.csv; climate computer from a Dutch installer price page (2026); the rest placeholder",
             "RFQ_SPEC §3.7 issued as a draft; 85 % of the residual is still a placeholder split, fixed share 17.7 %"),
            ("Second-hand glasshouse, re-erected (vs new single glass)", "modelled", round(sh["central"]["dcap_gbp"]), round(sh["central"]["dgbp_kg_8"], 3),
             "SAC/SRUC Table 11 purchase £60/m² (sourced); re-erection £25-50/m² and glass replacement are placeholders; the Avéro (2025) guideline could not be found",
             f"Range at 8 %: {sh['low']['dgbp_kg_8']:+.3f} to {sh['high']['dgbp_kg_8']:+.3f} £/kg. Fit-out and re-erection eat the purchase saving; check Scottish wind/snow rating (EN 13031-1)"),
            ("Basic glasshouse spec", "to test", None, None, "SAC/SRUC Table 11: £1M/ha basic vs £2M/ha commercial", "Lower yield / control"),
            ("Larger site (economies of scale)", "modelled (see Scale)", None, None, "'Scale' sheet; residual_items.csv fixed share; geometric perimeter share", "Shares are estimates until quotes; size study rerun with the fixed residual (HANDOFF BP19d)"),
            ("Phased build (phase 1 small, infrastructure sized for later)", "to test", None, None, "-", "Cuts day-one spend, raises £/m² of phase 1"),
            ("Re-optimise design at 8 % (sweep was at 3.5 %)", "to test", None, None, "refine.py", "Cheap run (~2 min)"),
            ("Lease heat pump / energy-as-a-service", "to test", None, None, "-", "Moves capex to opex; check supplier offers"),
            ("Capital grants", "to test", None, None, "Scottish Government / Scottish Enterprise schemes", "Financing, not cost: list eligible schemes"),
            ("Lower contingency after quotes (10 % -> 5 %)", "to test", None, None, "Estimate class", "Only once quotes are in hand"),
        ]
        for lever, status, dcap, dkg, ev, nxt in rows:
            s.put(1, lever, wrap=True)
            s.put(2, status, fill=Style.KEY_FILL if status == "modelled" else None)
            s.put(3, dcap, fmt=Style.GBP, font=Style.LINK if dcap else None)
            s.put(4, dkg, fmt=Style.GBP3, font=Style.LINK if dkg else None)
            s.put(5, ev, wrap=True)
            s.put(6, nxt, wrap=True)
            s.ws.row_dimensions[s.row].height = 30
            s.next()

    # ---- Prices ----------------------------------------------------------------------------------------------------
    def prices(self):
        import cashflow
        pm, n = cashflow.defra_monthly("cucumbers", "cucumbers")
        share = self.d["cashflow_S0"]["monthly_share"]
        s = Sheet(self.wb, "Prices", [14, 18, 18, 18, 70])
        s.title("Cucumber price by month", f"DEFRA wholesale fruit and vegetable prices, weekly average ({DEFRA_URL}), "
                                            "file fruitvegprices-260928.csv, 2023-26 mean by month; months with < 3 UK "
                                            "observations use the UK import CIF price (Comtrade 2023-25).")
        s.header(["Month", "Price (GBP/kg)", "Harvest share", "Weighted", "Note"])
        for m in range(12):
            s.put(1, ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m])
            s.put(2, round(float(pm[m]), 3), fmt=Style.GBP3)
            s.put(3, round(float(share[m]), 4), fmt=Style.PCT)
            s.put(4, f"=B{s.row}*C{s.row}", fmt=Style.GBP3)
            s.put(5, "import CIF (no UK market)" if m == 11 else "DEFRA")
            s.next()
        s.put(1, "Total", font=Style.BOLD)
        s.put(3, f"=SUM(C{s.row - 12}:C{s.row - 1})", fmt=Style.PCT)
        s.put(4, f"=SUMPRODUCT(B{s.row - 12}:B{s.row - 1},C{s.row - 12}:C{s.row - 1})/C{s.row}", fmt=Style.GBP3, font=Style.BOLD,
              fill=Style.KEY_FILL)
        assert s.row == 17, s.row

    # ---- Sources ---------------------------------------------------------------------------------------------------
    def sources(self):
        s = Sheet(self.wb, "Sources", [4, 130])
        s.title("Sources")
        src = [
            f"DEFRA, Wholesale fruit and vegetable prices, weekly average (accessed as fruitvegprices-260928.csv): {DEFRA_URL}",
            "UN Comtrade public API, UK imports by HS code and month, 2023-25 (CIF); ECB rates via api.frankfurter.dev",
            "SAC/SRUC (Jan 2026), Developing SME-scale Controlled Environment Agriculture in the Highlands & Islands, Table 11",
            "Danish Energy Agency, Technology Data for Generation of Electricity and District Heating (data sheets Aug 2026), ch. 40 heat pumps, ch. 41 electric boilers",
            "Danish Energy Agency, Technology Data for Energy Storage (hot-water tanks)",
            "Stanghellini C., van 't Ooster B., Heuvelink E. (2nd ed. 2023), Greenhouse Horticulture: Technology for Optimal Crop Production, Wageningen Academic: §8.8 buffers, §8.9 eq. 8.14 / fig. 8.14 heating economics",
            "RaboResearch (2025), Global Greenhouse Update: consolidation and scale (p. 6), labour productivity (fig. 6), investment classes (Table A2)",
            "BritFarmers, T. Harfield (2026), UK supermarket contracts vs wholesale pricing 2026 (trade guide): https://britfarmers.com/uk-supermarket-contracts-vs-wholesale-pricing-2026/",
            "Arup (2025) for DESNZ, Renewable Energy Generation Cost and Technical Assumptions 2024 (turbine O&M, capacity factor)",
            "Envirotec (5 Mar 2026), Kilbirnie 2.5 MW community turbine (capex anchor)",
            "Savills (2025), Unlocking the power of private wire (PPA £80-120/MWh)",
            "SteelConstruction.info / BCIS steel cost model; mixdesigncalc.co.uk concrete; KWIN 2023 substrate; J. Cleaner Production (2022) tomato LCC",
            "HM Treasury (2022), The Green Book; NESO TNUoS tariffs 2025/26 and 2026/27",
            "Model: BEng-CEA-Heatpump/lca (greenhouse_fast, crop_gh, energy_grid, site_opt, costing); verification results/bplan/VERIFICATION.md",
        ]
        for i, t in enumerate(src, 1):
            s.put(1, i, font=Style.CALC)
            s.put(2, t, wrap=True)
            s.next()

    def build(self):
        self.readme()
        self.inputs()
        self.rates()
        self.scenarios()
        self.capex()
        self.energy()
        self.opex()
        self.results()
        self.scale()
        self.levers()
        self.prices()
        self.sources()
        for ws in self.wb.worksheets:
            ws.freeze_panes = "C5" if ws.title in ("Scenarios", "Capex", "Energy", "Opex", "Results") else None
        OUT.parent.mkdir(parents=True, exist_ok=True)
        self.wb.save(OUT)
        print("wrote", OUT)


if __name__ == "__main__":
    Workbook_(json.loads((HERE / "results" / "bplan" / "xlsx_inputs.json").read_text())).build()
