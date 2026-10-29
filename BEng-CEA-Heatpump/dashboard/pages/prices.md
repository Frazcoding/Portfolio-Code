---
title: Prices and harvest
sidebar_position: 3
---

<script>
  const style = { legend: { type: 'plain', top: 'auto', bottom: 0 }, grid: { bottom: 80 } };
</script>

The sale price is set a little below import parity: the monthly import CIF price plus haulage to the retailer
distribution centre. No supermarket contract price backs it yet (HANDOFF BP5, BP30).

## Lead design: harvest by month against import parity

```sql monthly
select m.month, m.harvest_share as share_of_harvest, m.parity_gbp_kg as import_parity
from cea.lead_monthly m
join (select distinct case_id from cea.lead_cases where is_lead) l using (case_id)
order by m.month
```

<BarChart chartAreaHeight=300 data={monthly} x=month y=share_of_harvest y2=import_parity y2SeriesType=line xAxisTitle="Month [-]" yAxisTitle="Share of annual harvest [-]" y2AxisTitle="Import parity [£/kg]" yFmt=pct0 y2Fmt=gbp2 echartsOptions={style} />

## UK wholesale and import prices

```sql crops
select distinct crop from cea.import_cif order by crop
```

<Dropdown data={crops} name=crop value=crop defaultValue="cucumber" title="Crop" />

```sql market
select cast(date as date) as date, 'Import CIF (monthly)' as series, gbp_kg_cif as gbp_kg
from cea.import_cif where crop = '${inputs.crop.value}'
union all
select date_trunc('month', cast(date as date)) as date, 'UK wholesale (DEFRA, monthly mean)' as series, avg(gbp_kg) as gbp_kg
from cea.uk_wholesale where crop = '${inputs.crop.value}' and cast(date as date) >= date '2023-01-01'
group by 1
order by date
```

<LineChart chartAreaHeight=300 data={market} x=date y=gbp_kg series=series xAxisTitle="Date [-]" yAxisTitle="Price [£/kg]" yFmt=gbp2 echartsOptions={style} />

UK wholesale (DEFRA) mostly sits below the import CIF price. This is why the plan needs a contract priced against
imports rather than a sale into the wholesale market. Gaps are months with no DEFRA quote.
