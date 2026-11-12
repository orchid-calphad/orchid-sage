# ORCHID identifiers for data that ORCHID has not released

Design note, 6 Nov 2026. It implements the PI decision of 6 Nov 2026: people who produce their own ORCHID-compatible data
(measurements, calculations, readings of papers) must be able to give every observation and every state an id
that stays valid after ORCHID releases the data. The note describes the id rules as they are implemented and released
today, the provisional namespace, the alias records and the tooling (`orchid_ids`, the `compute_ids` tools of
ORCHID-SAGE and orchid-mcp). It lists the schema gaps and the choices that need a PI decision. It does not change
any released record or any released rule.

Sources read: `asset_ids.py` (all 29 copies in the group's checkouts), orchid-project.org `tools/export_literature_data.py`,
orchid-data `literature/SCHEMA.md`, `espei/SCHEMA.md`, `contributions/SCHEMA.md` and `contributions/tools/orchid_contrib.py`
(main and `Y25/coord-rule-2`), `graph/SCHEMA.md` and `graph/tools/build_registry.py` (`Y25/coord-rule-2`, c987995dd5,
5 Nov 2026), the Y14 prototype `orchid-review-analysis-20261026/state-ids-20261028/build_state_registry.py`, and the
FIGSTATES exporter.

## 1. The decisions being implemented

1. **Unpublished data** need a stable source namespace in the locator: the user's dataset DOI (for example a Zenodo
   DOI) when there is one, otherwise the provisional namespace `local:<ORCID>/<dataset-uuid>`, with the record flagged
   provisional. On publication an alias record links the provisional id to the published one. Old ids are never
   rewritten.
2. **State ids** (`S-`, `C-`) follow the same principle as ORC ids: they are derived from the canonical state, so two
   people who describe the same state get the same id. If the current implementation assigns them from a registry, a
   switch to derived ids is proposed (section 4).
3. **Tooling**: the id functions ship with ORCHID-SAGE and the ORCHID MCP (`compute_ids`); the SAGE schema and
   validator accept `orchid_link: provisional` with its namespace.

Later on 6 Nov the PI decided the state-id rule (`coord-rule/3`, section 4): invariants keep their own temperature,
the SGTE reference state is part of the descriptor, rounding is decimal, and pressure is `unknown` unless printed.

## 2. Record ids (`ORC-`) as implemented

### 2.1 Canonical code

The rule lives in `asset_ids.py` of the SGTE-corpus tools. There are two versions on this machine, both with the same
`compact()`:

| md5 | copies | difference |
|---|---|---|
| `d6a63407d8d498852490f388d37472e6` | 23, including `orchid-pipeline/pipelines/sgte-corpus/tools-release-v2.1.18/` and `open-tdb/build/sgte-corpus/tools-release-v2.1.18/` (the release tools of v2026.10) | adds `link_observation()` and `require_link()` |
| `637c23e5fe8ef0a3f85f1d60318f295c` | 6 (`tools-release-v2`, `v2.1`, `v2.1.1`, `v2.1.2`, the `db-v2.1/bin/overlay` copies) | older, otherwise identical |

The canonical current module is `orchid-pipeline/pipelines/sgte-corpus/tools-release-v2.1.18/asset_ids.py`. The
released data use it: the corpus stores `pid` and `pid_compact` on every observation, and the exporter
(`export_literature_data.py`, `base_record`) copies `pid_compact` into the record `id`. The website has no second
implementation (no base32 code in orchid-project.org). The FIGSTATES exporter imports the same module.

### 2.2 Rule

```
pid      = source / asset [/ panel] / element [/ cell] [#datum]
source   doi:<lowercased DOI> | isbn:<isbn>[:ch-<n>] | sha256:<first 16 hex of the PDF>
asset    p<page>/tab-<label>[@<y-band>] | p<page>/fig-<label>[@<y-band>][/panel-<x>] | p<page>/text-<nn> | supp-<file>
element  r<nn>[/c<nn>] | s-<series>/pt-<nnn> | s-<series>/crv-<nn>
         in the release also: r-unplaced-<8 hex> (a row whose printed position was not placed), s<nn> (a sentence of a passage)
datum    #<token>; released tokens: equilibrium_property, invariant_reaction, invariant, phase_transition, transition,
         phase_region_vertex_set, phase_assemblage_node, structural_property, property_expression
labels   lowercase, every run of characters outside [a-z0-9._-] replaced by "-", trimmed ("x" when empty)

id       = "ORC-" + base32(SHA-256(pid as UTF-8))[:10]              (RFC 4648 alphabet A-Z2-7; 50 bits)
suffix   when several released values share one pid: id + "." + hex(SHA-256(internal observation id))[:6]
```

Three properties of the release matter for anyone who recomputes ids:

- **The pid is the identity, the other locator fields describe it.** An id is computed once, from the pid at issue,
  and is never recomputed. `locator.asset`, `locator.row` and `paper` may be corrected later: in 13,723 table records
  the pid's source differs from the current `paper` (mostly a `sha256:` PDF hash where `paper` is now a DOI), and
  1,886 invariant or transition rows have a
  `locator.row` that differs from the row in the pid. In 44 records the pid itself was corrected (gate `CX20261028`,
  table 19 to table 15); their ids keep the old pid's hash, and the old pid is in `corrections[field=pid].before`.
- **The datum token is the extraction tool's.** Older invariant readers wrote `#invariant` and `#transition`, newer
  ones `#invariant_reaction` and `#phase_transition`. New data should use the observation type
  (`#equilibrium_property`, `#invariant_reaction`, ...), as the current tools do.
- **The suffix key is not released.** 24,965 of 73,542 records (34%) carry a suffix. The key is the corpus
  observation id, for example `obs:artifact:10-1007-bf02869269:p4:table-4:row-00:lat-1`, which no released field
  holds. Their base recomputes from the pid; the suffix can be checked only with the corpus.

Other record families have their own ids: contributed values `ORC-C` + 10 base32 characters of SHA-256 of the
canonical row content without the contributor (`orchid_contrib.py contribution_id`, 15 characters, a content hash,
not a locator hash), and assessed phase assemblages `aspa-<16 hex>`.

### 2.3 Release check

`orchid_ids` recomputes every record of v2026.10 (orchid-data `main`, `literature/orchid-literature.jsonl.gz`):
73,542 records, 60,118 distinct pids, every pid parses under the grammar above; 73,498 ids recompute from their pid,
the 44 others from the pid at issue. No two distinct pids share a 10-character base. (Test
`OrcIds.test_full_release`, run with `ORCHID_IDS_RELEASE_DATA=<orchid-data checkout>`.)

### 2.4 Test vectors (released records)

Twenty records chosen by a seeded hash over the release (`orchid_ids/tests/vectors.json`, also the public fixture
`orchid-mcp/tests/fixtures/ids_vectors.json`). All recompute.

| id | pid | case |
|---|---|---|
| `ORC-PUAMUBXOHR` | `doi:10.1016/j.jallcom.2009.04.032/p4/tab-2/r13#phase_region_vertex_set` | table row, DOI source |
| `ORC-N72XUKIHP4` | `doi:10.1016/j.calphad.2005.12.006/p7/tab-4/r04#invariant_reaction` | table row |
| `ORC-5II4PLRXME` | `doi:10.1016/j.jallcom.2003.09.017/p2/tab-1/r24#phase_transition` | table row |
| `ORC-TUKNUULK5Y` | `doi:10.1007/s11661-013-1652-8/p9/tab-iii/r45#phase_region_vertex_set` | table row |
| `ORC-GZFNDMYDYQ` | `doi:10.1016/j.calphad.2013.07.013/p12/tab-9/r12#invariant_reaction` | table row |
| `ORC-HEX3VCHY6Z` | `doi:10.1016/j.jallcom.2004.02.012/p2/tab-1/r06#invariant_reaction` | table row |
| `ORC-W2QZISNQG3` | `doi:10.1016/j.jallcom.2007.07.105/p5/tab-2/r15#invariant_reaction` | table row |
| `ORC-2ACYPXXJ45` | `doi:10.1016/s1359-6454(01)00337-8/p6/tab-1/r01#phase_region_vertex_set` | table row |
| `ORC-ZDI62FNVY5` | `doi:10.1016/s0022-3115(00)00713-3/p23/tab-27/r05#equilibrium_property` | table row |
| `ORC-MCI7SEAG5L` | `doi:10.1016/j.pnsc.2018.04.001/p4/tab-2/r02#invariant` | table row, older datum token |
| `ORC-3F4IKD7X5A` | `sha256:8df6e975c3b6dbea/p3/tab-3/r03#equilibrium_property` | PDF-hash source |
| `ORC-JM2SNHD7WB` | `sha256:862a5fa5a46caf69/p6/tab-6/r08#phase_transition` | PDF-hash source |
| `ORC-3FRPCWCPFP` | `doi:10.1016/s0925-8388(00)01077-x/p2/text-15/s11#phase_transition` | text passage, sentence |
| `ORC-GZZDZGOBQE` | `doi:10.1016/j.calphad.2012.02.001/p4/text-25/s18#phase_transition` | text passage, sentence |
| `ORC-2KRMXFM6BV` | `doi:10.1016/j.intermet.2010.03.010/p11/text-02/s02#phase_transition` | text passage, sentence |
| `ORC-KI3CDQOJCE` | `doi:10.1016/j.intermet.2007.04.004/p6/tab-4/r-unplaced-e6f197c9#invariant` | unplaced row |
| `ORC-FUNK6KUKBT` | `doi:10.1016/j.intermet.2010.01.026/p3/tab-1/r-unplaced-742b6b43#invariant` | unplaced row |
| `ORC-ZC4MQXMEFO.241167` | `sha256:80bf7a00c2756190/p3/tab-1/r03#structural_property` | suffixed: base recomputes |
| `ORC-4TRLPVSQ75.661390` | `sha256:c69f23abc99ca9fc/p2/tab-1/r06#structural_property` | suffixed: base recomputes |
| `ORC-EWA34MXCLM.d3fd78` | `doi:10.1016/0364-5916(87)90045-9/p5/tab-ii/r10#invariant` | suffixed: base recomputes |

Suffix rule, with the corpus key: `ORC-YYVN2DF6OA.308f06` and `ORC-YYVN2DF6OA.780394` share
`doi:10.1007/bf02869269/p4/tab-4/r01#structural_property`; the suffixes are the first six hex of SHA-256 of
`obs:artifact:10-1007-bf02869269:p4:table-4:row-00:lat-1` and `...:lat-0`. Corrected pid:
`ORC-22H75DIX7G.405364` has pid `.../p13/tab-15/r06#equilibrium_property` and recomputes from the pid at issue
`.../p13/tab-19/r06#equilibrium_property`.

## 3. State ids (`S-`, `C-`) as implemented

### 3.1 Status

State ids are **not in any release**. v2026.10 has none; the v2027.01 candidate (`Y25/coord-rule-2`, applied as
"registry9") puts `state_class_id` and `state_id` on all 73,542 literature records and on the ESPEI
`orchid.observations[]`. The registry has 178,767 classes and 417,076 coordinate states (current and superseded).

### 3.2 Rule: a hash of a canonical descriptor, issued through a registry

```
C- descriptor = {system, phases, pressure_class[, unresolved_observation]}
S- descriptor = C- descriptor + {coordinates, assignment_rule}
id            = prefix + hex(SHA-256(json.dumps(descriptor, sort_keys=True, separators=(",", ":"), ensure_ascii=False)))[:10]
collision     = the registry hashes descriptor + "#1", "#2", ... and logs it
```

Every row of the registry satisfies this: 178,767 of 178,767 class ids and 417,076 of 417,076 state ids equal the
prefix plus the first ten hex of the SHA-256 of their stored descriptor, and no row needed the collision fallback.
The hash is derived. **The descriptor is not always a function of the observation alone**: the registry builds it with
its ledger in four places.

| registry-dependent part | effect | share of literature records |
|---|---|---|
| invariant and transition groups (`reaction_group {kind, founding_T_K}`) | readings on one phase set that are not shown to be one reaction are separate states; the group's coordinates are the kind and the temperature of its first reading, frozen at issue. A new reading joins a compatible group within 46 K (taking its id), or founds a group at its own temperature | 5,857 (8.0%) |
| invariant readings outside 1 < T <= 6000 K (`reading_alone`) | a new reading stands alone; ledger readings keep the coordinates they were issued with | 10 |
| boundary vs field-point reconciliation | a boundary state whose cell equals a field-point state's is issued under the field-point rule, unless the boundary id was already issued | 8 |
| near-identical merges | dT <= 0.5 K and dx <= 0.001 with the same paper, source, property and value within reading error merge | changes no literature record's id |

Everything else is derived from the record and the phase registry: phases resolve through `phases/registry.json`
(public in every release), the coordinates come from `coord-rule/2` (below), and the configuration block from what
the record prints.

### 3.3 `coord-rule/2` (PI rulings 28 Oct and 1 Nov 2026)

| kind (`assignment_rule`) | when | coordinates |
|---|---|---|
| `invariant-or-transition` | observation type invariant reaction or phase transition | none (T stays on the observations); see groups above |
| `calculated-field-envelope` | calculated two-phase field | none |
| `no-coordinates` | T and composition absent, or a range field present | none; the state is unresolved |
| `boundary-5K-0.02x` | liquidus, solidus, solvus, phase-field vertex | `T_cell_K` = round(T/5)·5, `x_cells` = round(x/0.02)·0.02 |
| `field-point-10K-0.02x` | phase assemblage node | `T_cell_K` = round(T/10)·10, `x_cells` as above |
| `compound-1K-exact-x` | one phase with a registry stoichiometry | `T_cell_K` = round(T), `x` to 4 decimals |
| `solution-exact` | any other property state | `T_K` to 2 decimals, `x` to 4 decimals |
| `0K-exact-x` | T exactly 0 K | `T_K` 0.0, `x` to 4 decimals |

- **Units**: K and mole fractions. Pressure enters only as a class: `ambient` (0.8 to 1.2 x 10^5 Pa), `subambient`,
  `elevated` (up to 10^7 Pa), `high`, and `unknown` when `pressure_Pa` is absent. The literature records carry
  101325 Pa with `pressure_basis: assumed_default_1_atm_not_printed`, so they are `ambient`.
- **Composition**: one form. In a binary with one fraction given, the fraction of the second element (system order);
  when all elements are given and sum to 1 within 0.01, every element but the first; otherwise as given. Keys are
  sorted by the canonical JSON.
- **Rounding**: `round(round(v/step)*step, 8)` in IEEE 754 doubles with Python's half-to-even rounding. This is
  deterministic but not decimal: 0.55 lands in the 0.56 cell (0.55/0.02 = 27.500000000000004) while 0.05 lands in
  0.04 (2.5 rounds to 2). Readings on either side of a cell edge are neighbouring states, compared and never merged.
- **Phases**: printed label and `model_phase` are normalised (uppercase, `L`/`LIQ`/`LIQUIDUS` = `LIQUID`, characters
  outside A-Z0-9 removed) and looked up in the system's registry names (preferred name, TDB names, every namespaced
  name); `model_phase` first. Unmatched phases become `model:<name>` or `label:<name>`. Phases are a sorted set.
  A label that names no phase (`label:` empty, numbers, reaction words, `matrix`, ...) makes the state unresolved.
- **Configuration** (PI 1 Nov): what the record prints enters (`label_terms` such as `b2`, `l12`, a sublattice label,
  a printed Pearson symbol or prototype that differs from the registry's, a record `structure`); a solution phase
  with nothing printed is random by assumption (`configuration.assumed`, basis `assumed_default_not_printed`); no
  assumption for a phase whose name, stoichiometry or model implies order.
- **Reference state, property, source, evidence class** are not part of the state (PI 1 Nov); they live on the
  observation. One state carries many observations. (For the reference state this is superseded on 6 Nov: in
  `coord-rule/3` the SGTE reference is part of the descriptor, section 4.)
- **Unresolved observations** (unknown phases, or missing T or composition) are a state of their own whose descriptor
  holds the record id (`unresolved_observation`).

### 3.4 Reproduction from the records

`orchid_ids.state` is a standard-library port of the descriptor code (`build_registry.py` and the Y14 helpers it
imports). Run on the 73,542 literature records of the v2027.01 candidate with the candidate's phase registry:

| | records |
|---|---|
| `state_class_id` equal | 73,542 (100%) |
| `state_id` equal | 67,667 (92.0%) |
| differ: invariant on a phase set with several reaction groups (2,168 founded their group: the registry id is `alternative_state_ids[0]`; 3,689 joined a group founded by another reading) | 5,857 |
| differ: legacy invariant reading outside 1 < T <= 6000 K held in the ledger | 10 |
| differ: boundary issued under the field-point rule | 8 |

Every difference is one of the registry-dependent parts; `compute_state_id` flags them in `registry_dependent` and
gives `alternative_state_ids` for invariants. (Test `StateIds.test_full_checkout`, `ORCHID_IDS_FULL_DATA=
<orchid-data checkout>`.)

### 3.5 Test vectors (v2027.01 candidate; internal, not released)

38 records, two to eight per rule, resolved and unresolved, printed and assumed configuration
(`orchid_ids/tests/vectors.json` with the phase-registry subset they need). All recompute. Examples:

| rule | record | system | T | composition | `state_class_id` | `state_id` |
|---|---|---|---|---|---|---|
| 0K-exact-x | `ORC-DD374OL74D` | CO-V | 0 K | V 0.25 | `C-9107ddb0d2` | `S-1f210f92bc` |
| boundary-5K-0.02x | `ORC-PSU4C32VEZ` | AL-MG-ZN | 673.15 K | MG 0.40, ZN 0.02 | `C-84330af02a` | `S-23544e80d6` |
| compound-1K-exact-x | `ORC-PAWX3UJ3S3.7a9df8` | B-CR | 298.15 K | CR 0.428571 | `C-fc6ab0e7db` | `S-54a447ab0e` |
| field-point-10K-0.02x | `ORC-XGWLOAZKEQ` | CU-LI-MG | 298.15 K | LI 0.042, MG 0.309 | `C-de7cd4ac11` | `S-3011dc5a6e` |
| invariant-or-transition | `ORC-YBUV7CWUWS` | GA-TE | 303 K | | `C-3704260ca8` | `S-8bf5235f49` |
| solution-exact | `ORC-H2IL4MAZZY` | GA-PB | 830 K | PB 0.6 | `C-aadd9ba176` | `S-acd35b87ad` |
| no-coordinates (unresolved) | `ORC-HAZ44M7NHT.8dddb9` | MN-O | | O 0.6 | `C-5c4ddd1a45` | `S-0ff61116a4` |

The GA-PB descriptor, for example, is
`{"assignment_rule":"coord-rule/2:solution-exact","coordinates":{"T_K":830.0,"configuration":{"assumed":{"basis":"assumed_default_not_printed","configuration":"random","phases":["phase:ga-pb:liquid"]}},"x":{"PB":0.6}},"phases":["phase:ga-pb:liquid"],"pressure_class":"ambient","system":"GA-PB"}`.
Two grouped invariants (`ORC-34X655FK2P`, eutectic at 1553 K, registry `S-2af19581c8`; `ORC-6C7GGYQCSM`, 993.15 K,
`S-553130b665`) test that the registry id is the alternative "own founding group" id.

## 4. `coord-rule/3`: the rule decided on 6 Nov 2026 (for v2027.01)

PI decisions of 6 Nov 2026, with the coordinator's choices within them. `orchid_ids` computes `coord-rule/3` by
default (`rule="coord-rule/2"` reproduces the current candidate registry). The candidate registry has not been
rebuilt; no `coord-rule/3` id has been issued.

| part | `coord-rule/3` | was (`coord-rule/2`) |
|---|---|---|
| invariants and transitions | PI: "Invariant temperature is important. We should not exclude it." Coordinates = the record's own temperature in a 5 K cell (`T_cell_K`, the boundary cell) + the printed reaction kind (`reaction_kind`, `transition_kind` of the record, `unstated` when absent) + configuration; rule `coord-rule/3:invariant-5K-kind`. No ledger groups. Readings of one reaction that fall in different cells get different ids, linked in the graph by `same_reaction_as` edges | ledger groups `reaction_group {kind, founding_T_K}` |
| reference state | PI: "The whole point of ORCHID is that we use SGTE reference states to guarantee compatibility with other CALPHAD databases." The class descriptor carries `reference_state` = the SGTE SER of every element of the system, in the literature field's form `{EL: {phase, fixed_state_variables: {T: 298.15, P: 100000}}}` (SER phases from the ELEMENT lines of the SGTE Unary Database V5.0). It is the same for every state of a system: values printed on another reference are converted to SER before they enter; a value that cannot be converted is flagged, never given another reference in its id. This supersedes, for the id descriptor, the 1 Nov ruling that the reference state stays on the observation | not in the descriptor |
| rounding | decimal round-half-even of the decimal value as written (a float by its shortest repr), also for the 4-decimal and 0.01 K exact values and the binary complement 1 - x | binary floating point (`round(round(v/step)*step, 8)`) |
| pressure | `unknown` unless a pressure is printed: absent, or `pressure_basis` starting with `assumed` / `unstated`, gives `unknown` (no 101325 Pa assumption) | class of the stored value (101325 assumed gives `ambient`) |
| boundary vs field point | no reconciliation: the observation type chooses the rule; equal stored coordinates become a graph edge | field-point rule when the cells coincide |
| near-identical merges | graph edges (`same_state_as`), `merged_into` appended after review | merged by the registry |
| out-of-range invariant readings | stand alone on their record id (`reading_alone`) | same for new readings; ledger readings kept their issued coordinates |

Everything else is `coord-rule/2` (cells for boundaries, field points and compounds, phase resolution, configuration,
unresolved observations). The id is now a pure function of the record and the phase-registry release.

### 4.1 Effect on the v2027.01 candidate (73,542 literature records, `Y25/coord-rule-2`)

- **Every candidate S- id and C- id changes**: the class descriptor gains `reference_state` and the pressure class
  becomes `unknown` for all records (73,537 have `pressure_basis: assumed_default_1_atm_not_printed`; the other 5 have
  no stored pressure). As the ids are not published, nothing is rewritten.
- **The partition of records into states**: 42,296 registry states become 49,583. 4,185 registry states split (all
  invariants or transitions, and 4 field points); 21 `coord-rule/3` states join records of more than one registry
  state (19 invariants, 2 boundaries).
- **Decimal rounding** changes the coordinates of 109 of the 37,420 non-invariant records.
- **Test vectors**: the 40 state-vector records of section 3.5 also carry their `coord-rule/3` ids
  (`state_vectors_rule3`, regression vectors, since no registry has issued them), and hand-built descriptors check the
  invariant, reference, rounding and pressure rules. Examples: GA-PB liquid at 830 K (`ORC-H2IL4MAZZY`)
  `C-2866cf1b1e` / `S-7333e24e7b` (was `C-aadd9ba176` / `S-acd35b87ad`); the GA-TE invariant at 303 K
  (`ORC-YBUV7CWUWS`) `C-a87ca8c9b9` / `S-17a525f6f0` (was `C-3704260ca8` / `S-8bf5235f49`).

### 4.2 Invariant replicates: the 5 K cell splits many of them

The ledger holds 6,415 invariant or transition states with two or more readings (24,050 readings); their spread in
temperature is 0 K for 1,127, at most 1 K for 932 more, at most 5 K for 1,488, at most 10 K for 884 and up to 46 K for
1,984. Readings of one ledger state that land in different `coord-rule/3` states:

| key | ledger states split | states they become | readings outside their group's largest cell |
|---|---|---|---|
| 1 K cell + kind | 5,081 (79%) | 15,757 | 12,335 (51%) |
| **5 K cell + kind (`coord-rule/3`)** | **4,185 (65%)** | **11,489** | **9,385 (39%)** |
| 5 K cell, no kind | 3,980 (62%) | 10,025 | 8,035 (33%) |
| 10 K cell + kind | 3,499 (55%) | 8,934 | 7,652 (32%) |
| 10 K cell, no kind | 3,191 (50%) | 7,453 | 6,091 (25%) |
| 46 K band + kind (option C) | 1,938 (30%) | 4,243 | 4,016 (17%) |
| 46 K band, no kind | 1,279 (20%) | 2,558 | 2,019 (8%) |

So quantisation by the 5 K cell splits replicate readings of one reaction in two of every three multi-reading
invariant states, and puts 39% of replicate readings outside their group's main cell. Most of this is the ordinary
scatter of invariant temperatures between papers (1,984 of the ledger states span 10 to 46 K); the printed kind (a
reading with a kind and one without, or `eutectic` vs `other`) adds 205 split states at 5 K and 659 at 46 K. Even the
46 K band splits 30% of the states. The graph keeps
them linked (`same_reaction_as`), but an ESPEI user who groups by `state_id` would see one reaction as several states.
This is the number the coordinator asked for before putting option C (46 K band) to the PI. Note that any fixed band
splits readings that straddle its edges; the ledger avoided that only by being history-dependent.

### 4.3 Reference states of the released records (v2026.10, 73,542 records)

`orchid_ids.reference_status` compares each record's `reference_state` with SER:

| status | records | meaning |
|---|---|---|
| not applicable | 59,256 | property does not depend on a reference (invariant T, phase compositions, lattice, Cp, ...) |
| SER | 7,131 | every element on its SGTE SER phase (with TDB spellings such as `A1_FCC`, `DIA_A4`, `GRAPHITE_A9`, `ORTHORHOMBIC_GA`), or printed text naming SER |
| convertible | 2,341 | a pure-element phase of the SGTE unary other than SER, mostly `LIQUID` for mixing and partial quantities (HM_MIX 902, PARTIAL_ENTHALPY 505, HM_FORM 234, EMF 209, GM_FORM 79, GM_MIX 79, ACR_* ...): converts with the SGTE unary lattice stabilities at the record's temperature |
| needs reading | 3,872 | only printed text, often `none` (`{phase: "printed: none"}`), or a phrase ("solid Ln and solid Ru", "Ru solid and Sn liquid"): the reference has to be read from the page before conversion (HM_FORM 2,817, HM_MIX 274, SM_FORM 256, GM_FORM 240, ...) |
| missing | 910 | a reference-dependent property without a reference (HM_FORM 293, PARTIAL_ENTHALPY 228, EMF 220, CHEMICAL_POTENTIAL 53, ...) |
| not convertible | 32 | referred to a compound or an ordered phase (`AL8MG5_BETA`, `AL12MG17_A12`, `B2_BCC`, `AL13FE4`, `SIGMA_D8B`, `L12_FCC`, ...): needs that phase's Gibbs energy, not the unary |

The existing fields hold the conversion: `reference_state` (after), `reference_state_stored` and
`corrections[].evidence.conversion` (literature/SCHEMA.md: "Reference-state conversions retain the original value and
conversion"), and the ESPEI `orchid_reference_state` with `basis`. No conversion was made here: the conversion code
(the unary functions at T, H = G - T dG/dT for enthalpies) is v2027.01 work. Gas-referenced elements (SER
`1/2_MOLE_O2(G)` and the other diatomic gases) have no unary phase parameters in the unary file, so values referred to
them convert only with the gas data.

## 5. Collisions

Expected number of colliding pairs for n ids of b bits: n(n-1)/2^(b+1).

| id | bits | n today | expected pairs today | at 10^6 | at 10^7 |
|---|---|---|---|---|---|
| ORC- base (10 base32) | 50 | 60,118 pids (v2026.10) | 1.6 x 10^-6 (none found) | 4.4 x 10^-4 | 0.044 |
| ORC suffix (6 hex, within one pid) | 24 | at most a few values per pid | below 10^-6 per row | | |
| C- (10 hex) | 40 | 178,767 | 0.015 (none found) | 0.45 | 45 |
| S- (10 hex) | 40 | 417,076 (all rows ever issued) | 0.079 (none found) | 0.45 | 45 |

Ten hex characters were chosen for MLIP-scale growth (PI, 28 Oct); at 10^7 states about 45 collisions are expected,
so the collision path will be used. Handling today: the state registry issues `descriptor#1` (first free); the record
exporter asserts uniqueness and would fail the build (no rule). A collision makes the second-comer's id
non-derivable, so offline ids must be checked at intake: intake recomputes, finds the raw id held by another
descriptor, issues the `#n` id and writes an alias row from the raw (provisional) id. The collision log stays in the
registry. For ORC ids the same handling is proposed (the later pid takes `pid#1`), to be confirmed (section 11).

## 6. Provisional namespace and the flag

```
source  = local:<ORCID>/<dataset-uuid>
ORCID   bare 0000-0000-0000-000X form, ISO 7064 mod 11-2 checksum verified (as orchid_contrib.orcid_ok)
uuid    canonical lowercase 8-4-4-4-12 (version 4 recommended), generated once per dataset and kept with it
pid     local:0000-0002-1825-0097/3f2504e0-4f89-41d3-9a0c-0305e82c3301/supp-dsc-runs.csv/r03#equilibrium_property
id      ORC-...  (same compact() as every other pid)
```

The rest of the locator uses the existing grammar: a data file is a `supp-<file>` asset with rows `r<nn>` (or a
figure `p<n>/fig-<label>/s-<series>/pt-<nnn>` when the data are read from the user's own plot). A deposited dataset
uses its DOI as source: `doi:10.5281/zenodo.1234567/supp-dsc-runs.csv/r03#equilibrium_property`. Such ids are final,
not provisional; they become ORCHID-released when ORCHID takes the data in.

**The flag.** The namespace prefix is self-describing: a pid starting with `local:` is provisional. No new record field
is needed for the tools (`compute_orc_id` and `parse_pid` return `provisional: true`). Whether a record should also
carry an explicit flag (and under which existing field) is a schema decision (section 10). In ORCHID-SAGE evidence,
`orchid_link: provisional` marks a link to ids that ORCHID has not released (either namespace); each `orchid_links`
item carries the `pid` its `id` recomputes from.

State ids need no namespace: a resolved state's S- id does not depend on the source, so a provisional and a published
observation of one state share it. Only an unresolved state (its descriptor holds the record id) changes with the
record id.

## 7. Alias records

When provisional data are published (a paper or a dataset DOI), every observation gets the ORC id of its published
locator. The provisional id is never rewritten or reused; an alias row points from it to the published id. Field names
are the existing ones (`id`, `pid` from literature/SCHEMA.md; `status`, `superseded_by`, `first_release`,
`lineage_note` from the registry rows of graph/SCHEMA.md):

```json
{"id": "ORC-<provisional>", "pid": "local:<ORCID>/<uuid>/supp-data.csv/r01#equilibrium_property",
 "status": "superseded", "superseded_by": "ORC-<published>", "first_release": "2027.01",
 "lineage_note": {"reason": "provisional_namespace_published",
                  "published_pid": "doi:10.5281/zenodo.1234567/supp-data.csv/r01#equilibrium_property",
                  "provisional_source": "local:<ORCID>/<uuid>", "published_source": "doi:10.5281/zenodo.1234567"}}
```

The published record also lists the provisional id and pid in its existing `merged_ids` / `merged_pids` (an earlier
identification of the same observation). An unresolved state whose S- id held the provisional record id gets a state
alias row `{state_id, status: superseded, superseded_by}`. `orchid_ids.build_alias_record` refuses an alias whose ids do
not recompute from their locators, whose target is still provisional, or that points the wrong way.

## 8. Computing ids offline

- **Library**: `orchid_ids` in ORCHID-SAGE (standard library only, Python 3.10+): `compute_orc_id`, `build_pid`,
  `make_provisional_namespace`, `new_dataset_uuid`, `compute_state_id` (with `PhaseRegistry.load(<ORCHID data dir>)`;
  `phases/registry.json` and `phases/systems/*.json` of a release), `compute_ids` (both), `check_link`,
  `check_provisional_link`, `validate_id`, `build_alias_record`, `build_state_alias`, `contribution_to_record`.
- **Command line**: `python -m orchid_ids namespace --orcid ...`, `record --pid ...`, `state --record r.json --data
  <dir>`, `file records.json --data <dir>`, `check --id ... --pid ...` (also installed as `orchid-ids`).
- **MCP**: `compute_ids` in the ORCHID-SAGE server (phase registry of `ORCHID_DATA_DIR`) and in orchid-mcp (phase
  registry of its data source, local or `data.orchid-project.org`; vendored copy in `src/orchid_mcp/vendor/`).

`compute_state_id`, `compute_ids`, the CLI (`--rule`) and both MCP tools take `rule`: `coord-rule/3` (default) or
`coord-rule/2` (the candidate registry). Every state result names the rule, the phase-registry release used, whether the
value is on the SGTE reference (`value_reference`, `flags`), and what keeps the id
provisional (`registry_dependent`, unresolved observation, no phase registry loaded).

## 9. How ORCHID intake accepts them

1. Contributed records carry `id` and `pid` (and may carry the `state_id` / `state_class_id` they computed).
2. Intake parses the pid (grammar of section 2.2 plus the `local:` source), checks the ORCID checksum and UUID form,
   and recomputes the id; a mismatch is an error.
3. `local:` ids are accepted as provisional: the values stay `contributed_unverified`, never `espei_ready`, as every
   contributed value.
4. State ids are recomputed by the registry; the registry's value is issued. A contributor's state id that differs is
   reported, with the reason (`registry_dependent`, phase-registry release, collision).
5. On publication the contributor (or a maintainer) submits the published locator; intake issues the published ids,
   writes the alias rows and the `merged_ids` / `merged_pids`, and never changes the provisional rows.

## 10. Schema gaps and v2027.01 proposals

Decided 6 Nov 2026: gaps 1 to 5 and 10 are carried as proposals for v2027.01 (frozen 15 Jan, released 29 Jan 2027).
No change goes to the released schema now, and the point release carries no schema change. Proposals 1 to 5 and 10
below are what the schema branch would take; each still needs the PI's approval of the text when the schema is frozen.

1. **`local:` source** (proposal P1). Now: not in literature/SCHEMA.md; `asset_ids.require_link` accepts only `doi:`,
   `isbn:`, `sha256:`; `contributions/SCHEMA.md` and `orchid_contrib.py` require `provenance.doi` or
   `provenance.dataset_doi`, so intake refuses `local:`. Proposal: add `local:<ORCID>/<dataset-uuid>` to the source
   grammar of `pid` (literature/SCHEMA.md, asset_ids.py, `require_link`), and let contribution types C and D give it
   in place of a DOI, as provisional values (`contributed_unverified`, never `espei_ready`).
2. **Record-level provisional flag** (P2). Now: no field. Proposal: the pid prefix is the flag (a record whose `pid`
   starts with `local:` is provisional); no new field. Alternatives, if an explicit field is wanted: an enum value of
   `flags.review_state`, or `lifecycle_status: provisional` (the registry's word, now used for ternary-and-higher
   states, a different meaning).
3. **Alias rows for ORC ids** (P3). Now: no table; the registry has `status` / `superseded_by` for S-/C-, literature
   has `merged_ids` / `merged_pids` on the survivor. Proposal: the alias rows of section 7 (registry field names) in
   one append-only file next to the literature records, plus `merged_ids` / `merged_pids` on the published record.
4. **Who sets state ids** (P4). Now: contributions/SCHEMA.md says `state_class_id`, `state_id`, `locator` are "set by
   maintainers on accepted values, never by a contributor". Proposal: contributors may submit the ids they computed as
   claims; intake recomputes under the release's rule and issues; a difference is reported, never silently replaced.
5. **Suffix key for new data** (P5). Now: released suffixes hash an unreleased corpus key. Proposal: new data give one
   value per locator, with a distinct datum per value (`#property-<quantity>`, already in the asset_ids.py grammar),
   so no suffix is needed; released suffixed ids stay as they are.
6. **Contributed record ids** `ORC-C...` hash the row content: a corrected value gets a new id, and the 15-character
   form fails the SAGE schema `orchid_record_id` pattern `^ORC-[0-9A-Z]{10}$`.
7. **Contributed values in the registry** are read from the raw rows (`build_registry.contributed_claims`): no
   observation type and the invariant temperature only from `state.temperature_K`; `orchid_contrib.to_record` takes
   the invariant T from the value. (Pressure now agrees with `coord-rule/3`: `unknown` when not printed.)
8. **Dataset assets**: `locator.artifact: dataset` exists for contributed values, but there is no pid grammar for a
   data file other than `supp-<file>`; this note uses `supp-` (no new grammar).
9. **Pid element forms** `r-unplaced-<hex>` and `s<nn>` are in the release but not in the asset_ids docstring.
10. **ORC collisions** (P10). Now: no rule (the exporter would stop). Proposal: as for state ids, the later pid takes
    `compact(pid + "#1")`, logged, with an alias row from the raw id.
11. **SGTE reference in the records** (new with `coord-rule/3`). The id is SER-based, but 2,341 released values are on
    a convertible non-SER reference, 3,872 need the reference read from the page, 910 have none and 32 are referred
    to compounds or ordered phases (section 4.3). The conversion uses existing fields (`reference_state_stored`,
    `corrections[].evidence.conversion`); there is no flag for "not convertible to SER". Proposal: a `gate_failures`
    code (the existing mechanism for such flags), for example `reference_state_not_sgte`, styled after the existing
    `reference_state_not_ser` drop reason of the ESPEI builder.

## 11. Decisions

Decided on 6 Nov 2026 (PI, with the coordinator's choices within them):

1. Invariants keep their temperature: own printed T in the 5 K cell + reaction kind + configuration (not option B).
2. The SGTE SER reference state is part of the descriptor; non-SER values are converted before they enter, or flagged.
   The 1 Nov ruling (reference on the observation) is superseded for the id descriptor.
3. Decimal round-half-even.
4. Pressure `unknown` when not printed (coordinator).
5. `orchid_link: provisional` covers `local:` and dataset-DOI ids.
6. Gaps 1 to 5 and 10 are v2027.01 proposals; no schema change in the point release.

Open:

1. Invariant cell vs band: the 5 K cell splits 65% of multi-reading invariant states (section 4.2); the coordinator
   may put option C (46 K band, 30% split) to the PI.
2. Whether `reaction_kind` stays in the invariant descriptor (it adds 205 split states at 5 K, 659 at 46 K).
3. The text of proposals P1 to P5, P10 and the new gap 11 when the schema is frozen.
4. Publishing: orchid-mcp is public; the `compute_ids` branch (`ids-compute-tool`, local only) ports the unreleased
   state rules. The coordinator asks the PI before any push.

## 12. Files

| file | content |
|---|---|
| `orchid_ids/locator.py` | ORC ids, pid grammar, provisional namespace, link check |
| `orchid_ids/state.py` | C-/S- ids: `coord-rule/3` (decided 6 Nov) and the `coord-rule/2` port, phase registry |
| `orchid_ids/alias.py` | alias rows |
| `orchid_ids/reference.py` | SGTE SER phases and unary phases (SGTE Unary V5.0), reference status of a value |
| `orchid_ids/__init__.py`, `__main__.py` | `compute_ids`, `check_provisional_link`, command line |
| `orchid_ids/tests/` | tests and vectors (released ORC vectors; candidate state vectors, internal) |
| `sage_mcp/ids.py`, `sage_mcp/server.py` | `compute_ids` tool; tests in `sage_mcp/tests/test_ids.py` |
| `protocols/schema/common.schema.json`, `assessment-results.schema.json` | `orchid_link: provisional` |
| `protocols/tools/validate.py` | provisional links must recompute from their pid |
