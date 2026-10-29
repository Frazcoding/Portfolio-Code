# One-time setup of a new Windows machine for the glasshouse study (run from this lca folder in PowerShell):
#   powershell -ExecutionPolicy Bypass -File setup_machine.ps1
# Creates ~/.venvs/portfolio (Python 3.14 or 3.12) and ~/.venvs/greenlight (Python 3.12), downloads the Global Wind
# Atlas rasters (~120 MB) to ~/.cache/gwa, then runs the quick checks. Needs the Python launcher (py) with 3.12 and
# 3.14 (or 3.12 only) installed from python.org.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvs = Join-Path $HOME ".venvs"
New-Item -ItemType Directory -Force $venvs | Out-Null

$mainPy = "3.14"
try { py -3.14 -c "print()" | Out-Null } catch { $mainPy = "3.12" }
Write-Host "Main environment: Python $mainPy -> $venvs\portfolio"
if (-not (Test-Path "$venvs\portfolio\Scripts\python.exe")) { py -$mainPy -m venv "$venvs\portfolio" }
& "$venvs\portfolio\Scripts\python.exe" -m pip install --upgrade pip
& "$venvs\portfolio\Scripts\python.exe" -m pip install -r "$here\requirements.txt"

Write-Host "GreenLight environment: Python 3.12 -> $venvs\greenlight"
if (-not (Test-Path "$venvs\greenlight\Scripts\python.exe")) { py -3.12 -m venv "$venvs\greenlight" }
& "$venvs\greenlight\Scripts\python.exe" -m pip install --upgrade pip
& "$venvs\greenlight\Scripts\python.exe" -m pip install -r "$here\requirements-greenlight.txt"

$gwa = Join-Path $HOME ".cache\gwa"
New-Item -ItemType Directory -Force $gwa | Out-Null
foreach ($h in 100, 50) {
    $f = Join-Path $gwa "GBR_wind-speed_${h}m.tif"
    if (-not (Test-Path $f)) {
        Write-Host "Downloading Global Wind Atlas ${h} m raster"
        Invoke-WebRequest "https://globalwindatlas.info/api/gis/country/GBR/wind-speed/$h" -OutFile $f
    }
}

Write-Host "Checks"
Push-Location $here
& "$venvs\portfolio\Scripts\python.exe" tests\test_costing.py
& "$venvs\portfolio\Scripts\python.exe" -c "import site_opt, json; print('site model imports OK')"
& "$venvs\greenlight\Scripts\python.exe" -c "import greenlight; print('GreenLight', greenlight.__version__)"
Pop-Location
Write-Host "Done. Optional full checks: python tests\test_reproduce.py (~5 min), python tests\test_fast.py (~12 min)."
