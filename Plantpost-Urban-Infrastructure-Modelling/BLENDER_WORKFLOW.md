# Plantpost Blender workflow

`plantpost.blend` is the editable model. `plantpost.glb` is loaded by `viewer.html`; the two preview PNGs show summer and winter states in the browser. The documented dimensions, calculations and visual estimates are itemized in `MODEL_DIMENSIONS.md`.

Keep the names `ReservoirWater`, `Luminaire` and `PVCanopy` when editing. They are checked during `python build_all.py` and used by the viewer to bind water level and lamp state.

To re-export a manually edited `.blend` file:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' plantpost.blend --background --python export_plantpost_asset.py
```

`create_plantpost_asset.py` rebuilds the complete pilot model and overwrites manual edits. Run `python ..\build_all.py`, then `run_viewer.cmd` after exporting. Keep the server window open while using the viewer.
