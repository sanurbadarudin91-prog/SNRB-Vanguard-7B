"""FastAPI wrapper lokal bergaya OpenAI untuk SNRB-Vanguard-7B.

Meneruskan request ke backend inference lokal (Ollama, llama-server,
vLLM, dsb.) yang alamatnya diatur lewat environment variable:

    INFERENCE_BASE_URL  default: http://127.0.0.1:11434   (Ollama)
    MODEL_NAME          default: snrb-vanguard-7b
    API_HOST            default: 0.0.0.0
    API_PORT            default: 8000
    REQUEST_TIMEOUT     default: 120 (detik)

Jalankan:
    uvicorn api.server:app --host 0.0.0.0 --port 8000

Endpoint:
    GET  /health
    POST /v1/chat/completions
"""

from __future__ import annotations

import os
import time
import uuid

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from api.schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    HealthResponse,
    Usage,
)

INFERENCE_BASE_URL = os.getenv("INFERENCE_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
MODEL_NAME = os.getenv("MODEL_NAME", "snrb-vanguard-7b")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))

app = FastAPI(
    title="SNRB-Vanguard-7B Local API",
    description="Wrapper bergaya OpenAI untuk inference lokal SNRB-Vanguard-7B.",
    version="0.1.0",
)


def _backend_health() -> bool:
    """Cek apakah backend inference lokal dapat dijangkau."""
    try:
        # Ollama: /api/tags ; llama-server: /health
        for path in ("/api/tags", "/health", "/v1/models"):
            try:
                r = requests.get(f"{INFERENCE_BASE_URL}{path}", timeout=3)
                if r.status_code < 500:
                    return True
            except requests.RequestException:
                continue
    except Exception:  # pragma: no cover - defensif
        return False
    return False


def _call_backend(payload: dict) -> dict:
    """Kirim request ke backend dengan format OpenAI-compatible."""
    url = f"{INFERENCE_BASE_URL}/v1/chat/completions"
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Backend inference tidak dapat dihubungi: {exc}",
        ) from exc

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Backend error {resp.status_code}: {resp.text[:500]}",
        )

    try:
        return resp.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Respons backend bukan JSON") from exc


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    reachable = _backend_health()
    return HealthResponse(
        status="ok" if reachable else "degraded",
        model=MODEL_NAME,
        backend=INFERENCE_BASE_URL,
        backend_reachable=reachable,
    )


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
def chat_completions(req: ChatCompletionRequest) -> ChatCompletionResponse:
    if not req.messages:
        raise HTTPException(status_code=400, detail="'messages' tidak boleh kosong")

    backend_payload = {
        "model": MODEL_NAME,
        "messages": [m.model_dump(exclude_none=True) for m in req.messages],
        "temperature": req.temperature,
        "top_p": req.top_p,
        "stream": False,
    }
    if req.max_tokens is not None:
        backend_payload["max_tokens"] = req.max_tokens
    if req.stop is not None:
        backend_payload["stop"] = req.stop

    data = _call_backend(backend_payload)

    # Normalisasi respons backend (bisa OpenAI-style atau Ollama-style)
    content = ""
    finish_reason = "stop"
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") or {}
        content = msg.get("content", "") or ""
        finish_reason = choices[0].get("finish_reason", "stop")
    else:
        # Fallback Ollama /api/generate style
        content = data.get("response", "") or (data.get("message") or {}).get("content", "")

    if not content:
        raise HTTPException(status_code=502, detail="Backend mengembalikan konten kosong")

    usage_raw = data.get("usage") or {}
    prompt_tokens = int(usage_raw.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage_raw.get("completion_tokens", 0) or 0)

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        created=int(time.time()),
        model=MODEL_NAME,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=content),
                finish_reason=finish_reason,
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse(
        {
            "service": "SNRB-Vanguard-7B Local API",
            "model": MODEL_NAME,
            "backend": INFERENCE_BASE_URL,
            "endpoints": ["GET /health", "POST /v1/chat/completions"],
            "docs": "/docs",
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.server:app", host=API_HOST, port=API_PORT, reload=False)
