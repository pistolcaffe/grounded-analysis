import json
from datetime import datetime
from pathlib import Path

from config import TRAJECTORIES_DIR
from agent.client import call_model


def run_agent(data_path: str, prompt_path: str, model: str, provider: str) -> str:
    """Load data + prompt, call the model, log the trajectory, and return the response.

    Args:
        data_path: Path to the CSV data file.
        prompt_path: Path to the prompt template (.txt with {data} placeholder).
        model: Model name to pass to call_model.
        provider: Provider name ("anthropic" or "openai").

    Returns:
        Raw response string from the model.
    """
    # TODO: read CSV with pandas and format as string for prompt insertion
    # TODO: read prompt template and replace {data} placeholder
    # TODO: call call_model(prompt, model, provider)
    # TODO: log trajectory (input, prompt, response, timestamp) to TRAJECTORIES_DIR
    #       as JSON — filename: trajectory_<case>_<mode>_<timestamp>.json
    # TODO: support retry loop when verifier rejects a claim
    #       (verifier calls go here; rejections appended to trajectory log)
    raise NotImplementedError("run_agent is not yet implemented")
