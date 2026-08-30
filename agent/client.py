import os
import time

from dotenv import load_dotenv

from config import MAX_RETRIES, RETRY_DELAY

load_dotenv()


def call_model(prompt: str, provider: str, model: str, max_tokens: int = 2048) -> str:
    """Call the specified model and return the response text.

    Args:
        prompt:     Full prompt string to send.
        provider:   "anthropic" or "openai".
        model:      Model ID (e.g. "claude-sonnet-4-6", "gpt-4o").
        max_tokens: Maximum tokens in the response.

    Returns:
        Response text as a plain string.

    Raises:
        ValueError:       Unsupported provider.
        EnvironmentError: Required API key env var missing.
        RuntimeError:     API call failed after all retries.
    """
    if provider == "anthropic":
        return _call_anthropic(prompt, model, max_tokens)
    if provider == "openai":
        return _call_openai(prompt, model, max_tokens)
    raise ValueError(f"Unsupported provider {provider!r}. Choose 'anthropic' or 'openai'.")


# ── Anthropic ────────────────────────────────────────────────────────────────

def _call_anthropic(prompt: str, model: str, max_tokens: int) -> str:
    try:
        import anthropic
    except ImportError:
        raise ImportError("Run: pip install anthropic") from None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. Copy .env.example → .env and add your key."
        )

    client = anthropic.Anthropic(api_key=api_key)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except anthropic.RateLimitError as e:
            _handle_retry(attempt, "rate limit", e)
        except anthropic.APIConnectionError as e:
            _handle_retry(attempt, "connection error", e)
        except anthropic.APIError as e:
            raise RuntimeError(f"Anthropic API error: {e}") from e

    raise RuntimeError(f"Anthropic call failed after {MAX_RETRIES} attempts.")


# ── OpenAI ───────────────────────────────────────────────────────────────────

def _call_openai(prompt: str, model: str, max_tokens: int) -> str:
    try:
        import openai
    except ImportError:
        raise ImportError("Run: pip install openai") from None

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY not set. Copy .env.example → .env and add your key."
        )

    client = openai.OpenAI(api_key=api_key)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content
        except openai.RateLimitError as e:
            _handle_retry(attempt, "rate limit", e)
        except openai.APIConnectionError as e:
            _handle_retry(attempt, "connection error", e)
        except openai.OpenAIError as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e

    raise RuntimeError(f"OpenAI call failed after {MAX_RETRIES} attempts.")


# ── helpers ──────────────────────────────────────────────────────────────────

def _handle_retry(attempt: int, reason: str, exc: Exception) -> None:
    if attempt == MAX_RETRIES:
        raise RuntimeError(
            f"{reason} — failed after {MAX_RETRIES} attempts: {exc}"
        ) from exc
    wait = RETRY_DELAY * attempt
    print(f"    [retry {attempt}/{MAX_RETRIES}] {reason} — waiting {wait}s...")
    time.sleep(wait)
