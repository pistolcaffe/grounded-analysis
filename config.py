from pathlib import Path

# Model settings
MODEL_PROVIDER = "anthropic"  # "anthropic" | "openai"
MODEL_NAME = "claude-sonnet-4-6"

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
TRAJECTORIES_DIR = BASE_DIR / "trajectories"
PROMPTS_DIR = BASE_DIR / "prompts"

# Run settings
DEFAULT_REPEAT = 3  # number of repetitions for consistency measurement
