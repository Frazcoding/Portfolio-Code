"""Free-form greenhouse geometry, light and quantities for the shape optimisation.

A design is `n_spans` identical spans side by side, each with a free cross-section profile z(x) (a polyline of
points across the span, any shape: pitched, arched, sawtooth, asymmetric, mono-pitch), extruded along `length`, with
the ridge lines at any compass bearing. Venlo, gothic arch, wide span and the asymmetric earth-sheltered 'Chinese
solar greenhouse' are all special cases of the profile plus which faces are opaque.

From a design this module derives:
  * facets (area, tilt, azimuth, glazed/opaque) for roof, side walls and gable ends
  * hourly light transmitted to the floor (W/m2 floor): Hay-Davies plane-of-array irradiance per facet
    (simcore.solar.poa) x angle-dependent transmission (Fresnel, N layers; Duffie & Beckman, Solar Engineering of
    Thermal Processes, 4th ed., eqs. 5.1.4-5.3.1, diffuse at the Brandemuehl & Beckman effective angles) calibrated to
    the product's hemispherical transmission, x (1 - frame shading) from the frame members of this design
  * heat-loss terms (UA of glazed roof, glazed walls, opaque elements), volume, glazed area
  * floor usable for a high-wire crop (interior height >= h_min)
  * material quantities for costing and embodied carbon (glazing by type, insulated panel, gutters, glazing bars,
    columns, foundations, floor) -- the steel tonnage is a placeholder scaling until the structural design is done

Limitations (stated, not hidden): light between neighbouring spans is not ray-traced (inter-span shading of low sun is
ignored), and the light distribution inside is uniform. Opaque heavy walls are treated as insulated panels without
thermal storage until a wall-mass node is added.
"""
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simcore import solar  # noqa: E402

# Glazing products. U: whole-cover W/m2K; t_hem: hemispherical (diffuse) transmission of the glazing alone (NEN 2675
# THem), or t_normal where the source gives only a normal-incidence value; n, layers: for the Fresnel angular shape; pane_w: glazing-bar spacing (m); bar_w: bar width
# seen from below (m). Sources in data/input_register.csv.
GLAZING = {
    "etfe3": dict(U=1.9, t_normal=0.857, n=1.403, layers=3, pane_w=3.0, bar_w=0.06,
                  note="Architen 3-layer cushion U 1.8 (ISO 6946) + frame; 0.95 per layer (upper value); n DuPont Tefzel"),
    "dbl_ar_lowe": dict(U=2.0, t_hem=0.785, n=1.526, layers=2, pane_w=1.25, bar_w=0.05,
                        note="Hemming et al. 2011 Acta Hort 893: k 2.4/7.6 of single glass, THem 78.5 %"),
    "dbl_ar": dict(U=2.9, t_hem=0.84, n=1.526, layers=2, pane_w=1.25, bar_w=0.05,
                   note="Hemming et al. 2011: k 3.6/7.6 of single glass, THem 83-85 %"),
    "single_2ar": dict(U=6.2, t_hem=0.894, n=1.526, layers=1, pane_w=1.25, bar_w=0.05,
                       note="ASABE EP406.4 single glass; AGC Fountain 2xAR THem 89.4 %"),
    "single_plain": dict(U=6.2, t_hem=0.82, n=1.526, layers=1, pane_w=1.25, bar_w=0.05,
                         note="Traditional single horticultural glass, THem 82-83 % (Hemming et al. 2011); Dutch yield ref"),
    "pc_twin": dict(U=3.4, t_normal=0.80, n=1.585, layers=2, pane_w=1.05, bar_w=0.05,
                    note="ASABE EP406.4 PC double-wall 3.2-3.6; transmission ~80 % (BC Greenhouses guide, normal)"),
}
OPAQUE_U = 0.25            # insulated sandwich panel (to source: manufacturer datasheet, ~100 mm PIR)


def _fresnel_tau(theta_deg, n, N):
    """Reflection-only transmittance of N parallel covers at incidence theta (Duffie & Beckman eq. 5.1.4, 5.1.8)."""
    t1 = np.radians(np.clip(theta_deg, 0.0, 89.9))
    t2 = np.arcsin(np.sin(t1) / n)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(t1 < 1e-6, ((n - 1) / (n + 1)) ** 2, np.sin(t2 - t1) ** 2 / np.sin(t2 + t1) ** 2)
        rp = np.where(t1 < 1e-6, ((n - 1) / (n + 1)) ** 2, np.tan(t2 - t1) ** 2 / np.tan(t2 + t1) ** 2)
    return 0.5 * ((1 - rs) / (1 + (2 * N - 1) * rs) + (1 - rp) / (1 + (2 * N - 1) * rp))


def _hem(n, N):
    th = np.linspace(0, 89.9, 400)
    w = 2 * np.sin(np.radians(th)) * np.cos(np.radians(th))
    return float(np.trapezoid(_fresnel_tau(th, n, N) * w, np.radians(th)))


def tau_angle(g, theta_deg):
    """Transmission at incidence theta, scaled to the product's hemispherical (t_hem) or normal (t_normal) value."""
    ref = _hem(g["n"], g["layers"]) if "t_hem" in g else float(_fresnel_tau(0.0, g["n"], g["layers"]))
    return g.get("t_hem", g.get("t_normal")) * _fresnel_tau(theta_deg, g["n"], g["layers"]) / ref


@dataclass
class Design:
    length: float = 100.0              # m, along the ridges
    n_spans: int = 12
    span_w: float = 8.0                # m
    profile: list = field(default_factory=lambda: [(0.0, 0.0), (0.5, 1.6), (1.0, 0.0)])  # (x/span, z above gutter, m)
    gutter_h: float = 7.0              # m, height of the profile's zero line (side-wall height)
    ridge_bearing: float = 0.0         # deg clockwise from north of the ridge lines (0: ridges N-S, faces E/W)
    glazing: str = "etfe3"
    opaque_north: bool = False         # facets facing within +-60 deg of north are insulated panel (roof and walls)
    opaque_min_tilt: float = 30.0      # ...only if steeper than this (so near-flat roof stays glazed)
    bay_w: float = 4.5                 # m, column spacing along the ridges
    h_min: float = 4.5                 # m, interior height needed by a high-wire crop (wire height + clearance)
    path_frac: float = 0.06            # share of usable floor lost to main path and headlands (to source)

    @property
    def width(self):
        return self.n_spans * self.span_w

    @property
    def floor(self):
        return self.length * self.width


def _facets(d):
    """(area, tilt_deg, azimuth_deg, kind) with kind in roof/wall/gable."""
    out = []
    pts = d.profile
    b = d.ridge_bearing
    for (x0, z0), (x1, z1) in zip(pts[:-1], pts[1:]):
        dx, dz = (x1 - x0) * d.span_w, z1 - z0
        if dx <= 0:
            continue
        s = math.hypot(dx, dz)
        tilt = math.degrees(math.atan2(abs(dz), dx))
        # a rising segment (dz > 0, moving +x) faces -x; +x is bearing + 90
        az = (b - 90.0) % 360 if dz > 0 else (b + 90.0) % 360
        if abs(dz) < 1e-9:
            az = 180.0
        out.append((s * d.length * d.n_spans, tilt, az, "roof"))
    h0 = d.gutter_h + pts[0][1]
    h1 = d.gutter_h + pts[-1][1]
    out.append((h0 * d.length, 90.0, (b - 90.0) % 360, "wall"))
    out.append((h1 * d.length, 90.0, (b + 90.0) % 360, "wall"))
    prof_area = d.gutter_h * d.span_w + sum(0.5 * (z0 + z1) * (x1 - x0) * d.span_w
                                           for (x0, z0), (x1, z1) in zip(pts[:-1], pts[1:]))
    for az in (b % 360, (b + 180.0) % 360):
        out.append((prof_area * d.n_spans, 90.0, az, "gable"))
    return out, prof_area


def _faces_north(az, tilt, d):
    return d.opaque_north and tilt >= d.opaque_min_tilt and min(abs(az - 0.0), 360 - abs(az - 0.0)) <= 60.0


def analyse(d, wx, lat, lon, wall_light=1.0):
    """Geometry, hourly light and heat-loss terms for design d at a site (wx: simcore.weather frame)."""
    g = GLAZING[d.glazing]
    facets, prof_area = _facets(d)
    zen, az_sun, doy = solar.position(wx["time"], lat, lon)
    ghi, dni, dhi = (wx[k].to_numpy() for k in ("ghi", "dni", "dhi"))
    I_floor = np.zeros(len(wx))
    ua_roof_gl = a_roof_gl = ua_wall_gl = a_wall_gl = ua_opaque = a_opaque = 0.0
    # Roof: the faces of a multi-span roof shade and screen each other, so together they cannot intercept more than
    # falls on the horizontal footprint. Each face keeps its own incidence angle (for transmission); the intercepted
    # beam and diffuse are scaled down to the footprint totals when the faces' sum exceeds them. Walls add their own.
    rb, rd = [], []
    Sb = np.zeros(len(wx))
    Sd = np.zeros(len(wx))
    for area, tilt, az, kind in facets:
        opaque = _faces_north(az, tilt, d)
        if opaque:
            ua_opaque += OPAQUE_U * area
            a_opaque += area
            continue
        beam, diff, grnd, aoi = solar.poa(ghi, dni, dhi, zen, az_sun, doy, tilt, az)
        th_sky = 59.7 - 0.1388 * tilt + 0.001497 * tilt ** 2          # Brandemuehl & Beckman (1980)
        th_gnd = 90.0 - 0.5788 * tilt + 0.002693 * tilt ** 2
        if kind == "roof":
            rb.append(area * beam * tau_angle(g, aoi))
            rd.append(area * diff * tau_angle(g, th_sky))
            Sb += area * beam
            Sd += area * diff
        else:
            I_floor += wall_light * area * (beam * tau_angle(g, aoi) + diff * tau_angle(g, th_sky)
                                            + grnd * tau_angle(g, th_gnd))
        if kind == "roof":
            ua_roof_gl += g["U"] * area
            a_roof_gl += area
        else:
            ua_wall_gl += g["U"] * area
            a_wall_gl += area
    beam_h = np.clip(ghi - dhi, 0, None) * d.floor
    kb = np.where(Sb > beam_h, beam_h / np.maximum(Sb, 1e-9), 1.0)
    kd = np.where(Sd > dhi * d.floor, dhi * d.floor / np.maximum(Sd, 1e-9), 1.0)
    I_floor += kb * sum(rb, np.zeros(len(wx))) + kd * sum(rd, np.zeros(len(wx)))
    # frame shading: glazing bars at pane spacing across the roof, one gutter per span valley, a truss/purlin line
    # per bay; projected widths over the floor (to replace with the structural design's member sizes)
    roof_run = sum(a for a, t, _, k in facets if k == "roof") / (d.length * d.n_spans)   # m of roof per m of span
    bars = g["bar_w"] / g["pane_w"] * roof_run / d.span_w
    gutters = 0.25 / d.span_w
    trusses = 0.12 / d.bay_w
    shade = min(0.5, bars + gutters + trusses)
    I_floor = I_floor * (1 - shade) / d.floor
    # usable floor for a high-wire crop: share of the span cross-section with interior height >= h_min
    xs = np.linspace(0, 1, 401)
    zs = d.gutter_h + np.interp(xs, [p[0] for p in d.profile], [p[1] for p in d.profile])
    usable = float((zs >= d.h_min).mean()) * (1 - d.path_frac)
    volume = prof_area * d.n_spans * d.length
    return dict(I_floor=I_floor, shade=shade, ua_roof_glazed=ua_roof_gl, a_roof_glazed=a_roof_gl,
                ua_wall_glazed=ua_wall_gl, a_wall_glazed=a_wall_gl, ua_opaque=ua_opaque, a_opaque=a_opaque,
                volume=volume, floor=d.floor, usable_frac=usable, prof_area=prof_area,
                roof_area=sum(a for a, _, _, k in facets if k == "roof"),
                wall_area=sum(a for a, _, _, k in facets if k != "roof"), facets=facets)


def quantities(d, a):
    """Material quantities (per design) for costing and embodied carbon. Structure is a placeholder scaling."""
    glazed = a["a_roof_glazed"] + a["a_wall_glazed"]
    n_cols = (d.n_spans + 1) * (int(math.ceil(d.length / d.bay_w)) + 1)
    return dict(glazing_m2=glazed, glazing_type=d.glazing, opaque_panel_m2=a["a_opaque"],
                gutter_m=(d.n_spans + 1) * d.length, glazing_bar_m=glazed / GLAZING[d.glazing]["pane_w"],
                columns=n_cols, column_m=n_cols * d.gutter_h, floor_m2=d.floor, perimeter_m=2 * (d.length + d.width),
                volume_m3=a["volume"])


def to_config(d, a, cfg):
    """SiteConfig for design d (analysis a) on top of a crop/system config: footprint, glazed areas and U, opaque UA,
    volume. Light goes in separately as a['I_floor'] (simulate_fast(..., i_floor=...))."""
    from dataclasses import replace
    g = GLAZING[d.glazing]
    u_roof = a["ua_roof_glazed"] / a["a_roof_glazed"] if a["a_roof_glazed"] > 0 else g["U"]
    u_wall = a["ua_wall_glazed"] / a["a_wall_glazed"] if a["a_wall_glazed"] > 0 else g["U"]
    geo = replace(cfg.geometry, length=d.length, width=d.width, gutter_height=d.gutter_h,
                  a_roof_override=a["a_roof_glazed"], a_wall_override=a["a_wall_glazed"], volume_override=a["volume"])
    env = replace(cfg.envelope, u_cover=u_roof, u_wall=u_wall, u_north_wall=None, ua_extra=a["ua_opaque"])
    return replace(cfg, geometry=geo, envelope=env)
