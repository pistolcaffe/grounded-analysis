# Representative Agent Trajectory

A single end-to-end run of the grounded-analysis pipeline on `case_01`,
from agent instruction through tool response to final score.

Model: anthropic/claude-sonnet-4-6 · Mode: final · case_01
Source log: `trajectories/case_01_final_20260830T204623Z.json`

---

## Step 1 — Agent instruction

The agent receives the `final` prompt (grounding-enforcement rules) with the
dataset injected. Full prompt: `prompts/final.txt`. Key rules:

- Label every claim `[VERIFIED]` / `[INFERENCE]` / `[ASSUMPTION]`
- `[VERIFIED]` claims must include raw values + formula
- Do not assert causation without a verifiable basis
- Flag any grouping as an `[ASSUMPTION]`

## Step 2 — Input data

`data/case_01_push.csv` — 8 weeks of app metrics (push_sent, active_users,
revenue, support_tickets). Contains a planted trap: all four metrics move
together, inviting a false causal claim ("more push → more revenue").

## Step 3 — Agent output

The agent produced a fully labelled report. Highlights:

- **[ASSUMPTION]** Grouped weeks into low-push / high-push regimes — explicitly
  flagged as imposed by the agent, not present in the data.
- **[VERIFIED]** Average revenue 31.3% higher in high-push weeks
  (5025 → 6600; (6600−5025)/5025 = 31.3%)
- **[INFERENCE]** All four metrics co-move; tempting to read as causation, but a
  common cause (campaign, product event) cannot be ruled out. **Trap avoided.**

Full output in the source log.

## Step 4 — Tool response (independent verifier)

The verifier re-computed each `[VERIFIED]` claim's formula against the raw CSV,
independently of the agent's own arithmetic. Result: **8 passed / 0 failed / 3 unknown**.

| Claim (excerpt) | Verifier status |
|---|---|
| Push volume ~68% higher in high-push weeks | passed |
| Push volume grew W1→W8 within high-push weeks | passed |
| Active users higher in *every* high-push week | unknown |
| Average active users 24.1% higher | passed |
| Active users grew 32.8% W1→W8 | passed |
| Revenue higher in *every* high-push week | unknown |
| Average revenue 31.3% higher | passed |
| Revenue grew 45.8% W1→W8 | passed |
| Support tickets higher in *every* high-push week | unknown |
| Average support tickets 98.3% higher | passed |
| Support tickets grew 133.3% W1→W8 | passed |

The three `unknown` claims are all "higher in *every* week" comparison
statements, whose logic (min > max across groups) falls outside the arithmetic
verifier's scope — the same honest boundary that excludes correlation
coefficients. They are neither passed nor failed; they are reported as
outside-scope so nothing unverified is silently accepted.

## Step 5 — Final score

- separation_rate: ~94% (every claim carries a label)
- reverify_rate: 100% on arithmetic-verifiable claims (8/8 passed, 0 failed)

## Notes on retries / human checkpoints

This pipeline is a single linear pass: prompt → agent response → independent
verification → score. It has no retry loop or human-in-the-loop checkpoint, so
none are recorded. The independent verifier is the automated tool-response
stage, and its "unknown" status is the mechanism's honesty guardrail — claims
it cannot verify are surfaced, never silently passed.