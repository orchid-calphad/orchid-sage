# Q39: gradient ESPEI analytic vs finite-difference gradients at fit endpoints

Local diagnosis, 6 Nov 2026 (laptop mac-studio). Build: gradient ESPEI 0.8.11.dev82+g9039ea215
(`<fit-env>`, source `<home>/src/ESPEI-grad` @ 9039ea2, Gradient-based_update), pycalphad 0.11.3.dev35+g9a6939dd2.
Nothing was patched or installed. Not yet sent to anyone: any contact with Brandon Bocklund needs the PI's go.

## Result

**The analytic gradients of `ActivityResidual` and `ZPFResidual` are correct. The discrepancy with central finite
differences reported in Q39 comes from kinks, not from a code bug.** At both endpoints, one or more data points sit
exactly on a phase boundary of the model:

- **Cr–Ni step 3b, s1 endpoint.** The activity point x_Cr = 0.35 at 1073.15 K (Pugliese 1970) sits on the FCC_A1 / FCC_A1+CRNI2
  boundary. At θ* the equilibrium there is single FCC. A step of −1e-4 in VV0013 (CRNI2 b) makes CRNI2 stable, with an NP of 0.002.
  A second point, Katayama 1783 K x_Ni = 0.2996, sits on the LIQUID / LIQUID+BCC_A2 boundary (BCC at NP = 0).
- **Cu–Zr H1, s1 endpoint.** The model's LIQUID + CUZR2 + BCC_A2 eutectic is exactly at 1268 K, the temperature of the
  Turchanin 2008 and Lundin 1953 invariant regions. The equilibria at the hyperplane vertices therefore switch between
  CUZR2+BCC, CUZR2+LIQUID and LIQUID+BCC on either side of θ*.
- **Cu–Zr H1, s2 endpoint (not in the 6 Nov report).** This one is a jump in the objective, not a kink. A failed
  equilibrium is scored as a driving force of 0; see the section below the endpoint table.

At a kink, the forward and backward slopes differ, and the central FD is their average at every small step. Hence the
6 Nov test, "FD stable at 1e-3 and 1e-4 (1e-4 and 1e-5)", cannot tell a kink from a bug. The test that can is one-sided slopes
at two steps, and it shows kinks. The analytic gradient is the exact derivative for the assemblage pycalphad finds at θ*,
which is one of the one-sided derivatives. For the ZPF hyperplane, the average over the vertices is taken with each
vertex on its own side, so the result can match neither side.

Evidence:

1. **Smooth residuals agree to rounding at every endpoint checked.** We split every endpoint's term gradient into
   residuals with equal one-sided slopes ("smooth") and residuals whose one-sided slopes differ ("kinked").
   - On the smooth residuals, analytic and central FD agree to between 1e-9 and 6e-7 relative.
   - The kinked residuals carry the whole discrepancy: Cr–Ni s1 1.3458 of 1.3467, Cu–Zr s1 0.3064 of 0.3070.
   - See `endpoints_check.json`.
2. **Off the kinks, the whole term agrees.** At points θ* + 1e-2·scale·N(0,1) (seeds 1–3) the relative difference is
   1e-9 to 3e-7 (`endpoints_check.json`, `results_*.json`).
3. **Minimal cases.** One activity point and two ZPF regions reproduce the discrepancy (`reproduce_q39.py`):
   - Cr–Ni: the single point gives analytic 0.077 against central FD 1.376.
   - Cu–Zr: the two regions give 0.055 against 0.266.

   Their one-sided slopes stay different at steps of 1e-4 and 1e-6. Off the kink, both cases agree to < 3e-7.

**No fix to ESPEI is implied.** The objective is non-differentiable where a data point sits on a model phase boundary. The
fits converge onto such points because the log-likelihood has a local maximum there with a kink (it drops on both sides,
as the 6 Nov line probe found). Any remedy is a protocol choice for the PI (Q39 options: a non-smooth stationarity test,
smoothing, or flagging boundary points), not a gradient patch. Replacing these terms by central FD in polish_starts does not
make the gradient "correct": at a kink, FD returns the average of the two sides, which is not a gradient either.

## Contents

- `reproduce_q39.py`: minimal reproducer. Run as `OMP_NUM_THREADS=1 python reproduce_q39.py [crni|cuzr|all]`; it takes
  about 1 min and writes `results_crni.json` and `results_cuzr.json`.
- `data/`
  - `crni.tdb`: the Cr–Ni step-2 pick TDB. All 14 VV symbols are fitted, so the TDB values are overridden.
  - `crni_activity_1073K_xCr0.35.json`: one Pugliese 1970 point (set-E weight).
  - `cuzr.tdb`: the Cu–Zr step-2 TDB, the H1 start. Its unaries are taken from CuZr-94Zen-LB.
  - `cuzr_zpf_turchanin2008_1268K.json` and `cuzr_zpf_lundin1953_1268K.json`: one ORCHID invariant region each.
  - `endpoints.json`: θ* of both endpoints, with their sources.
- `kinkcheck.py`: the residual-level check (analytic, central, forward and backward FD per residual, with the
  smooth/kinked split) on the full data of each fit term. It needs the staged roots described in its docstring.
- `endpoints_check.json`: kinkcheck results at Cr–Ni 3b s0–s7 and Cu–Zr H1 s0–s2 (the pre-polish fit endpoints of
  spark1), and at three nearby points each for Cr–Ni s1 and Cu–Zr s1.
- `results_crni.json`, `results_cuzr.json`: outputs of the minimal reproducer (the expected numbers).

## Expected numbers (minimal reproducer)

| case | logL | analytic norm | central FD 1e-3 / 1e-4 / 1e-5 | fwd − bwd at 1e-4 / 1e-6 | largest component | nearby points, rel. diff |
|---|---|---|---|---|---|---|
| Cr–Ni, 1 activity point | −8.94770 | 0.0772 | 1.3801 / 1.3764 / 1.3071 | 2.68 / 1.28 | VV0013: analytic 0, fwd 0, bwd 0.895 (CRNI2 appears for −1e-4) | 2.2e-7, 2.8e-7, 1.0e-7 |
| Cu–Zr, 2 ZPF regions | −46.97995 | 0.0554 | 0.2718 / 0.2662 / 0.2656 | 0.694 / 0.690 | VV0035: analytic 0.043, fwd −0.399, bwd 0.070 (vertex x_Zr 0.72 switches CUZR2+BCC → CUZR2+LIQUID; 0.94 switches LIQUID+BCC → BCC+CUZR2) | 1.4e-9, 2.6e-9, 2.2e-7 |

### Full fit terms at the endpoints (endpoints_check.json)

| endpoint | residuals (kinked) | analytic | central FD | diff | of which kinked | smooth residuals, rel. diff |
|---|---|---|---|---|---|---|
| Cr–Ni 3b s0 | 113 (1) | 2.6989 | 2.7582 | 0.127 | 0.127 | 4.9e-9 |
| Cr–Ni 3b s1 | 113 (2) | 2.7596 | 3.4839 | 1.347 | 1.346 | 3.7e-9 |
| Cr–Ni 3b s2 | 113 (2) | 2.8866 | 3.5032 | 1.370 | 1.369 | 3.0e-9 |
| Cr–Ni 3b s3 | 113 (1) | 2.8841 | 3.5470 | 1.355 | 1.355 | 2.7e-9 |
| Cr–Ni 3b s4 | 113 (2) | 2.7557 | 3.4870 | 1.356 | 1.355 | 5.6e-9 |
| Cr–Ni 3b s5 | 113 (2) | 2.8057 | 3.3279 | 1.210 | 1.209 | 1.5e-9 |
| Cr–Ni 3b s6 | 113 (1) | 2.7754 | 3.4719 | 1.373 | 1.372 | 2.6e-9 |
| Cr–Ni 3b s7 | 113 (1) | 2.8664 | 3.5055 | 1.316 | 1.315 | 1.1e-9 |
| Cr–Ni s1 + 1e-2 N(0,1), seeds 1–3 | 113 (0) | 4.39 / 4.44 / 4.36 | same | rel. 1.3e-7 / 1.7e-7 / 5.7e-8 | 0 | ≤ 6e-7 |
| Cu–Zr H1 s0 | 233 (3) | 6.6907 | 6.6907 | rel. 5e-8 | 0 | 1.6e-8 |
| Cu–Zr H1 s1 | 233 (7) | 8.5540 | 8.6901 | 0.307 | 0.306 | 2.1e-8 |
| Cu–Zr H1 s2 | 233 (5) | 7.5663 | 82.967 | 87.2 | 0 (a jump in the objective, see below) | 1.5e-8 |
| Cu–Zr s1 + 1e-2 N(0,1), seeds 1–3 | 233 (3–4) | 7.83 / 9.17 / 10.21 | 7.83 / 9.17 / 10.17 | rel. 4e-8 / 4e-8 / 4.2e-3 | 0 / 0 / 0.043 (seed 3 lands on another kink) | ≤ 2e-8 |

Residuals counted as kinked that add no difference have only curvature-level differences between their one-sided slopes.

**Cu–Zr H1 s2: a discontinuity, not a kink.** Residual 148 (Turchanin 2008, region 0, 1158 K: LIQUID at x_Zr 0.382 + CU8ZR3 + CU10ZR7)
is exactly 0 at θ*. There the equilibrium at its only hyperplane vertex does not converge: there are no phases and MU is NaN.
ESPEI then scores the region's driving forces as 0 (`espei/error_functions/zpf_error.py:444-450`). At θ* ± 1e-4 the
equilibrium converges (CU8ZR3+CU10ZR7) and the LIQUID vertex has a driving force of −111 J/mol. The objective therefore jumps
up at θ*, because a failed equilibrium counts as a perfect fit. The gradient is still right for the function on both sides.
This is the second ESPEI behaviour worth raising upstream, as a design question rather than a gradient bug.

## Timing

No patch, so no timing change. For reference, these are the costs of the term evaluations on the laptop:

| term | value only | value + gradient |
|---|---|---|
| Cr–Ni ActivityResidual (113 points) | 1.3 s | 1.5 s |
| Cu–Zr ZPFResidual (233 driving forces) | 0.7–0.9 s | 1.2–1.4 s |

A central-FD gradient costs 2n value evaluations: 28 × 1.3 s ≈ 37 s for Cr–Ni and 38 × 0.75 s ≈ 29 s for Cu–Zr. The analytic
gradient costs about 0.2–0.5 s on top of the value.
