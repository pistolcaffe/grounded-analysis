# Grounded Analysis

A system that defines the trust boundary of AI agent judgments — it forces every claim to be grounded in verifiable evidence, then cross-checks it with an independent verifier.

---

## Problem

In judgment tasks where you cannot verify before executing and cannot undo after, people without domain expertise blindly trust agent conclusions. Experts can spot the traps; non-experts cannot — yet non-experts are exactly the ones who need agents most.

## User

Practitioners who delegate judgment and interpretation to agents. Especially **people who lack domain expertise** — non-specialists who hand over data and ask "pull out some insights."

## Bottleneck

Agents produce plausible-sounding judgments fluently, but:

- **Vertical trust collapse**: It is impossible to tell whether a claim comes from real evidence or is fabricated.
- **Horizontal trust collapse**: The same data yields a different answer every time.

You cannot trust it without re-verifying, and if you have to re-verify yourself, there is no point using the agent.

## Approach

1. **Fact / Inference / Assumption separation** — force every claim to be labelled `[VERIFIED]` / `[INFERENCE]` / `[ASSUMPTION]`
2. **Evidence chain enforcement** — require `[VERIFIED]` claims to include raw values + formula
3. **Independent verifier** — a separate deterministic code path re-computes each figure from the raw data, breaking self-reference

**The boundary (key insight)**: The mechanism works where there is a verifiable ground truth (data); it breaks down where there is none (subjective content). This boundary itself defines *the conditions under which AI judgment can be trusted*.

## Measured Results

Actual pipeline runs (anthropic/claude-sonnet-4-6, case_01, repeat=5):

| | Baseline | Final |
|---|---|---|
| Separation rate | 0.0% (stdev 0.0) | 94.5% (stdev 0.97pp) |
| Re-verifiability | N/A (nothing to verify) | 100% |
| Consistency | — | Tight across repeats |

The independent verifier re-computes each arithmetic claim against the raw data. On a reference response: **12 passed / 0 failed / 2 unknown** (Pearson-type claims fall outside the arithmetic verifier's scope).

**Boundary result**: The same enforcement applied to a subjective task (does a video script "hook" the viewer?) produces high separation but **zero re-verifiable core claims** — every hook judgment falls to `[INFERENCE]` because there is no verifiable floor. The system honestly labels its judgment as inference rather than disguising it as fact. This confirms the boundary.

---

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Set API keys:

```bash
cp .env.example .env
# Edit .env and fill in ANTHROPIC_API_KEY or OPENAI_API_KEY
```

## Usage

```bash
# Help
python run.py --help

# Run baseline + final 3 times each and score
python run.py --case case_01 --mode both --repeat 3

# Baseline only
python run.py --case case_01 --mode baseline

# Final only, 5 repetitions
python run.py --case case_01 --mode final --repeat 5
```

## Runtime & Cost

- One `--mode both --repeat 5` run makes ~10 API calls and completes in approximately under one minute.
- Approximate cost: a few cents per full run (Claude Sonnet, short prompts + small data).
- Requires an Anthropic (or OpenAI) API key with billing enabled.

## Project Structure
```
grounded-analysis/
  run.py              # pipeline entry point
  config.py           # model and path settings
  agent/              # model call wrapper (swappable provider)
  verifier/           # response parser + independent re-computation verifier
  scorer/             # separation/reverify/consistency scoring + auto CHANGELOG
  data/               # synthetic datasets + ground truth
  prompts/            # baseline.txt / final.txt
  results/            # run outputs (gitignored)
  trajectories/       # agent trajectory logs
```


See [CHANGELOG.md](CHANGELOG.md) for the full iteration history, the boundary case, and the hot take.
