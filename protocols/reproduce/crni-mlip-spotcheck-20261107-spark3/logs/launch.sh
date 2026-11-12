#!/bin/bash
# GPU spot check (PI approval 7 Nov 2026): one SQS cell + one liquid MD state, commands as code/launch_liquid.sh of crni-phaseforge-20261105
R=<home>/orchid-crni-spotcheck-20261107
L=$R/logs/launch.tsv
run () { # name cmd
  docker run -d --gpus all --name $1 --ipc=host -e XLA_FLAGS=--xla_gpu_cuda_data_dir=/opt/cuda13 \
    -v /usr/local/cuda-13.0:/opt/cuda13:ro -v $R:/campaign -v $R/inputs/potential:/root/.cache/grace:ro \
    cuzr-phaseforge-grace-gpu:20261104 sh -c "$2" > /tmp/cid.$$
  cid=$(cat /tmp/cid.$$); pid=$(docker inspect -f "{{.State.Pid}}" $cid)
  printf "%s\t%s\t%s\t%s\n" "$1" "$cid" "$pid" "$(date -u +%FT%TZ)" >> $L
}
run orchid-crni-spot2-solids-20261107 "python -u /campaign/code/relax_solids.py GRACE-2L-SMAX-OMAT-large > /campaign/logs/solids-SMAX.log 2>&1"
run orchid-crni-spot2-liq-x050-N108-T2200 "python -u /campaign/code/run_liquid.py --size 108 --x-ni 0.5 --temperature 2200 --seed 2026110503 > /campaign/logs/liquid-x050-N108-T2200.log 2>&1"
cat $L
