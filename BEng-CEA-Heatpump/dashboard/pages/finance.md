---
title: Cash flow and finance
sidebar_position: 2
---

<script>
  const style = { legend: { type: 'plain', top: 'auto', bottom: 0 }, grid: { bottom: 80 } };
</script>

<Alert status="warning">
Pre-tax, real terms, from vendor_finance.py. Supplier-credit and asset-finance rates are PLACEHOLDERS (BP37d).
Corporation tax, CPI, the year-1 repayment holiday and the DSRA come with finance.py (BP33), which is not built yet.
</Alert>

```sql price_cases
select distinct price_case from cea.lead_cases order by price_case
```

<Dropdown data={price_cases} name=price_case value=price_case defaultValue="undercut 10%" title="Price below import parity" />

## Cumulative cash flow, all designs

```sql cumulative
select c.year, c.cumulative_gbp, k.label
from cea.lead_cashflow c
join (select distinct case_id, label from cea.lead_cases) k using (case_id)
where c.price_case = '${inputs.price_case.value}'
order by k.label, c.year
```

<LineChart chartAreaHeight=300 data={cumulative} x=year y=cumulative_gbp series=label xAxisTitle="Year [-]" yAxisTitle="Cumulative cash flow [£]" yFmt=gbp1m echartsOptions={style} />

## Financing structures, lead design

```sql structures
select f.structure, f.debt_gbp, f.equity_gbp, f.debt_service_yr1_gbp, f.min_dscr, f.equity_irr,
       f.project_irr, f.equity_payback_yr, f.min_price_gbp_kg
from cea.lead_finance f
join (select distinct case_id from cea.lead_cases where is_lead) l using (case_id)
where f.price_case = '${inputs.price_case.value}'
order by f.debt_gbp, f.structure
```

<DataTable data={structures} rows=all>
  <Column id=structure title="Structure" />
  <Column id=debt_gbp title="Debt" fmt=gbp2m />
  <Column id=equity_gbp title="Equity" fmt=gbp2m />
  <Column id=debt_service_yr1_gbp title="Debt service yr 1" fmt=gbp0k />
  <Column id=min_dscr title="Min DSCR" fmt=num2 />
  <Column id=equity_irr title="Equity IRR" fmt=pct1 />
  <Column id=project_irr title="Project IRR" fmt=pct1 />
  <Column id=equity_payback_yr title="Equity payback (yr)" fmt=num1 />
  <Column id=min_price_gbp_kg title="Min price (£/kg)" fmt=gbp2 />
</DataTable>

The minimum DSCR binds in year 1, the ramp-up year at 80 % output. Lenders usually want 1.25 or more.

## Minimum DSCR by design and structure

```sql dscr
select k.label, f.structure, f.min_dscr
from cea.lead_finance f
join (select distinct case_id, label from cea.lead_cases) k using (case_id)
where f.price_case = '${inputs.price_case.value}' and f.debt_gbp > 0
```

<BarChart chartAreaHeight=300 data={dscr} x=label y=min_dscr series=structure type=grouped swapXY=true yAxisTitle="Minimum DSCR [-]" yFmt=num2 echartsOptions={style} />

## Debt tranches, lead design

```sql tranches
select t.structure, t.tranche, t.amount_gbp, t.rate, t.tenor_yr, t.payment_gbp
from cea.lead_tranches t
join (select distinct case_id from cea.lead_cases where is_lead) l using (case_id)
where t.price_case = '${inputs.price_case.value}'
order by t.structure, t.tranche
```

<DataTable data={tranches} rows=all>
  <Column id=structure title="Structure" />
  <Column id=tranche title="Tranche" />
  <Column id=amount_gbp title="Amount" fmt=gbp2m />
  <Column id=rate title="Rate (placeholder)" fmt=pct2 />
  <Column id=tenor_yr title="Tenor (yr)" />
  <Column id=payment_gbp title="Annual payment" fmt=gbp0k />
</DataTable>
