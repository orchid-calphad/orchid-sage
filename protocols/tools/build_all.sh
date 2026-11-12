#!/bin/sh
# Rebuild every generated protocol file in dependency order, then validate. Reads campaign directories; writes only
# under protocols/. Usage: sh tools/build_all.sh   (from protocols/)
set -e
cd "$(dirname "$0")/.."
# machine-specific locations from the environment or local/config.json (tools/localpaths.py; template local.example/config.json)
FIT_PY=$(python3 tools/localpaths.py fit_python); MLIP_PY=$(python3 tools/localpaths.py mlip_python); ORCHID_NEXT=$(python3 tools/localpaths.py orchid_data_next)
# Frozen records (tools/frozen.py: pinned by a protocol, crate or manifest, or an approved protocol) are never changed.
# Every builder below refuses (exit 3, nothing written, files named) when a frozen record would change; refusals are
# also collected in $ORCHID_FROZEN_LOG, and build_all exits 3 if any builder refused, even one whose failure is tolerated.
# The preflight runs the run-card builder in --check mode first, so its known case (a campaign directory moved under
# frozen run cards) stops the build before anything at all is written.
ORCHID_FROZEN_LOG="$(python3 tools/localpaths.py state_dir)/build_all_frozen.log"; export ORCHID_FROZEN_LOG
mkdir -p "$(dirname "$ORCHID_FROZEN_LOG")"; : > "$ORCHID_FROZEN_LOG"
frozen_report() { if [ -s "$ORCHID_FROZEN_LOG" ]; then echo "build_all: refused to change frozen records:" >&2; cat "$ORCHID_FROZEN_LOG" >&2; exit 3; fi; }
python3 tools/backfill_run_cards.py --check || { echo "build_all: preflight refused (frozen run cards named above); nothing written" >&2; exit 3; }
python3 tools/sync_palette.py
python3 tools/snapshot_code.py crni-paper-fit-step4c-b && python3 tools/snapshot_code.py || echo "snapshot_code: frozen snapshot kept; live campaign files changed since (reported above, not absorbed)"   # refuses to overwrite a frozen file
S=${Y25_OBSERVATIONS:?set Y25_OBSERVATIONS to graph/observations.parquet of orchid-data-next branch Y25/state-ids-locator}
for w in cuzr crni; do "$FIT_PY" -I tools/build_evidence_bundle.py $w --registry "$S" --version 2.0.0 --orchid "$ORCHID_NEXT" || echo "build_evidence_bundle $w 2.0.0: frozen bundle kept; the 7 Nov builder fixes (vertex element, unknown vertices) change its states, so applying them needs a new --version"; done   # a frozen version is never overwritten: bump --version on any change
"$FIT_PY" -I tools/build_evidence_bundle.py crni4cb --registry "$S" --version 1.1.0 --previous "MANIFEST@1.0.0.json (kept; 1.0.0 labelled ZPF vertices given in x(CR) as x(NI) and re-derived exclusion tiers instead of copying those the fit read)" --orchid "$ORCHID_NEXT"   # Cr-Ni step-4 pick step4c-b (PI 6 Nov); 1.1.0 = 7 Nov builder fixes; states_evaluated@1.1.0 by evaluate_states.py (reproduce item evaluate_states of 1.0.2)
"$FIT_PY" -I tools/build_evidence_bundle.py crni4cb --registry "$S" --version 1.2.0 --previous "MANIFEST@1.1.0.json (kept; 1.1.0 read the stale hinge label 'assumed_from_diagram (option C)' as non-observed at all 366 hinge states, re-derived the ZPF tiers instead of copying the fit's, and held two files with a personal home path)" --orchid "$ORCHID_NEXT"   # 1.2.0 = record fixes of crni-paper-fit-step4c-b@1.0.4 (7 Nov); states_evaluated@1.2.0 by evaluate_states.py
for a in cuzr-oneshot-h2-s7 crni-paper-fit-step4-s1 crni-paper-fit-step4c-b; do python3 tools/prepare_intake.py ../assessments/$a || echo "prepare_intake $a: frozen intake kept (build a new --version)"; done   # never overwrites a pinned intake (7 Nov)
python3 tools/prepare_intake.py ../assessments/crni-paper-fit-step4c-b --version 1.1.0 --bundle 1.2.0   # pinned by crni-paper-fit-step4c-b@1.0.4
python3 tools/backfill_run_cards.py
python3 tools/pin_hashes.py general/*.yaml
python3 tools/pin_hashes.py specific/*.yaml                        # instantiates + run-card hashes (dashboards may still be missing)
# the extractors are frozen records themselves (the dashboard data pin their sha256), so they are not edited: they write
# into a build directory and the result is installed through the guard
BT="$(python3 tools/localpaths.py state_dir)/build_tmp"; mkdir -p "$BT"
python3 tools/extract_dashboard_data.py cuzr "$BT/cuzr-oneshot-h2-s7.json" && python3 tools/frozen.py install "$BT/cuzr-oneshot-h2-s7.json" dashboards/cuzr-oneshot-h2-s7/dashboard_data.json
python3 tools/extract_dashboard_data.py crni "$BT/crni-paper-fit-step4-s1.json" && python3 tools/frozen.py install "$BT/crni-paper-fit-step4-s1.json" dashboards/crni-paper-fit-step4-s1/dashboard_data.json
python3 tools/extract_dashboard_data_crni4cb.py "$BT/crni-paper-fit-step4c-b.json" && python3 tools/frozen.py install "$BT/crni-paper-fit-step4c-b.json" dashboards/crni-paper-fit-step4c-b/dashboard_data.json
for d in cuzr-oneshot-h2-s7 crni-paper-fit-step4-s1 crni-paper-fit-step4c-b; do python3 tools/build_dashboard.py dashboards/$d/dashboard_data.json dashboards/$d/dashboard.html --snapshot; done
"$FIT_PY" -I tools/fig_dashboard_panels.py dashboards/crni-paper-fit-step4-s1/dashboard_data.json figures/crni-paper-fit-step4-s1 2>&1 | grep -v findfont
"$FIT_PY" -I tools/fig_dashboard_panels.py dashboards/crni-paper-fit-step4c-b/dashboard_data.json figures/crni-paper-fit-step4c-b 2>&1 | grep -v findfont
python3 tools/pin_hashes.py specific/*.yaml                        # dashboard hashes
for f in general/*.yaml; do b=$(basename "$f" .yaml); python3 tools/build_crate.py --render "$f" "general/$b.md" "general/$b.html"; done
# crates: one per id, except crni-paper-fit-step4c-b: the 1.0.0 crate in crates/crni-paper-fit-step4c-b is frozen and never
# rebuilt; the approved 1.0.2 has its own crates/crni-paper-fit-step4c-b-1.0.2 and 1.0.3 crates/crni-paper-fit-step4c-b-1.0.3, both FROZEN since 7 Nov
# (a rebuild would copy the newer evidence versions into them); the final 1.0.4 has crates/crni-paper-fit-step4c-b-1.0.4 (pinned evidence only,
# substitutes, reproduce subfolders); 0.2.0-draft and 1.0.1 are superseded (rendered, no crate)
for f in specific/*.yaml; do b=$(basename "$f" .yaml); python3 tools/build_crate.py --render "$f" "specific/$b.md" "specific/$b.html"
  case "$b" in
    crni-paper-fit-step4c-b@1.0.4) d=crates/crni-paper-fit-step4c-b-1.0.4 ;;
    crni-paper-fit-step4c-b@*) continue ;;
    *) d="crates/${b%@*}" ;;
  esac
  if [ "$b" = "crni-paper-fit-step4c-b@1.0.4" ]; then python3 tools/build_crate.py "$f" "$d" --addenda --decisions --pinned-evidence --substitutes --reproduce-tree --public; else python3 tools/build_crate.py "$f" "$d"; fi; done
frozen_report
python3 tools/validate.py --quiet --crosscheck "$MLIP_PY"
