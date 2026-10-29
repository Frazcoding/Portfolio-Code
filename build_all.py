"""build_all.py
Rebuild all eight annual simulations, their viewers and the portfolio hub.

    python build_all.py            # regenerate viewers, re-using existing simulation results
    python build_all.py --force    # re-run every annual simulation first (several minutes)
    python build_all.py --models   # also rebuild every Blender model (needs Blender 5.x)

Real weather, grid and texture assets are cached in simcore/cache and assets/ (fetch with assets/fetch_assets.py).
"""
import subprocess
import sys
from pathlib import Path

import make_beng_cea
import make_building_retrofit
import make_carbon_wlc
import make_green_hydrogen
import make_heatpump_sim
import make_index_hub
import make_industrial_hthp
import make_plantpost
import make_uniboat

BASE = Path(__file__).resolve().parent
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
MODELS = [
    ("Heat-Pump-Simulation", "create_heatpump_asset.py"),
    ("High-Temp-Waste-Heat-Recovery", "create_industrial_asset.py"),
    ("Building-Heatpump-Retrofit", "create_retrofit_asset.py"),
    ("BEng-CEA-Heatpump", "create_greenhouse_asset.py"),
    ("Plantpost-Urban-Infrastructure-Modelling", "create_plantpost_asset.py"),
    ("PyPsa-Green-Hydrogen-Microgrid", "create_hydrogen_asset.py"),
    ("UniBoat-Powertrain-Cooling", "create_uniboat_asset.py"),
    ("Whole-Carbon-Lifecycle-Assessment", "create_wlc_asset.py"),
]


def main():
    force = "--force" in sys.argv
    if "--models" in sys.argv:
        for folder, script in MODELS:
            print("Blender:", folder)
            subprocess.run([BLENDER, "-b", "--factory-startup", "-P", script], cwd=BASE / folder, check=True,
                           stdout=subprocess.DEVNULL)
    for mod in (make_heatpump_sim, make_industrial_hthp, make_building_retrofit, make_beng_cea, make_plantpost,
                make_green_hydrogen, make_uniboat, make_carbon_wlc):
        print(mod.__name__)
        mod.generate(force=force)
    make_index_hub.generate()
    print("All viewers generated.")


if __name__ == "__main__":
    main()
