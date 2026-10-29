"""Site configuration for the avocado greenhouse study: one dataclass drives geometry, location, climate and plant.

Every scale-dependent quantity in the original 400 m2 model is expressed per m2 of floor (or per unit of heat-pump
capacity) here, so `thesis(source)` reproduces sim/annual_sim.py and any other size is a change of inputs.
"""
import math
from dataclasses import dataclass, field, replace
from typing import Optional

THESIS_AREA = 400.0


@dataclass
class Geometry:
    length: float = 100.0              # m
    width: float = 100.0               # m
    gutter_height: float = 5.5         # m; dwarf avocado needs >= 5 m
    roof_slope_deg: float = 22.0       # Venlo roof pitch
    roof_width: float = 4.0            # m, width of one Venlo roof section (sets ridge rise)
    a_roof_override: Optional[float] = None
    a_wall_override: Optional[float] = None   # glazed wall area (design.py free-form shapes)
    volume_override: Optional[float] = None

    @property
    def area(self):
        return self.length * self.width

    @property
    def perimeter(self):
        return 2 * (self.length + self.width)

    @property
    def a_wall(self):
        """Side and gable walls to gutter height (gable triangles are counted in the roof rise volume only)."""
        if self.a_wall_override is not None:
            return self.a_wall_override
        return self.perimeter * self.gutter_height

    @property
    def a_roof(self):
        if self.a_roof_override is not None:
            return self.a_roof_override
        return self.area / math.cos(math.radians(self.roof_slope_deg))

    @property
    def volume(self):
        if self.volume_override is not None:
            return self.volume_override
        rise_mean = self.roof_width / 4 * math.tan(math.radians(self.roof_slope_deg))
        return self.area * (self.gutter_height + rise_mean)


@dataclass
class Envelope:
    u_cover: float = 3.0               # W/m2K, twin-wall PC (thesis value)
    tau_solar: float = 0.70            # cover + structure transmission of global radiation
    screen_u_factor: float = 0.55      # roof U multiplier with the energy screen closed: Ludvig Svensson energy saving
                                       # (Svensson method, closed vs no screen) LUXOUS 1243 43 %, XLS 10 47 % -> 0.55
    screen_below_C: float = 15.0       # screen closes at night below this outdoor temperature
    infiltration_ach: float = 0.5      # base air changes per hour (+ 0.05 per m/s wind)
    u_wall: Optional[float] = None     # W/m2K side/gable glazing; None = same as u_cover
    ua_extra: float = 0.0              # W/K of opaque insulated elements (design.py), no light, no condensation
    u_north_wall: Optional[float] = None  # W/m2K opaque insulated north wall (length side); None = glazed like the rest
    cover_t_from_u: bool = False       # inner cover temperature from U and ISO 6946 Rsi (0.10, upward flow);
                                       # False = thesis fixed formula. Matters for condensation (dehumidification)
    vent_ach: float = 6.0              # air changes per hour with the vents fully open, plus vent_ach_wind per m/s wind
    vent_ach_wind: float = 3.0         # (thesis values; GreenLight roof vents of 11.7 % of floor give ~24 at 3.5 m/s)
    vent_area_frac: float = 0.0        # roof vent area / floor area; > 0 switches vent_ach to the Vanthoor (2011) law:
    vent_cd: float = 0.75              #   f = u*frac*Cd/2*sqrt(|g h dT/(2 Tm) + Cw v^2|) m3/m2/s  (GreenLight, Katzin 2021)
    vent_cw: float = 0.09              #   Cd discharge coeff, Cw wind pressure coeff, h vertical vent dimension (m)
    vent_h: float = 1.3
    floor_frac_hourly: Optional[object] = None  # hourly floor light share (transp.floor_light_frac of the LAI); None = floor_sol_frac
    soil_layers: bool = False          # GreenLight/Vanthoor floor: thin floor + 5 soil layers (0.04-0.64 m) over the ISO 13370
                                       # deep conductance U_b, instead of one 0.15 m floor node (thesis)
    transp_hourly: Optional[tuple] = None  # (transp_rad[h], transp_vpd[h]) hourly arrays from transp.hourly_coeffs; None = constants
    transp_rad: float = 0.30           # transpiration LE = (transp_rad*0.7*I_in + transp_vpd*VPD_kPa) W/m2 floor; thesis
    transp_vpd: float = 14.0           # (avocado) values; a dense tomato/cucumber canopy transpires more (R6)
    floor_sol_frac: float = 0.3        # share of the light reaching the floor that the floor absorbs (thesis 0.3); the rest
                                       # goes to the air node. Under a dense crop the floor sees less (R6 test)

    def wall_ua(self, g):
        """UA of the side and gable walls (W/K). The north wall is one `length` side; walls admit no light in the
        model (I_in uses the roof transmission only), so an opaque north wall changes heat loss, not light."""
        u = self.u_cover if self.u_wall is None else self.u_wall
        if self.u_north_wall is None:
            return u * g.a_wall + self.ua_extra
        a_n = g.length * g.gutter_height
        return u * (g.a_wall - a_n) + self.u_north_wall * a_n + self.ua_extra


@dataclass
class Location:
    site: str = "chelmsford"           # key in simcore.weather.SITES, or a new key with lat/lon below
    lat: Optional[float] = None
    lon: Optional[float] = None
    description: str = ""
    form: str = "ground"               # "ground" (soil below the floor) or "rooftop" (heated building below)
    roof_height_m: float = 0.0         # rooftop only: height of the host roof above ground
    t_building_C: float = 20.0         # rooftop only: temperature of the space below the deck
    u_deck: float = 0.35               # rooftop only: W/m2K, roof deck between greenhouse floor and building
    z0_m: float = 0.5                  # rooftop only: surface roughness for scaling 10 m wind to roof height
    u_ground: Optional[float] = None   # ground only: floor-to-soil W/m2K; None = ISO 13370 from floor size
    soil_lambda: float = 2.0           # W/mK, ISO 13370 default for clay/silt
    edge_insul_depth_m: float = 0.0    # ground only: vertical perimeter insulation depth (0 = none), ISO 13370
    edge_insul_R: float = 0.0          # m2K/W of that insulation; edge_insul_d_m its thickness
    edge_insul_d_m: float = 0.0


@dataclass
class ClimatePeriod:
    """Setpoints applying from `start_doy` until the next period starts."""
    start_doy: int
    heat_day: float
    heat_night: float
    vent_day: float
    vent_night: float
    label: str = ""


@dataclass
class Climate:
    name: str = "thesis"
    periods: list = field(default_factory=lambda: [ClimatePeriod(1, 18.0, 18.0, 24.0, 22.0, "thesis: continuous 18 C")])
    rh_vent_start: float = 85.0        # % RH at which humidity venting starts
    ramp_K_per_h: float = 2.0          # heating setpoint moves towards the calendar value at most this fast
    source: str = "BEng thesis: continuous 18 C heating, 24/22 C venting"

    def at(self, doy, day):
        p = self.periods[0]
        for q in self.periods:
            if doy >= q.start_doy:
                p = q
        return (p.heat_day, p.vent_day) if day else (p.heat_night, p.vent_night)


@dataclass
class Hydronics:
    pipe_m_per_m2: float = 2.25        # pipe rail, 51 mm (900 m in 400 m2)
    k_pipe: float = 0.7                # W/m/K^1.25 pipe emission constant
    c_pipe_per_m: float = 1.0e4        # J/K per metre of pipe incl. water
    m_pipe_per_m2: float = 0.005       # kg/s/m2 heating-water flow (2.0 kg/s in 400 m2)
    buffer_m3_per_m2: float = 1.5 / THESIS_AREA
    buffer_height_m: float = 1.8       # at thesis size; grows with cube root of volume, max 12 m
    t_sup_max: float = 72.0
    aux_base_w_m2: float = 150.0 / THESIS_AREA      # controls, sensors
    aux_pump_w_m2: float = 1200.0 / THESIS_AREA     # heating circulation pump while heating
    aux_vent_w_m2: float = 900.0 / THESIS_AREA      # vent drives + circulation fans while venting
    aux_screen_w_m2: float = 60.0 / THESIS_AREA     # screen motors while closed
    pump_vsd: bool = False             # True: circulation pump power follows (heat demand / design)^3, min 15 %
    # Heat-pump supply control (thesis values; `optimised()` lowers them)
    buf_min_C: float = 35.0            # heat pump keeps the buffer at least this warm
    hp_margin_K: float = 5.0           # heat pump flow target above the requested supply temperature
    sup_base_C: float = 32.0           # supply temperature at zero error before the PI correction
    sup_curve_K_per_K: float = 0.0     # weather compensation: extra supply K per K of (setpoint - outdoor)
    # Price-led buffer charging (0 = off): in the cheapest hours of each day the buffer is charged this far above need
    shift_boost_K: float = 0.0
    shift_quantile: float = 0.35       # hours whose price is in this lowest fraction of the day count as cheap

    def buffer(self, area):
        v = self.buffer_m3_per_m2 * area
        v0 = self.buffer_m3_per_m2 * THESIS_AREA
        return v, min(12.0, self.buffer_height_m * (v / v0) ** (1 / 3))


@dataclass
class HeatSupply:
    kind: str = "hp"                   # "hp" now; "boiler", "chp" added in step 4
    source: str = "air"                # hp: "air", "ground" or "water"
    cycle: str = "two_stage"           # "two_stage" (thesis R717), "single_stage" (liquid sources only) or
                                       # "co2_tc" (transcritical R744, air source; greenhouse.CO2_AIR)
    waste_T_C: float = 80.0            # direct waste-heat source temperature (waste_kw series passed to simulate)
    charge_m_w: Optional[float] = None  # kg/s per thesis-unit scale through the heat pump when charging the
                                       # buffer; None = heating-pipe flow (thesis). CO2 units want low flow.
    hx_scale: float = 1.0              # evaporator and condenser UA multiplier on the thesis unit (larger plate HX)
    scale: Optional[float] = None      # multiples of the thesis R717 unit; None = sized to design heat loss
    design_outdoor_C: float = -4.0     # design condition for automatic sizing
    design_indoor_C: float = 18.0
    design_wind_ms: float = 4.0
    # Ground field per thesis unit (16 boreholes): borehole-to-fluid UA, store heat capacity, leakage to far field
    field_ua_w_K: float = 7000.0
    field_cap_J_K: float = 4.7e10
    field_leak_w_K: float = 9000.0
    field_T_far_C: float = 11.0


@dataclass
class Lighting:
    """Supplementary LED top-lighting. ppfd = 0 disables it."""
    ppfd: float = 0.0                  # umol/m2/s installed at canopy
    efficacy: float = 3.0              # umol/J photosynthetic photon efficacy (current horticultural LEDs ~2.7-3.5)
    photoperiod: tuple = (5, 21)       # local hours lights may run [start, end)
    on_below_par: float = 150.0        # natural PAR at canopy below which lights switch on, umol/m2/s
    dli_target: float = 18.0           # mol/m2/d; lights stop once the day's sun + LED integral reaches it (assumption)
    radiant_frac: float = 0.55         # share of electric power leaving as light (rest convective heat)
    off_above_C: float = 27.0          # lights off when the greenhouse is this hot
    inter_frac: float = 0.0            # share of the LED PPFD delivered as interlighting inside the canopy (crop.py)
    allow_hourly: object = None        # optional 8760 array, 1 = lights may run (wind/price-following); None = always

    @property
    def w_per_m2(self):
        return self.ppfd / self.efficacy


@dataclass
class CO2:
    enrich: bool = False
    setpoint_closed: float = 800.0     # ppm target with vents near-closed
    setpoint_open: float = 450.0       # ppm target with vents open (only replace what the crop takes)
    vent_closed: float = 5.0           # % vent opening at or below which the closed setpoint applies
    vent_open: float = 30.0            # % vent opening at or above which the open setpoint applies
    capacity_kg_m2_h: float = 0.015    # dosing capacity (150 kg/ha/h, typical pure-CO2 installation; to verify)
    outdoor_ppm: float = 420.0
    source: str = "purchased"          # "purchased" liquid CO2, or "flue" (boiler/CHP, step 4)


@dataclass
class HumidityControl:
    """Dutch-practice humidity control: above `rh_set` the vents open a humidity gap and the heating pipe is held at a
    minimum temperature, both ramping in over `band` % RH (sources: see data/input_register.csv). With heat-recovery
    dehumidification on, the units take over and the gap/minimum pipe are not used."""
    enabled: bool = False
    rh_set: float = 85.0
    band: float = 5.0
    vent_gap: float = 0.05             # vent opening fraction at full humidity action
    pipe_min_C: float = 40.0           # supply temperature at full humidity action


@dataclass
class HeatRecoveryDehum:
    """Dehumidification with outside air through a heat exchanger (Dutch 'Next Generation Growing' air treatment).
    When the humidity vent would open, a mechanical exchange of up to `flow_m3_m2_h` replaces it; exhaust heat is
    recovered at `effectiveness`. Defaults: EU Ecodesign Reg. 1253/2014 Annex III minimum thermal efficiency for
    non-residential heat recovery (73 %); EN 16798-3 SFP category 3 (1250 W per m3/s)."""
    enabled: bool = False
    flow_m3_m2_h: float = 5.0          # capacity per m2 floor; swept in experiments (sizing, not a standard)
    effectiveness: float = 0.73
    sfp_w_per_m3s: float = 1250.0


@dataclass
class Cooling:
    """Semi-closed greenhouse: fan-coil units cool and dehumidify the air with water from the heat-pump source
    (ground: the borehole field is recharged for winter; river: heat rejected). Opdam et al. (2005) Acta Hort 691;
    Vadiee & Martin (2012) Renew. Sust. Energy Rev. 16:5087."""
    enabled: bool = False
    set_C: float = 24.0                # cooling starts here (photosynthesis optimum ~24 C), full output 2 K above
    ua_w_m2K: float = 10.0             # fan-coil UA per m2 floor (~100-150 W/m2 at design)
    approach_K: float = 1.0            # coil water above field/river temperature
    eer: float = 20.0                  # heat removed per unit fan + pump electricity (free cooling; assumption)


@dataclass
class Crop:
    planting: str = "bed"                    # "bed" (in-ground beds) or "container"; beds default from 2026-10-02
    root_factor: Optional[float] = None  # photosynthetic capacity multiplier; None = 1.0 bed / 0.5 container
    lai: float = 3.0                   # maintained by pruning (gives ~84 % interception with k = 0.6)
    k_ext: float = 0.6                 # PAR extinction coefficient (mostly diffuse light under the cover)
    trees_per_ha: float = 1667.0       # high-density reference (Stassen et al. 1999)

    def root(self):
        if self.root_factor is not None:
            return self.root_factor
        return 1.0 if self.planting == "bed" else 0.5


@dataclass
class SiteConfig:
    name: str = "custom"
    geometry: Geometry = field(default_factory=Geometry)
    envelope: Envelope = field(default_factory=Envelope)
    location: Location = field(default_factory=Location)
    climate: Climate = field(default_factory=Climate)
    hydronics: Hydronics = field(default_factory=Hydronics)
    heat: HeatSupply = field(default_factory=HeatSupply)
    lighting: Lighting = field(default_factory=Lighting)
    co2: CO2 = field(default_factory=CO2)
    crop: Crop = field(default_factory=Crop)
    cooling: Cooling = field(default_factory=Cooling)
    hrd: HeatRecoveryDehum = field(default_factory=HeatRecoveryDehum)
    hum: HumidityControl = field(default_factory=HumidityControl)
    legacy_aux_vent: bool = False      # True reproduces the original sim's vent-power expression (see greenhouse.py)

    @property
    def area(self):
        return self.geometry.area

    def design_heat_loss_w(self, screen=False):
        """Steady design heat loss (cover + infiltration), used to size plant relative to the thesis unit.
        screen: roof energy screen closed (the design hour is a cold night, when the screen is shut below
        screen_below_C); walls unscreened."""
        g, e, h = self.geometry, self.envelope, self.heat
        dT = h.design_indoor_C - h.design_outdoor_C
        ua = e.wall_ua(g) + (e.u_cover + 0.06 * h.design_wind_ms) * g.a_roof * (e.screen_u_factor if screen else 1.0)
        ach = e.infiltration_ach + 0.05 * h.design_wind_ms
        return (ua + ach * g.volume * 1.2 * 1006 / 3600) * dT

    def u_floor_below(self):
        """Floor coupling to what is below it (W/m2K): deck U on a roof; on the ground the ISO 13370 uninsulated
        slab-on-ground value, U = 2 lam / (pi B' + dt) * ln(pi B' / dt + 1), B' = A / (P/2), dt = w + lam (Rsi + Rse)."""
        loc = self.location
        if loc.form == "rooftop":
            return loc.u_deck
        if loc.u_ground is not None:
            return loc.u_ground
        lam, B = loc.soil_lambda, self.area / (0.5 * self.geometry.perimeter)
        dt = 0.3 + lam * (0.17 + 0.04)
        u0 = 2 * lam / (math.pi * B + dt) * math.log(math.pi * B / dt + 1)
        D = loc.edge_insul_depth_m
        if D <= 0:
            return u0
        # ISO 13370 vertical edge insulation: psi = -(lam/pi)[ln(2D/dt + 1) - ln(2D/(dt + d') + 1)], d' = R' lam,
        # R' = R_n - d_n/lam; U = U0 + 2 psi / B'
        d_ = (loc.edge_insul_R - loc.edge_insul_d_m / lam) * lam
        psi = -lam / math.pi * (math.log(2 * D / dt + 1) - math.log(2 * D / (dt + d_) + 1))
        return u0 + 2 * psi / B

    def hp_scale(self):
        if self.heat.scale is not None:
            return self.heat.scale
        return self.design_heat_loss_w() / thesis(self.heat.source).design_heat_loss_w()


# ---------------------------------------------------------------- presets

def thesis(source="air"):
    """The BEng 400 m2 greenhouse exactly as in sim/annual_sim.py."""
    return SiteConfig(
        name=f"thesis_{source}",
        geometry=Geometry(20.0, 20.0, 5.0, a_roof_override=431.0, volume_override=2350.0),
        location=Location("chelmsford", u_ground=1.2),
        heat=HeatSupply("hp", source, scale=1.0),
        legacy_aux_vent=True,
    )


def commercial(area_ha=1.0, source="ground", site="chelmsford", climate=None):
    """Square Venlo block of the given area with a 5.5 m gutter."""
    side = math.sqrt(area_ha * 1e4)
    return SiteConfig(name=f"commercial_{area_ha:g}ha_{source}", geometry=Geometry(side, side),
                      location=Location(site), climate=climate or Climate(), heat=HeatSupply("hp", source))


def rooftop(length, width, site="london", roof_height_m=12.0, source="air", climate=None, **loc):
    """Greenhouse on a flat roof with a heated building below (e.g. a supermarket)."""
    return SiteConfig(name=f"rooftop_{length:g}x{width:g}_{site}_{source}",
                      geometry=Geometry(length, width, 5.0),
                      location=Location(site, form="rooftop", roof_height_m=roof_height_m, **loc),
                      climate=climate or Climate(), heat=HeatSupply("hp", source))


# Covers. Twin-wall PC is the thesis cover. Glass: single horticultural glass on a Venlo frame with an energy screen.
COVERS = {
    "pc": dict(u_cover=3.0, tau_solar=0.70,
               source="BEng thesis: twin-wall polycarbonate U 3.0 W/m2K, 70 % transmission incl. structure"),
    "glass": dict(u_cover=6.0, tau_solar=0.80,
                  source="Single 4 mm horticultural glass, Venlo: U ~6 W/m2K (5.7-7.5 typical), hemispherical "
                         "transmission ~80 % incl. structure (estimate; to source)"),
}


def cover(cfg, kind):
    c = COVERS[kind]
    return replace(cfg, envelope=replace(cfg.envelope, u_cover=c["u_cover"], tau_solar=c["tau_solar"]))


def optimised(cfg, seasonal_store=True, shift=False, cycle="two_stage", pipe_m_per_m2=4.5, hx_scale=2.0):
    """System optimisation (SCOPE §3.13): weather-compensated low-temperature supply with twice the emitter length
    (grow pipes alongside the pipe rail), double-size evaporator and condenser, variable-speed circulation pump at
    1 W/m2, and a borehole field sized as a seasonal store (twice the boreholes, quarter the leakage) recharged by
    semi-closed cooling (ground source only). Price-led buffer charging is available but off: in step 4a it raised
    electricity use more than it cut the unit price."""
    hy = replace(cfg.hydronics, buf_min_C=25.0, hp_margin_K=3.0, sup_base_C=24.0, sup_curve_K_per_K=0.5,
                 aux_pump_w_m2=1.0, pump_vsd=True, pipe_m_per_m2=pipe_m_per_m2,
                 buffer_m3_per_m2=0.015 if shift else cfg.hydronics.buffer_m3_per_m2,
                 shift_boost_K=8.0 if shift else 0.0)
    heat = replace(cfg.heat, cycle=cycle, hx_scale=hx_scale)
    out = replace(cfg, hydronics=hy, heat=heat)
    if seasonal_store and cfg.heat.source == "ground":
        out = replace(out, heat=replace(heat, field_ua_w_K=14000.0, field_leak_w_K=2250.0, field_cap_J_K=7.0e10),
                      cooling=replace(cfg.cooling, enabled=True))
    return out


def with_(cfg, **changes):
    """Shallow copy with top-level fields replaced, e.g. with_(cfg, climate=crop_led())."""
    return replace(cfg, **changes)
