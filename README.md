# ORCHID-SAGE

**SAGE: Systematic Assessment of Gibbs Energies.**

*Dedicated to the memory of Larry Kaufman, the sage of CALPHAD; see [DEDICATION.md](DEDICATION.md).*

ORCHID-SAGE is a standard for CALPHAD assessments that someone else, a person or a machine, can regenerate from their
inputs. An assessment is described by a **general protocol** (the method, `protocols/general/`) and a **specific
protocol** that instantiates it for one system (`protocols/specific/`). Every input is named by its SHA-256, every run
leaves a **run card** (`protocols/run_cards/`), every judgement is a recorded decision, and a **reproduction tool**
reruns the protocol and compares the result with the published one within declared tolerances. This repository holds:

| part | where |
|---|---|
| the general protocol `orchid-calphad-fit` (2.0.0 to 2.1.2) and its prose rationale | `protocols/general/`, `docs/fit_protocol.md` |
| the Cr–Ni assessment of the paper: specific protocol `crni-paper-fit-step4c-b@1.0.4` (approved), its earlier versions, run cards, evidence bundles, code snapshots, dashboards and rerun reports | `protocols/specific/`, `assessments/crni-paper-fit-step4c-b/`, `assessments/crni-paper-fit-step4-s1/`, `protocols/reproduce/` |
| the schema of protocols, run cards and results | `protocols/schema/`, `protocols/SCHEMA.md` |
| the validator, the reproduction tool and the other protocol tools | `protocols/tools/` |
| the MCP server, so that an agent can read, stage and rerun a protocol | `sage_mcp/` |
| the ORCHID identifier rules (offline) | `orchid_ids/`, `docs/ID_SCHEME.md` |
| the model-screening prototype (recipe catalog, endmember enumeration) | `calphad_model_guide/`, `examples/`, `docs/RECIPE_CATALOG.md` |

It accompanies the paper *ORCHID-SAGE: Fully Reproducible CALPHAD Assessment from Evidence to Phase Diagram*
(R. Arróyave; DOI pending). The workflow RO-Crate of the Cr–Ni assessment is archived separately on Zenodo.

## Requirements

Python 3.11 or newer and git. The protocol tools, the validator, the reproduction tool and the MCP server use only the
standard library. Rerunning the fits needs a fitting environment (see *Reproduce the Cr–Ni assessment*).

## Quick start from a clean clone

```sh
git clone <repository URL> orchid-sage
cd orchid-sage

# tests (standard library only)
python3 -m unittest discover -s tests
python3 -m unittest discover -s sage_mcp/tests -t .
python3 -m unittest discover -s orchid_ids/tests -t .

# validate every protocol, run card and dashboard record: schema, step graph and the sha256 of every file reference
python3 protocols/tools/validate.py --quiet
# the same, re-checked with PyYAML and jsonschema from an interpreter that has them
python3 -m pip install pyyaml jsonschema
python3 protocols/tools/validate.py --quiet --crosscheck "$(command -v python3)"

# scan for local information (paths, host and user names, credentials) before publishing anything
python3 protocols/tools/check_public.py .
```

The validator ends with `errors: 0`. The records keep the sha256 of every file they read. Files that live outside the
repository (the campaign directories of the machines that ran the fits, restricted sources) are not in this public
copy; the validator counts them as "outside this public copy (pinned by sha256 only)" instead of failing. Records
written before 7 November 2026 hold the paths and host names of the machines that ran them, so this copy holds
sanitized copies of them: hosts as machine labels (`mac-studio`, and `spark1` to `spark4` for the four NVIDIA DGX Spark
nodes) and machine-specific locations as placeholders: `<orchid-sage>` for this repository, `<fit-python>` for the fit
interpreter (the one given with `--python`), `<fit-env>` for its virtual environment and `<home>` for the home directory
of the machine that wrote the record. `PUBLIC_SUBSTITUTES.json` lists each such file with the sha256 of the original and
of the copy, and the validator and the reproduction tool accept the copy wherever the original is pinned
(`protocols/tools/public_sanitize.py proof ORIGINAL COPY` recomputes a copy).

## Reproduce the Cr–Ni assessment

The reproduction tool stages the inputs of a specific protocol by hash into a new directory, checks the environment,
runs the protocol's reproduction plan and writes a JSON and a Markdown report (`protocols/REPRODUCE.md`).

**1. Stage the inputs (no dependencies).** Every staged file is checked against the bundle manifests:

```sh
python3 protocols/tools/orchid_reproduce.py protocols/specific/crni-paper-fit-step4c-b@1.0.4.yaml \
    --root /path/to/new/empty/dir --stage-only
```

**2. Build the fitting environment.** The fits used the gradient branch of ESPEI (pull request 268 of ESPEI, commit
9039ea2) and pycalphad at commit 9a6939d; the full environment is locked in `protocols/environment/espei-pr268.lock.txt`.

```sh
python3.12 -m venv fitenv
fitenv/bin/pip install "numpy==2.5.4" "scipy==1.18.1" "symengine==0.13.0" \
  "pycalphad @ git+https://github.com/pycalphad/pycalphad@9a6939dd29f05987df91dfb43418479f90c8e6bc" \
  "espei @ git+https://github.com/cjkunselman18/ESPEI@9039ea215c8946ff6761528071db9e519f37dfb1"
fitenv/bin/python -c "import espei, pycalphad; print(espei.__version__, pycalphad.__version__)"
# expected: 0.8.11.dev82+g9039ea215 0.11.3.dev35+g9a6939dd2
```

The hinge model of the fits comes from PhaseForge+. The records name commit c66656f, which is on a private repository;
public commit 2da1d69 has the identical source tree (git tree 1c7ba5fb356ced5a4bbf4bb533eee04ca12d8c5b, recorded in
`protocols/environment/pins/phaseforgeplus_equivalence.json`). Until pull request
[dogusariturk/PhaseForgePlus#163](https://github.com/dogusariturk/PhaseForgePlus/pull/163) is merged and tagged, take
PhaseForge+ from that commit and give its `src/` directory as `--pfp`:

```sh
git clone https://github.com/ArroyaveLab/PhaseForgePlus.git
git -C PhaseForgePlus checkout 2da1d69ee713aebff16f76ee16cc9b6f40a0777b
git -C PhaseForgePlus rev-parse HEAD^{tree}     # 1c7ba5fb356ced5a4bbf4bb533eee04ca12d8c5b
```

The reproduction tool checks the ten source files by sha256 against
`protocols/environment/pins/spark1_phaseforgeplus_src_files.sha256` (pinned by the specific protocol), so either commit
passes, and its report names the commit and tree it was given.

**3. Rerun.** The per-state evaluation of the published TDB (`evaluate_states`, byte-identical output) takes seconds.
The full plan refits step 4c-b (`step4c_b`), repeats the converged-start check that makes the 10a pick (`check10a`) and
the global search (`global_10c`), and then checks the pick: phase sequence, pure elements, thermochemistry and the
Laplace weights. It takes several hours on four cores; the checks after `check10a` need its pick, so they cannot be run
alone.

```sh
python3 protocols/tools/orchid_reproduce.py protocols/specific/crni-paper-fit-step4c-b@1.0.4.yaml \
    --root /path/to/new/empty/dir --python fitenv/bin/python --pfp PhaseForgePlus/src \
    --only evaluate_states --report report.json
# leave out --only for the full plan (and use a new --root)
```

The verdict is `overall PASS` when every prediction is within its declared tolerance and every byte check that matters
for data identity holds; the environment and PhaseForge+ checks are reported as notes. Earlier reruns, on another
machine and by an agent that used only the MCP server, are in `protocols/reproduce/`.

## Run the MCP server

```sh
python3 -m sage_mcp                    # stdio, built-in JSON-RPC server (standard library)
python3 -m sage_mcp --fallback         # force the built-in server even if the `mcp` SDK is installed
```

For example, with Claude Code: `claude mcp add orchid-sage -e PYTHONPATH=<checkout> -- python3 -m sage_mcp`. The
server reads the repository it sits in and never edits it. It lists the protocols, returns steps, run cards, decisions
and evidence, plans a reproduction and runs one step at a time in a run root outside the repository. Its tools,
settings and safety model are described in [sage_mcp/README.md](sage_mcp/README.md).

## Local configuration

No location on a particular machine and no host or user name is written in the code. Every such setting (data
checkouts, interpreters, campaign directories) comes from an environment variable or from `local/config.json`
(gitignored; template `local.example/config.json`), and otherwise from a default inside the checkout, so a clean clone
runs without one (`protocols/tools/localpaths.py`).

## Frozen records

A record is never edited once a protocol, run card, dashboard or crate pins its sha256, and an approved protocol is
never edited. The builders write through `protocols/tools/frozen.py`, which refuses (exit status 3, nothing written,
files named) to change a frozen record; a change is a new version. When the living rationale `docs/fit_protocol.md`
changes after a protocol pinned it, the pinned text is kept beside it as `docs/fit_protocol@<version>.md`
(`docs/fit_protocol.versions.json`), and the validator resolves the pin by hash.

## The model-screening prototype

`calphad_model_guide` (command `orchid-sage` after `pip install .`) screens candidate sublattice models against a
source-backed recipe catalog, audits model metadata and enumerates endmembers. It does not fit Gibbs energies.

```sh
python3 -m calphad_model_guide search --topic vacancies
python3 -m calphad_model_guide recommend examples/sigma.json
python3 -m calphad_model_guide plan examples/sigma.json --limit 8
```

See [the literature review](docs/LITERATURE_REVIEW.md), [the recipe catalog](docs/RECIPE_CATALOG.md) and
[the implementation notes](docs/IMPLEMENTATION_V02.md).

## Licence and citation

Code is under the MIT licence ([LICENSE](LICENSE)). Protocols, the schema, documentation and data (evidence bundles,
run cards, dashboards, TDB files, figures) are under the Creative Commons Attribution 4.0 International licence
(CC BY 4.0). The scope of each licence is in [LICENSES.md](LICENSES.md). Restricted sources are referenced by sha256
only and are not redistributed. Please cite the paper and this software ([CITATION.cff](CITATION.cff)).

This work was supported by the U.S. National Science Foundation under awards OAC-2608825 and DMR-2534344.
