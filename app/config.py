"""Central configuration. Everything tunable lives here and comes from env vars."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # --- AI provider (Gemini through its OpenAI-compatible endpoint) ---
    api_key: str | None = os.getenv("API_KEY")
    base_url: str = os.getenv(
        "BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    model: str = os.getenv("MODEL", "gemini-2.5-flash")
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "30"))  # seconds
    max_retries: int = int(os.getenv("MAX_RETRIES", "2"))  # SDK retries 429/5xx/timeouts

    # --- Limits (protect cost and the server) ---
    max_message_chars: int = int(os.getenv("MAX_MESSAGE_CHARS", "2000"))  # per user message
    max_history_messages: int = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))  # sent to the model
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))  # per IP


settings = Settings()