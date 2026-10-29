"""The final Temple Works hub design (Ember-Site-Selection, scripts/hub_design.py), imported by ``tools/export_design.py``.

Two variants on the real yards (HM Land Registry title 19736799, Savills yard plan):

* ``base`` (EMB-HUB-003): 8 single-depth drive-through lanes (no coach can be blocked in), 2 x 600 kW on an overhead
  gantry wired to lanes 1-4, 2,000 kVA NGED substation, wash bay, office + 2 rest cabins, 16 staff spaces,
  16 forward-only movements checked (min. clearance 0.58 m).
* ``expansion`` (EMB-HUB-005): 11 lanes on the same plot (+3), 22 movements checked.

The simulator picks the smallest variant with a lane for every coach (fleet incl. spare); above 11 coaches the site is
full. The designs exist for S1 only: for other sites the views show the S1 design for reference and feasibility rests on
the sheet's area check.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class HubDesign:
    """The imported design file (``data/temple_works_design.json``)."""

    data: dict

    @classmethod
    def load(cls, data_dir: Path) -> "HubDesign":
        return cls(json.loads((Path(data_dir) / "temple_works_design.json").read_text(encoding="utf-8")))

    @property
    def site_id(self) -> str:
        return self.data["site_id"]

    @property
    def capacity(self) -> int:
        return max(v["lanes"] for v in self.data["variants"])

    def variant_for(self, coaches: int) -> dict:
        """Smallest variant with one lane per coach (the largest if none has enough)."""
        for v in sorted(self.data["variants"], key=lambda v: v["lanes"]):
            if v["lanes"] >= coaches:
                return v
        return max(self.data["variants"], key=lambda v: v["lanes"])

    def layout(self, coaches: int, site_id: str, area_ok: bool) -> dict[str, Any]:
        """Payload for the views: the chosen variant plus the frame, the dead-run route and the fit flags."""
        v = self.variant_for(coaches)
        own = site_id == self.site_id
        return {
            **{k: v[k] for k in ("name", "drawing", "lanes", "slots", "queue", "features", "bounds")},
            "summary": {k: v["summary"][k] for k in ("stats", "clearances", "site_m2") if k in v["summary"]},
            "frame": self.data["frame"],
            "deadrun_route": self.data["deadrun_route"] if own else None,
            "site_specific": own,
            "capacity": self.capacity,
            "fits": (coaches <= v["lanes"]) if own else area_ok,
            "coaches": coaches,
        }
