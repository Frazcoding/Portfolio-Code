"""Candidate glasshouse sites in Scotland next to waste-heat sources, with wind and logistics.

Sources and methods (see data/input_register.csv):
  * Waste heat: BRE (2020) for ClimateXChange, 'Potential sources of waste heat for heat networks in Scotland'
    (doi:10.7488/era/730), method per sector:
      - distilleries (70-90 C, direct): LPA x 6.66 kWh/LPA x 0.76 gas share x 0.8 fuel-to-heat x 10 % recovery;
        sites and capacities: Wikipedia distillery articles (data/siting/distilleries_wikipedia.json)
      - waste-water treatment works (low grade, mean 12.3 C, water-source heat pump): BRE's 24 sites average
        0.66 kWh per m3 of effluent (318,905 MWh / (24 x 55,200 m3/d x 365)); flow = load (p.e.) x 0.2 m3/p.e./d
        (to source); sites: EEA Waterbase UWWTD via EMODnet (data/siting/uwwtp_scotland_emodnet.json), latest
        report per works, load capped at the works' capacity
  * Wind: Global Wind Atlas 3 (DTU / World Bank, CC BY 4.0) mean wind speed rasters at 50 and 100 m (~250 m grid),
    interpolated to the hub height with the power law between the two layers
  * Logistics: road distance to the Scottish supermarket regional distribution centres (all in the Central Belt)
"""
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "siting"
GWA_DIR = Path.home() / ".cache" / "gwa"

# BRE (2020) factors
DIST_KWH_PER_LPA = 6.66
DIST_GAS, DIST_FUEL2HEAT, DIST_RECOVERY = 0.76, 0.8, 0.10
WWTP_KWH_PER_M3 = 318_905e3 / (24 * 55_200 * 365)
WWTP_M3_PER_PE_DAY = 0.2            # to source (UK dry-weather flow per population equivalent)

# Supermarket RDCs (all Central Belt). Coordinates from the published addresses (approximate to the estate).
RDC = {
    "Tesco Livingston (Carnegie Rd, EH54 8TB)": (55.879, -3.560),
    "Asda Grangemouth (Earls Rd, FK3 8XG)": (56.012, -3.712),
    "Sainsbury's East Kilbride (Langlands Park)": (55.746, -4.169),
    "Morrisons Bellshill (Righead Ind. Est.)": (55.823, -4.038),
    "Aldi Bathgate (West Lothian)": (55.893, -3.613),
    "Lidl Eurocentral (ML1 4YF)": (55.838, -3.937),
    "Co-op Newhouse (M8 J6)": (55.839, -3.904),
}


class GWA:
    """Global Wind Atlas mean wind speed lookup (EPSG:4326 GeoTIFF)."""

    def __init__(self):
        import tifffile
        self.layers = {}
        for h in (50, 100):
            with tifffile.TiffFile(GWA_DIR / f"GBR_wind-speed_{h}m.tif") as tf:
                p = tf.pages[0]
                tags = {t.name: t.value for t in p.tags.values()}
                self.layers[h] = (p.asarray(), tags["ModelPixelScaleTag"], tags["ModelTiepointTag"])

    def at(self, lat, lon, h, r_cells=0):
        a, sc, tp = self.layers[h]
        c, r = int((lon - tp[3]) / sc[0]), int((tp[4] - lat) / sc[1])
        win = a[max(0, r - r_cells):r + r_cells + 1, max(0, c - r_cells):c + r_cells + 1]
        return float(np.nanmax(win)) if r_cells else float(a[r, c])

    def hub(self, lat, lon, hub_m, r_cells=0):
        v50, v100 = self.at(lat, lon, 50, r_cells), self.at(lat, lon, 100, r_cells)
        alpha = math.log(v100 / v50) / math.log(2.0)
        return v50 * (hub_m / 50.0) ** alpha, alpha


def haversine_km(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    d = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(d))


def distilleries():
    rows = json.loads((DATA / "distilleries_wikipedia.json").read_text())
    # supplement (sourced capacities/coordinates missing from the articles); same-site distilleries are merged
    sup = {r["name"]: r for r in json.loads((DATA / "distilleries_supplement.json").read_text())}
    rows = [dict(r, **{k: sup[r["name"]][k] for k in ("lpa", "lat", "lon")}) if r["name"] in sup else r for r in rows]
    girvan = next(r for r in rows if r["name"] == "Girvan distillery")
    ailsa = next(r for r in rows if r["name"] == "Ailsa Bay distillery")
    girvan["lpa"] = girvan["lpa"] + ailsa["lpa"]
    girvan["name"] = "Girvan + Ailsa Bay distilleries"
    ailsa["lpa"] = None
    out = []
    for r in rows:
        if not (r.get("lat") and r.get("lpa")):
            continue
        gwh = r["lpa"] * DIST_KWH_PER_LPA * DIST_GAS * DIST_FUEL2HEAT * DIST_RECOVERY / 1e6
        out.append(dict(name=r["name"], kind="distillery", lat=r["lat"], lon=r["lon"], heat_GWh=gwh, grade="direct",
                        T_C=80.0, size=r["lpa"], size_unit="LPA"))
    return out


def wwtps():
    rows = json.loads((DATA / "uwwtp_scotland_emodnet.json").read_text())
    latest = {}
    for r in rows:
        k = r["uwwcode"]
        if k not in latest or r["year"] > latest[k]["year"]:
            latest[k] = r
    out = []
    for r in latest.values():
        load = float(r["loadent_pe"] or 0)
        cap = float(r["capacit_pe"] or 0)
        pe = min(load, cap) if cap > 0 else load
        if pe <= 0:
            continue
        gwh = pe * WWTP_M3_PER_PE_DAY * 365 * WWTP_KWH_PER_M3 / 1e6
        out.append(dict(name=r["uwwname"].replace("Â", "").replace("\xa0", " ").strip(), kind="wwtp",
                        lat=r["latitude"], lon=r["longitude"], heat_GWh=gwh, grade="low", T_C=12.3, size=pe,
                        size_unit="p.e."))
    return out


GAS_KG_CO2_PER_KWH = 0.18290       # DESNZ 2025 GHG conversion factors, natural gas (gross CV), kg CO2 per kWh
PAPER_THERMAL, IND_FUEL2HEAT, IND_RECOVERY = 0.51, 0.8, 0.10   # BRE (2020) after McKenna & Norman (2010)


def industrial():
    """SEPA SPRI 2023 sites with reported CO2 to air: paper/board mills (BRE paper method: fuel from CO2, x 0.51
    thermal, x 10 % recovery) and food/drink, rendering and AD sites (BRE industrial method: x 0.8 fuel-to-heat,
    x 10 %). Distilleries are excluded here (covered by capacity); their SPRI-implied heat is kept as a check."""
    import pandas as pd
    from pyproj import Transformer
    f = DATA / "spri_2023_full.xlsx"
    R = pd.read_excel(f, "Returns").drop_duplicates("NIC").set_index("NIC")
    P = pd.read_excel(f, "Pollutants")
    R["co2_t"] = P[(P.POLLUTANT_NAME == "Carbon dioxide") & (P.MEDIUM == "Air")].groupby("NIC").TOTAL_RELEASE.sum() / 1e3
    tr = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
    out, checks = [], {}
    for nic, r in R.dropna(subset=["co2_t", "SITE_X_COORD"]).iterrows():
        desc, name = str(r["Activity code description"]), str(r.SITE_NAME)
        fuel_kwh = r.co2_t * 1e3 / GAS_KG_CO2_PER_KWH
        lon, lat = tr.transform(r.SITE_X_COORD, r.SITE_Y_COORD)
        if "distill" in name.lower() or "dist," in name.lower():
            checks[name] = fuel_kwh * IND_FUEL2HEAT * IND_RECOVERY / 1e6
            continue
        if "paper and board" in desc or "production of pulp" in desc:
            kind, gwh, T = "paper_board", fuel_kwh * PAPER_THERMAL * IND_RECOVERY / 1e6, 150.0
        elif any(k in desc for k in ("Vegetable raw", "Animal raw", "milk", "Slaughter", "animal carcasses")):
            kind, gwh, T = "food_drink_ad", fuel_kwh * IND_FUEL2HEAT * IND_RECOVERY / 1e6, 80.0
        else:
            continue
        out.append(dict(name=name, kind=kind, lat=lat, lon=lon, heat_GWh=gwh, grade="direct", T_C=T, size=r.co2_t,
                        size_unit="t CO2 (SPRI 2023)"))
    return out, checks


def candidates(hub_m=45.0, min_heat_GWh=1.0):
    g = GWA()
    out = []
    ind, _ = industrial()
    for s in distilleries() + wwtps() + ind:
        if s["heat_GWh"] < min_heat_GWh:
            continue
        v, alpha = g.hub(s["lat"], s["lon"], hub_m)
        v_best, _ = g.hub(s["lat"], s["lon"], hub_m, r_cells=8)       # best cell within ~2 km
        d = [haversine_km((s["lat"], s["lon"]), c) for c in RDC.values()]
        out.append(dict(s, wind_hub=v, wind_hub_best2km=v_best, shear_alpha=alpha, rdc_km_crow=float(np.mean(d))))
    return out


# ---------------------------------------------------------------- logistics (site -> Central Belt RDCs)
# DfT TAG data book v2.03 (May 2026), 2023 prices: OGV2 diesel fuel cost L = a/v + b + c v + d v^2 p/km (Table A1.3.12,
# work, excl. VAT, 2026 row); non-fuel 18.187 p/km (A1.3.14); OGV working time GBP 86.476/h factor cost (A1.3.1,
# driver + vehicle). Load 12.13 t = DESNZ 2025 refrigerated artic (>33t) average laden 1.08051 kg/km / 0.08908 kg/tkm.
# Carbon DESNZ 2025: 0.08908 + WTT 0.02086 kg CO2e/tkm. Electric HGV: ICCT (Aug 2025) 91 BEV tractor-trailers,
# 0.92-1.50 kWh/km, 65 % less energy than diesel; at DESNZ 2025 grid 0.245 kg/kWh vs diesel -> factor 0.27 of diesel.
OGV2_FUEL = (611.8772, 31.7759, -0.2105, 0.0013)
OGV2_NONFUEL_P_KM = 18.187
OGV_TIME_GBP_H = 86.476
LOAD_T = 1.08051 / 0.08908
REEFER_KG_TKM = 0.08908 + 0.02086
EHGV_FACTOR = 0.27
RETURN_EMPTY = 2.0                   # cost of the trip back counted (no backhaul assumed)


def logistics(c):
    """GBP/kg and kg CO2e/kg to deliver to the RDCs (mean over the seven), diesel and electric."""
    km = c["rdc_road_km_mean"]
    hours = [h for h in c["rdc_road_h"] if h]
    v = km / (sum(hours) / len(hours))
    a, b, cc, d = OGV2_FUEL
    p_km = (a / v + b + cc * v + d * v * v) + OGV2_NONFUEL_P_KM + OGV_TIME_GBP_H * 100 / v
    gbp_kg = RETURN_EMPTY * km * p_km / 100 / (LOAD_T * 1000)
    kg_kg = km * REEFER_KG_TKM / 1000
    return dict(road_km=km, speed_kmh=v, gbp_kg=gbp_kg, kg_kg_diesel=kg_kg, kg_kg_ehgv=kg_kg * EHGV_FACTOR,
                p_per_vkm=p_km)
