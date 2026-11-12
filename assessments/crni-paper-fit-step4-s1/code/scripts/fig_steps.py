#!/usr/bin/env python3
"""Computed Cr-Ni diagrams of the step picks (house style), with the ZPF observations of the fit overlaid.
usage: fig_steps.py <out_stem> <label:tdb> [<label:tdb> ...]"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / "projects/2026_arroyave_nicr_paper/scripts"))
import matplotlib
matplotlib.use("Agg")
import style as st
if hasattr(st, "apply"):
    st.apply()
import matplotlib.pyplot as plt
import model
import pd4

R = model.RUN


def panel(ax, th, label, letter):
    T = pd4.TT
    di = pd4.diagram(th, T, pd4.ref_grid(T))
    for t, segs in zip(T, di):
        for kind, phs, xl, xr in segs:
            if kind == 2 and (xr - xl) > 2.5 / (pd4.NX - 1):
                xs = [z for z in (xl, xr) if pd4.X[0] < z < pd4.X[-1]]
                col = st.ACCENT if phs[0] == phs[1] else st.INK
                ax.plot(xs, [t] * len(xs), ".", color=col, ms=0.5, mew=0)
            if kind == 1 and phs == ("CRNI2",):
                ax.plot([xl], [t], ".", color=st.C_MODEL, ms=0.8, mew=0)
    for g in ("liq", "solid"):
        for f in sorted((R / "data" / g).glob("zpf*.json")):
            d = json.loads(f.read_text())
            for t, r in zip(d["conditions"]["T"], d["values"]):
                for v in r:
                    if v[2][0] is not None:
                        xn = v[2][0] if v[1] == ["NI"] else 1 - v[2][0]
                        ax.plot(xn, t, "o", ms=1.4, mfc="none", mec=st.C_EXP, mew=0.35)
    ax.set_xlim(0, 1); ax.set_ylim(600, 2200)
    ax.set_xlabel("Mole fraction Ni"); ax.set_ylabel("Temperature (K)")
    ax.text(0.03, 0.03, label, transform=ax.transAxes, fontsize=6, color=st.INK2)
    ax.text(-0.18, 1.04, letter, transform=ax.transAxes, fontsize=8, fontweight="bold")


def main():
    out = sys.argv[1]
    items = [a.split(":", 1) for a in sys.argv[2:]]
    n = len(items)
    nc = 2 if n > 1 else 1
    nr = int(np.ceil(n / nc))
    fig, axs = plt.subplots(nr, nc, figsize=(st.W2 if nc == 2 else st.W1, min(st.HMAX, 62 * st.MM * nr)), squeeze=False)
    for k, (lab, tdb) in enumerate(items):
        panel(axs.flat[k], model.read_theta(R / tdb), lab, "abcdefgh"[k])
    for k in range(n, nr * nc):
        axs.flat[k].axis("off")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out}.{ext}", dpi=300)


if __name__ == "__main__":
    main()
