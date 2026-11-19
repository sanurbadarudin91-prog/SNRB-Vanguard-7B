"""Skema Pydantic untuk API lokal bergaya OpenAI."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str | None = Field(
        default=None, description="Diabaikan/opsional; backend menentukan model."
    )
    messages: list[ChatMessage]
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=1024, ge=1)
    stream: bool = False
    stop: list[str] | str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "model": "snrb-vanguard-7b",
                "messages": [
                    {"role": "user", "content": "Jelaskan risiko SQL injection singkat."}
                ],
                "temperature": 0.2,
                "max_tokens": 256,
            }
        }
    }


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str | None = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: Usage = Field(default_factory=Usage)


class HealthResponse(BaseModel):
    status: str
    model: str
    backend: str
    backend_reachable: bool
