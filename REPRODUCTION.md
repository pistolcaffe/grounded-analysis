# Reproduction Guide

Written for someone starting from a clean environment.

## Requirements

- Python 3.11+ (developed on 3.11.6)
- An Anthropic API key with billing enabled (or OpenAI)
- Packages: see `requirements.txt` (anthropic, openai, pandas, python-dotenv)

## Setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY and MODEL_PROVIDER=anthropic
```

## Data

Synthetic dataset, no private data required:
- `data/case_01_push.csv` — 8 weeks of app metrics (push_sent, active_users, revenue, support_tickets)
- `data/case_01_push.answer.json` — ground truth, including the planted trap (correlation mistaken for causation)

## Run the evaluation

```bash
# Baseline and Final, 5 repetitions each, scored
python run.py --case case_01 --mode both --repeat 5
```

This calls the model, scores each response with the independent verifier, and prints a comparison.

## Expected output

```
COMPARISON  baseline → final
  separation_rate :    0.0%  →   ~94%   (+94pp)
  reverify_rate   :     N/A  →   100.0%
  unknown_count   :       0  →     3–18
```

- **Baseline**: separation 0% every run (no labels, nothing to verify).
- **Final**: separation ~94% (stdev ~1pp), reverify 100% on runs that emit arithmetic claims.
- `unknown_count` varies run to run (Pearson-type claims outside arithmetic scope). This variance is expected and documented in CHANGELOG.md.

## Verify the independent verifier in isolation

```bash
python tests/test_verifier.py
```

Expected: `TOTAL 14 / passed 12 / failed 0 / unknown 2` on the reference response.

## Runtime & cost

- `--mode both --repeat 5`: ~10 API calls, under one minute.
- Cost: a few cents per full run (Claude Sonnet, short prompts, small data).

## Boundary case (optional)

The boundary result (grounding breaks down without a verifiable floor) was produced by applying the same `final` prompt to a subjective task. See CHANGELOG.md "Boundary case" row and `results/sim/` for the reference response.