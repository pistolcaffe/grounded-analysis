from dataclasses import dataclass
from pathlib import Path

# ── Model settings ──────────────────────────────────────────────────────────
MODEL_PROVIDER = "anthropic"       # "anthropic" | "openai"
MODEL_NAME     = "claude-sonnet-4-6"
MAX_TOKENS     = 2048

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
DATA_DIR        = BASE_DIR / "data"
RESULTS_DIR     = BASE_DIR / "results"
TRAJECTORIES_DIR = BASE_DIR / "trajectories"
PROMPTS_DIR     = BASE_DIR / "prompts"

# ── Run settings ─────────────────────────────────────────────────────────────
# Keep low for cost safety. Use --repeat 1 on the first test run.
DEFAULT_REPEAT = 1
MAX_RETRIES    = 3   # per API call
RETRY_DELAY    = 5   # seconds between retries


@dataclass
class ModelConfig:
    provider:   str = MODEL_PROVIDER
    model:      str = MODEL_NAME
    max_tokens: int = MAX_TOKENS
