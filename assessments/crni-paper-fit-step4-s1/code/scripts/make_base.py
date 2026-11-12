"""Write tdb/step1_oneshot.tdb: the PhaseForge one-shot (S_ex variant) with its interaction and compound terms as VV symbols.
Unaries and phase definitions copied verbatim from the one-shot TDB; values identical to the one-shot."""
import hashlib, json, re
from pathlib import Path
R = Path(__file__).resolve().parents[1]
SRC = Path.home() / "ScientificRuns/crni-phaseforge-20261105/tdb/CrNi_PhaseForge_oneshot_Sex_GRACE-2L-SMAX-OMAT-large.tdb"
SRC0 = Path.home() / "ScientificRuns/crni-phaseforge-20261105/tdb/CrNi_PhaseForge_oneshot_GRACE-2L-SMAX-OMAT-large.tdb"
NAMES = [f"VV{i:04d}" for i in range(14)]
LABELS = ["L0liq_a", "L0liq_b", "L1liq_a", "L1liq_b", "L0bcc_a", "L0bcc_b", "L1bcc_a", "L1bcc_b",
          "L0fcc_a", "L0fcc_b", "L1fcc_a", "L1fcc_b", "CrNi2_a", "CrNi2_b"]


def values(src):
    t = src.read_text()
    def par(ph, k):
        m = re.search(r"PARAMETER L\(%s,CR,NI;%d\) 1 ([^;]+);" % (ph, k), t)
        return m.group(1) if m else "0"
    def ab(e):
        e = e.replace(" ", "")
        m = re.fullmatch(r"([-+.\dEe]+)(?:([-+][.\dEe]+)\*T)?", e)
        return float(m.group(1)), float(m.group(2) or 0)
    v = []
    for ph in ("LIQUID", "BCC_A2", "FCC_A1"):
        for k in (0, 1):
            v += list(ab(par(ph, k)))
    m = re.search(r"G\(CRNI2,CR:NI;0\) 1 GFCCCR\+2\*GHSERNI([-+][.\dEe]+);", t)
    v += [float(m.group(1)), 0.0]
    return v


def build(src, out):
    t = src.read_text()
    v = values(src)
    head, _, _ = t.partition("PARAMETER L(")
    lines = [l for l in t.splitlines() if not l.startswith("PARAMETER L(") and not l.startswith("PARAMETER G(CRNI2")]
    body = "\n".join(lines)
    funcs = "\n".join(f"FUNCTION {n} 298.15 {x:.6f}; 6000 N !" for n, x in zip(NAMES, v))
    pars = """PARAMETER L(LIQUID,CR,NI;0) 1 VV0000+VV0001*T; 10000 N !
PARAMETER L(LIQUID,CR,NI;1) 1 VV0002+VV0003*T; 10000 N !
PARAMETER L(BCC_A2,CR,NI;0) 1 VV0004+VV0005*T; 10000 N !
PARAMETER L(BCC_A2,CR,NI;1) 1 VV0006+VV0007*T; 10000 N !
PARAMETER L(FCC_A1,CR,NI;0) 1 VV0008+VV0009*T; 10000 N !
PARAMETER L(FCC_A1,CR,NI;1) 1 VV0010+VV0011*T; 10000 N !
PARAMETER G(CRNI2,CR:NI;0) 1 GFCCCR+2*GHSERNI+VV0012+VV0013*T; 10000 N !"""
    hdr = (f"$ crni-paper-fit-20261106 step-1 base: {src.name} (sha256 {hashlib.sha256(src.read_bytes()).hexdigest()[:16]}...)\n"
           "$ interaction and CRNI2 terms written as VV symbols with the one-shot values; unaries SGTE91, never fitted\n")
    out.write_text(hdr + body.replace("TYPE_DEFINITION", funcs + "\nTYPE_DEFINITION", 1) + "\n" + pars + "\n")
    return v


if __name__ == "__main__":
    v = build(SRC, R / "tdb/step1_oneshot.tdb")
    v0 = build(SRC0, R / "tdb/step1_oneshot_noSex.tdb")
    json.dump({"names": NAMES, "labels": LABELS, "oneshot_Sex": v, "oneshot_noSex": v0,
               "src": str(SRC), "src_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
               "src_noSex": str(SRC0), "src_noSex_sha256": hashlib.sha256(SRC0.read_bytes()).hexdigest()},
              open(R / "results/oneshot_parameters.json", "w"), indent=1)
    print(dict(zip(LABELS, v))); print(dict(zip(LABELS, v0)))
