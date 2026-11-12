# Not used (PI, 6 Nov 2026: "we cannot change things every time"; the original 5 Nov campaign protocol stands)

USED: the 5 Nov campaign as planned, with the PI decisions that followed:
- m_scraps 128-atom SQS, 2 seeds, both potentials;
- staged relaxation s0–s3 with lattice checks, s2 as the protocol value and the [s3, s0] interval as σ;
- the RK fit with SGTE end-members, alphabetical L(CR,NI;k);
- the whole composition range;
- disordered FCC_A1 only;
- 100 ps liquid MD at 1900 and 2200 K, with 108 vs 864 atoms and the corrected Hong–Liu entropy.
Results: solids_*.json, liquid_*.json, oneshot_tdb.json, tdb/.

NOT USED, kept for the record:
- pf_standard/ (ATAT-SQS sqscal attempts) and pf_mscraps/ (fork 88669ba, failed on the heredoc bug; fork 517967b, stopped):
  tests of the PhaseForge fork, not used.
- Ordered fcc cells (L1₂, L1₀, D0₂₂, Pt₂Mo-type CrNi₂): computed, labelled "not used" in solids_*.json.
- attic/: the withdrawn oneshot_ordered TDB, the L0–L2 liquid TDB, the stopped inflection-detection job, and superseded labels.
