"""Everything that talks to the AI provider lives here."""
import logging
from collections.abc import AsyncIterator
from functools import lru_cache

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

from .config import settings
from .prompts import SYSTEM_PROMPT
from .schemas import Message

log = logging.getLogger("chatbot.llm")


class LLMError(Exception):
    """An error we can safely show to the user, with the HTTP status to return."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@lru_cache
def get_client() -> AsyncOpenAI:
    if not settings.api_key:
        raise LLMError(500, "The server is not configured yet (missing API key).")
    return AsyncOpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=settings.request_timeout,
        # The SDK retries only retryable failures (429, 5xx, timeouts) with backoff.
        max_retries=settings.max_retries,
    )


def build_messages(history: list[Message]) -> list[dict]:
    """System prompt + the most recent messages (bounded, so cost stays predictable)."""
    recent = history[-settings.max_history_messages :]
    # After trimming, make sure the conversation starts with a user turn.
    while recent and recent[0].role != "user":
        recent = recent[1:]
    return [{"role": "system", "content": SYSTEM_PROMPT}] + [
        {"role": m.role, "content": m.content} for m in recent
    ]


async def open_stream(history: list[Message]):
    """Start a streaming completion.

    Errors that happen *before* the first token (bad key, rate limit, timeout) are
    raised here as LLMError, so the API can still return a proper HTTP status.
    """
    client = get_client()
    try:
        return await client.chat.completions.create(
            model=settings.model,
            messages=build_messages(history),
            stream=True,
        )
    except AuthenticationError:
        log.error("Provider rejected the API key")
        raise LLMError(500, "The server could not authenticate with the AI service.") from None
    except RateLimitError:
        log.warning("Provider rate limit hit")
        raise LLMError(429, "The AI service is busy right now. Please try again shortly.") from None
    except APITimeoutError:  # must come before APIConnectionError (it is a subclass)
        log.warning("Provider timed out")
        raise LLMError(504, "The AI service took too long to respond. Please try again.") from None
    except APIConnectionError:
        log.warning("Could not reach provider")
        raise LLMError(503, "Could not reach the AI service. Check your connection and retry.") from None
    except BadRequestError:
        log.warning("Provider rejected the request")
        raise LLMError(400, "The AI service could not process that message.") from None
    except APIStatusError as exc:
        log.error("Provider error status=%s", exc.status_code)
        raise LLMError(502, "The AI service had a problem. Please try again.") from None


async def iter_text(stream) -> AsyncIterator[str]:
    """Yield only the text pieces from the provider's stream of chunks."""
    async for chunk in stream:
        if chunk.choices:
            text = chunk.choices[0].delta.content
            if text:
                yield text