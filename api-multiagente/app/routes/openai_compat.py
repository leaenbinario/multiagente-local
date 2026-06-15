import time
from typing import Any, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config.settings import settings
from app.services.routing_service import procesar_consulta_enrutada

router = APIRouter(tags=["openai-compat"])


class Message(BaseModel):
    role: str
    content: Any


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


def extraer_ultimo_mensaje_usuario(messages: List[Message]) -> str:
    for message in reversed(messages):
        if message.role == "user" and isinstance(message.content, str):
            contenido = message.content.strip()
            if contenido:
                return contenido

    raise HTTPException(
        status_code=400,
        detail="No se encontró un mensaje de usuario válido.",
    )


@router.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": settings.DEFAULT_CHAT_MODEL,
                "object": "model",
                "owned_by": "local",
                "created": int(time.time()),
            }
        ],
    }


@router.get("/models")
def list_models_alias():
    return list_models()


@router.post("/v1/chat/completions")
def chat_completions(payload: ChatCompletionRequest):
    try:
        user_message = extraer_ultimo_mensaje_usuario(payload.messages)
        resultado = procesar_consulta_enrutada(user_message)

        contenido = str(resultado.get("respuesta", "")).strip()

        return {
            "id": f"chatcmpl-{uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": payload.model or settings.DEFAULT_CHAT_MODEL,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": contenido,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error en endpoint OpenAI-compatible: {str(exc)}",
        )


@router.post("/chat/completions")
def chat_completions_alias(payload: ChatCompletionRequest):
    return chat_completions(payload)