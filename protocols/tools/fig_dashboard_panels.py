#!/usr/bin/env python3
"""Static, publication-grade versions of the dashboard panels, in the ORCHID hero style of the paper figures.

  FIT_PYTHON tools/fig_dashboard_panels.py DASHBOARD_DATA.json OUT_DIR      (FIT_PYTHON: fit_python of local/config.json)

Reads only the assessment-results document (no recomputation; same numbers as the dashboard). Style: the paper's
style.py (Arial 6-7 pt, pdf.fonttype 42, 89/183 mm widths, Okabe-Ito evidence-class colours with fixed meanings),
imported read-only from the Cr-Ni paper repository's scripts/style.py (sibling checkout 2026_arroyave_nicr_paper, or
'siblings' in local/config.json) and recorded by sha256 in the manifest.
Brand rules (PI 6 Nov 2026): class colours only for their classes; steps, starts and topology classes in neutral inks,
markers and line styles, ORCHID's own objects (the pick) in the accent #7B3FA0. Colours come from tools/palette.json.
Every figure that shows ORCHID records gets the ORCHID badge through orchid_badge() (a hook: the badge design is being
specified in the "ORCHID Brand" design system; until then it writes the ORC ids of the panel to the manifest).
Writes OUT_DIR/fig_<panel>.pdf and .png and OUT_DIR/figures_manifest.json (sha256 of every file, ORC ids per panel).
"""
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))
import localpaths  # noqa: E402
import frozen  # noqa: E402

STYLE = localpaths.sibling("2026_arroyave_nicr_paper") / "scripts/style.py"
spec = importlib.util.spec_from_file_location("orchid_paper_style", STYLE)
st = importlib.util.module_from_spec(spec); spec.loader.exec_module(st)   # applies the rcParams
PAL = json.loads((T / "palette.json").read_text())
ACC = PAL["data"]["orchid"]["light"]; EXP = PAL["data"]["experimental"]["light"]; DFT = PAL["data"]["dft"]["light"]
INK, INK2, GM, GL = st.INK, st.INK2, st.GREY_M, st.GREY_L
MK = {"circle": "o", "square": "s", "diamond": "D", "triangle": "^", "triangle-down": "v", "plus": "P", "star": "*", "hexagon": "h"}
STARTMK = [MK[m] for m in PAL["starts"]["markers"]]
MANIFEST = {"style": {"path": localpaths.tilde(STYLE), "sha256": hashlib.sha256(STYLE.read_bytes()).hexdigest()},
            "palette": {"path": localpaths.REPO_ALIASES[0] + "/protocols/tools/palette.json", "sha256": hashlib.sha256((T / "palette.json").read_bytes()).hexdigest()}, "panels": {}}


def orchid_badge(fig, release, orc_ids=(), panel=None, corner="upper right"):
    """ORCHID badge, as specified in the ORCHID brand repository (design-system/figures.md) (icon 3 mm + "ORCHID" bold orchid +
    release tag in fig-ink2, Arial 6 pt, 1 mm inset at the canvas corner; values PROPOSED there, pending the PI). Drawn
    only on figures that plot ORCHID records (orc_ids non-empty); writes fig_<panel>_orchid_ids.json for traceability."""
    if not orc_ids:
        return None
    import matplotlib.image as mpimg
    from matplotlib.offsetbox import AnchoredOffsetbox, HPacker, OffsetImage, TextArea
    ptmm = 72 / 25.4
    img = mpimg.imread(str(T / "assets/orchid-icon-512.png"))
    pic = OffsetImage(img, zoom=3.0 * ptmm / img.shape[0], interpolation="lanczos")
    txt = dict(fontsize=6, fontfamily="Arial")
    words = HPacker(children=[TextArea("ORCHID", textprops=dict(color=st.ACCENT, fontweight="bold", **txt)), TextArea(release, textprops=dict(color=st.INK2, **txt))],
                    sep=0.6 * ptmm, pad=0, align="baseline")
    W, H = fig.get_size_inches(); dx, dy = 1.0 * st.MM / W, 1.0 * st.MM / H
    xy = {"upper right": (1 - dx, 1 - dy), "lower right": (1 - dx, dy)}[corner]
    box = AnchoredOffsetbox(loc=corner, child=HPacker(children=[pic, words], sep=0.8 * ptmm, pad=0, align="center"), pad=0, borderpad=0, frameon=False,
                            bbox_to_anchor=xy, bbox_transform=fig.transFigure)
    box.set_zorder(10); fig.add_artist(box)
    MANIFEST["panels"].setdefault(panel, {})["orchid_badge"] = {"release": release, "drawn": True, "spec": "orchid-brand figures.md (proposed values)"}
    return box


def tc_style(c):
    return {"ok": ("o", ACC, ACC), "wrong": ("^", INK2, "none")}.get(c, ("s", GM, "none"))


def save(fig, out, name, d, orc=()):
    if orc:
        fig.get_layout_engine().set(rect=(0, 0, 1, 1 - 5 * st.MM / fig.get_size_inches()[1]))
        orchid_badge(fig, d.get("orchid_release", "release pending").split(" ")[0], orc, name)
        # generated from the evidence links (states_evaluated rows, PI 6 Nov 2026), not from free-text ids
        ids = {"figure": f"fig_{name}", "orchid_release": d.get("orchid_release"), "evidence_bundle_version": (d.get("states_summary") or {}).get("evidence_bundle_version"),
               "labels": {}, "records": [], "missing": {}}
        for i in d["invariants"] if isinstance(d.get("invariants"), list) else []:
            ids["labels"][i["reaction"]] = i.get("orchid_ids", [])
        seen = set()
        for r in d["states_evaluated"] if isinstance(d.get("states_evaluated"), list) else []:
            for l in r.get("orchid_links") or []:
                k = (l["id"], l.get("state_id"))
                if k not in seen:
                    seen.add(k); ids["records"].append({**{k2: l.get(k2) for k2 in ("id", "state_id", "state_class_id", "paper_id", "pid", "in_release")},
                                                        "resolved": bool(l.get("paper_id") or l.get("state_id"))})
            if r.get("orchid_link") == "missing":
                ids["missing"][r.get("missing_reason")] = ids["missing"].get(r.get("missing_reason"), 0) + 1
        ids["records"].sort(key=lambda q: (q["id"], q.get("state_id") or ""))
        frozen.write(out / f"fig_{name}_orchid_ids.json", json.dumps(ids, indent=1))
    files = []
    for ext in ("pdf", "png"):
        p = out / f"fig_{name}.{ext}"
        b = frozen.render(fig, ext, dpi=600 if ext == "png" else None, metadata={"CreationDate": None} if ext == "pdf" else {"Software": None})   # no timestamps: byte-identical rebuilds
        frozen.write(p, b)   # refuses a frozen file
        files.append({"path": localpaths.tilde(p), "sha256": hashlib.sha256(b).hexdigest()})
    plt.close(fig)
    MANIFEST["panels"].setdefault(name, {})["files"] = files
    MANIFEST["panels"][name]["source"] = d["id"]


def steps_panel(d, out):
    R = [r for r in d["trajectory"]["runs"] if r["step"] != d["trajectory"]["runs"][0]["step"]]
    steps = list(dict.fromkeys(r["step"] for r in R))
    fig, ax = plt.subplots(figsize=(st.W1, 55 * st.MM), layout="constrained")
    for i, s in enumerate(steps):
        rs = [r for r in R if r["step"] == s]
        for j, r in enumerate(rs):
            e = r["points"][-1]
            if e["objective"] is None:
                continue
            m, c, f = tc_style(r["final_topology_class"])
            if r["is_pick"]:
                ax.plot(i, e["objective"], "*", ms=7, mfc=ACC, mec=ACC, zorder=5)
            else:
                ax.plot(i + (j - len(rs) / 2) * 0.03, e["objective"], m, ms=3, mfc=f, mec=c, mew=0.5)
    ax.set_xticks(range(len(steps)), [s.replace("_", " ").replace("thermo crni2free", "thermo (CrNi2 free)") for s in steps], rotation=20, ha="right")
    ax.set_yscale("symlog", linthresh=100)
    ax.set_ylabel("Log posterior at the end of each start")
    ax.plot([], [], "o", ms=3, mfc=ACC, mec=ACC, label="right topology"); ax.plot([], [], "^", ms=3, mfc="none", mec=INK2, label="wrong topology")
    ax.plot([], [], "*", ms=6, mfc=ACC, mec=ACC, label="pick"); ax.legend(loc="lower left")
    save(fig, out, "steps", d)


def shifts_panel(d, out):
    S = d["oneshot_shifts"]
    if isinstance(S, dict):
        return
    steps = list(dict.fromkeys(s["step"] for s in S)); ids = list(dict.fromkeys(s["id"] for s in S))
    fig, ax = plt.subplots(figsize=(st.W1, (25 + 4.2 * len(ids)) * st.MM), layout="constrained")
    ax.axvspan(-1, 1, color=st.FILL["accent"], lw=0); ax.axvline(0, color=GM, lw=0.5)
    for j, s in enumerate(steps):
        last = j == len(steps) - 1
        for k, i in enumerate(ids):
            q = next((x for x in S if x["id"] == i and x["step"] == s), None)
            if q and q["shift_sigma"] is not None:
                ax.plot(q["shift_sigma"], k, STARTMK[j], ms=3.2 if not last else 4, mfc=ACC if last else "none", mec=ACC if last else INK2, mew=0.6)
        ax.plot([], [], STARTMK[j], ms=3.2, mfc=ACC if last else "none", mec=ACC if last else INK2, label=s.replace("_", " "))
    ax.set_yticks(range(len(ids)), [i.replace("_x", " x=").replace("_", " ") for i in ids]); ax.invert_yaxis()
    ax.set_xlabel(r"Shift from the one-shot value ($\sigma$)"); ax.legend(loc="lower right", fontsize=5.5)
    save(fig, out, "oneshot_shifts", d)


def residuals_panel(d, out):
    R = d["per_dataset_residuals"]
    if isinstance(R, dict):
        return
    R = sorted(R, key=lambda r: -(r["rms_z"] or 0))[:25]
    fig, ax = plt.subplots(figsize=(st.W1, (20 + 3.3 * len(R)) * st.MM), layout="constrained")
    ax.barh(range(len(R)), [r["rms_z"] for r in R], color=INK2, height=0.6)
    ax.set_yticks(range(len(R)), [r["dataset"].replace(".json", "")[:44] for r in R], fontsize=5)
    ax.invert_yaxis(); ax.set_xscale("log"); ax.set_xlabel("RMS residual / $\\sigma$ (ZPF: per 1000 J/mol default scale)")
    save(fig, out, "residuals", d)


def invariants_panel(d, out):
    I = d["invariants"]
    if isinstance(I, dict):
        return
    fig, ax = plt.subplots(figsize=(st.W1, (18 + 6 * len(I)) * st.MM), layout="constrained")
    orc = []
    for k, i in enumerate(I):
        orc += i.get("orchid_ids", [])
        if i["observed_K"] is not None and i["calculated_K"] is not None:
            ax.plot([i["observed_K"], i["calculated_K"]], [k, k], color=GM, lw=1)
        if i["observed_K"] is not None:
            ax.errorbar(i["observed_K"], k, xerr=i.get("sigma_K") or 0, fmt="s", ms=3.5, color=EXP, mfc=EXP, elinewidth=0.6, capsize=1.5)
        if i["calculated_K"] is not None:
            ax.plot(i["calculated_K"], k, "o", ms=3.0, color=ACC, mec="white", mew=0.4, zorder=4)
    ax.set_yticks(range(len(I)), [f"{i['reaction']}\n{', '.join(i['orchid_ids'][:2])}" for i in I], fontsize=5.5); ax.invert_yaxis()
    ax.set_xlabel("Temperature (K)")
    ax.plot([], [], "s", ms=3, color=EXP, label="ORCHID observation (experimental)"); ax.plot([], [], "o", ms=3, color=ACC, label="pick (calculated)"); ax.legend(loc="best", fontsize=5.5)
    save(fig, out, "invariants", d, orc)


def _proj(d):
    P = d["projection"]
    def pr(th):
        z = [th[i] / P["scale"][i] - P["center"][i] / P["scale"][i] for i in range(len(th))]
        return (sum(z[i] * P["basis"][i][0] for i in range(len(z))), sum(z[i] * P["basis"][i][1] for i in range(len(z))))
    return P, pr


def projection_panel(d, out):
    if isinstance(d["projection"], dict) and d["projection"].get("status") == "pending":
        return
    P, pr = _proj(d)
    fig, ax = plt.subplots(figsize=(st.W1, 70 * st.MM), layout="constrained")
    dr = [q["xy"] for q in P.get("uq_points", []) if q["kind"] == "draw"]
    if dr:
        ax.scatter([x for x, _ in dr], [y for _, y in dr], s=1.2, color=GM, lw=0, label="Laplace-mixture draws", zorder=1)
    for q in P.get("uq_points", []):
        if q["kind"] == "mode":
            ax.plot(*q["xy"], "D", ms=3, mfc="none", mec=INK, mew=0.6, zorder=3)
    for r in d["trajectory"]["runs"]:
        Q = [pr(p["theta"]) for p in r["points"] if p.get("theta")]
        if len(Q) > 1:
            ax.plot([q[0] for q in Q], [q[1] for q in Q], color=ACC if r["is_pick"] else INK2, lw=0.8 if r["is_pick"] else 0.4,
                    ls="-" if r["recorded"] else (0, (1.5, 1.5)), alpha=1 if r["is_pick"] else 0.6, zorder=2)
        if Q:
            m, c, f = tc_style(r["final_topology_class"])
            if r["is_pick"]:
                ax.plot(*Q[-1], "*", ms=7, mfc=ACC, mec=ACC, zorder=5)
            else:
                ax.plot(*Q[-1], m, ms=2.6, mfc=f, mec=c, mew=0.5, zorder=4)
    s1 = pr(d["trajectory"]["oneshot_theta"]); ax.plot(*s1, "*", ms=6, mfc=DFT, mec=DFT, zorder=5)
    ev = P["explained_variance_ratio"]
    ax.set_xlabel(f"PC1 ({100 * ev[0]:.1f} %)"); ax.set_ylabel(f"PC2 ({100 * ev[1]:.1f} %)")
    ax.plot([], [], "*", ms=5, color=DFT, label="one-shot (MLIP)"); ax.plot([], [], "*", ms=5, color=ACC, label="pick")
    ax.plot([], [], "o", ms=2.6, color=ACC, label="right topology"); ax.plot([], [], "^", ms=2.6, mfc="none", mec=INK2, label="wrong topology")
    ax.plot([], [], "D", ms=2.6, mfc="none", mec=INK, label="Laplace modes"); ax.legend(loc="best", fontsize=5.5)
    save(fig, out, "projection", d)


def distance_panel(d, out):
    if isinstance(d["projection"], dict) and d["projection"].get("status") == "pending":
        return
    T_ = d["trajectory"]; P = d["projection"]; phs = list(dict.fromkeys(T_["phase_of_parameter"]))
    fig, ax = plt.subplots(figsize=(st.W1, (20 + 7 * len(phs)) * st.MM), layout="constrained")
    for j, r in enumerate(T_["runs"][1:]):
        th = r["points"][-1].get("theta")
        if not th:
            continue
        for k, ph in enumerate(phs):
            v = math.sqrt(sum(((th[i] - T_["oneshot_theta"][i]) / P["scale"][i]) ** 2 for i, p in enumerate(T_["phase_of_parameter"]) if p == ph))
            m, c, f = tc_style(r["final_topology_class"])
            if r["is_pick"]:
                ax.plot(v, k, "*", ms=6, mfc=ACC, mec=ACC, zorder=5)
            else:
                ax.plot(v, k + (j % 5 - 2) * 0.06, m, ms=2.4, mfc=f, mec=c, mew=0.5)
    ax.set_yticks(range(len(phs)), phs); ax.invert_yaxis()
    ax.set_xlabel("Distance from the one-shot (prior/scale units)")
    save(fig, out, "distance", d)


def trajectory_panel(d, out):
    R = [r for r in d["trajectory"]["runs"] if r["recorded"]]
    if not R:
        return
    steps = list(dict.fromkeys(r["step"] for r in R)); off, seg = 0, {}
    for st_ in steps:
        n = max(r["points"][-1]["eval"] for r in R if r["step"] == st_); seg[st_] = off; off += n * 1.05 + 5
    fig, ax = plt.subplots(figsize=(st.W2, 55 * st.MM), layout="constrained")
    for r in R:
        pts = [p for p in r["points"] if p["objective"] is not None]
        if not pts:
            continue
        x = [seg[r["step"]] + p["eval"] for p in pts]; y = [-p["objective"] for p in pts]
        ax.plot(x, y, color=INK2, lw=0.4, alpha=0.7)
        m, c, f = tc_style(r["final_topology_class"]); ax.plot(x[-1], y[-1], m, ms=2.6, mfc=f, mec=c, mew=0.5)
    for st_ in steps:
        ax.axvline(seg[st_], color=GM, lw=0.4, ls=(0, (2, 2))); ax.text(seg[st_], 1.0, " " + st_.replace(f" (rerun {localpaths.host('spark1')})", "").replace("_", " "), transform=ax.get_xaxis_transform(), fontsize=5.5, va="top", color=INK2)
    ax.set_yscale("log"); ax.set_xlabel("Objective evaluation (cumulative across steps)"); ax.set_ylabel("−log posterior")
    ax.plot([], [], "o", ms=2.6, color=ACC, label="end: right topology"); ax.plot([], [], "^", ms=2.6, mfc="none", mec=INK2, label="end: wrong topology"); ax.legend(loc="upper right", fontsize=5.5)
    save(fig, out, "trajectory", d)


if __name__ == "__main__":
    d = json.loads(Path(sys.argv[1]).read_text()); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    for f in (steps_panel, shifts_panel, residuals_panel, invariants_panel, projection_panel, distance_panel, trajectory_panel):
        f(d, out)
    frozen.write(out / "figures_manifest.json", json.dumps(MANIFEST, indent=1))
    print(len(MANIFEST["panels"]), "panels ->", out)
