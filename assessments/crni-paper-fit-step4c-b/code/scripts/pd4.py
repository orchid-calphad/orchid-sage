"""Fast exact-on-grid Cr-Ni phase diagram from lower convex hulls (adapted from cr-ni-rebuild-20261105/scripts/pdfast.py).

Changes: LIQUID carries L0 and L1 (a + bT); the stoichiometric CRNI2 enters as one point at x_Ni = 2/3 with
G = [G_ref(GFCCCR + 2 GHSERNI) + VV0012 + VV0013 T] / 3 per mole of atoms; topology check over 600-2200 K for the accepted Cr-Ni
diagram with CrNi2 (stated in PLAN.md before ranking); two-phase labels are written with the phase names sorted.
G_ref + ideal of the solutions comes from pycalphad `calculate` with every VV = 0 (cached in data/cache)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
PH = ["BCC_A2", "FCC_A1", "LIQUID"]
NX = 1201
X = np.concatenate([[1e-6], np.linspace(0, 1, NX)[1:-1], [1 - 1e-6]])  # x_Ni
J23 = 800                     # X[800] = 2/3
X[J23] = 2.0 / 3.0
TT = np.arange(600.0, 2201.0, 2.0)


def ref_grid(T, tdb=R / "tdb" / "step1_oneshot.tdb"):
    """(4, nT, nX): G_ref+ideal for BCC, FCC, LIQ on (T, X); row 3 = CRNI2 reference per atom (only [:, :, 0] used)."""
    T = np.asarray(T, float)
    cache = R / "data" / "cache" / f"ref_{len(T)}_{T[0]:.0f}_{T[-1]:.0f}_{NX}.npy"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        return np.load(cache)
    from pycalphad import Database, calculate
    db = Database(str(tdb))
    pars = {f"VV{i:04d}": 0.0 for i in range(14)}
    pts = np.stack([1 - X, X], axis=1)
    out = np.empty((4, len(T), len(X)))
    for k, ph in enumerate(PH):
        r = calculate(db, ["CR", "NI", "VA"], ph, T=T, P=101325, N=1, points=pts, parameters=pars)
        out[k] = np.asarray(r.GM.squeeze()).reshape(len(T), len(X))
    r = calculate(db, ["CR", "NI", "VA"], "CRNI2", T=T, P=101325, N=1, parameters=pars)
    out[3] = np.asarray(r.GM.squeeze()).reshape(len(T), -1)[:, :1]
    np.save(cache, out)
    return out


def excess(theta, T):
    """(3, nT, nX) excess Gibbs energies of BCC, FCC, LIQ; and (nT,) CRNI2 parameter term per atom."""
    th = np.asarray(theta, float)
    T = np.asarray(T, float)[:, None]
    xc, xn = 1 - X[None, :], X[None, :]

    def rk(L0, L1):
        return xc * xn * (L0 + L1 * (xc - xn))
    liq = rk(th[0] + th[1] * T, th[2] + th[3] * T)
    bcc = rk(th[4] + th[5] * T, th[6] + th[7] * T)
    fcc = rk(th[8] + th[9] * T, th[10] + th[11] * T)
    c2 = (th[12] + th[13] * T[:, 0]) / 3.0
    return np.stack([bcc, fcc, liq]), c2


def _lower_hull(x, g):
    h = []
    for i in range(len(x)):
        while len(h) >= 2:
            a, b = h[-2], h[-1]
            if (x[b] - x[a]) * (g[i] - g[a]) - (g[b] - g[a]) * (x[i] - x[a]) <= 0:
                h.pop()
            else:
                break
        h.append(i)
    return h


def G_at(theta, T, ref):
    ex, c2 = excess(theta, T)
    G = ref[:3] + ex
    gc2 = ref[3][:, 0] + c2
    return G, gc2


def regions_at(G, gc2):
    """G: (3, nX), gc2: float at one T. Segments [(kind, phases, x_left, x_right)], kind 1 single, 2 two-phase."""
    idx = np.argmin(G, axis=0)
    gmin = G[idx, np.arange(G.shape[1])]
    names = [PH[i] for i in idx]
    if gc2 < gmin[J23]:
        gmin = gmin.copy()
        gmin[J23] = gc2
        names[J23] = "CRNI2"
    h = _lower_hull(X, gmin)
    segs = []
    for a, b in zip(h[:-1], h[1:]):
        pa, pb = names[a], names[b]
        if b - a == 1 and pa == pb:
            if segs and segs[-1][0] == 1 and segs[-1][1] == (pa,):
                segs[-1] = (1, (pa,), segs[-1][2], X[b])
            else:
                segs.append((1, (pa,), X[a], X[b]))
        else:
            if pa == "CRNI2" and not (segs and segs[-1][1] == ("CRNI2",)):
                segs.append((1, ("CRNI2",), X[a], X[a]))
            segs.append((2, (pa, pb), X[a], X[b]))
            if pb == "CRNI2":
                segs.append((1, ("CRNI2",), X[b], X[b]))
    return segs


def diagram(theta, T, ref):
    G, gc2 = G_at(theta, T, ref)
    return [regions_at(G[:, i, :], gc2[i]) for i in range(len(T))]


def seq_string(segs):
    out = []
    if segs and segs[0][0] == 2 and segs[0][2] <= X[0] + 1e-12:   # end solubility below one grid cell: still a field
        out.append(segs[0][1][0])
    if segs and segs[-1][0] == 2 and segs[-1][3] >= X[-1] - 1e-12:
        segs = list(segs) + [(1, (segs[-1][1][1],), X[-1], X[-1])]
    for kind, phs, xl, xr in segs:
        if kind == 2 and (xr - xl) < 2.5 / (NX - 1) and phs[0] != phs[1] and "CRNI2" not in phs:
            continue  # a grid-cell step at a G crossing is not a two-phase field
        s = "+".join(sorted(phs)) if kind == 2 else phs[0]
        if kind == 2 and phs[0] == phs[1]:
            s = phs[0] + "+" + phs[0]
        if not out or out[-1] != s:
            out.append(s)
    return out


B, F, L, C = "BCC_A2", "FCC_A1", "LIQUID", "CRNI2"
WANT_LOW = [[B, f"{B}+{C}", C, f"{C}+{F}", F],                                   # peritectoid CrNi2
            [B, f"{B}+{F}", F, f"{C}+{F}", C, f"{C}+{F}", F],                    # congruent ordering window
            [B, f"{B}+{F}", f"{C}+{F}", C, f"{C}+{F}", F]]                       # fcc window closed on the Cr side
WANT_MID = [[B, f"{B}+{F}", F]]
WANT_EUT = [[B, f"{B}+{L}", L, f"{F}+{L}", F]]
WANT_HI = [[B, f"{B}+{L}", L]]


def topology(theta, T=TT, ref=None, t_eut=(1560.0, 1680.0), t_c2=(800.0, 930.0)):
    ref = ref_grid(T) if ref is None else ref
    di = diagram(theta, T, ref)
    seqs = [seq_string(s) for s in di]
    gaps = []
    for t, segs in zip(T, di):
        for kind, phs, xl, xr in segs:
            if kind == 2 and phs[0] == phs[1] and (xr - xl) > 2.5 / (NX - 1):
                gaps.append((float(t), phs[0], float(xl), float(xr)))
    liq_T = [float(t) for t, s in zip(T, seqs) if any(L in z for z in s)]
    tliq = min(liq_T) if liq_T else np.inf
    c2_T = [float(t) for t, s in zip(T, seqs) if C in s]
    tc2 = max(c2_T) if c2_T else -np.inf
    bad = []
    for t, s in zip(T, seqs):
        if t < tc2:
            want = WANT_LOW
        elif t < tliq:
            want = WANT_MID
        elif t < 1727.0:
            want = WANT_EUT
        elif t < 2179.0:
            want = WANT_HI
        else:
            want = [[L]]
        near = abs(t - tliq) < 12 or abs(t - 1728) < 12 or abs(t - 2180) < 4 or abs(t - tc2) < 12
        if s not in want and not near:
            bad.append((float(t), s))
    ok = (not bad) and (not gaps) and t_eut[0] <= tliq <= t_eut[1] and t_c2[0] <= tc2 <= t_c2[1]
    sev = "none"
    if bad:
        Tb = np.array([b[0] for b in bad])
        sev = "practical (<1500 K)" if (Tb < 1500).any() else "high-T only"
    return {"ok": bool(ok), "T_liquid_min": tliq, "T_CrNi2_max": tc2, "gaps": gaps[:20], "n_gap_T": len({g[0] for g in gaps}),
            "n_bad": len(bad), "bad": bad[:25], "bad_T_range": [min(b[0] for b in bad), max(b[0] for b in bad)] if bad else None,
            "spurious_severity": sev,
            "eutectic_ok": bool(t_eut[0] <= tliq <= t_eut[1]), "crni2_ok": bool(t_c2[0] <= tc2 <= t_c2[1])}


def phase_at(theta, t, x, ref1):
    G, gc2 = G_at(theta, [t], ref1)
    segs = regions_at(G[:, 0, :], gc2[0])
    for kind, phs, xl, xr in segs:
        if xl - 1e-12 <= x <= xr + 1e-12 and not (kind == 1 and phs == ("CRNI2",)):
            return "+".join(sorted(phs)) if kind == 2 else phs[0]
    return "?"


def boundaries(theta, T, ref):
    di = diagram(theta, T, ref)
    keys = ("bcc_bf", "fcc_bf", "sol_bcc", "liq_bccside", "liq_fccside", "sol_fcc")
    out = {k: [] for k in keys}
    for segs in di:
        r = dict((k, np.nan) for k in keys)
        for kind, phs, xl, xr in segs:
            if kind != 2:
                continue
            if set(phs) == {B, F} and xl < 0.6:
                r["bcc_bf"], r["fcc_bf"] = xl, xr
            elif set(phs) == {B, L}:
                r["sol_bcc"], r["liq_bccside"] = xl, xr
            elif set(phs) == {F, L}:
                r["liq_fccside"], r["sol_fcc"] = xl, xr
        for k in keys:
            out[k].append(r[k])
    return {k: np.asarray(v) for k, v in out.items()}
