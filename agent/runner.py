import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import DATA_DIR, PROMPTS_DIR, TRAJECTORIES_DIR, ModelConfig
from agent.client import call_model


def run_agent(case_id: str, mode: str, model_config: ModelConfig) -> str:
    """Load data + prompt, call the model, save trajectory, return response text.

    Args:
        case_id:      e.g. "case_01" — matches data/case_01_*.csv
        mode:         "baseline" or "final" — matches prompts/{mode}.txt
        model_config: ModelConfig(provider, model, max_tokens)

    Returns:
        Raw response text from the model.

    Raises:
        FileNotFoundError: If CSV or prompt file is missing.
    """
    # ── Resolve paths ──────────────────────────────────────────────────────
    data_files = sorted(DATA_DIR.glob(f"{case_id}_*.csv"))
    if not data_files:
        raise FileNotFoundError(
            f"No CSV found for case_id={case_id!r} in {DATA_DIR}. "
            f"Expected a file matching data/{case_id}_*.csv"
        )
    data_path = data_files[0]

    prompt_path = PROMPTS_DIR / f"{mode}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    # ── Build prompt ───────────────────────────────────────────────────────
    df = pd.read_csv(data_path)
    data_text = df.to_csv(index=False)

    template = prompt_path.read_text(encoding="utf-8")
    prompt = template.replace("{data}", data_text)

    # ── Call model ─────────────────────────────────────────────────────────
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"  Calling {model_config.provider}/{model_config.model} [{mode}] ...")

    response = call_model(
        prompt=prompt,
        provider=model_config.provider,
        model=model_config.model,
        max_tokens=model_config.max_tokens,
    )

    # ── Log trajectory ─────────────────────────────────────────────────────
    TRAJECTORIES_DIR.mkdir(parents=True, exist_ok=True)
    traj_path = TRAJECTORIES_DIR / f"{case_id}_{mode}_{timestamp}.json"
    traj_path.write_text(
        json.dumps(
            {
                "case_id":   case_id,
                "mode":      mode,
                "provider":  model_config.provider,
                "model":     model_config.model,
                "timestamp": timestamp,
                "data_path": str(data_path),
                "data_text": data_text,
                "prompt":    prompt,
                "response":  response,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  Trajectory → trajectories/{traj_path.name}")

    return response
