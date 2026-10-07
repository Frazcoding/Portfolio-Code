#!/usr/bin/env bash
# Gate B chain (2026-10-03): sweep -> rank -> refine -> size -> LP -> EN 13031 -> RFQ quantities -> thesis test
set -e
cd "$(dirname "$0")"
python site_opt.py 100 cucumber tomato
python site_rank.py > results/site_opt/ranking_print.txt
python refine.py
python size_study.py
python en13031.py
python finalist_lp.py 2>&1 | grep -E "GBP/kg|: [0-9]+ s|Error|Traceback"
python rfq_quantities.py cucumber > results/site_opt/rfq_cucumber.md
python tests/test_reproduce.py 2>&1 | tail -3
echo CHAIN_DONE
