# Improvement Changelog

Append one row per iteration. Numbers are auto-recorded by the scorer; interpretation is manual.
Removed experiments must also be kept in the log.

| Stage | What & Why | Evidence (separation / reverify) | Decision / Learning |
|---|---|---|---|
| Baseline | Plain "analyze this" prompt | separation 0% / reverify N/A (no verifiable claims) | Starting point. No labels, no formulas — nothing to verify |
| Iteration 1+2 | Force label separation + raw values & formula exposure (skill) | separation 100% / reverify 100% (unknown 2) | Kept. Not yet measured as separate steps — current final prompt applies both together |
| Iteration 3 | Independent verifier re-computes arithmetic against source data (verification) | passed 12 / failed 0 / unknown 2 | Kept. Self-reference eliminated; Pearson claims fall outside arithmetic verifier scope |
| Iteration 4 | (planned) removed-experiment slot | (planned) | (planned) |
| Final | Combine what worked | (planned — pending full pipeline run) | Core contribution: separation + independent re-verification |

## Key Failure Modes & Hot Take
Grounding enforcement only works where there is a verifiable floor. Running code alone does not raise trust — it can disguise assumptions as facts. Trust has two layers: vertical (reason to believe) + horizontal (consistency); both must be restored.
