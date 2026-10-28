"""Where simcore keeps downloaded data and computed caches (outside the repo and outside kDrive)."""
from __future__ import annotations

import os
from pathlib import Path


class Paths:
    """Cache location: ``$SIMCORE_CACHE`` if set, else the per-user local cache directory."""

    @staticmethod
    def cache() -> Path:
        env = os.environ.get("SIMCORE_CACHE")
        if env:
            root = Path(env)
        elif os.name == "nt":
            root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "simcore" / "cache"
        else:
            root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "simcore"
        root.mkdir(parents=True, exist_ok=True)
        return root
