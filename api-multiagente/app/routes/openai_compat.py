from typing import Any, List, Optional
from uuid import uuid4
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config.settings import settings
from app.services.routing_service import enrutar_consulta

router = APIRouter()


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
        mensajes_usuario = [
            m for m in payload.messages
            if m.role == "user" and isinstance(m.content, str)
        ]

        if not mensajes_usuario:
            raise HTTPException(
                status_code=400,
                detail="No se encontró un mensaje de usuario válido.",
            )

        user_message = mensajes_usuario[-1].content
        resultado = enrutar_consulta(user_message)

        if isinstance(resultado, tuple) and len(resultado) == 3:
            agente, respuesta, fuentes = resultado
        else:
            agente = str(resultado)
            respuesta = ""
            fuentes = []

        contenido = (respuesta or "").strip()

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
            "debug": {
                "destino": agente,
                "fuentes": fuentes,
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


@router.options("/models")
async def options_models():
    return JSONResponse(content={}, headers={"Access-Control-Allow-Origin": "*"})


@router.options("/chat/completions")
async def options_chat_completions():
    return JSONResponse(content={}, headers={"Access-Control-Allow-Origin": "*"})