"""Step 6 data pull: UK imports by origin for avocado and the comparison crops (UN Comtrade, HS codes in crops.py)
and USD->GBP annual mean rates (ECB via Frankfurter). Writes data/imports_trade.csv (one row per crop, year, origin).
Re-run to refresh; the CSV is the record used by imports.py and crop_imports.py.
"""
import csv
import json
import statistics
import time
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crops  # noqa: E402
YEARS = (2023, 2024, 2025)
COMTRADE = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=826&period={y}&flowCode=M"
            "&cmdCode={hs}&includeDesc=true")
HS = {"avocado": "080440", **{k: c["hs"] for k, c in crops.CROPS.items()}}
FX = "https://api.frankfurter.dev/v1/{y}-01-01..{y}-12-31?base=USD&symbols=GBP"
SOURCE = ("UN Comtrade public API, reporter United Kingdom (826), imports, HS {hs}, partner = country of origin as "
          "reported by HMRC; value is CIF")
FX_SOURCE = "ECB reference rates via api.frankfurter.dev, mean of daily USD->GBP over the calendar year"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main():
    rows = []
    fx = {y: statistics.mean(r["GBP"] for r in get(FX.format(y=y))["rates"].values()) for y in YEARS}
    for crop, hs in HS.items():
        for y in YEARS:
            data = get(COMTRADE.format(y=y, hs=hs))["data"]
            time.sleep(4)  # public endpoint is rate limited
            agg = {}
            for r in data:  # lettuce spans two HS lines: sum them per origin
                if r["customsCode"] != "C00" or r["motCode"] != 0 or r["partner2Code"] != 0 or not r["netWgt"]:
                    continue
                a = agg.setdefault(r["partnerISO"], {"origin": r["partnerDesc"], "kg": 0.0, "usd": 0.0})
                a["kg"] += r["netWgt"]
                a["usd"] += r["primaryValue"]
            for iso3, a in agg.items():
                rows.append({
                    "crop": crop, "year": y, "origin": a["origin"], "iso3": iso3, "tonnes": round(a["kg"] / 1000, 1),
                    "value_usd": round(a["usd"]), "usd_per_kg": round(a["usd"] / a["kg"], 3),
                    "gbp_per_usd": round(fx[y], 4), "gbp_per_kg_cif": round(a["usd"] * fx[y] / a["kg"], 3),
                    "source": SOURCE.format(hs=hs), "fx_source": FX_SOURCE,
                })
    rows.sort(key=lambda r: (r["crop"], r["year"], -r["tonnes"]))
    out = HERE / "data" / "imports_trade.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
