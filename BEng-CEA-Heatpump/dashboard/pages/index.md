---
title: Lead case
sidebar_position: 1
---

<script>
  const style = { legend: { type: 'plain', top: 'auto', bottom: 0 }, grid: { bottom: 80 } };
</script>

Lit lead study (HANDOFF BP37a, `lca/results/bplan/lit_open.json`): 2.9 ha single glass, 150 umol LEDs, two PPA turbines,
cucumber, Stranraer. The price is set below monthly import parity. Cash flow is pre-tax and in real terms; the finance
model with tax and CPI (BP33) is not built yet.

```sql price_cases
select distinct price_case from cea.lead_cases order by price_case
```

<Dropdown data={price_cases} name=price_case value=price_case defaultValue="undercut 10%" title="Price below import parity" />

```sql lead
select * from cea.lead_cases
where is_lead and price_case = '${inputs.price_case.value}'
```

<BigValue data={lead} value=capex_gbp title="Capex" fmt=gbp2m />
<BigValue data={lead} value=price_gbp_kg title="Sale price (£/kg)" fmt=gbp2 />
<BigValue data={lead} value=lcop_8pct title="Cost at 8 % (£/kg)" fmt=gbp2 />
<BigValue data={lead} value=irr title="Project IRR" fmt=pct1 />
<BigValue data={lead} value=payback_yr title="Payback (yr)" fmt=num1 />
<BigValue data={lead} value=npv_8pct title="NPV at 8 %" fmt=gbp2m />
<BigValue data={lead} value=yield_kg_m2 title="Yield (kg/m²)" fmt=num1 />
<BigValue data={lead} value=carbon_kg_kg title="Carbon (kg CO2e/kg)" fmt=num2 />

## All designs at this price

```sql designs
select label, capex_gbp, yield_kg_m2, price_gbp_kg, lcop_8pct, lcop_3p5pct, irr, payback_yr, npv_8pct,
       carbon_kg_kg, winter_share
from cea.lead_cases
where price_case = '${inputs.price_case.value}'
order by lcop_8pct
```

<DataTable data={designs} rows=all>
  <Column id=label title="Design" />
  <Column id=capex_gbp title="Capex" fmt=gbp2m />
  <Column id=yield_kg_m2 title="Yield (kg/m²)" fmt=num1 />
  <Column id=price_gbp_kg title="Price (£/kg)" fmt=gbp2 />
  <Column id=lcop_8pct title="Cost 8 % (£/kg)" fmt=gbp2 />
  <Column id=lcop_3p5pct title="Cost 3.5 % (£/kg)" fmt=gbp2 />
  <Column id=irr title="IRR" fmt=pct1 />
  <Column id=payback_yr title="Payback (yr)" fmt=num1 />
  <Column id=npv_8pct title="NPV 8 %" fmt=gbp2m />
  <Column id=carbon_kg_kg title="kg CO2e/kg" fmt=num2 />
  <Column id=winter_share title="Winter share" fmt=pct0 />
</DataTable>

## Where the capital goes (lead design)

```sql capex
select replace(x.component, '_', ' ') as component, x.gbp
from cea.lead_capex x
join (select distinct case_id from cea.lead_cases where is_lead) l using (case_id)
where x.gbp > 0
order by x.gbp desc
```

<BarChart chartAreaHeight=300 data={capex} x=component y=gbp legend=false swapXY=true sort=false yAxisTitle="Capex [£]" yFmt=gbp1m echartsOptions={style} />

## What a kilo costs to run (lead design)

```sql cost
select replace(c.item, '_', ' ') as item, c.gbp_kg
from cea.lead_cost_per_kg c
join (select distinct case_id from cea.lead_cases where is_lead) l using (case_id)
where c.gbp_kg > 0
order by c.gbp_kg desc
```

<BarChart chartAreaHeight=300 data={cost} x=item y=gbp_kg legend=false swapXY=true sort=false yAxisTitle="Operating cost [£/kg]" yFmt=gbp2 echartsOptions={style} />

Capital recovery is not in this chart. It is the gap between the operating cost here and the 8 % levelised cost above.
