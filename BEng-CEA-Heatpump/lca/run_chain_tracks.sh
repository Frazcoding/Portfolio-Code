#!/bin/sh
# R10 chain, both tracks (A waste heat, B no waste heat), central electricity route = owned 2.5 MW turbine, B7 winter-waste
# sensitivity, B8 gutter 4.0 m, 2010 cold-year sensitivity and cold-year-safe LP heat-pump sizing. Logs: results/site_opt*/R10_chain.log
PY="C:/Users/frase/.venvs/portfolio/Scripts/python.exe"
cd "$(dirname "$0")"
for T in A B; do
  export CEA_TRACK=$T
  D=results/site_opt; [ "$T" = B ] && D=results/site_opt_B
  mkdir -p $D
  {
  for step in "site_opt.py 100 cucumber tomato" "site_rank.py" "refine.py" "size_study.py" "en13031.py" "finalist_lp.py" "coldyear.py"; do
    echo "=== $(date +%H:%M:%S) START [$T] $step"
    "$PY" $step || { echo "=== FAILED [$T] $step"; exit 1; }
    echo "=== $(date +%H:%M:%S) DONE [$T] $step"
  done
  "$PY" rfq_quantities.py cucumber && "$PY" rfq_quantities.py tomato && echo "=== rfq done"
  echo "=== TRACK $T COMPLETE $(date +%H:%M:%S)"
  } > $D/R10_chain.log 2>&1 || exit 1
done
echo "=== CHAIN COMPLETE $(date +%H:%M:%S)"
