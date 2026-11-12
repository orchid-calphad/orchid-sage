"""model2 (6 Nov, step4c): model.py + (1) records in data/zpf_susp are evaluated against the start TDB WITHOUT the CRNI2 phase
(metastable bcc+fcc with CRNI2 suspended, PI kinetic rule; ESPEI's ZPF has no per-record phase switch); (2) optional smooth hinge
onset (config "hinge_smooth": "softplus_sigma_over_5"): the PhaseForge+ term 0.5 c (max(0, u)/sigma)^2, u = margin - DG, becomes
0.5 c (w softplus(u/w)/sigma)^2 with w = sigma/5 (continuous gradient), applied by replacing phaseforgeplus.utils.hinge._hinge_term
in this process only (PhaseForgePlus source unchanged).

Shared definitions for the Cr-Ni paper fit (adapted from cr-ni-rebuild-20261105/scripts/crni.py; same GradTarget design).

Changes from crni.py, and only these: the TDB is the step's start TDB (the PhaseForge one-shot with VV symbols, then each accepted
step), the fitted symbols are the step's free subset of VV0000-VV0013 (the others stay at the start TDB's values), the data are the
step's file list (configs in steps/configs/), the hinge sidecar is the step's, and the weak Normal prior is centred at the one-shot
(sd 50 kJ/mol on a terms, 30 J/mol/K on b terms) instead of the paper's start values.
Optimiser coordinates q = theta / SCALE (a-terms /1000, b-terms /1), as in crni.py.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

RUN = Path(__file__).resolve().parents[1]
NAMES = [f"VV{i:04d}" for i in range(14)]
LABELS = ["L0liq_a", "L0liq_b", "L1liq_a", "L1liq_b", "L0bcc_a", "L0bcc_b", "L1bcc_a", "L1bcc_b",
          "L0fcc_a", "L0fcc_b", "L1fcc_a", "L1fcc_b", "CrNi2_a", "CrNi2_b"]
IS_T = np.array([n.endswith("b") for n in LABELS])
SCALE_ALL = np.where(IS_T, 1.0, 1000.0)
ONESHOT = np.array(json.loads((RUN / "results" / "oneshot_parameters.json").read_text())["oneshot_Sex"])
PRIOR_CENTER_ALL = ONESHOT.copy()
PRIOR_SD_ALL = np.where(IS_T, 30.0, 50000.0)
PHASES = ["BCC_A2", "CRNI2", "FCC_A1", "LIQUID"]
sys.path.insert(0, os.environ.get("PFP_SRC", str(Path.home() / "src/PhaseForgePlus/src")))


def read_theta(tdb) -> np.ndarray:
    t = Path(tdb).read_text()
    return np.array([float(re.search(r"FUNCTION\s+%s\s+298\.15\s+([-+.\dEe]+);" % n, t).group(1)) for n in NAMES])


def write_tdb(src_tdb, theta, out, header=""):
    txt = Path(src_tdb).read_text()
    for s, v in zip(NAMES, theta):
        txt = re.sub(r"(FUNCTION\s+%s\s+298\.15\s+)[-+.\dEe]+;" % s, lambda mm: mm.group(1) + "%.6f;" % v, txt)
    Path(out).write_text((header + "\n" if header else "") + txt)


def load_config(cfg):
    c = json.loads(Path(cfg).read_text()) if not isinstance(cfg, dict) else cfg
    files = []
    for g in c["groups"]:
        files += sorted(glob.glob(str(RUN / "data" / g / "*.json")))
    return c, files


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class GradTarget:
    """log posterior and gradient (free symbols only) from ESPEI-grad residual objects + hinge, in q coordinates."""

    def __init__(self, cfg, start_tdb=None):
        from espei.datasets import load_datasets
        from espei.error_functions.context import setup_context
        from pycalphad import Database
        self.cfg, self.files = load_config(cfg)
        self.tdb = Path(start_tdb or (RUN / self.cfg["start_tdb"]))
        self.free = list(self.cfg["free"])
        self.idx = np.array([NAMES.index(s) for s in self.free])
        self.theta_fixed = read_theta(self.tdb)
        self.scale = SCALE_ALL[self.idx]
        self.pc, self.psd = PRIOR_CENTER_ALL[self.idx], PRIOR_SD_ALL[self.idx]
        self.hinge = None
        if self.cfg.get("hinge"):  # PhaseForge+ hinge on excluded phases, built before ESPEI touches the symbols
            from phaseforgeplus.utils.hinge import HingeOptions, HingePenalty
            sc = json.loads((RUN / self.cfg["hinge"]).read_text())
            keys = ("T", "x", "expected", "sigma", "tie_line", "confidence", "penalize")
            cells = [{k: c[k] for k in keys if k in c} for c in sc["cells"]]
            self.hinge = HingePenalty(Database(str(self.tdb)), self.free, cells, sc["element"],
                                      HingeOptions(margin=float(sc["margin_J_per_mol_atom"])))
        dbf = Database(str(self.tdb))
        # one ESPEI context per data category so that the objective splits into components (same total likelihood):
        # zpf (liq*/solid*), thermo, oneshot_anchor (one-shot HM_MIX/HM_FORM observations), S_ex (provisional liquid SM_MIX)
        self.res, self.cat = [], []
        if self.cfg.get("hinge_smooth"):
            install_smooth_hinge()
        for cat, fl in self.categories().items():
            if not fl:
                continue
            db_use = dbf
            if cat == "zpf_susp":
                db_use = Database(no_crni2_tdb(self.tdb))
            ctx = setup_context(db_use, load_datasets(fl), symbols_to_fit=self.free)
            assert list(ctx["symbols_to_fit"]) == self.free, ctx["symbols_to_fit"]
            for r in ctx["residual_objs"]:
                self.res.append(r); self.cat.append(cat)
        self.n = 0
        self.last_parts = None

    def categories(self):
        c = {"zpf": [], "zpf_susp": [], "thermo": [], "oneshot_anchor": [], "S_ex": []}
        for f in self.files:
            g = Path(f).parent.name
            if g == "zpf_susp":
                c["zpf_susp"].append(f)
            elif g.startswith("oneshot"):
                c["S_ex" if "SM_MIX" in Path(f).name else "oneshot_anchor"].append(f)
            elif g == "thermo":
                c["thermo"].append(f)
            else:
                c["zpf"].append(f)
        return c

    def full(self, theta_free):
        th = self.theta_fixed.copy()
        th[self.idx] = theta_free
        return th

    def log_prior(self, theta):
        z = (np.asarray(theta) - self.pc) / self.psd
        return float(-0.5 * np.sum(z ** 2) - np.sum(np.log(self.psd * np.sqrt(2 * np.pi))))

    def log_prior_grad(self, theta):
        return -(np.asarray(theta) - self.pc) / self.psd ** 2

    def parts(self, theta, gradient=True):
        out = {}
        for r, cat in zip(self.res, self.cat):
            k = f"{cat}:{type(r).__name__}"
            if gradient:
                v, g = r.get_likelihood_and_gradient(np.asarray(theta, float))
                g = np.atleast_1d(np.asarray(g, float))
                if g.size != len(theta):
                    g = np.zeros(len(theta))
                v0, g0 = out.get(k, (0.0, np.zeros(len(theta))))
                out[k] = (v0 + float(v), g0 + g)
            else:
                v0 = out.get(k, (0.0, None))[0]
                out[k] = (v0 + float(r.get_likelihood(np.asarray(theta, float))), None)
        if self.hinge is not None:  # penalty is a negative log-likelihood
            p, gp = self.hinge(np.asarray(theta, float))
            out["HingePenalty"] = (-float(p), -np.asarray(gp, float) if gradient else None)
        return out

    def value_only(self, theta):
        return sum(v for v, _ in self.parts(theta, gradient=False).values()) + self.log_prior(theta)

    def __call__(self, q):
        theta = np.asarray(q, float) * self.scale
        self.n += 1
        parts = self.parts(theta)
        self.last_parts = {k: v for k, (v, _) in parts.items()}
        self.last_parts["log_prior"] = self.log_prior(theta)
        val = sum(v for v, _ in parts.values()) + self.log_prior(theta)
        g = sum(g for _, g in parts.values()) + self.log_prior_grad(theta)
        return val, g * self.scale


def no_crni2_tdb(tdb):
    """the TDB text without the CRNI2 phase (PHASE, CONSTITUENT, PARAMETER lines); VV symbols kept"""
    src = Path(tdb)
    out = RUN / "data" / "cache" / (src.stem + "_noCRNI2.tdb")
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [l for l in src.read_text().splitlines() if not re.match(r"\s*(PHASE|CONSTITUENT)\s+CRNI2\b", l) and "G(CRNI2" not in l]
    out.write_text("\n".join(lines) + "\n")
    return str(out)


def install_smooth_hinge():
    import phaseforgeplus.utils.hinge as H
    if getattr(H, "_smooth_installed", False):
        return

    def _hinge_term(driving_force, margin, sigma, confidence):
        w = sigma / 5.0
        u = (margin - driving_force) / w
        sp = (u + np.log1p(np.exp(-u))) if u > 0 else np.log1p(np.exp(u))
        sig = 1.0 / (1.0 + np.exp(-u))
        s = w * sp / sigma
        return 0.5 * confidence * s * s, -confidence * s / sigma * sig

    H._hinge_term_original = H._hinge_term
    H._hinge_term = _hinge_term
    H._smooth_installed = True


def espei_version():
    import espei
    import pycalphad
    return {"espei_version": espei.__version__, "espei_file": espei.__file__, "pycalphad_version": pycalphad.__version__,
            "python": sys.executable, "host": os.uname().nodename}
