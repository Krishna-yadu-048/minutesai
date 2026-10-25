# Keep API keys out of logs and turn API errors into plain messages.
import re

import openai
from pydantic import ValidationError

# Matches OpenAI keys (sk-..., sk-proj-...) and Groq keys (gsk_...)
KEY_PATTERN = re.compile(r"(sk-|gsk_)[A-Za-z0-9_\-]{8,}")


def redact(text: str) -> str:
    """Replace anything that looks like an API key with [REDACTED]."""
    return KEY_PATTERN.sub("[REDACTED]", text)


def friendly_error(error: Exception) -> str:
    # Return a message that's safe to show users (never the raw API error).
    if isinstance(error, openai.AuthenticationError):
        return "The provider rejected this API key. Check it and try again."
    if isinstance(error, openai.RateLimitError):
        return "Rate limit or quota reached. Wait a minute, or check your billing."
    if isinstance(error, openai.APITimeoutError):
        return "The provider took too long to respond. Please try again."
    if isinstance(error, openai.APIConnectionError):
        return "Couldn't reach the provider. Check your internet connection."
    if isinstance(error, ValidationError):
        return "The model's answer wasn't in the expected format. Try again or switch provider."
    return f"Something went wrong ({type(error).__name__}). Please try again."
