#!/bin/sh
# Full Gate B chain after the R6-R8 model changes (run once, in order). Log: results/site_opt/R6_chain.log
PY="C:/Users/frase/.venvs/portfolio/Scripts/python.exe"
cd "$(dirname "$0")"
for step in "site_opt.py 100 cucumber tomato" "site_rank.py" "refine.py" "size_study.py" "en13031.py" "finalist_lp.py"; do
  echo "=== $(date +%H:%M:%S) START $step"
  "$PY" $step || { echo "=== FAILED $step"; exit 1; }
  echo "=== $(date +%H:%M:%S) DONE $step"
done
"$PY" rfq_quantities.py cucumber && echo "=== rfq done"
echo "=== CHAIN COMPLETE $(date +%H:%M:%S)"
