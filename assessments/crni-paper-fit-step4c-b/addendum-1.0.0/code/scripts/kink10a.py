"""fit_protocol 10a eligibility test as worded by the PI on 6 Nov 2026 (orchid-sage 6b8f443), shared by the Cr-Ni and Cu-Zr checks.
Identical copies in crni-paper-fit-20261106/scripts and cuzr-protocol-oneshot-20261106/scripts.

eligibility(L, x, scale, g_scaled):
  smooth   analytic gradient norm in the optimiser scaling < THR (1e-3, the plan value);
  kink     otherwise, when the endpoint is kink-stationary: every one-sided directional derivative <= 0, i.e. no improvement above
           1e-6 log-units, along +- the analytic gradient, +- each parameter and 16 seeded random directions (numpy default_rng(20261106),
           standard normal, unit length in the optimiser scaling), at scaled steps 1e-6, 1e-5 and 1e-4;
  not_stationary otherwise. The directional test is run (and reported) for smooth endpoints too.
boundary_points(objs, x, scale): data points that sit on a model phase boundary at the endpoint = activity points and ZPF vertices whose
  one-sided slopes differ (|fwd - bwd| > 1e-2 (1 + |fwd|) for some parameter at h = 1e-4 in the optimiser scaling; the kinkcheck.py
  rule, Q39), each with its residual r, its sigma s and |r|/s ("within its own uncertainty": |r| <= s, the agent's operational
  reading of 10a, labelled).
failed_equilibria(objs, x): ZPF phase regions whose target hyperplane is NaN at x (ESPEI scores them as zero driving force).
Central FD is not used as a gradient."""
import numpy as np

THR = 1e-3
IMPROVE = 1e-6
STEPS = (1e-6, 1e-5, 1e-4)
KTOL = 1e-2


def eligibility(L, x, scale, g_scaled, seed=20261106, n_random=16):
    x = np.asarray(x, float); n = len(x); L0 = L(x)
    gn = float(np.linalg.norm(g_scaled))
    dirs = []
    if gn > 0:
        u = np.asarray(g_scaled, float) / gn
        dirs += [("+grad", u), ("-grad", -u)]
    for i in range(n):
        e = np.zeros(n); e[i] = 1.0
        dirs += [(f"+p{i}", e), (f"-p{i}", -e)]
    rng = np.random.default_rng(seed)
    for k in range(n_random):
        d = rng.standard_normal(n); dirs.append((f"rand{k}", d / np.linalg.norm(d)))
    worst = {"dir": None, "step": None, "improvement": -np.inf}
    viol = []
    for name, d in dirs:
        for s in STEPS:
            imp = L(x + s * scale * d) - L0
            if imp > worst["improvement"]:
                worst = {"dir": name, "step": s, "improvement": float(imp)}
            if imp > IMPROVE:
                viol.append([name, s, float(imp)])
    kink_stationary = not viol
    kind = "smooth" if gn < THR else ("kink" if kink_stationary else "not_stationary")
    return {"kind": kind, "eligible": kind in ("smooth", "kink"), "grad_norm_scaled_analytic": gn, "kink_stationary_test": kink_stationary,
            "n_directions": len(dirs), "steps": list(STEPS), "improvement_tolerance": IMPROVE, "worst_direction": worst,
            "n_violations": len(viol), "violations_first": viol[:10]}


def _activity_labels(r):
    import tinydb
    kw = r._activity_likelihood_kwargs
    dss = kw["datasets"].search((tinydb.where("output").test(lambda o: "ACR" in o)) & (tinydb.where("components").test(lambda c: set(c).issubset(kw["comps"]))))
    out = []
    for ds in dss:
        T = np.ravel(ds["conditions"]["T"]); vals = np.ravel(ds["values"])
        X = [(k, np.ravel(v)) for k, v in ds["conditions"].items() if k not in ("P", "T")]
        for i in range(len(vals)):
            out.append({"reference": ds.get("reference"), "output": ds["output"], "T": float(T[i] if len(T) > 1 else T[0]),
                        "x": {k: float(v[i] if len(v) > 1 else v[0]) for k, v in X}, "value": float(vals[i])})
    return out


def _zpf(z, x):
    from espei.error_functions.zpf_error import calculate_zpf_driving_forces
    p = np.asarray(x, float)[z._sorted_order]
    out = calculate_zpf_driving_forces(z.zpf_data, p, short_circuit=False)
    r = np.concatenate([np.asarray(a, float) for a in out[0]]) if out[0] else np.zeros(0)
    w = np.concatenate([np.asarray(a, float) for a in out[1]]) if out[1] else np.zeros(0)
    return r, 1000.0 / z.weight / w


def _zpf_labels(z):
    lab = []
    for data in z.zpf_data:
        for j, pr in enumerate(data["phase_regions"]):
            for vx in pr.vertices:
                lab.append({"reference": data["dataset_reference"], "region": j, "conditions": {str(a): float(b) for a, b in pr.potential_conds.items()},
                            "phase": vx.phase_name, "composition": {str(a): (None if b is None else float(b)) for a, b in vx.comp_conds.items()},
                            "region_phases": [w.phase_name for w in pr.vertices]})
    return lab


def boundary_points(objs, x, scale, h=1e-4, groups=None):
    from espei.error_functions.activity_error import ActivityResidual
    from espei.error_functions.zpf_error import ZPFResidual
    x = np.asarray(x, float); n = len(x); out = []
    for gi, r in enumerate(objs):
        grp = groups[gi] if groups else ""
        if isinstance(r, ActivityResidual):
            f = lambda xx, r=r: tuple(np.asarray(a, float) for a in r.get_residuals(np.asarray(xx, float)))
            labels = _activity_labels(r); kind = "activity"
        elif isinstance(r, ZPFResidual):
            f = lambda xx, r=r: _zpf(r, xx)
            labels = _zpf_labels(r); kind = "zpf_vertex"
        else:
            continue
        r0, s0 = f(x)
        if r0.size == 0:
            continue
        kinked = np.zeros(r0.size, bool); jumps = np.zeros(r0.size)
        for i in range(n):
            e = np.zeros(n); e[i] = h * scale[i]
            rp, rm = f(x + e)[0], f(x - e)[0]
            fwd, bwd = (rp - r0) / h, (r0 - rm) / h
            kinked |= np.abs(fwd - bwd) > KTOL * (1 + np.abs(fwd))
            jumps = np.maximum(jumps, np.maximum(np.abs(rp - r0), np.abs(r0 - rm)))
        for k in np.where(kinked)[0]:
            lb = labels[k] if k < len(labels) else {}
            out.append({"group": grp, "kind": kind, "index": int(k), **lb, "residual": float(r0[k]), "sigma": float(s0[k]),
                        "abs_residual_over_sigma": float(abs(r0[k]) / s0[k]) if s0[k] else None,
                        "within_own_uncertainty": bool(abs(r0[k]) <= s0[k]), "max_one_step_change": float(jumps[k])})
    return out


def failed_equilibria(objs, x, groups=None):
    from espei.error_functions.zpf_error import ZPFResidual, estimate_hyperplane
    out = []
    for gi, r in enumerate(objs):
        if not isinstance(r, ZPFResidual):
            continue
        p = np.asarray(x, float)[r._sorted_order]
        for data in r.zpf_data:
            for j, pr in enumerate(data["phase_regions"]):
                if np.any(np.isnan(estimate_hyperplane(pr, data["dbf"], p))):
                    out.append({"group": groups[gi] if groups else "", "reference": data["dataset_reference"], "region": j,
                                "conditions": {str(a): float(b) for a, b in pr.potential_conds.items()},
                                "vertices": [[vx.phase_name, {str(a): (None if b is None else float(b)) for a, b in vx.comp_conds.items()}] for vx in pr.vertices]})
    return out
