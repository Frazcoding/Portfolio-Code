"""lca/greenhouse.py with the thesis preset must reproduce sim/annual_sim.py (reference_original.json).

Run: python tests/test_reproduce.py [air ground water]   (each source takes about a minute)
"""
import json
import sys
from pathlib import Path

import numpy as np

LCA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LCA))
import config  # noqa: E402
import greenhouse  # noqa: E402

REF = json.loads((Path(__file__).with_name("reference_original.json")).read_text())
RTOL = 1e-9


def check(source):
    H, acc, wx, gr, meta, _ = greenhouse.simulate(config.thesis(source))
    ref = REF[source]["sums"]
    bad = []
    for k, v in ref.items():
        got = float(np.sum(H[k]))
        if not np.isclose(got, v, rtol=RTOL, atol=1e-9):
            bad.append(f"{k}: {got} vs {v}")
    first = np.allclose(H["T_air_in"][:48], REF[source]["T_air_in_first"], rtol=RTOL)
    print(f"{source}: {len(ref) - len(bad)}/{len(ref)} annual sums match, first 48 h {'match' if first else 'DIFFER'}")
    for b in bad:
        print("   ", b)
    return not bad and first


if __name__ == "__main__":
    ok = all([check(s) for s in sys.argv[1:] or ["air", "ground", "water"]])
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
