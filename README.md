# Grounded Analysis

A system that defines the trust boundary of AI agent judgments — forces every claim to be grounded in verifiable evidence, then cross-checks it with an independent verifier.

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

1. **Fact / Inference / Assumption separation** — force every claim to be labelled `[verified]` / `[inference]` / `[assumption]`
2. **Evidence chain enforcement** — require `[verified]` claims to include raw values + formula
3. **Independent verifier** — a separate deterministic code path re-computes each figure from raw data, breaking self-reference

**The boundary (key insight)**: The mechanism works where there is a verifiable ground truth (data); it breaks down where there is none (content). This boundary itself defines *the conditions under which AI judgment can be trusted*.

## Measured Results (Prompt Simulation)

| | Baseline | Final |
|---|---|---|
| Separation rate | ~12% | ~95% |
| Re-verifiability | ~0% | ~95% |
| Causation stance | Asserted ↔ hedged (varies by model) | Refused (converges across models) |

Once the independent verifier code is complete, re-verification reaches **100%** real validation.

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

See [CHANGELOG.md](CHANGELOG.md) for the iteration history.
