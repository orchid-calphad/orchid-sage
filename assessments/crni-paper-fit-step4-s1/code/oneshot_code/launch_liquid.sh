#!/bin/bash
# Launch detached liquid MD containers on spark1 (run there). Records container ids and host PIDs.
R=<home>/runs/crni-phaseforge-20261105
L=$R/logs/launch_liquid.tsv
launch () { # name size x T seed
  docker run -d --gpus all --name crni-liq-$1 --ipc=host -e XLA_FLAGS=--xla_gpu_cuda_data_dir=/opt/cuda13 \
    -v /usr/local/cuda-13.0:/opt/cuda13:ro -v $R:/campaign -v $R/inputs/potential:/root/.cache/grace:ro \
    cuzr-phaseforge-grace-gpu:20261104 sh -c "python -u /campaign/code/run_liquid.py --size $2 --x-ni $3 --temperature $4 --seed $5 > /campaign/logs/liquid-$1.log 2>&1" > /tmp/cid.$$
  cid=$(cat /tmp/cid.$$); pid=$(docker inspect -f '{{.State.Pid}}' $cid)
  printf "%s\t%s\t%s\t%s\n" "crni-liq-$1" "$cid" "$pid" "$(date -u +%FT%TZ)" >> $L
}
launch x050-N864-T2200 864 0.5 2200 2026110560
i=0
for T in 2200 1900; do for x in 0 0.25 0.5 0.75 1; do i=$((i+1))
  tag=$(printf "x%03d-N108-T%s" $(python3 -c "print(int(round($x*100)))") $T)
  launch $tag 108 $x $T $((2026110500+i))
done; done
cat $L
