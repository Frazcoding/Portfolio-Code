"""Monthly UK imports by origin (UN Comtrade public API, freq M) for the seasonality comparison, same filters as
fetch_imports_data.py. Writes data/imports_monthly.csv (crop, year, month, origin, tonnes, value, GBP/kg CIF).
FX: ECB reference rates via Frankfurter, monthly mean USD->GBP.
"""
import csv
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fetch_imports_data import HS, get  # noqa: E402

YEARS = (2023, 2024, 2025)
CROPS = sys.argv[1:] or ["tomato", "cucumber"]
URL = ("https://comtradeapi.un.org/public/v1/preview/C/M/HS?reporterCode=826&period={p}&flowCode=M&cmdCode={hs}"
       "&includeDesc=true")
FXM = "https://api.frankfurter.dev/v1/{y}-{m:02d}-01..{y}-{m:02d}-28?base=USD&symbols=GBP"


def main():
    fx = {}
    for y in YEARS:
        for m in range(1, 13):
            fx[(y, m)] = statistics.mean(r["GBP"] for r in get(FXM.format(y=y, m=m))["rates"].values())
    rows = []
    for crop in CROPS:
        for y in YEARS:
            for month in range(1, 13):            # preview endpoint: one period per call, rate limited
                per = f"{y}{month:02d}"
                for attempt in range(6):
                    try:
                        data = get(URL.format(p=per, hs=HS[crop]))["data"]
                        break
                    except Exception:
                        time.sleep(10 * (attempt + 1))
                time.sleep(6)
                agg = {}
                for r in data:
                    if r["customsCode"] != "C00" or r["motCode"] != 0 or r["partner2Code"] != 0 or not r["netWgt"]:
                        continue
                    m = int(str(r["period"])[4:6])
                    a = agg.setdefault((m, r["partnerISO"]), {"origin": r["partnerDesc"], "kg": 0.0, "usd": 0.0})
                    a["kg"] += r["netWgt"]
                    a["usd"] += r["primaryValue"]
                for (m, iso3), a in agg.items():
                    rows.append(dict(crop=crop, year=y, month=m, origin=a["origin"], iso3=iso3,
                                     tonnes=round(a["kg"] / 1e3, 1), value_usd=round(a["usd"]),
                                     gbp_per_kg_cif=round(a["usd"] * fx[(y, m)] / a["kg"], 3)))
    # default crops keep the original file; other crops (business-plan diversification, 2026-10-05) go to their own file
    name = "imports_monthly.csv" if set(CROPS) <= {"tomato", "cucumber"} else "imports_monthly_diversify.csv"
    out = HERE / "data" / name
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
