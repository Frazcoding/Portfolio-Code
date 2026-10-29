"""
Publication-grade visual generator for the Plantpost modelling suite.
Strictly adheres to GEMINI.md Section 7.4 standards:
- Class-based OOP architecture (PlantpostPlotter)
- Pure black typography exclusively (#000000)
- Zero in-plot annotations (strictly legend only, no ax.annotate or ax.text)
- Legends strictly positioned below graphs with ample clearance to prevent collisions
- Explicit bracketed physical units on all axes
- 300 DPI PNG and vector SVG exports
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from typing import Dict, Any, Optional

from src.hydraulics import VerticalHydraulicManifold
from src.ecosystem import UrbanEcosystemServices


class PlantpostPlotter:
    """Publication-grade figure generator enforcing strict visual and typographic standards."""

    def __init__(self, output_dir: str = 'figures'):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self._apply_theme()

    @staticmethod
    def _apply_theme():
        try:
            plt.style.use('seaborn-v0_8-whitegrid')
        except OSError:
            plt.style.use('seaborn-whitegrid')

        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.size': 10.5,
            'text.color': '#000000',
            'axes.labelcolor': '#000000',
            'axes.titlecolor': '#000000',
            'xtick.color': '#000000',
            'ytick.color': '#000000',
            'axes.edgecolor': '#333333',
            'axes.linewidth': 0.8,
            'grid.color': '#e8e8e8',
            'grid.linestyle': '--',
            'grid.linewidth': 0.5,
            'figure.dpi': 300,
            'savefig.dpi': 300,
        })

    def plot_figure_1_annual_resource_balance(
        self,
        df_monthly_sim: pd.DataFrame
    ) -> str:
        """Figure 1 — Annual Dual-Resource Balance: Energy & Water."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.5, 8.8), sharex=True)

        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        x = np.arange(len(months))
        w = 0.35

        pv_gen = df_monthly_sim['pv_generation_kwh']
        total_load = df_monthly_sim['total_load_kwh']
        net_energy = pv_gen - total_load

        ax1.bar(x - w/2, pv_gen, w, label='Solar PV Generation [kWh/month]', color='#2b5c8f', edgecolor='#000000', linewidth=0.5)
        ax1.bar(x + w/2, total_load, w, label='Total Electrical Demand [kWh/month]', color='#d95f02', edgecolor='#000000', linewidth=0.5)
        ax1.plot(x, net_energy, color='#7570b3', marker='o', linewidth=1.8, label='Net Energy Balance [kWh/month]')
        ax1.axhline(0, color='#000000', linestyle=':', linewidth=0.8)
        ax1.set_ylabel('Electrical Energy [kWh/month]', color='#000000')
        ax1.set_title('(A) Photovoltaic Generation vs Public Lighting and Pumping Demand', fontweight='bold', loc='left', color='#000000', pad=10)
        ax1.set_ylim(-15, 35)
        ax1.legend(loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=True, fontsize=9.2)

        rain_harvested = df_monthly_sim['rain_harvested_l']
        irr_demand = df_monthly_sim['irr_required_l']
        net_water = rain_harvested - irr_demand

        ax2.bar(x - w/2, rain_harvested, w, label='Rainwater Inflow [L/month]', color='#1b9e77', edgecolor='#000000', linewidth=0.5)
        ax2.bar(x + w/2, irr_demand, w, label='FAO-56 Irrigation Demand [L/month]', color='#e7298a', edgecolor='#000000', linewidth=0.5)
        ax2.plot(x, net_water, color='#386cb0', marker='s', linewidth=1.8, label='Net Water Balance [L/month]')
        ax2.axhline(0, color='#000000', linestyle=':', linewidth=0.8)
        ax2.set_ylabel('Water Volume [L/month]', color='#000000')
        ax2.set_xlabel('Month of Year', color='#000000')
        ax2.set_title('(B) Rainwater Inflow vs Dynamic Foliage Irrigation Demand', fontweight='bold', loc='left', color='#000000', pad=10)
        ax2.set_xticks(x)
        ax2.set_xticklabels(months, color='#000000')
        ax2.set_ylim(-50, 320)
        ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=True, fontsize=9.2)

        plt.subplots_adjust(hspace=0.48, bottom=0.14)
        base = os.path.join(self.output_dir, 'fig1_annual_resource_balance_water_energy')
        fig.savefig(f"{base}.png", dpi=300, bbox_inches='tight')
        fig.savefig(f"{base}.svg", bbox_inches='tight')
        plt.close(fig)
        return base

    def plot_figure_2_winter_stress_soc(
        self,
        df_weather: pd.DataFrame,
        sim_results_dict: dict
    ) -> str:
        """Figure 2 — Hourly Battery State of Charge & Winter Solstice Stress Test."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.5, 8.2), sharex=True, gridspec_kw={'height_ratios': [1, 1.2]})

        dt = df_weather['datetime']
        winter_mask = (dt >= '2023-12-10 00:00:00') & (dt <= '2023-12-31 23:59:59')
        winter_window = df_weather[winter_mask].copy()
        times = winter_window['datetime']

        # Top Track: GHI and Lighting Load
        ax1.plot(times, winter_window['ghi_w_m2'], color='#e6ab02', linewidth=1.2, label='Global Horizontal Irradiance [W/m²]')
        load_w = np.where(winter_window['is_civil_night'], 47.1, 0.0)
        ax1.step(times, load_w, where='mid', color='#7570b3', linewidth=1.4, label='Public Luminaire Load [W]')
        ax1.set_ylabel('Power / Irradiance [W, W/m²]', color='#000000')
        ax1.set_title('(A) Solar Irradiance Input vs Dusk-to-Dawn Luminaire Load', fontweight='bold', loc='left', color='#000000', pad=10)
        ax1.set_xlim(times.iloc[0], times.iloc[-1])
        ax1.set_ylim(0, 450)
        ax1.legend(loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=True, fontsize=9.2)

        # Bottom Track: Battery SoC across sizings
        colors = {'0.8 kWh': '#d95f02', '1.28 kWh (Baseline)': '#2b5c8f', '2.0 kWh': '#1b9e77'}
        for label, (_, sim_df) in sim_results_dict.items():
            sim_w = sim_df[winter_mask]
            soc_pct = sim_w['battery_soc'] * 100.0
            ax2.plot(times, soc_pct, label=f"Battery Capacity: {label}", color=colors.get(label, '#333333'), linewidth=1.8)

        ax2.axhline(20.0, color='#e41a1c', linestyle='--', linewidth=1.4, label='Reserve Limit (20% SoC Floor)')
        ax2.set_ylabel('Battery State of Charge [%]', color='#000000')
        ax2.set_xlabel('Date (December)', color='#000000')
        ax2.set_title('(B) Dynamic LiFePO4 State of Charge across Sizing Configurations', fontweight='bold', loc='left', color='#000000', pad=10)
        
        ax2.set_xlim(times.iloc[0], times.iloc[-1])
        ax2.xaxis.set_major_locator(mdates.DayLocator(interval=4))
        ax2.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"Dec {mdates.num2date(val).day:02d}"))
        ax2.set_ylim(10, 105)
        ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=True, fontsize=9.2)

        plt.subplots_adjust(hspace=0.48, bottom=0.14)
        base = os.path.join(self.output_dir, 'fig2_dynamic_battery_soc_winter_stress')
        fig.savefig(f"{base}.png", dpi=300, bbox_inches='tight')
        fig.savefig(f"{base}.svg", bbox_inches='tight')
        plt.close(fig)
        return base

    def plot_figure_3_tank_storage_drought(
        self,
        df_weather: pd.DataFrame,
        df_hydrology: pd.DataFrame
    ) -> str:
        """Figure 3 — Rainwater Reservoir Storage & Drought Resilience."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.5, 8.2), sharex=True, gridspec_kw={'height_ratios': [1, 1.2]})

        dt = pd.to_datetime(df_weather['datetime'])
        harvest_daily = df_hydrology.groupby(dt.dt.date)['rain_harvested_l'].sum()
        irr_daily = df_hydrology.groupby(dt.dt.date)['irr_required_l'].sum()
        daily_dates = [pd.Timestamp(d) for d in harvest_daily.index]

        ax1.bar(daily_dates, harvest_daily, color='#1b9e77', width=1.0, alpha=0.8, label='Harvested Precipitation Inflow [L/day]')
        ax1.plot(daily_dates, irr_daily, color='#d95f02', linewidth=1.6, label='FAO-56 Irrigation Demand [L/day]')
        ax1.set_ylabel('Water Rate [L/day]', color='#000000')
        ax1.set_title('(A) Daily Harvested Inflow vs Temperature-Driven Crop Demand', fontweight='bold', loc='left', color='#000000', pad=10)
        ax1.set_ylim(0, 200)
        ax1.legend(loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=True, fontsize=9.2)

        storage = df_hydrology['tank_volume_l']
        ax2.plot(dt, storage, color='#2b5c8f', linewidth=2.0, label='Reservoir Stored Water Volume [L]')
        ax2.fill_between(dt, 0, storage, color='#2b5c8f', alpha=0.15)
        ax2.axhline(150.0, color='#1b9e77', linestyle='--', linewidth=1.6, label='Maximum Tank Capacity (150 L)')
        ax2.axhline(0.0, color='#e41a1c', linestyle=':', linewidth=1.6, label='Empty Reservoir (Drought Floor)')
        ax2.set_ylabel('Stored Water Volume [L]', color='#000000')
        ax2.set_xlabel('Month of Year', color='#000000')
        ax2.set_title('(B) Continuous 8,760-Hour Reservoir Mass Balance', fontweight='bold', loc='left', color='#000000', pad=10)
        
        month_starts = pd.date_range('2023-01-01', '2023-12-01', freq='MS')
        month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        ax2.set_xlim(dt.iloc[0], dt.iloc[-1])
        ax2.set_xticks(month_starts)
        ax2.set_xticklabels(month_labels, color='#000000')
        ax2.set_ylim(-5, 170)
        ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=True, fontsize=9.2)

        plt.subplots_adjust(hspace=0.48, bottom=0.14)
        base = os.path.join(self.output_dir, 'fig3_rainwater_tank_storage_drought_resilience')
        fig.savefig(f"{base}.png", dpi=300, bbox_inches='tight')
        fig.savefig(f"{base}.svg", bbox_inches='tight')
        plt.close(fig)
        return base

    def plot_figure_4_hydraulics_pumping(self) -> str:
        """Figure 4 — Multi-Tier Hydraulic Head & Micro-Pump Power Dynamics."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.2))

        manifold = VerticalHydraulicManifold()
        water_levels = np.linspace(0.0, 1.0, 50)
        tiers = [1.0, 2.0, 3.0, 4.0]
        colors = ['#1b9e77', '#2b5c8f', '#7570b3', '#e7298a']

        lines = []
        labels = []
        for z, c in zip(tiers, colors):
            heads = [manifold.tier_dynamic_head(z, h)['h_total_m'] for h in water_levels]
            l = ax1.plot(water_levels, heads, color=c, linewidth=1.8)[0]
            lines.append(l)
            labels.append(f"Tier at z = {z:.1f} m")

        ax1.set_xlabel('Reservoir Water Level [m]', color='#000000')
        ax1.set_ylabel('Total Dynamic Pumping Head [m]', color='#000000')
        ax1.set_title('(A) Dynamic Head vs Reservoir Storage Level', fontweight='bold', loc='left', color='#000000')
        ax1.set_xlim(0, 1.0)
        ax1.set_ylim(1.8, 6.5)

        for z, c in zip(tiers, colors):
            powers = [manifold.micro_pump_power_w(manifold.tier_dynamic_head(z, h)['h_total_m']) for h in water_levels]
            ax2.plot(water_levels, powers, color=c, linewidth=1.8)

        ax2.set_xlabel('Reservoir Water Level [m]', color='#000000')
        ax2.set_ylabel('Micro-Pump Electrical Power [W]', color='#000000')
        ax2.set_title('(B) Instantaneous Micro-Pump Electrical Draw', fontweight='bold', loc='left', color='#000000')
        ax2.set_xlim(0, 1.0)
        ax2.set_ylim(0.35, 1.45)

        # Unified single shared legend centered below both panels
        fig.legend(lines, labels, loc='lower center', bbox_to_anchor=(0.5, -0.05), ncol=4, frameon=True, fontsize=9.5)

        plt.subplots_adjust(bottom=0.20, wspace=0.25)
        base = os.path.join(self.output_dir, 'fig4_hydraulic_vertical_head_pumping_dynamics')
        fig.savefig(f"{base}.png", dpi=300, bbox_inches='tight')
        fig.savefig(f"{base}.svg", bbox_inches='tight')
        plt.close(fig)
        return base

    def plot_figure_5_ecosystem_services(
        self,
        df_weather: pd.DataFrame,
        df_hydrology: pd.DataFrame,
        df_crop: pd.DataFrame
    ) -> str:
        """Figure 5 — Urban Ecosystem Services & Microclimate Co-Benefits Dashboard."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(11, 8.5))

        eco = UrbanEcosystemServices()
        cool_df = eco.evaporative_cooling(df_hydrology, df_weather)
        storm = eco.stormwater_attenuation(df_hydrology, df_weather)
        pm = eco.particulate_biofiltration(df_weather, df_crop, 'bologna')
        carb = eco.avoided_grid_carbon(3922, 'bologna')

        # Q1: Evaporative Cooling
        monthly_cooling = cool_df.groupby(df_weather['month'])['cooling_energy_kwh_th'].sum()
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        x = np.arange(len(months))
        ax1.bar(x, monthly_cooling, color='#1b9e77', edgecolor='#000000', linewidth=0.5)
        ax1.set_xticks(x)
        ax1.set_xticklabels(months, color='#000000')
        ax1.set_ylabel('Cooling Energy [kWh_th/month]', color='#000000')
        ax1.set_title('(A) Microclimate Sensible Heat Abatement', fontweight='bold', loc='left', color='#000000')

        # Q2: Stormwater Attenuation Fate
        storm_vols = [storm['retained_in_reservoir_l'], storm['overflow_volume_l'], storm['total_rain_volume_l'] - storm['harvested_volume_l']]
        labels = ['Retained for Foliage', 'Reservoir Overflow', 'Uncaptured Runoff']
        ax2.bar(labels, storm_vols, color=['#2b5c8f', '#a6cee3', '#fb9a99'], width=0.5, edgecolor='#000000', linewidth=0.5)
        ax2.set_ylabel('Water Volume [L/yr]', color='#000000')
        ax2.set_title('(B) Stormwater Runoff Attenuation Fate', fontweight='bold', loc='left', color='#000000')

        # Q3: Particulate Bio-Filtration
        pm_types = ['PM2.5 Interception', 'PM10 Interception']
        pm_vals = [pm['annual_pm25_filtered_g'], pm['annual_pm10_filtered_g']]
        ax3.bar(pm_types, pm_vals, color=['#7570b3', '#e7298a'], width=0.45, edgecolor='#000000', linewidth=0.5)
        ax3.set_ylabel('Particulate Mass Captured [g/yr]', color='#000000')
        ax3.set_title('(C) Particulate Dry Deposition on Ivy Foliage', fontweight='bold', loc='left', color='#000000')
        ax3.set_ylim(0, 22)

        # Q4: Avoided Grid Operational Carbon
        categories = ['vs Legacy HPS (150W)', 'vs Modern Grid LED (50W)']
        co2_vals = [carb['avoided_co2e_vs_hps_kg'], carb['avoided_co2e_vs_grid_led_kg']]
        ax4.bar(categories, co2_vals, color=['#d95f02', '#2b5c8f'], width=0.45, edgecolor='#000000', linewidth=0.5)
        ax4.set_ylabel('Avoided Carbon Emissions [kg CO2e/yr]', color='#000000')
        ax4.set_title('(D) Avoided Municipal Grid Operational Carbon', fontweight='bold', loc='left', color='#000000')
        ax4.set_ylim(0, 180)

        plt.subplots_adjust(hspace=0.35, wspace=0.25, bottom=0.08)
        base = os.path.join(self.output_dir, 'fig5_urban_ecosystem_services_dashboard')
        fig.savefig(f"{base}.png", dpi=300, bbox_inches='tight')
        fig.savefig(f"{base}.svg", bbox_inches='tight')
        plt.close(fig)
        return base

    def plot_figure_6_multi_city_frontier(
        self,
        multi_city_metrics: dict
    ) -> str:
        """Figure 6 — Multi-City Climate Feasibility & Storage Frontier."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(10.5, 8.0))

        cities = list(multi_city_metrics.keys())
        x = np.arange(len(cities))
        w = 0.45
        labels = [c.capitalize() for c in cities]

        solar_yield = [multi_city_metrics[c]['solar_generation_kwh'] for c in cities]
        ax1.bar(x, solar_yield, w, color='#e6ab02', edgecolor='#000000', linewidth=0.5)
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, color='#000000')
        ax1.set_ylabel('Solar Yield [kWh/yr]', color='#000000')
        ax1.set_title('(A) Annual Photovoltaic Canopy Generation', fontweight='bold', loc='left', color='#000000')
        ax1.set_ylim(0, 300)

        bat_req = [multi_city_metrics[c]['req_battery_kwh_99pct'] for c in cities]
        ax2.bar(x, bat_req, w, color='#2b5c8f', edgecolor='#000000', linewidth=0.5)
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, color='#000000')
        ax2.set_ylabel('Required Battery Capacity [kWh]', color='#000000')
        ax2.set_title('(B) Battery Sizing for 99% Winter Reliability', fontweight='bold', loc='left', color='#000000')
        ax2.set_ylim(0, max(bat_req) * 1.25)

        rain_harvested = [multi_city_metrics[c]['rain_harvested_l'] for c in cities]
        ax3.bar(x, rain_harvested, w, color='#1b9e77', edgecolor='#000000', linewidth=0.5)
        ax3.set_xticks(x)
        ax3.set_xticklabels(labels, color='#000000')
        ax3.set_ylabel('Rainwater Harvested [L/yr]', color='#000000')
        ax3.set_title('(C) Annual Harvested Precipitation Inflow', fontweight='bold', loc='left', color='#000000')
        ax3.set_ylim(0, max(rain_harvested) * 1.2)

        sufficiency = [multi_city_metrics[c]['water_self_sufficiency_pct'] for c in cities]
        ax4.bar(x, sufficiency, w, color='#7570b3', edgecolor='#000000', linewidth=0.5)
        ax4.set_xticks(x)
        ax4.set_xticklabels(labels, color='#000000')
        ax4.set_ylabel('Water Self-Sufficiency [%]', color='#000000')
        ax4.set_title('(D) Foliage Irrigation Water Self-Sufficiency', fontweight='bold', loc='left', color='#000000')
        ax4.set_ylim(0, 115)

        plt.subplots_adjust(hspace=0.35, wspace=0.25, bottom=0.08)
        base = os.path.join(self.output_dir, 'fig6_multi_city_climate_feasibility_frontier')
        fig.savefig(f"{base}.png", dpi=300, bbox_inches='tight')
        fig.savefig(f"{base}.svg", bbox_inches='tight')
        plt.close(fig)
        return base


# Functional adapters
def plot_figure_1_annual_resource_balance(df_excel, df_sim, output_dir='figures'):
    return PlantpostPlotter(output_dir).plot_figure_1_annual_resource_balance(df_sim)

def plot_figure_2_winter_stress_soc(df_w, sim_dict, output_dir='figures'):
    return PlantpostPlotter(output_dir).plot_figure_2_winter_stress_soc(df_w, sim_dict)

def plot_figure_3_tank_storage_drought(df_w, df_h, output_dir='figures'):
    return PlantpostPlotter(output_dir).plot_figure_3_tank_storage_drought(df_w, df_h)

def plot_figure_4_hydraulics_pumping(output_dir='figures'):
    return PlantpostPlotter(output_dir).plot_figure_4_hydraulics_pumping()

def plot_figure_5_ecosystem_services(df_w, df_h, df_c, output_dir='figures'):
    return PlantpostPlotter(output_dir).plot_figure_5_ecosystem_services(df_w, df_h, df_c)

def plot_figure_6_multi_city_frontier(metrics, output_dir='figures'):
    return PlantpostPlotter(output_dir).plot_figure_6_multi_city_frontier(metrics)
