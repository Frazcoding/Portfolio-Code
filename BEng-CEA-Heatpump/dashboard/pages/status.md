---
title: Status and evidence gaps
sidebar_position: 5
---

<script>
  const style = { legend: { type: 'plain', top: 'auto', bottom: 0 }, grid: { bottom: 80 } };
</script>

Task state comes from `lca/HANDOFF.md`. Input quality comes from `lca/data/input_register.csv` and
`residual_items.csv`. Re-run `python evidence_export.py` after editing any of them.

```sql states
select state, count(*) as items from cea.handoff_items group by state
```

```sql done
select items from ${states} where state = 'done'
```

```sql open
select items from ${states} where state = 'open'
```

```sql blocked
select items from ${states} where state = 'blocked'
```

<BigValue data={done} value=items title="HANDOFF items done" />
<BigValue data={open} value=items title="Open" />
<BigValue data={blocked} value=items title="Blocked on outside input" />

## Blocked and open items

```sql todo
select item, state, case when item like 'BP%' then 'business plan' else 'study backlog' end as track, text
from cea.handoff_items where state <> 'done'
order by case state when 'blocked' then 0 else 1 end, track, item
```

<DataTable data={todo} rows=all>
  <Column id=item title="Item" />
  <Column id=state title="State" />
  <Column id=track title="Track" />
  <Column id=text title="Description" wrap=true />
</DataTable>

## Input quality by group

```sql quality
select "group" as input_group, quality, count(*) as inputs from cea.input_register group by all
```

<BarChart chartAreaHeight=300 data={quality} x=input_group y=inputs series=quality type=stacked swapXY=true yAxisTitle="Inputs [-]" echartsOptions={style} />

## Placeholder inputs

```sql placeholders
select "group" as input_group, input, value, unit, status, source from cea.input_register
where quality = 'placeholder' order by input_group, input
```

<DataTable data={placeholders} rows=20 search=true>
  <Column id=input_group title="Group" />
  <Column id=input title="Input" />
  <Column id=value title="Value" />
  <Column id=unit title="Unit" />
  <Column id=status title="Status" />
  <Column id=source title="Source or note" wrap=true />
</DataTable>

## Residual capex lines awaiting quotes (RFQ_SPEC §3.7)

```sql residual
select label, gbp_m2, fixed_gbp, life_yr, tier, rfq_to from cea.residual_items order by gbp_m2 desc nulls last
```

<DataTable data={residual} rows=all>
  <Column id=label title="Item" />
  <Column id=gbp_m2 title="£/m²" fmt=num1 />
  <Column id=fixed_gbp title="Fixed per site" fmt=gbp0 />
  <Column id=life_yr title="Life (yr)" />
  <Column id=tier title="Evidence tier" />
  <Column id=rfq_to title="Quote from" />
</DataTable>
