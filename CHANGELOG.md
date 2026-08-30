# Improvement Changelog

Numbers from actual pipeline runs (anthropic/claude-sonnet-4-6, case_01, repeat=5) unless noted.
Removed experiments are kept in the log.

| Stage | What & Why | Evidence | Decision / Learning |
|---|---|---|---|
| Baseline | Plain "analyze this" prompt | separation mean 0.0% (stdev 0.0) / reverify N/A | No labels, no formulas — nothing to verify. Consistently unverifiable. |
| Removed: tools-only approach | First hypothesis: force the agent to run code and compute everything, expecting trust to rise | On a code-running baseline (Gemini), the agent silently grouped weeks into a "campaign" and asserted causation more strongly — the computation disguised an assumption as fact | Removed. Running code alone does not raise trust; it can hide assumptions inside plausible output. Pivoted to explicit separation + independent verification. |
| Final (label + formula enforcement) | Force fact/inference/assumption separation + raw values & formula exposure | separation mean 94.5% (stdev 0.97pp) / reverify mean 100% | Kept. Both vertical-trust metrics jump; consistency is tight (low stdev). |
| Independent verifier | Separate deterministic engine re-computes arithmetic against source data | passed 12 / failed 0 / unknown 2 (on ref response) | Kept. Self-reference eliminated. Pearson-type claims fall outside arithmetic scope (unknown). |
| Observation: residual variance | Same prompt, repeated runs | separation 93.3–95.7%, unknown 3–18, one run reverify N/A | Final is not perfectly deterministic; occasionally emits no arithmetic-verifiable claims. Honest limit, not a failure. |
| Boundary case (content) | Apply the same grounding enforcement to a subjective judgment task ("does this video script hook the viewer?") instead of data | separation high (labels still applied) / reverify **not applicable** — no [VERIFIED] claim answers the core question; only peripheral facts (word count, phrase presence) are verifiable, while every hook judgment falls to [INFERENCE] | Confirms the boundary: grounding only produces verified judgments where a verifiable floor exists. Without a floor, the core judgment cannot be verified — the system honestly labels it as inference rather than disguising it as fact. |

## Key Failure Modes & Hot Take
Grounding enforcement only works where there is a verifiable floor. Running code alone does not raise trust — it can disguise assumptions as facts. Trust has two layers: vertical (reason to believe) + horizontal (consistency); both must be restored. Even with enforcement, the agent occasionally produces no arithmetic-verifiable claims — the floor must be checked, not assumed.

Demonstrated across two arenas: on data (verifiable floor) the core claims are [VERIFIED] and reverify 100%; on subjective content (no floor) the same enforcement pushes every core judgment to [INFERENCE] with nothing to re-verify. The boundary is not a failure mode — it is the answer: ask whether a judgment has a verifiable floor before trusting an agent with it.