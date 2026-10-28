# Sharing the simulator with assessors

The simulator has a static build that needs no server and no install: the Python model runs in the viewer's browser
(Pyodide), and routes, place search and site screening call the public OpenStreetMap services from the browser. Any
static web host can serve it.

## 1. Build

```
uv run python tools/build_static.py
```

This writes `dist/` (committed to the repository for direct Git-to-Pages deployment) and `ember-hub-simulator-web.zip`
(about 160 kB).

## 2. Put it online (pick one, each is free and takes a few minutes)

**Cloudflare Pages (via GitHub).** In Cloudflare Dashboard go to *Workers & Pages → Create → Pages → Connect to Git*,
select the `Ember-Hub-Simulator` repository, and configure:
- **Production branch:** `main`
- **Build command:** `python tools/build_static.py` (or leave blank — `dist/` is already committed)
- **Build output directory:** `dist`

*(Alternatively, under **Upload assets**, upload `ember-hub-simulator-web.zip` or `dist/` directly.)*

**Netlify Drop.** Go to https://app.netlify.com/drop, sign in (free account), and drag the `dist` folder onto
the page. Netlify gives you a link such as `https://<name>.netlify.app`. Under *Site configuration* you can rename it.
To update it, drag a new `dist` folder onto the site's *Deploys* page.

**GitHub Pages.** In *Settings → Pages* choose *Deploy from a branch* or *GitHub Actions* serving `dist/`.

Send the assessors the link. The first visit downloads the Python engine (about 25 MB, cached afterwards) and shows
a loading message for 10 to 20 seconds; after that every input change re-runs the model in about 0.3 s.

## What works in the shared version

Everything in the app except **Save run**, which writes run folders on disk and needs the server version
(`uv run ember-hub-simulator app`). Route changes and site screening need internet access to the public OSRM,
Nominatim and Overpass servers; if one is busy, the app says so and keeps the last result.

## Check before sending

```
python -m http.server -d dist 8800
```

Open http://localhost:8800, wait for *Ready*, change the headway and watch the fleet, the hub design and the costs
update. (Opening `dist/index.html` straight from the file system does not work: browsers block module scripts there.)
