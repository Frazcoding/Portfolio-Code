"""R10 private-wire screen: operating wind turbines within RADIUS_KM of each shortlisted site (OpenStreetMap via the
Overpass API: power=generator + generator:source=wind). OSM is volunteered data (incomplete; no ownership or contract
status); it shows where a private wire is physically plausible, not that a farm would sign. Writes
data/siting/wind_nearby.json."""
import json
import math
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
RADIUS_KM = 5.0
URLS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter")
OUTF = HERE / "data" / "siting" / "wind_nearby.json"


def km(a, b, c, d):
    p = math.pi / 180
    h = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def query(lat, lon):
    q = f"""[out:json][timeout:60];
    (node["power"="generator"]["generator:source"="wind"](around:{RADIUS_KM * 1000:.0f},{lat},{lon});
     way["power"="generator"]["generator:source"="wind"](around:{RADIUS_KM * 1000:.0f},{lat},{lon}););
    out center tags;"""
    for k in range(8):
        try:
            r = requests.post(URLS[k % 2], data={"data": q}, timeout=120,
                              headers={"User-Agent": "cea-glasshouse-study/1.0 (research)", "Accept": "application/json"})
            if r.status_code == 200:
                return r.json()["elements"]
        except requests.RequestException:
            pass
        time.sleep(15 * (k + 1))
    raise RuntimeError("Overpass unavailable")


def kw(tags):
    v = tags.get("generator:output:electricity", "")
    try:
        n, u = v.split()
        return float(n) * {"W": 1e-3, "kW": 1, "MW": 1e3}.get(u, 0)
    except ValueError:
        return None


if __name__ == "__main__":
    SL = json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())
    out = json.loads(OUTF.read_text()) if OUTF.exists() else {}      # resumable
    for s in SL:
        if s["site_key"] in out:
            continue
        el = query(s["lat"], s["lon"])
        t = []
        for e in el:
            la, lo = (e["lat"], e["lon"]) if "lat" in e else (e["center"]["lat"], e["center"]["lon"])
            t.append(dict(km=km(s["lat"], s["lon"], la, lo), kw=kw(e.get("tags", {})),
                          name=e.get("tags", {}).get("name", "")))
        t.sort(key=lambda x: x["km"])
        big = [x for x in t if (x["kw"] or 0) >= 500]
        out[s["site_key"]] = dict(name=s["name"], n=len(t), n_big=len(big), nearest_km=t[0]["km"] if t else None,
                                  nearest_big_km=big[0]["km"] if big else None,
                                  mw_known=sum(x["kw"] or 0 for x in t) / 1e3, turbines=t[:20])
        print(f"{s['name'][:30]:30} turbines {len(t):3d}  >=500kW {len(big):3d}  nearest "
              f"{out[s['site_key']]['nearest_km'] or float('nan'):.1f} km  nearest big "
              f"{out[s['site_key']]['nearest_big_km'] or float('nan'):.1f} km  known {out[s['site_key']]['mw_known']:.1f} MW",
              flush=True)
        OUTF.write_text(json.dumps(out, indent=1))
        time.sleep(5)
