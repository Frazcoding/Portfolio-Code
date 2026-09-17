"""
Publication-grade visual generator for the Plantpost modelling suite.
Produces the extended 6-figure publication suite conforming to master portfolio standards:
minimalist aesthetic (seaborn-v0_8-whitegrid), explicit bracketed units on all axes,
high-contrast accessible palettes, exported at 300 DPI PNG and vector SVG.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Set publication style
try:
    plt.style.use('seaborn-v0_8-whitegrid')
except OSError:
    plt.style.use('seaborn-whitegrid')

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 14,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'axes.edgecolor': '#cccccc',
    'axes.linewidth': 0.8,
    'grid.color': '#e0e0e0',
    'grid.linestyle': '--',
    'grid.linewidth': 0.5,
})


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def plot_figure_1_annual_resource_balance(
    df_monthly_excel: pd.DataFrame,
    df_monthly_sim: pd.DataFrame,
    output_dir: str = 'figures'
) -> str:
    """
    Figure 1 — Annual Dual-Resource Balance: Energy & Water
    2-panel linked monthly overview directly validating and extending the Excel model.
    """
    _ensure_dir(output_dir)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8.5), sharex=True)

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    x = np.arange(len(months))
    width = 0.35

    # Panel A: Energy Balance (kWh/month)
    pv_gen = df_monthly_sim['pv_generation_kwh']
    total_load = df_monthly_sim['total_load_kwh']
    net_energy = pv_gen - total_load

    rects1 = ax1.bar(x - width/2, pv_gen, width, label='Solar PV Generation [kWh]', color='#2b5c8f', edgecolor='black', linewidth=0.5)
    rects2 = ax1.bar(x + width/2, total_load, width, label='Total Demand (LED + Pump) [kWh]', color='#d95f02', edgecolor='black', linewidth=0.5)
    
    # Net balance line
    ax1.plot(x, net_energy, color='#7570b3', marker='o', linewidth=2.0, label='Net Energy Balance (Surplus/Deficit) [kWh]')
    ax1.axhline(0, color='gray', linestyle=':', linewidth=1.0)

    # Highlight winter deficit and summer surplus
    ax1.annotate('Winter Deficit\n(-6.7 kWh Dec)', xy=(11, net_energy.iloc[11]), xytext=(9.2, -10),
                 arrowprops=dict(arrowstyle='->', color='#d95f02', lw=1.2),
                 fontsize=9.5, fontweight='bold', color='#d95f02')
    ax1.annotate('Summer Surplus\n(+12.3 kWh Jul)', xy=(6, net_energy.iloc[6]), xytext=(4.5, 17),
                 arrowprops=dict(arrowstyle='->', color='#2b5c8f', lw=1.2),
                 fontsize=9.5, fontweight='bold', color='#2b5c8f')

    ax1.set_ylabel('Electrical Energy [kWh/month]')
    ax1.set_title('Plantpost Annual Dual-Resource Balance (Bologna Baseline)\n(A) Photovoltaic Generation vs Public Lighting & Irrigation Pumping Demand', fontweight='bold', loc='left')
    ax1.legend(loc='upper right', framealpha=0.95)
    ax1.set_ylim(-15, 35)

    # Panel B: Water Balance (Liters/month)
    rain_harvested = df_monthly_sim['rain_harvested_l']
    irr_demand = df_monthly_sim['irr_required_l']
    net_water = rain_harvested - irr_demand

    ax2.bar(x - width/2, rain_harvested, width, label='Rainwater Inflow [L]', color='#1b9e77', edgecolor='black', linewidth=0.5)
    ax2.bar(x + width/2, irr_demand, width, label='FAO-56 Foliage Irrigation Demand [L]', color='#e7298a', edgecolor='black', linewidth=0.5)
    ax2.plot(x, net_water, color='#386cb0', marker='s', linewidth=2.0, label='Net Water Inflow [L]')
    ax2.axhline(0, color='gray', linestyle=':', linewidth=1.0)

    ax2.set_ylabel('Water Volume [L/month]')
    ax2.set_title('(B) Rainwater Harvesting vs Dynamic FAO-56 Crop Evapotranspiration', fontweight='bold', loc='left')
    ax2.set_xticks(x)
    ax2.set_xticklabels(months)
    ax2.set_xlabel('Month of Year')
    ax2.legend(loc='upper right', framealpha=0.95)
    ax2.set_ylim(-50, 320)

    plt.tight_layout()
    base_name = os.path.join(output_dir, 'fig1_annual_resource_balance_water_energy')
    fig.savefig(f"{base_name}.png", dpi=300)
    fig.savefig(f"{base_name}.svg")
    plt.close(fig)
    return base_name


def plot_figure_2_winter_stress_soc(
    df_weather: pd.DataFrame,
    sim_results_dict: dict,  # keys: capacity float, values: sim DataFrame
    output_dir: str = 'figures'
) -> str:
    """
    Figure 2 — Hourly Battery State of Charge & Winter Solstice Stress Test
    Detailed time-series across the critical December/January period comparing 3 battery sizes.
    """
    _ensure_dir(output_dir)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True, gridspec_kw={'height_ratios': [1, 1.2]})

    # Focus window: Dec 15 to Jan 15 (744 hours)
    # Datetime filter
    dt = df_weather['datetime']
    winter_mask = (dt >= '2023-12-15 00:00:00') | (dt <= '2023-01-15 23:00:00')
    
    # We slice Dec 15 to Dec 31
    winter_window = df_weather[dt >= '2023-12-10 00:00:00'].copy()

    times = winter_window['datetime']
    ghi = winter_window['ghi_w_m2']

    # Top Track: Solar irradiance and Lighting Load
    ax1.plot(times, ghi, color='#e6ab02', linewidth=1.2, label='Global Horizontal Irradiance GHI [W/m²]')
    # Plot load pulse (47.1 W when civil night)
    load_w = np.where(winter_window['is_civil_night'], 47.1, 0.0)
    ax1.step(times, load_w, where='mid', color='#7570b3', linewidth=1.5, label='LED Public Lighting Draw [W]')

    ax1.set_ylabel('Power / Irradiance [W, W/m²]')
    ax1.set_title('Plantpost Winter Solstice Battery Stress Test (December 10 – 31, Bologna)\n(A) Solar Irradiance Input vs Dusk-to-Dawn Luminaire Load Pulses', fontweight='bold', loc='left')
    ax1.legend(loc='upper right', framealpha=0.95)
    ax1.set_ylim(0, 450)

    # Bottom Track: Dynamic Battery SoC(t) across sizings
    colors = {'0.8 kWh': '#d95f02', '1.28 kWh (Baseline)': '#2b5c8f', '2.0 kWh': '#1b9e77'}
    
    for label, (cap_kwh, sim_df) in sim_results_dict.items():
        sim_window = sim_df[dt >= '2023-12-10 00:00:00']
        soc_pct = sim_window['battery_soc'] * 100.0
        c = colors.get(label, '#333333')
        lw = 2.2 if '1.28' in label else 1.6
        ax2.plot(times, soc_pct, label=f"Battery Capacity: {label}", color=c, linewidth=lw)

    # SoC Reserve threshold line (20%)
    ax2.axhline(20.0, color='#e41a1c', linestyle='--', linewidth=1.5, label='DoD Limit / Reserve Floor (20% SoC)')
    ax2.fill_between(times, 0, 20.0, color='#e41a1c', alpha=0.10, label='Blackout Zone (Load Curtailment)')

    ax2.set_ylabel('Battery State of Charge [%]')
    ax2.set_xlabel('Date (December)')
    ax2.set_title('(B) Dynamic LiFePO4 State of Charge & Cold-Cloudy Autonomous Survival', fontweight='bold', loc='left')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax2.legend(loc='lower left', framealpha=0.95)
    ax2.set_ylim(10, 105)

    plt.tight_layout()
    base_name = os.path.join(output_dir, 'fig2_dynamic_battery_soc_winter_stress')
    fig.savefig(f"{base_name}.png", dpi=300)
    fig.savefig(f"{base_name}.svg")
    plt.close(fig)
    return base_name


def plot_figure_3_tank_storage_drought(
    df_weather: pd.DataFrame,
    df_hydrology: pd.DataFrame,
    output_dir: str = 'figures'
) -> str:
    """
    Figure 3 — Rainwater Reservoir Storage & Drought Resilience
    Full 8760-hour continuous reservoir storage curve with rainfall and FAO-56 withdrawals.
    """
    _ensure_dir(output_dir)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True, gridspec_kw={'height_ratios': [1, 1.3]})

    times = df_weather['datetime']

    # Panel A: Daily Rainfall Inflow & Daily FAO-56 Demand
    daily_rain = df_hydrology.groupby(df_weather['day_of_year'])['rain_harvested_l'].sum()
    daily_irr = df_hydrology.groupby(df_weather['day_of_year'])['irr_required_l'].sum()
    doy_dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')

    ax1.bar(doy_dates, daily_rain, width=1.0, color='#1b9e77', alpha=0.8, label='Daily Harvested Precipitation [L/day]')
    ax1.plot(doy_dates, daily_irr, color='#d95f02', linewidth=1.5, label='Daily FAO-56 Crop Water Demand [L/day]')
    ax1.set_ylabel('Volume Rate [L/day]')
    ax1.set_title('Plantpost Rainwater Catchment & Reservoir Storage Dynamics (8760-Hour Profile)\n(A) Atmospheric Water Inflow vs Temperature-Driven Crop Demand', fontweight='bold', loc='left')
    ax1.legend(loc='upper right', framealpha=0.95)
    ax1.set_ylim(0, max(daily_rain.max() * 1.1, 30))

    # Panel B: Reservoir Volume Storage Curve
    tank_vol = df_hydrology['tank_volume_l']
    ax2.plot(times, tank_vol, color='#2b5c8f', linewidth=1.8, label='Internal Base Reservoir Storage [L]')
    ax2.axhline(150.0, color='#1b9e77', linestyle='--', linewidth=1.5, label='Maximum Tank Capacity (150 L / 1.0 m Head)')
    ax2.axhline(0.0, color='#e41a1c', linestyle=':', linewidth=1.2, label='Empty Reservoir (Drought Stress Floor)')
    ax2.fill_between(times, 0, tank_vol, color='#2b5c8f', alpha=0.15)

    # Highlight summer drawdown
    ax2.annotate('Mediterranean Summer Drawdown\n(High VPD & Stomatal Demand)',
                 xy=(pd.Timestamp('2023-07-20'), tank_vol.iloc[int(8760*0.55)]),
                 xytext=(pd.Timestamp('2023-04-15'), 35),
                 arrowprops=dict(arrowstyle='->', color='#d95f02', lw=1.2),
                 fontsize=9.5, fontweight='bold', color='#d95f02')

    ax2.set_ylabel('Stored Water Volume [L]')
    ax2.set_xlabel('Month of Year')
    ax2.set_title('(B) Continuous Reservoir Mass Balance & Drought Resilience Tracking', fontweight='bold', loc='left')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax2.legend(loc='upper right', framealpha=0.95)
    ax2.set_ylim(-5, 170)

    plt.tight_layout()
    base_name = os.path.join(output_dir, 'fig3_rainwater_tank_storage_drought_resilience')
    fig.savefig(f"{base_name}.png", dpi=300)
    fig.savefig(f"{base_name}.svg")
    plt.close(fig)
    return base_name


def plot_figure_4_hydraulics_pumping(
    output_dir: str = 'figures'
) -> str:
    """
    Figure 4 — Multi-Tier Hydraulic Head & Micro-Pump Power Dynamics
    Total dynamic head vs tank level and instantaneous power vs flow velocity.
    """
    _ensure_dir(output_dir)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.2))

    from src.hydraulics import calculate_tier_dynamic_head, calculate_micro_pump_power_w

    # Panel A: Dynamic Head vs Tank Water Level (0.0 to 1.0 m)
    water_levels = np.linspace(0.0, 1.0, 50)
    tiers = [1.0, 2.0, 3.0, 4.0]
    colors = ['#1b9e77', '#386cb0', '#7570b3', '#e7298a']

    for z, c in zip(tiers, colors):
        heads = [calculate_tier_dynamic_head(z, h)['h_total_m'] for h in water_levels]
        ax1.plot(water_levels, heads, label=f"Tier at z = {z:.1f} m", color=c, linewidth=2.0)

    ax1.set_xlabel('Reservoir Water Level [m]')
    ax1.set_ylabel('Total Dynamic Pumping Head [m]')
    ax1.set_title('(A) Total Dynamic Pumping Head vs Reservoir Level\n(Static Head + Pipe Friction + Emitter Head)', fontweight='bold', loc='left')
    ax1.legend(loc='upper right')
    ax1.set_xlim(0, 1.0)
    ax1.set_ylim(2.5, 6.5)

    # Panel B: Micro-Pump Power Draw across tiers as reservoir level changes
    for z, c in zip(tiers, colors):
        powers = [calculate_micro_pump_power_w(calculate_tier_dynamic_head(z, h)['h_total_m']) for h in water_levels]
        ax2.plot(water_levels, powers, label=f"Tier at z = {z:.1f} m", color=c, linewidth=2.0)

    ax2.set_xlabel('Reservoir Water Level [m]')
    ax2.set_ylabel('Instantaneous Micro-Pump Power [W]')
    ax2.set_title('(B) DC Micro-Pump Electrical Power Draw\n(12V Centrifugal Pump, Combined Efficiency η = 70%)', fontweight='bold', loc='left')
    ax2.legend(loc='upper right')
    ax2.set_xlim(0, 1.0)
    ax2.set_ylim(0.4, 1.5)

    plt.tight_layout()
    base_name = os.path.join(output_dir, 'fig4_hydraulic_vertical_head_pumping_dynamics')
    fig.savefig(f"{base_name}.png", dpi=300)
    fig.savefig(f"{base_name}.svg")
    plt.close(fig)
    return base_name


def plot_figure_5_ecosystem_services(
    df_weather: pd.DataFrame,
    df_hydrology: pd.DataFrame,
    df_crop: pd.DataFrame,
    output_dir: str = 'figures'
) -> str:
    """
    Figure 5 — Urban Ecosystem Services & Microclimate Co-Benefits Dashboard
    4-quadrant executive scorecard visualising quantified urban environmental impact.
    """
    _ensure_dir(output_dir)
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(11.5, 9.0))

    from src.ecosystem import (
        calculate_evaporative_cooling,
        calculate_stormwater_attenuation,
        calculate_particulate_biofiltration,
        calculate_avoided_grid_carbon
    )

    cool_df = calculate_evaporative_cooling(df_hydrology, df_weather)
    storm = calculate_stormwater_attenuation(df_hydrology, df_weather)
    pm = calculate_particulate_biofiltration(df_weather, df_crop, 'bologna')
    carb = calculate_avoided_grid_carbon(3922, 'bologna')

    # Q1: Evaporative Cooling (Daily kWh_th)
    daily_cooling = cool_df.groupby(df_weather['month'])['cooling_energy_kwh_th'].sum()
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    x = np.arange(len(months))

    ax1.bar(x, daily_cooling, color='#1b9e77', edgecolor='black', linewidth=0.5)
    ax1.set_xticks(x)
    ax1.set_xticklabels(months, rotation=45)
    ax1.set_ylabel('Evaporative Cooling [kWh_th/month]')
    ax1.set_title('(A) Microclimate Sensible Heat Abatement\n(Total: 673 kWh_th/yr Local Cooling)', fontweight='bold', loc='left')

    # Q2: Stormwater Attenuation Breakdown
    labels = ['Retained for Foliage', 'Reservoir Overflow', 'Runoff Loss (Uncaptured)']
    sizes = [storm['retained_in_reservoir_l'], storm['overflow_volume_l'], storm['total_rain_volume_l'] - storm['harvested_volume_l']]
    colors_pie = ['#2b5c8f', '#a6cee3', '#fb9a99']
    ax2.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors_pie, startangle=140,
            wedgeprops=dict(edgecolor='white', linewidth=1.5))
    ax2.set_title(f"(B) Stormwater Runoff Attenuation\n(Total Rainfall: {storm['total_rain_volume_l']:.0f} L/yr on Canopy)", fontweight='bold', loc='left')

    # Q3: Particulate Bio-Filtration
    pm_types = ['PM2.5 Bio-Interception', 'PM10 Bio-Interception']
    pm_vals = [pm['annual_pm25_filtered_g'], pm['annual_pm10_filtered_g']]
    bars = ax3.bar(pm_types, pm_vals, color=['#7570b3', '#e7298a'], width=0.45, edgecolor='black', linewidth=0.5)
    ax3.set_ylabel('Particulate Mass Captured [g/yr]')
    ax3.set_title('(C) Particulate Matter Dry Deposition (Ivy Foliage)\n(Bologna Urban Background Concentrations)', fontweight='bold', loc='left')
    for bar in bars:
        yval = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 0.3, f"{yval:.1f} g/yr", ha='center', va='bottom', fontweight='bold')
    ax3.set_ylim(0, 22)

    # Q4: Avoided Grid Operational Carbon
    categories = ['vs Legacy HPS (150W)', 'vs Modern Grid LED (50W)']
    co2_vals = [carb['avoided_co2e_vs_hps_kg'], carb['avoided_co2e_vs_grid_led_kg']]
    bars4 = ax4.bar(categories, co2_vals, color=['#d95f02', '#2b5c8f'], width=0.45, edgecolor='black', linewidth=0.5)
    ax4.set_ylabel('Avoided Carbon Emissions [kg CO2e/yr]')
    ax4.set_title('(D) Net Avoided Municipal Grid Carbon\n(Italian Grid Factor: 260 g CO2e/kWh)', fontweight='bold', loc='left')
    for bar in bars4:
        yval = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2.0, yval + 2.5, f"{yval:.1f} kg/yr", ha='center', va='bottom', fontweight='bold')
    ax4.set_ylim(0, 180)

    plt.tight_layout()
    base_name = os.path.join(output_dir, 'fig5_urban_ecosystem_services_dashboard')
    fig.savefig(f"{base_name}.png", dpi=300)
    fig.savefig(f"{base_name}.svg")
    plt.close(fig)
    return base_name


def plot_figure_6_multi_city_frontier(
    multi_city_metrics: dict,
    output_dir: str = 'figures'
) -> str:
    """
    Figure 6 — Multi-City Climate Feasibility & Storage Frontier
    Contrasts Bologna (Mediterranean) vs Edinburgh (Northern Maritime) vs London (Temperate).
    """
    _ensure_dir(output_dir)
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(11.5, 8.5))

    cities = list(multi_city_metrics.keys())
    x = np.arange(len(cities))
    width = 0.45
    city_labels = [c.capitalize() for c in cities]

    # Metric 1: Annual Solar Generation
    solar_yield = [multi_city_metrics[c]['solar_generation_kwh'] for c in cities]
    bars1 = ax1.bar(x, solar_yield, width, color='#e6ab02', edgecolor='black', linewidth=0.5)
    ax1.set_xticks(x)
    ax1.set_xticklabels(city_labels)
    ax1.set_ylabel('Annual Solar Generation [kWh/yr]')
    ax1.set_title('(A) Annual Photovoltaic Canopy Generation', fontweight='bold', loc='left')
    for b in bars1:
        ax1.text(b.get_x() + b.get_width()/2, b.get_height() + 3, f"{b.get_height():.0f} kWh", ha='center', va='bottom')
    ax1.set_ylim(0, 300)

    # Metric 2: Required Battery Capacity for 99% Winter Reliability
    bat_req = [multi_city_metrics[c]['req_battery_kwh_99pct'] for c in cities]
    bars2 = ax2.bar(x, bat_req, width, color='#2b5c8f', edgecolor='black', linewidth=0.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(city_labels)
    ax2.set_ylabel('Required Battery Capacity [kWh]')
    ax2.set_title('(B) Battery Sizing for 99% Winter Solstice Reliability', fontweight='bold', loc='left')
    for b in bars2:
        ax2.text(b.get_x() + b.get_width()/2, b.get_height() + 0.05, f"{b.get_height():.2f} kWh", ha='center', va='bottom')
    ax2.set_ylim(0, max(bat_req) * 1.25)

    # Metric 3: Rainwater Collected
    rain_harvested = [multi_city_metrics[c]['rain_harvested_l'] for c in cities]
    bars3 = ax3.bar(x, rain_harvested, width, color='#1b9e77', edgecolor='black', linewidth=0.5)
    ax3.set_xticks(x)
    ax3.set_xticklabels(city_labels)
    ax3.set_ylabel('Rainwater Collected [L/yr]')
    ax3.set_title('(C) Annual Rainwater Harvested Inflow', fontweight='bold', loc='left')
    for b in bars3:
        ax3.text(b.get_x() + b.get_width()/2, b.get_height() + 30, f"{b.get_height():.0f} L", ha='center', va='bottom')
    ax3.set_ylim(0, max(rain_harvested) * 1.2)

    # Metric 4: Water Self-Sufficiency %
    sufficiency = [multi_city_metrics[c]['water_self_sufficiency_pct'] for c in cities]
    bars4 = ax4.bar(x, sufficiency, width, color='#7570b3', edgecolor='black', linewidth=0.5)
    ax4.set_xticks(x)
    ax4.set_xticklabels(city_labels)
    ax4.set_ylabel('Water Self-Sufficiency [%]')
    ax4.set_title('(D) Foliage Irrigation Rainwater Self-Sufficiency', fontweight='bold', loc='left')
    for b in bars4:
        ax4.text(b.get_x() + b.get_width()/2, b.get_height() + 1.5, f"{b.get_height():.1f}%", ha='center', va='bottom')
    ax4.set_ylim(0, 115)

    plt.tight_layout()
    base_name = os.path.join(output_dir, 'fig6_multi_city_climate_feasibility_frontier')
    fig.savefig(f"{base_name}.png", dpi=300)
    fig.savefig(f"{base_name}.svg")
    plt.close(fig)
    return base_name

