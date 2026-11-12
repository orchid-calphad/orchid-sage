# <System> CALPHAD fit — plan (written <date>, before any launch)

Protocol: orchid-calphad-fit@<version> (general/), rationale docs/fit_protocol.md (sha256 <...>).
Established practice read (0.0b): <rows that apply; quote what the last campaign did for every item this brief touches>

## Inputs (read only; path + sha256)
| what | path | sha256 |
|---|---|---|

## Model
Phases, sublattices, VV symbols (a + bT per term), SGTE unaries source.

## Data groups per step and free symbols per step
| step | groups | free | hinge | starts |
|---|---|---|---|---|

## Certainty tiers and exclusions
Classifier command, counts per tier, observed vs diagram-assumed exclusions.

## Ranking thresholds (stated before ranking)
R1 plausibility thresholds; R2 accepted topology over <T range>; R3 quantitative windows.

## Compute and wall time
Hosts (load checked at <time>), workers, per-block estimate; stop for a decision above 12 h.

## Run log
(appended during the run)
