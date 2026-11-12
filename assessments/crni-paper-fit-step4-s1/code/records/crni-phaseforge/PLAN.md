# Cr–Ni PhaseForge one-shot and corrected Hong–Liu liquid entropy — calculation plan (5 Nov 2026)

Inputs for the unified ORCHID + PhaseForge + PhaseForge+ paper (`<home>/projects/crni-consistent-assessment/paper/OUTLINE.md`, sections 1a, 1b, 7);
protocol `<orchid-sage>/docs/fit_protocol.md` v2.0 (sections 0, 9, 10). Studio = operator and archive; compute on DGX Spark **spark1 only**
(load checked 11:02 local: load 0.15, GPU 0 %, 116 GB free; spark2/spark3 run MCMC, spark4 production: not used).

## Reused from Cu–Zr (`<home>/ScientificRuns/cuzr-fresh-phaseforge-20261104/`)
- Container `cuzr-phaseforge-grace-gpu:20261104` on spark1 (TF 25.02, tensorpotential 0.6.2.1, materialsframework 1.0.0), CUDA 13 mount, `/campaign` bind.
- SQS generator: m_scraps 0.6.0, same objective and figure cutoffs (`code/sqs_mscraps_source.py` → `code/gen_sqs.py`).
- Liquid MD: `code/run_liquid_matrix.py` → `code/run_liquid.py` (same integrators, damping, timestep, sampling intervals, 100 ps production).
- Entropy: corrected Hong–Liu chemical term (`<home>/ScientificRuns/hongliu-chemical-mixing-20261105/hongliu_mixing.py`, pair/quasi-chemical) and the
  campaign VACF vibrational estimator (verbatim functions, via `run_cuzr.py` adapted to Cr–Ni).

## Deviations from Cu–Zr, and why
| item | Cu–Zr | Cr–Ni | why |
|---|---|---|---|
| MLIP | GRACE-2L-OMAT | **GRACE-2L-SMAX-OMAT-large** (solids also cross-checked with GRACE-2L-OMAT) | PI default potential since 31 Oct (memory `mlip-relaxation-protocol`: "never swapped for GRACE-2L-OMAT"); timing test on spark1: same cost at 108 atoms (31 ms/step), 0.29 vs 0.20 s/step at 864 |
| SQS size | 64 atoms | **128 atoms**, 2 seeds per composition | PI rule: solution SQS > 100 atoms, 128 for bcc/fcc; seeds give a configuration spread |
| relaxation | hydrostatic + ions only | **staged** s0 unrelaxed → s1 volume → s2 volume + ions (protocol value) → s3 full shape (lower bound), lattice check after each | PI rule 31 Oct: staged relaxation, keep the interval, never drop |
| liquid T | 2178 K (one T) | **2200 K** primary (all five states), **1900 K** secondary | 2200 K is just above T_m(Cr) = 2180 K (SGTE) and above the whole Cr–Ni liquidus, the analogue of Cu–Zr's choice just above T_m(Zr); 1900 K tests the temperature dependence the protocol asks for (pure Cr and the Cr-rich liquid are undercooled there; crystallization is checked, not assumed) |
| NPT stage | 5 ps, NVT at the final NPT volume | 10 ps, NVT at the mean volume of the last 5 ps | removes a ~1 % volume-fluctuation offset from the enthalpy |

## Calculation list
Solids (one container, sequential, per potential), 128-atom cells:
- BCC_A2: x_Ni 0, 0.0625, 0.125, 0.25, 0.375, 0.5 (2 seeds each for mixed) + bcc Ni reference (x = 1) → 12 cells × 4 stages.
- FCC_A1: x_Ni 0.3125, 0.375, 0.5, 0.625, 0.75, 0.875 (2 seeds) + fcc Cr and fcc Ni references → 14 cells × 4 stages.
- bcc elastic constants C11, C12, C44 (0 K, stress–strain, ions relaxed) at x_Ni 0, 0.125, 0.25, 0.5: 4 × 24 constrained relaxations.
- Pure-element MLIP references are computed and reported; the CALPHAD model keeps the SGTE unaries.
Liquid (detached containers, concurrent on the one GPU), GRACE-2L-SMAX-OMAT-large, 1 atm:
- N = 108: x_Ni 0, 0.25, 0.5, 0.75, 1 at 2200 K and at 1900 K → 10 runs.
- N = 864: x_Ni 0.5 at 2200 K (finite-size check, accept 108 if 100|S108 − S864|/|S864| < 5 % for the vibrational entropy) → 1 run.
- Each: 2 ps premelt (3500 K), 10 ps NPT, 5 ps NVT equilibration, 100 ps NVT production.
Analysis (Studio, CPU): liquid checks (species MSD/diffusion, RDF, no crystallization); H_mix(T) from <U+K>+pV with pure-liquid references at the
same T; corrected Hong–Liu S_chem,ex + VACF S_vib,ex with block and cut-off uncertainties; **ideal-mixing check first** (random label
permutation on the MD neighbour graphs must give S_chem,ex ≈ 0); RK fit of liquid (a_k + b_k T), bcc and fcc (a_k) from s2 energies; one-shot TDB
with SGTE unaries; diagram with pycalphad.

## Estimated wall time (spark1, measured single-job costs)
| block | estimate |
|---|---|
| solids, 2 potentials, incl. elastic | ~1–2 h |
| 10 × 108-atom liquid (117 k steps × 31 ms alone; concurrent, contention assumed ×2–3) | ~2–4 h |
| 864-atom liquid (117 k steps × 0.29 s alone; slowed while the 108 runs share the GPU) | **~10–13 h** (critical path) |
| analysis, TDB, diagram (Studio) | ~1 h |
| **total wall** | **~12–14 h**, below the ~24 h stop threshold → proceed |

If the measured 864-atom rate after launch projects beyond ~24 h, the 1900 K runs are stopped (by their own container names/PIDs) and this is reported.
Failures are listed and the campaign continues.

## Update after launch (17:12 UTC launch; measured 17:25 UTC)
The GB10 GPU is saturated (96 %) with 12 concurrent jobs, so the 108-atom runs are not overhead-bound when packed: measured 0.27 s/step
per 108-atom job with 11 MD jobs + solids sharing the GPU. Wall time is therefore set by total GPU work:
10 × 108-atom (≈ 10 GPU-h) + 864-atom (≈ 9.5 GPU-h) + solids (≈ 1 h) ≈ **20–21 h** wall, finishing ~13:30–14:30 UTC on 6 Nov.
This is still below the ~24 h stop threshold, so nothing is stopped. The 1900 K set will be stopped (own containers only) if pure Cr
crystallizes at 1900 K, since without the pure-Cr reference that set gives no excess quantities.

## Addition (PI via coordinator, 5 Nov): ordered fcc
Reason: higher-order compatibility (partitioned FCC_L12 with disordered part FCC_A1) and the real Pt2Mo-type CrNi2 (oI6) below ~863 K.
Added to the calculation list, same staged protocol (s0 → s3; volume + ions = protocol value; interval kept), both potentials:
- L12 Cr3Ni, L12 CrNi3 (108 atoms), L10 CrNi (108), D022 Cr3Ni, D022 CrNi3 (144) — the set the partitioned model uses; L10/D022 as
  ordering-competition references (not entered into the 2-sublattice L12 TDB) — and Pt2Mo-type CrNi2 (Immm, (420) planes Cr-Ni-Ni, 108 atoms).
  Space groups verified with spglib (`logs/gen_ordered.log`).
- Disordered fcc SQS at the ordered compositions not yet in the grid: x_Ni 0.25 (128 atoms, 2 seeds), 2/3 (108 atoms, 2 seeds).
- Reported: each ordered energy minus the disordered fcc SQS at the same x, and minus the fcc SQS lower hull (expected: L12 above, CrNi2 near/on).
- TDB variant `oneshot_ordered`: FCC_L12 (0.75:0.25) partitioned on FCC_A1, CR:CR = NI:NI = 0 (unary rule), G(CR:NI), G(NI:CR) set so the
  ordered L12 reproduces the MLIP L12 energies; CRNI2 stoichiometric from its MLIP formation energy on fcc references.
Cost: 10 extra cells × 4 stages × 2 potentials ≈ +0.5 h of GPU time, run after the first solids pass (queued, `code/queue_ordered.sh`).
Revised total ≈ 21 h wall, still below the ~24 h threshold.

## PI ruling on references (5 Nov, via coordinator): PhaseForge convention, SGTE standards
Checked in the code: `<home>/projects/phaseforge-orchid/bin/sqscal` (branch orchid/liquid-entropy-protocol @ 77204fd) runs `sqs2tdb -fit`
with `terms.in` = `1,0` and `2,0` for BCC_A2/FCC_A1/HCP_A3, then `sqs2tdb -tdb`. In the written TDB (e.g. PhaseFoundry
HfNbTiV_BCC_PhaseForge_v3.tdb) each end-member is G = E_MLIP(i, lattice) − [E_MLIP(i, lattice) − SGTE(i, lattice)] = SGTE, and the
interaction parameters are fitted to E(SQS) − Σ x_i E_MLIP(i, same lattice). So:
- every pure-element end-member is the SGTE91 unary, including fcc Cr (GFCCCR = GHSERCR + 7284 + 0.163 T) and bcc Ni;
- the MLIP supplies only the mixing energy relative to the same-lattice MLIP end-members (this is what `analyze_solids.py` computes);
- solution phases get L0 only (sqscal default terms); the L0 + L1 fit is kept in results as a diagnostic, not in the TDB.
No alternative referencing enters the main TDB. Each fcc (and bcc) point carries its staged interval [s3 full, s0 unrelaxed] (seed means);
σ = half-width of that interval (or half the seed spread, if larger; floor 0.1 kJ), so the later fit can weigh it.
Expected consequence: the MLIP puts fcc Cr ~37 kJ/mol-atom above bcc Cr (SGTE 7.3 kJ), so mixing energies referenced to MLIP fcc Cr
are strongly negative on the Cr-rich side (≈ −10 kJ/mol-atom at x_Ni 0.25, s2); with SGTE fcc Cr this over-stabilises Cr-rich fcc
in the one-shot diagram. This will be reported from the diagram (fcc single-phase boundary vs T), not corrected in the one-shot.

## End-member convention: what PhaseForge/ATAT actually do (checked 5 Nov; final TDB on hold for the PI)
Source read: ATAT 3.52 `atat/src/sqs2tdb` (Perl; tarball <home>/runs/scraps-perpair/benchmark-20261015/atat3_52.tar.gz, extracted to scratch),
`atat/glue/vasp/robustrelax_vasp`, `atat/src/infdet.c++`; PhaseForge `bin/sqscal`, `bin/robustrelax_MLIP`, `bin/runstruct_MLIP`.
- sqs2tdb -tdb writes G(phase,el) = ABIN_phase_el − REF_phase_el. If the phase exists in ATAT's data/sgte_phases.tdb (FCC_A1, BCC_A2,
  HCP_A3, LIQUID do) and SGTE_phase_el is not listed in an optional user file `exfromsgte.in`, REF = ABIN_phase_el − SGTE_phase_el, so the
  end-member is exactly SGTE. If it is listed, REF uses the element's stable phase: G = SGTE_stable + (ABIN_phase − ABIN_stable), i.e. the
  ab initio (MLIP) lattice stability. Nothing in sqs2tdb detects mechanical instability; exclusion is only by `exfromsgte.in`.
- Inflection detection is ATAT's `robustrelax_vasp -id` (infdet). PhaseForge's `sqscal` never calls it: the default path is
  `runstruct_MLIP` (full relaxation; optional -checkrelax cutoff), and `-vib` adds fitfc + `robustrelax_vasp -vib`, which only copies
  vibrational data (svib_ht). `robustrelax_MLIP` exists as a wrapper but is not used by sqscal. No `exfromsgte.in` is written by PhaseForge.
- So the PhaseForge default is SGTE for every end-member (fcc Cr, bcc Ni included). The Pt-W paper's treatment (inflection detection,
  SGTE excluded for mechanically unstable end-members) is an option a user sets by hand (robustrelax_MLIP -id + exfromsgte.in), not the default.
- PI decision (5 Nov): SGTE reference states for every pure-element end-member, including mechanically unstable ones (fcc Cr at
  SGTE's 7.3 kJ), for compatibility with existing databases. "We do not do inflection detection": the started inflection script was
  stopped (PID 80104, before any result) and moved to attic/inflection_detection_withdrawn_20261105/ with a note; no values exist or
  are reported. The TDB build resumes as planned (PhaseForge convention above; staged interval carried as the fcc uncertainty).

## Results notes (6 Nov, before the 864-atom run ends)
- All 10 liquids are liquid by MSD/diffusion, except pure Cr at 1900 K, which crystallized after 82 ps (2-ps U blocks drop
  −8.88 → −9.06 eV/atom; MSD over the last 20 ps 2 Å²). It is analysed over its first 80 ps only (`LIQUID_WINDOW_PS` in
  analyze_liquid.py), and the 1900 K excess quantities carry that disposition.
- Ideal-mixing check passed: random labels on the MD graphs give |S_chem,ex| ≤ 0.004 J/mol-atom/K.
- Liquid TDB term: L0 only (as for the solids). The first build used L0–L2, which interpolated the three noisy MD points exactly
  (W-shaped H_mix); it was moved to attic/tdb_liquid_L0L2_20261106/.
- SMAX D022 cells first failed with a GPU ResourceExhaustedError (12 jobs sharing the GPU); they were moved aside on spark1
  (attic/failed_D022_OOM_SMAX) and recomputed successfully.
- Paper figures: <home>/projects/2026_arroyave_nicr_paper/scripts/fig_{entropy,energetics,oneshot}.py → figs/, captions in figs/CAPTIONS_draft.md.

## PI decision (6 Nov): disordered fcc only
FCC_A1 only, no partitioned FCC_L12. The oneshot_ordered TDB was withdrawn (attic/tdb_ordered_variant_withdrawn_20261106/).
The L1₂, L1₀ and D0₂₂ energies stay in results/solids_*.json, each labelled "computed, NOT USED". The D0₂₂ retry had already
finished before this decision; no further ordered calculations will be run. Pt₂Mo-type CrNi₂ is a stoichiometric compound (CRNI2,
1:2) in both one-shot TDBs: G = GHSERCR + 2 GHSERNI + 3 H_f, with H_f = −1.90 kJ/mol-atom relative to MLIP bcc Cr and fcc Ni (the
Cu-Zr compound convention). In the one-shot it is not stable, because the over-stabilised fcc (SGTE fcc Cr + MLIP fcc mixing)
lies lower at x_Ni = 2/3.

## Extension (PI decision, 6 Nov): bcc and fcc SQS over the whole composition range
Reason: the bcc grid covered x_Ni 0–0.5 and the fcc grid 0.25–1. Each RK fit therefore extrapolated over the other half of the
range, which is where the one-shot diagram depends on it (Cr-rich fcc, Ni-rich bcc).
Added cells: bcc x_Ni 0.625, 0.75, 0.875, 0.9375 and fcc x_Ni 0.0625, 0.125, 0.1875, 0.9375. All are 128 atoms with 2 seeds
(the same m_scraps generator and seeds; code/gen_sqs_fullrange.py), with the same staged relaxation s0→s3 and lattice checks, on
both potentials (code/relax_solids_v2.py; container crni-solids-fullrange-20261106 on spark1, next to the 864-atom liquid). Cells
that transform are kept, and their interval [s3, s0] is their uncertainty.
Cost: 16 cells × 4 stages × 2 potentials, about 1 h of GPU time shared with the 864 run.
After it finishes, the RK terms are refitted on the full grid and the one-shot TDBs, diagrams and energetics figure are rebuilt.

## STANDARD PhaseForge run (PI decisions 6 Nov; fit_protocol.md Section 0.0a). This is the one-shot used in the paper.
Everything above this section (custom staged SQS relaxations, the full-range custom extension, custom RK fits, the TDBs built
by code/build_tdb.py, and the code/run_liquid.py MD including the 864-atom run) is **non-standard, not used in the paper**. It is
kept, and labelled so in results/NONSTANDARD_NOT_USED.md. The custom full-range container (crni-solids-fullrange-20261106) was
stopped by name on 6 Nov, 03:40 UTC, before it had finished any cell.

**Command** (README "Quick Start" form; the README's example is `sqscal -e Ni,Re -l FCC_A1,HCP_A3 -lv 2 -mlip Grace -model
GRACE-2L-OMAT`, introduced as "Use the `sqscal` command to generate a phase diagram with minimal setup", not as a demo-only setting):

    sqscal -e Cr,Ni -l FCC_A1,BCC_A2,LIQUID -lv 2 -mlip Grace -model GRACE-2L-SMAX-OMAT-large

- **Level 2**, as in the README example. In ATAT's sqsdb, level 2 gives binary levels 0, 1 and 2 (x = 0, 0.25, 0.5, 0.75, 1).
  The LIQUID uses ATAT's own 32-atom liquid SQS at those levels.
- No -vib, -sro or -checkrelax (none appears in the README example).
- Run directory: spark1 <home>/runs/crni-phaseforge-20261105/pf_standard/run (sqscal.log). Container
  crni-pf-standard-sqscal-20261106 (logs/launch_standard.tsv); the 864-atom liquid kept running next to it.

**Software**
- PhaseForge ORCHID branch orchid/liquid-entropy-protocol @ 77204fd (git archive sha256 6c4e79a4…), ternary_search compiled with
  g++ -std=c++14 (the only target of PhaseForge's CMakeLists).
- ATAT 3.52 (atat3_52.tar.gz sha256 8536fb07…), built with make / make install.
- MaterialsFramework 1.0.0 and tensorpotential 0.6.2.1 in the Cu-Zr image cuzr-phaseforge-grace-gpu:20261104.
- GRACE-2L-SMAX-OMAT-large; hashes in provenance/potential_sha256.txt.
- Image: phaseforge-standard-atat352:20261106 (Dockerfile in pf_standard_build/).

**Environment fixes needed to run as documented (no change to the science)**
- tcsh and bc installed, and /bin/sh linked to bash: ATAT's Perl calls use csh-style redirections.
- <home>/.ezvasp.rc plus placeholder POTCARs: ATAT's `runstruct_vasp -nr`, called by runstruct_MLIP to write the POSCAR, will not run
  without them. No VASP is run.
- PhaseForge's `cat > vasp.wrap << 'WRAPEOF'` in runstruct_MLIP and sqscal: in csh the quoted word only matches a line reading
  'WRAPEOF' with the quotes, so the here-document swallowed the rest of the script (verified with tcsh 6.24.10 and BSD csh).
  The quotes were removed in the image copy. The vasp.wrap written is byte-identical to the intended text. Worth reporting upstream.
- runstruct_MLIP prints "then: then/endif not found" from its -checkrelax block (csh evaluates `$?x && "$x"` eagerly). This is
  harmless here: it comes after extract_MLIP, and -checkrelax is not used.

**SQS (PI correction, 6 Nov: m_scraps allowed)**
- Generator: m_scraps 0.6.0, through code/gen_sqs.py make(). Settings: weighted_l1 objective; figure cut-offs in nearest-neighbour
  units (2.05, 1.45, 1.05) for fcc and (2.05, 1.20, 1.05) for bcc; auto_budget 2; 4 ranks.
- 128 atoms; seeds 2026110501 and 2026110502 for bcc, 2026110511 and 2026110512 for fcc.
- Same composition grid for both lattices: x_Ni = 0.0625, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 0.9375.
- The cells are the generator's POSCAR outputs, unchanged, written as ATAT str.out with a 'wait' flag
  (code/prep_standard_sqscal.py; pf_standard/run/mscraps_manifest.json lists source hashes).
- Seed 1 at x 0.25/0.5/0.75 uses ATAT's own directory names, so `sqs2tdb -cp` skips them and adds no ATAT SQS for the solids;
  the other cells are named sqs_lev=ms<k>_…
- Pure end-members (1-atom cells, endmem flag) come from sqscal's own `sqs2tdb -cp`.
- Relaxation, fit and TDB are sqscal's own: runstruct_MLIP → MLIPrelax (MaterialsFramework relax, fmax 0.001), terms.in "1,0 / 2,0",
  sqs2tdb -fit, then sqs2tdb -tdb -oc.

**Liquid**
- Energetics: sqscal's LIQUID path as it stands, in the same run. That is MLIPliquid -dt=50 (T = mean elemental T_m + 50 K;
  MLIPmd = 2000 steps NVT, 1 fs, nose-hoover) inside ternary_search over volume, then sqs2tdb -fit with terms "1,0 / 2,0".
- Entropy: BLOCKED as standard. PhaseForge's only MD entry points are MLIPmd and MLIPliquid. With their defaults they run 2000 steps
  (2 ps) and save only total energies (no positions or velocities). docs/protocols/liquid-entropy.md names no MD entry point and
  says the entropy implementation is "not yet integrated into the PhaseForge command line". So the protocol's 100 ps, 108/864-atom
  trajectories cannot come from a documented PhaseForge entry point. Reported to the PI; no substitute was run.

## ORCHID branch orchid/mscraps-sqs @ 88669ba (instructions of 6 Nov, ~04:00 UTC): BLOCKED, reported, not patched
The earlier ATAT-SQS "STANDARD" attempt (pf_standard/, container crni-pf-standard-sqscal2-20261106) was stopped by name and superseded.
It had used an image in which I had changed the quoted heredoc; that change is withdrawn from the new image.

Image phaseforge-orchid-mscraps:20261106 (pf_mscraps_build/Dockerfile on spark1):
- PhaseForge 88669ba, unmodified (git archive sha256 24fca557…); ternary_search compiled with g++ -std=c++14.
- ATAT 3.52 (8536fb07…).
- m_scraps 0.6.0 (<home>/src/m_scraps @ 776e698, sha256 160b8994…) with icet 4.0, built against Ubuntu OpenMPI.
- MaterialsFramework 1.0.0; GRACE-2L-SMAX-OMAT-large.
- Environment only: tcsh, bc, libopenmpi-dev, openmpi-bin, libeigen3-dev; /bin/sh → bash; OPAL_PREFIX=/usr; system mpirun first on
  PATH (the NVIDIA base's HPC-X mpirun fails against Ubuntu OpenMPI); <home>/.ezvasp.rc plus placeholder POTCARs for runstruct_vasp -nr.

Commands, in spark1 <home>/runs/crni-phaseforge-20261105/pf_mscraps/seed{1,2} (containers crni-pf-mscraps-seed{1,2}-20261106):

    sqscal -e Cr,Ni -l FCC_A1,BCC_A2,LIQUID -lv 5 -mlip Grace -model GRACE-2L-SMAX-OMAT-large -sqs mscraps -n 128 -seed 1 -relaxrange
    (and the same with -seed 2)

Result:
- mscraps_sqsdb worked: FCC/BCC levels 1, 2 and 5 (x_Ni = 1/8 … 7/8) at 128 atoms; LIQUID at 108 atoms.
- sqs2tdb -cp -df= worked: all directories were prepared.
- **Every MLIP calculation was skipped.** relaxrange_MLIP → runstruct_MLIP writes vasp.wrap with `cat > vasp.wrap << 'WRAPEOF'`
  (runstruct_MLIP line 34; sqscal line 168 for LIQUID). Under csh/tcsh (tcsh 6.24.10 here; BSD csh behaves the same) a quoted
  here-document word only ends at a line reading 'WRAPEOF' with the quotes. The here-document therefore takes in the rest of the
  script: vasp.wrap ends with "WRAPEOF / endif / runstruct_vasp -nr / if (! -e POSCAR) …", and runstruct_vasp, MLIPrelax and
  extract_MLIP never run. The log shows, for every structure and mode:
      cat: str_relax.out: No such file or directory
      cat: '.../relaxrange/FCC_A1/<sqs>/<mode>/energy': No such file or directory
  then "sqs_… skipped for property energy … Found no data for energy". The TDB written by sqs2tdb -tdb carries no fitted data.
- Suggested fix, for the branch owner, not applied: write `<< WRAPEOF` without quotes in runstruct_MLIP and sqscal. The text has no
  $ or backquotes, so the result is byte-identical; this was verified in the earlier image.
- Liquid entropy: blocked as before. PhaseForge has no documented MD entry point that writes the 100 ps position/velocity
  trajectories the entropy protocol needs (MLIPmd: 2000 steps, total energies only).

## Correction (PI, 6 Nov): campaign liquid MD is the standard for liquid entropy
The run_liquid.py MD (100 ps production; 108 atoms checked against 864 at x_Ni 0.5 and 2200 K; matched pure-liquid references at
1900 K and 2200 K) is the established liquid-entropy protocol (fit_protocol.md 0.0a corrected). It was taken out of
NONSTANDARD_NOT_USED.md, and the entropy figure and script were restored in the paper repo. The analysis stands as run on 6 Nov:
- liquid checks;
- H_mix(T);
- the ideal-mixing check, passed: |S_chem,ex(random)| ≤ 0.004;
- corrected Hong–Liu S_chem,ex plus VACF S_vib,ex, with block and cut-off uncertainties;
- the pure-Cr reference at 1900 K analysed over the 80 ps before it crystallized.
The finite-size acceptance is added when the 864-atom run ends.
The liquid energetics in the one-shot TDB come from the sqscal LIQUID path (517967b reruns), and are compared with the 100 ps MD H_mix.
Solids: both seeds rerun at 517967b (image phaseforge-orchid-mscraps:20261106-517967b, PhaseForge archive sha256 2aeb35f4…), in
pf_mscraps/seed{1,2}_517967b. The 88669ba directories seed1 and seed2 are kept, each labelled FAILED_heredoc_88669ba.txt.

## PI, 6 Nov ~04:10 UTC: today's detours are WITHDRAWN; the 5 Nov campaign protocol stands
"We cannot change things every time." The protocol is the 5 Nov campaign above:
- m_scraps 128-atom SQS, 2 seeds, both potentials;
- staged relaxation s0 → s3 with lattice checks; s2 (volume + ions, never shape) is the protocol value, s3 the lower bound, and
  the interval is used as σ; every stage is kept;
- the 100 ps liquid MD at 1900 and 2200 K, with 108 vs 864 atoms and the corrected Hong–Liu entropy;
- our RK fit with SGTE end-members.

Changed only by these PI decisions:
1. Whole composition range: the extension above (bcc x_Ni 0.625–0.9375, fcc 0.0625–0.1875 and 0.9375), relaunched with the
   original code as container crni-solids-fullrange2-20261106.
2. Disordered FCC_A1 only. The ordered cells stay computed and unused, CrNi₂ included: the TDB is LIQUID + BCC_A2 + FCC_A1.
3. Alphabetical order, L(CR,NI;k).
4. SGTE for every end-member.

Withdrawn, labelled in results/NOT_USED.md:
- the "standard sqscal" sections above;
- the fork runs pf_standard/ and pf_mscraps/ (tests of the fork, not used; the 517967b containers were stopped by name);
- the "non-standard" labels. The paper figures and scripts are restored, and the fork-based figure scripts sit in
  scripts/forktest/ (not used).
Clarification (coordinator, 6 Nov): "ordered cells unused" means L1₂, L1₀ and D0₂₂ only. Pt₂Mo-type CrNi₂ stays in the one-shot TDB
as a stoichiometric compound: G = GFCCCR + 2 GHSERNI + 3 H_f (SGTE fcc references). H_f is the MLIP s2 (volume + ions) formation
energy relative to fcc Cr and fcc Ni, and σ is half the [s3, s0] interval.

## Status 6 Nov 04:30 UTC (campaign protocol)
- Full-range solids finished on both potentials (crni-solids-fullrange2-20261106), no failures.
- RK fits of the s2 values with σ = half the [s3, s0] interval (seed spread if larger), L(CR,NI;k):
  - SMAX: bcc L0 = +22451, L1 = +38188; fcc L0 = −40467, L1 = −8325 J/mol.
  - OMAT cross-check: bcc +23498 / +29639; fcc −38583 / −5833 J/mol.
- One-shot TDBs in tdb/ (oneshot; oneshot_Sex):
  - LIQUID L0 = −19115 J/mol from the 2200 K MD, with b0 = −1.53 J/mol/K in the S_ex variant;
  - BCC_A2 and FCC_A1 as above;
  - CRNI2 = GFCCCR + 2 GHSERNI − 43488 J/mol-formula (H_f −14.50 ± 0.28 kJ/mol-atom vs fcc refs);
  - SGTE91 unaries throughout; pure-element check passed.
- One-shot diagram: Cr-rich fcc over-stabilised (fcc to x_Ni ≈ 0.26 at 1600 K, congruent melting near 2100 K); eutectic at about
  x_Ni 0.14 and 1745 K; CrNi2 stable up to about 1150 K.
- Figures and CAPTIONS_draft.md are in <home>/projects/2026_arroyave_nicr_paper/figs.
- Pending: the 864-atom run (37 000 of 100 000 production steps at 04:31 UTC, about 5 h left). When it ends: finite-size check,
  then the entropy figure, panel d.

PI ruling (6 Nov): the excess electronic entropy of the Cr-Ni liquid is taken as zero, an assumption for metallic liquids rather than a missing term. It is recorded in liquid_excess_entropy.json (meta.electronic_entropy, meta.S_el_excess_assumption), in code/analyze_liquid.py and in CAPTIONS_draft.md. No numbers change.

Finite-size check (6 Nov, 864-atom run ended about 09:25 UTC): Cr50Ni50 at 2200 K, S_vib 86.96 (108 atoms) vs 87.35 (864 atoms) J/mol-atom/K, a 0.45 % difference, which passes the < 5 % rule; 108 atoms accepted. S_chem,ex is −0.0022 (108) vs −0.0001 (864). The 864-atom liquid is liquid (D_Cr 5.9e-9, D_Ni 6.2e-9 m²/s). Entropy figure panel d is filled. All planned items are complete.

Correction (6 Nov): the "eutectic ~1745 K" reported earlier was the lowest temperature at which any single-phase liquid exists, which is the Ni-side liquidus near x_Ni = 1. It is not the eutectic. Read from the computed diagram, the bcc + liquid + fcc eutectic is about x_Ni 0.14 and 1900 K (one-shot) and about x_Ni 0.13 and 1930 K (with S_ex); ORCHID T7 is 1618 K. Figures restyled to the hero style: one-shot as a single panel with lines, entropy panel d as points, energetics ORCHID ids numbered D1–D7. No data changed.
