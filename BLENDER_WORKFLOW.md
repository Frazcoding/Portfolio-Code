# Greenhouse Blender model

Open [greenhouse.blend](greenhouse.blend) in Blender to edit the 20 × 20 m greenhouse and plant skid. The `.blend` file is the editable source. `greenhouse.glb` is the browser asset; `greenhouse_preview.png` is a Blender render for visual review.

The footprint (20 × 20 m), eaves (5 m) and buffer volume (1,500 L) come from `CALCULATIONS_WHITE_PAPER.md`. Roof pitch, crop rows, compressor shapes and pipe routing are illustrative because the thermal model does not specify those details.

Keep the mesh object names `ThermalScreen` and `BufferTank`. The browser uses those names to bind the screen position and buffer temperature to simulation state. The generated viewer checks that both nodes exist in the `.glb` file. In calibrated CSV runs, these state variables are absent, so the screen is hidden and the tank uses a neutral colour.

After editing in Blender, export and render a new preview from this directory:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' greenhouse.blend --background --python export_greenhouse_asset.py
```

`create_greenhouse_asset.py` rebuilds the pilot model from scratch. Use it only when you want to discard manual Blender edits.

Run `python ..\build_all.py` to regenerate the viewer, then run `run_viewer.cmd`. The command starts a local web server so the page can load `greenhouse.glb`. Inspect the model from the top, front, and orbit views, and compare both calibrated and illustrative scenarios. The calibrated runs use actual model output; the illustrative scenarios demonstrate visual state changes.
