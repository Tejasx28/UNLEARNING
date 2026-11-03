# Development decisions before held-out evaluation

The development author is Basil Mahfouz Al-Kuwaiti. Nikolai Abilov, Acanthus
Nectarius, and Moshe Ben-David are excluded from policy tuning for this study.
They are selected stress cases with existing historical project evidence, not
randomly sampled authors.

An initial development run is preserved separately in
`../atu_v2_v3_controlled_20261019`. Its v2 checkpoint suppressed all eight
control-validated probes but exceeded the retain limit (drop 0.0655 versus 0.03).
The initial v3 NPO attempt used learning rate 1e-5 and beta 0.1: after 20 steps,
its development leakage remained 100%, no canonical target crossed the floor,
and retain drop was 0.0004. That run was interrupted during a later retry to
correct model-reference retention between attempts.

Before the main held-out phase:

1. Balanced v3 starts from the existing canonical v2 optimizer calibration:
   learning rate 5e-5, beta 0.5. The v3 guard still restores safe round snapshots.
2. Candidate ranking prefers convergence, then lower development leakage, then
   canonical suppression among utility-safe trials. Unused utility margin does
   not override better leakage results within the allowed limit.
3. Safety callbacks release model references before loading a retry. A weak-
   reference regression test verifies actual model collection.
4. RMU uses a local generator for its fixed steering vector, preserving each
   experiment's training/shuffle random seed.
5. Both versions use a 48-token generation cap and five canonical ROUGE samples
   in the corrected comparison. All 20 forget examples retain likelihood
   evaluation. Eight final probe prompts and 12 retain validation examples are
   shared between versions; generation limits do not differ between them.

The final protocol and source hashes are saved in `frozen_protocol.json` before
any held-out request is trained. No held-out result is used to adjust these rules.
