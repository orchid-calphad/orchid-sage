#!/bin/sh
# Cr-Ni step 3b -> step 4 with polish_starts and the 10a pick (coordinator decision 6 Nov 2026). Run inside a staged Cr-Ni
# root after the step-3b multistart (steps/step3b_thermo_crni2free/multistart.json).
#   sh crni_polish_chain.sh PY PFP_SRC TOOLS_DIR [NPROC]
set -e
PY=$1; export PYTHONPATH=$2; T=$3; N=${4:-8}; export OMP_NUM_THREADS=1
FD=ActivityResidual
pick () {  # step: polish, evaluate, 10a pick, pick TDB
  [ -f steps/$1/polish_report.json ] || "$PY" -u "$T/polish_starts.py" crni $1 --nproc "$N" --max-evals 1000 --fd-terms $FD
  "$PY" -u scripts/evaluate.py $1 > logs/evaluate_$1.log 2>&1
  python3 "$T/pick_start.py" steps/$1 --threshold 1e-3
  P=$(python3 -c "import json;print(json.load(open('steps/$1/pick_protocol_10a.json'))['pick'] or '')")
  if [ -z "$P" ]; then echo "$1: no eligible start; chain stops"; exit 0; fi
  "$PY" -u scripts/evaluate.py $1 "$P" > logs/evaluate_$1_pick.log 2>&1
  echo "$1 pick $P"
}
mkdir -p logs
pick step3b_thermo_crni2free
[ -f steps/step4_solid/multistart.json ] || "$PY" -u scripts/fit.py steps/configs/step4_solid.json "$N" > logs/fit_step4.log 2>&1
pick step4_solid
echo chain done
