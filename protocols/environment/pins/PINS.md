# Pinned environment of the 6 Nov 2026 Cu–Zr and Cr–Ni picks

Recorded on 6 Nov 2026 between 07:40 and 07:50 CST. Collection was read-only except for one `docker run --rm` for the image's pip freeze and the detached image archive on spark1 (`docker save`, nice 19 / ionice idle). No running container was touched.

## MLIP container (closes Q22)

| item | value | file |
|---|---|---|
| image | `cuzr-phaseforge-grace-gpu:20261104`, local build, no registry digest | `spark1_container.txt` |
| image id | `sha256:ac223e2cfa3e630e957514574600bed099cdc934993493ff8cad9eb9ea48a98c` (arm64, linux, created 2026-11-04T12:20:40-06:00, 18.5 GB) | `spark1_container.txt` |
| recipe | `spark1:<home>/runs/cuzr-fresh-phaseforge-20261104/code/Dockerfile` (sha256 561dee68…) on `nvcr.io/nvidia/tensorflow:25.02-tf2-py3` with materialsframework 1.0.0 and tensorpotential 0.6.2.1 | `spark1_dockerfile.txt` |
| pip freeze inside the image | 200 lines | `spark1_container.txt` |
| archive | `spark1:<home>/archive/orchid-images/cuzr-phaseforge-grace-gpu_20261104.tar.gz` (+ `.sha256` when `docker save` ends; started 07:45 CST, PID 1690972) | — |
| containers | every `cuzr-*` and `crni-*` container on spark1 runs on image id ac223e2c…; their env, command and binds are recorded | `spark1_container.txt` |

The Cr–Ni "standard sqscal" and fork images (`phaseforge-standard-atat352:20261106`, `phaseforge-orchid-mscraps:*`) produced nothing used in either pick (crni-phaseforge NOT_USED.md).

## MLIP weights

GRACE-2L-SMAX-OMAT-large and GRACE-2L-OMAT have identical files (by sha256) in all three run roots on spark1 (`<home>/runs/{cuzr-protocol-oneshot-20261106,crni-phaseforge-20261105,cuzr-fresh-phaseforge-20261104}/inputs/potential/`). Hashes are in `spark1_mlip_weights_sha256.txt`.

The public source is recorded in `.grace_origin.json` (`spark1_mlip_weights_origin.json.txt`):

| model | source | tag |
|---|---|---|
| GRACE-2L-SMAX-OMAT-large | https://huggingface.co/AMS-ICAMS-RUB/grace-foundation-models/resolve/model-v5-uq-v6/models/GRACE-2L-SMAX-OMAT-large-model.tar.gz | model-v5-uq-v6 |
| GRACE-2L-OMAT | https://huggingface.co/AMS-ICAMS-RUB/grace-foundation-models/resolve/kk/models/GRACE-2L-OMAT-model.tar.gz | kk |

## PhaseForgePlus (closes Q24)

| copy | identity |
|---|---|
| Studio `<home>/src/PhaseForgePlus` | git c66656faad884c7ed11354417bc89074665a74f3, clean |
| spark1 `<home>/runs/cuzr-protocol-oneshot-20261106/src/PhaseForgePlus` (Cu–Zr fits) | not a git checkout; its 406 files are identical one by one to the Studio c66656f tree (`spark1_phaseforgeplus_files.sha256`; `hinge.py` 892c139f…) |

## Interpreters (closes Q23 for the environment part)

| interpreter | used by | lock |
|---|---|---|
| Studio `<fit-env>` (py 3.12.14; espei 0.8.11.dev82+g9039ea215, pycalphad 0.11.3.dev35+g9a6939dd2, numpy 2.5.4, scipy 1.18.1) | Cr–Ni fits, evaluation, Laplace; Cu–Zr ranking and evaluation | `studio_espei-pr268.lock.txt` |
| spark1 `<home>/orchid-crni-mcmc-20261105/env/grad` (same espei/pycalphad/numpy/scipy) | Cu–Zr fits (run 1) | `spark1_envs_hardware.txt` |
| spark1 `<home>/orchid-crni-mcmc-20261105/env/uq` (espei 0.9.0, pycalphad 0.11.2) | not used by either pick (MCMC environment) | `spark1_envs_hardware.txt` |
| Studio `<home>/.venvs/phaseforge` (m_scraps 0.6.0, ase 3.29.0) | SQS generation | `studio_phaseforge.lock.txt` |
| container python 3.12 (TF 2.17.0 NGC 25.02) | MLIP relaxations and MD | `spark1_container.txt` |

## Hardware, threads and determinism flags as used

| stage | host | threads and flags | deterministic? |
|---|---|---|---|
| MLIP solids and liquid MD | spark1: NVIDIA GB10 (driver 580.178.04), 20 Arm cores (Cortex-X925 + A725) | `OMP_NUM_THREADS=1`, `TF_FORCE_GPU_ALLOW_GROWTH=true` set in the scripts; image default `OMP_NUM_THREADS=2`, `OPENBLAS_NUM_THREADS=2`, `XLA_FLAGS=--xla_gpu_cuda_data_dir=/opt/cuda13` (overrides the image's `--xla_gpu_enable_triton_gemm=false`); no `TF_DETERMINISTIC_OPS` | no: GPU reductions are not bitwise stable; tolerance rule |
| Cu–Zr fits | spark1 CPU | `OMP_NUM_THREADS=1` per start, one process per start | bitwise on the same host and build; tolerance across hosts |
| Cr–Ni fits | Studio (Apple M1 Max, 10 cores, 64 GB, macOS 14.3) | `multiprocessing` spawn pool of 4 workers, one start per worker; BLAS threads not limited (Accelerate) | see the determinism check (F) |
| ranking and evaluation | Studio | single process | deterministic |

## PhaseForge+ source pin (6 Nov 2026, crni-paper-fit-step4c-b@1.0.1)

`spark1_phaseforgeplus_src_files.sha256` lists the 10 source files of the c66656f tree (the 9 files under `src/` and `pyproject.toml`), taken line by line from `spark1_phaseforgeplus_files.sha256`; caches (`.pytest_cache`, `.ruff_cache`), `.git`, tests, examples and documentation are left out. A specific protocol selects it through the file with id `source_pin` of its `phaseforgeplus` code entry (`orchid_reproduce.py`, `sage_mcp`); a protocol without that entry keeps the full-checkout list, so earlier reruns are judged as before. The spark1 copy `<home>/orchid-crni-mcmc-20261105/src/PhaseForgePlus` matches all 10 (checked 6 Nov, 21:57 CST).
