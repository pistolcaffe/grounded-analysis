import os
from dotenv import load_dotenv

load_dotenv()


def call_model(prompt: str, model: str, provider: str) -> str:
    """Call the specified model via the appropriate provider SDK.

    Args:
        prompt: The full prompt string to send.
        model: Model name (e.g. "claude-sonnet-4-6", "gpt-4o").
        provider: "anthropic" or "openai".

    Returns:
        The model's response as a plain string.

    Raises:
        ValueError: If provider is not supported.
        EnvironmentError: If the required API key env var is missing.
    """
    # TODO: implement Anthropic branch
    #   import anthropic
    #   client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    #   message = client.messages.create(model=model, max_tokens=2048,
    #                                    messages=[{"role": "user", "content": prompt}])
    #   return message.content[0].text

    # TODO: implement OpenAI branch
    #   import openai
    #   client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    #   resp = client.chat.completions.create(model=model,
    #                                         messages=[{"role": "user", "content": prompt}])
    #   return resp.choices[0].message.content

    raise NotImplementedError("call_model is not yet implemented")
