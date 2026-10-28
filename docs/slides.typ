// Slides wired to the latest run (see report.typ).
#import "style/fraser.typ": *

#let k = json("kpis.json")

#show: slides.with(title: k.project + " — hub sizing and operation")

#title-slide(k.project, subtitle: k.origin + " to " + k.dest + " · hub " + k.site + " · run " + k.run)

#slide("Headline results")[
  #grid(columns: (1fr, 1fr, 1fr, 1fr), column-gutter: 10pt,
    kpi(k.fmt.fleet_total, "Coaches", size: 26pt),
    kpi(k.fmt.total_chargers, "Chargers", size: 26pt),
    kpi(k.fmt.drivers, "Drivers", size: 26pt),
    kpi(k.fmt.gbp_per_trip, "£ per trip", size: 26pt))
  #v(14pt)
  - Every #k.headway_min min, #k.distance_km km one way, #k.charge_power_kW kW chargers
  - Substation #k.fmt.substation_kVA kVA; peak load #k.fmt.peak_kVA kVA (sheet), #k.fmt.sim_peak_kVA kVA simulated
  - #k.fmt.sim_on_time_pct % of simulated departures on time
]

#slide("The operating day")[
  #align(center, image("figures/day.svg", height: 100%))
]

#slide("Candidate sites")[
  #align(center, image("figures/sites.svg", height: 100%))
]
