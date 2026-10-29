---
title: Design study
sidebar_position: 4
---

<script>
  const style = { legend: { type: 'plain', top: 'auto', bottom: 0 }, grid: { bottom: 80 } };
</script>

Year-round design-of-experiments with wind scaled to area (HANDOFF BP35b), from `yearround_wind_doe_<crop>.json` and
`yearround_wind_verify_<crop>.json`. The tomato run is partial (BP19h) and resumes on the desktop.

```sql crops
select distinct crop from cea.design_study order by crop
```

<Dropdown data={crops} name=crop value=crop defaultValue="cucumber" title="Crop" />

```sql points
select *
from cea.design_study
where crop = '${inputs.crop.value}' and lcop8 is not null
```

```sql runs
select count(*) as designs from ${points}
```

<BigValue data={runs} value=designs title="Designs run" />

## Levelised cost against area

<ScatterPlot chartAreaHeight=300 data={points} x=d_ha y=lcop8 series=d_wind xAxisTitle="Area [ha]" yAxisTitle="Levelised cost at 8 % [£/kg]" yFmt=gbp2 echartsOptions={style} />

## Levelised cost against capex

<ScatterPlot chartAreaHeight=300 data={points} x=capex y=lcop8 series=d_glazing xAxisTitle="Capex [£]" yAxisTitle="Levelised cost at 8 % [£/kg]" xFmt=gbp0m yFmt=gbp2 echartsOptions={style} />

## Cheapest 15 designs

```sql best
select stage, d_ha, d_glazing, d_ppfd, d_hours, d_wind, d_turbines, capex, y, lcop8, price_cover, carbon, winter_share
from ${points}
order by lcop8
limit 15
```

<DataTable data={best} rows=all>
  <Column id=stage title="Stage" />
  <Column id=d_ha title="Area (ha)" fmt=num2 />
  <Column id=d_glazing title="Glazing" />
  <Column id=d_ppfd title="PPFD (umol)" fmt=num0 />
  <Column id=d_hours title="Light hours" fmt=num1 />
  <Column id=d_wind title="Wind route" />
  <Column id=d_turbines title="Turbines" />
  <Column id=capex title="Capex" fmt=gbp2m />
  <Column id=y title="Yield (kg/m²)" fmt=num1 />
  <Column id=lcop8 title="Cost 8 % (£/kg)" fmt=gbp2 />
  <Column id=price_cover title="Price cover" fmt=num2 />
  <Column id=carbon title="kg CO2e/kg" fmt=num2 />
  <Column id=winter_share title="Winter share" fmt=pct0 />
</DataTable>

Price cover is cost divided by the evidence price. Below 1 means the design pays at that price.
