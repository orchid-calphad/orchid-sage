#!/usr/bin/env python3
"""Evaluate and rank every start of a step (protocol 0.3, thresholds stated in PLAN.md before ranking).

Per start: topology over 600-2200 K (pd4), pure-element check, one-shot energy shifts in units of their sigma, plausibility
(solid/compound enthalpies within 10 kJ/mol-atom of the one-shot; |S_ex(0.5)| <= 2.5 J/mol-atom/K for bcc/fcc; liquid S_ex within 3u),
eutectic and CrNi2 temperatures, objective by residual type. Ranking: plausible first, then topology (ok, then fewer bad
temperatures, practical-T severity), then quantitative (|T_eut - 1618| and |T_CrNi2 - 863|, then logpost).
Writes steps/<step>/evaluation.json, the pick TDB tdb/<step>_pick.tdb, and the pick's diagram figures/<step>_pick.{png,pdf}.
usage: evaluate.py <step_name> [pick_start_name]
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import model
import pd4

R = model.RUN
OBS = json.loads((R / "results" / "oneshot_observations.json").read_text())


def oneshot_values(th):
    out = []
    for o in OBS["observations"]:
        x = o["x_Ni"]
        if o["phase"] == "CRNI2":
            v = (th[12] + 7284.0) / 3.0
        else:
            i = {"LIQUID": 0, "BCC_A2": 4, "FCC_A1": 8}[o["phase"]]
            v = x * (1 - x) * (th[i] + th[i + 2] * (1 - 2 * x))
        out.append({"id": o["id"], "obs": o["value"], "model": v, "shift_J": v - o["value"], "sigma": o["sigma"],
                    "shift_sigma": (v - o["value"]) / o["sigma"], "shift_from_oneshot_model_J": None})
    th1 = model.ONESHOT
    for r, o1 in zip(out, oneshot_values_raw(th1)):
        r["shift_from_oneshot_model_J"] = r["model"] - o1
        r["shift_from_oneshot_model_sigma"] = (r["model"] - o1) / r["sigma"]
    return out


def oneshot_values_raw(th):
    vals = []
    for o in OBS["observations"]:
        x = o["x_Ni"]
        if o["phase"] == "CRNI2":
            vals.append((th[12] + 7284.0) / 3.0)
        else:
            i = {"LIQUID": 0, "BCC_A2": 4, "FCC_A1": 8}[o["phase"]]
            vals.append(x * (1 - x) * (th[i] + th[i + 2] * (1 - 2 * x)))
    return vals


def liquid_sex(th):
    out = []
    for s in OBS["liquid_S_ex"]:
        x = s["x_Ni"]
        m = -x * (1 - x) * (th[1] + th[3] * (1 - 2 * x))
        out.append({"state": s["state"], "obs": s["S_ex"], "model": m, "z": (m - s["S_ex"]) / s["u"]})
    return out


def plausibility(th, osh, lsx):
    notes = []
    big = [o for o in osh if o["id"] != "LIQUID" and not o["id"].startswith("LIQUID") and abs(o["shift_J"]) > 10000]
    if big:
        notes.append("one-shot solid/compound value moved > 10 kJ/mol-atom: " + ", ".join(f"{o['id']} {o['shift_J']/1e3:+.1f}" for o in big))
    for nm, i in (("BCC_A2", 5), ("FCC_A1", 9)):
        if abs(th[i]) / 4 > 2.5:
            notes.append(f"{nm} S_ex(0.5) = {-th[i]/4:+.2f} J/mol-atom/K (|.| > 2.5)")
    if abs(th[13]) / 3 > 10:
        notes.append(f"CRNI2 S_f = {-th[13]/3:+.2f} J/mol-atom/K (|.| > 10)")
    badl = [s for s in lsx if abs(s["z"]) > 3]
    if badl:
        notes.append("liquid S_ex beyond 3u: " + ", ".join(f"{s['state']} z={s['z']:+.1f}" for s in badl))
    return (not notes), notes


def pure_check(th):
    ref = pd4.ref_grid(pd4.TT)
    G, gc2 = pd4.G_at(th, pd4.TT, ref)
    out = {}
    for el, j, Tm, low in (("CR", 0, 2180.0, "BCC_A2"), ("NI", -1, 1728.0, "FCC_A1")):
        st = [pd4.PH[int(np.argmin(G[:, i, j]))] for i in range(len(pd4.TT))]
        okl = all(s == low for t, s in zip(pd4.TT, st) if t < Tm - 2)
        okh = all(s == "LIQUID" for t, s in zip(pd4.TT, st) if t > Tm + 2)
        exc = float(np.max(np.abs(pd4.excess(th, pd4.TT)[0][:, :, j])))
        out[el] = {"stable_below_Tm": low if okl else "WRONG", "liquid_above_Tm": bool(okh), "max_excess_at_endpoint_J": exc}
    out["ok"] = all(out[e]["stable_below_Tm"] != "WRONG" and out[e]["liquid_above_Tm"] for e in ("CR", "NI"))
    return out


def rank_key(e):
    t = e["topology"]
    return (0 if e["plausible"] else 1, 0 if t["ok"] else 1, t["n_bad"] + 5 * t["n_gap_T"],
            abs(t["T_liquid_min"] - 1618) if np.isfinite(t["T_liquid_min"]) else 1e9,
            abs(t["T_CrNi2_max"] - 863) if np.isfinite(t["T_CrNi2_max"]) else 1e9, -e["logpost"])


def draw(th, path, title=None, data_groups=("liq", "solid")):
    import matplotlib
    matplotlib.use("Agg")
    sys.path.insert(0, str(Path.home() / "projects/2026_arroyave_nicr_paper/scripts"))
    import style as st
    st.apply() if hasattr(st, "apply") else None
    import matplotlib.pyplot as plt
    T = pd4.TT
    di = pd4.diagram(th, T, pd4.ref_grid(T))
    fig, ax = plt.subplots(figsize=(st.W1, st.W1 * 0.85))
    for t, segs in zip(T, di):
        for kind, phs, xl, xr in segs:
            if kind == 2 and (xr - xl) > 2.5 / (pd4.NX - 1):
                if phs[0] == phs[1]:
                    ax.plot([xl, xr], [t, t], color=st.ACCENT, lw=0.3, alpha=0.6)
                xs = [z for z in (xl, xr) if pd4.X[0] < z < pd4.X[-1]]
                ax.plot(xs, [t] * len(xs), ".", color=st.INK, ms=0.6, mew=0)
            if kind == 1 and phs == ("CRNI2",):
                ax.plot([xl], [t], ".", color=st.C_MODEL, ms=1.0, mew=0)
    for g in data_groups:
        for f in sorted((R / "data" / g).glob("zpf*.json")):
            d = json.loads(f.read_text())
            for t, r in zip(d["conditions"]["T"], d["values"]):
                for v in r:
                    if v[2][0] is not None:
                        xn = v[2][0] if v[1] == ["NI"] else 1 - v[2][0]
                        ax.plot(xn, t, "o", ms=1.6, mfc="none", mec=st.C_EXP, mew=0.4)
    ax.set_xlim(0, 1); ax.set_ylim(600, 2200)
    ax.set_xlabel("Mole fraction Ni"); ax.set_ylabel("Temperature (K)")
    for txt, x, y in (("bcc", 0.06, 1200), ("fcc", 0.85, 1200), ("liquid", 0.45, 2050)):
        ax.text(x, y, txt, fontsize=6, color=st.INK2)
    if title:
        ax.text(0.01, 1.01, title, transform=ax.transAxes, fontsize=6, color=st.INK2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(str(path) + "." + ext, dpi=300)
    plt.close(fig)


def main():
    step = sys.argv[1]
    d = R / "steps" / step
    ms = json.loads((d / "multistart.json").read_text())
    ref = pd4.ref_grid(pd4.TT)
    ref1 = pd4.ref_grid(np.array([1473.0]))
    evals = []
    for r in ms:
        th = np.asarray(r["theta"])
        t = pd4.topology(th, pd4.TT, ref)
        osh = oneshot_values(th)
        lsx = liquid_sex(th)
        pl, notes = plausibility(th, osh, lsx)
        e = {"start": r["start"], "logpost": r["logpost"], "parts": r["parts"], "final": r["final"], "nfev": r["nfev"],
             "grad_norm_q": r["grad_norm_q"], "n_nonfinite": r["n_nonfinite"], "theta": r["theta"],
             "theta_labeled": dict(zip(model.LABELS, r["theta"])), "topology": t, "pure_elements": pure_check(th),
             "oneshot_shifts": osh, "max_abs_shift_sigma": max(abs(o["shift_sigma"]) for o in osh),
             "liquid_S_ex": lsx, "plausible": pl, "plausibility_notes": notes,
             "phase_at_x052_1473K": pd4.phase_at(th, 1473.0, 0.52, ref1)}
        evals.append(e)
    evals.sort(key=rank_key)
    pick = sys.argv[2] if len(sys.argv) > 2 else evals[0]["start"]
    pe = next(e for e in evals if e["start"] == pick)
    cfg, _ = model.load_config(R / "steps" / "configs" / f"{step}.json")
    model.write_tdb(R / cfg["start_tdb"], pe["theta"], R / "tdb" / f"{step}_pick.tdb",
                    header=f"$ {step} pick = start {pick} (crni-paper-fit-20261106; gradient ESPEI {ms[0].get('espei_version')})")
    for e in evals:
        model.write_tdb(R / cfg["start_tdb"], e["theta"], d / f"{e['start']}.tdb", header=f"$ {step} start {e['start']}")
    draw(np.asarray(pe["theta"]), R / "figures" / f"{step}_pick", title=f"{step}: {pick}")
    out = {"step": step, "pick": pick, "pick_rule": "PLAN.md ranking (0.3): plausible, topology, quantitative",
           "ranking": [e["start"] for e in evals], "evaluations": evals}
    (d / "evaluation.json").write_text(json.dumps(out, indent=1, default=float))
    for e in evals:
        t = e["topology"]
        print(f"{e['start']:22s} lp {e['logpost']:11.2f} plaus {e['plausible']!s:5} top_ok {t['ok']!s:5} nbad {t['n_bad']:4d} "
              f"gapT {t['n_gap_T']:3d} Teut {t['T_liquid_min']:7.1f} Tc2 {t['T_CrNi2_max']:7.1f} sev {t['spurious_severity']:20s} "
              f"maxshift {e['max_abs_shift_sigma']:.2f}s pt {e['phase_at_x052_1473K']} {e['final'][:20]}")
        if e["plausibility_notes"]:
            print("    notes:", "; ".join(e["plausibility_notes"]))
    print("PICK", pick)


if __name__ == "__main__":
    main()
