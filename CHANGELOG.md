# Improvement Changelog

Append one row per iteration. Numbers are auto-recorded by the scorer; interpretation is manual.
Removed experiments must also be kept in the log.

| Stage | What & Why | Evidence (separation / reverify) | Decision / Learning |
|---|---|---|---|
| Baseline | Plain "analyze this" prompt | separation ~12% / reverify 0% | Starting point. Facts and inferences mixed; nothing verifiable |
| Iteration 1 | Force fact/inference/assumption label separation (skill) | separation ~95% | Kept. Labelling is decisive |
| Iteration 2 | Force raw values + formula exposure (skill) | re-verifiable ~95% | Kept. Verification material now present in response |
| Iteration 3 | Independent verifier re-computes and cross-checks (verification) | reverify 100% real | Kept. Self-reference eliminated |
| Iteration 4 | (e.g. orchestration sub-agent split attempt) | (drop in numbers) | Removed. Evidence chain requires full context |
| Final | Combine what worked | (final numbers) | Core contribution: separation + independent re-verification |

## Key Failure Modes & Hot Take
Grounding enforcement only works where there is a verifiable floor. Running code alone does not raise trust — it can disguise assumptions as facts. Trust has two layers: vertical (reason to believe) + horizontal (consistency); both must be restored.
