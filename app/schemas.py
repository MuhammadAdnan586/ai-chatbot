"""Request models. Validation happens here, before anything reaches the AI API."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .config import settings

# Model replies are long, so assistant messages get a much higher cap than user input.
MAX_ASSISTANT_CHARS = 20_000


class Message(BaseModel):
    # Literal (not str): a client can NOT inject its own "system" message.
    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty.")
        return value


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def check_conversation(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("The last message must come from the user.")
        for message in self.messages:
            limit = (
                settings.max_message_chars
                if message.role == "user"
                else MAX_ASSISTANT_CHARS
            )
            if len(message.content) > limit:
                raise ValueError(
                    f"Message too long (max {settings.max_message_chars} characters)."
                    if message.role == "user"
                    else "Assistant message too long."
                )
        return self