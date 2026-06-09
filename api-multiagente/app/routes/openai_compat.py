from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.config.settings import settings
from app.services.routing_service import enrutar_consulta

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]


def _resolver_respuesta_stub(destino: str, user_message: str) -> str:
    if destino == "forense":
        return f"[forense] Consulta recibida: {user_message}"
    if destino == "contador":
        return f"[contador] Consulta recibida: {user_message}"
    if destino == "memoria":
        return f"[memoria] Consulta recibida: {user_message}"
    return f"[asistente] Consulta recibida: {user_message}"


@router.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": settings.DEFAULT_CHAT_MODEL,
                "object": "model",
                "owned_by": "local"
            }
        ]
    }


@router.get("/models")
def list_models_alias():
    return list_models()


@router.post("/v1/chat/completions")
def chat_completions(payload: ChatCompletionRequest):
    user_message = payload.messages[-1].content if payload.messages else ""
    destino = enrutar_consulta(user_message)
    respuesta = _resolver_respuesta_stub(destino, user_message)

    return {
        "id": "chatcmpl-local",
        "object": "chat.completion",
        "created": 1710000000,
        "model": payload.model or settings.DEFAULT_CHAT_MODEL,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": respuesta
                },
                "finish_reason": "stop"
            }
        ],
        "debug": {
            "destino": destino
        }
    }


@router.post("/chat/completions")
def chat_completions_alias(payload: ChatCompletionRequest):
    return chat_completions(payload)
