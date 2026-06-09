from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from app.config.settings import settings

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]


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
                    "content": f"Stub OK. Mensaje recibido: {user_message}"
                },
                "finish_reason": "stop"
            }
        ]
    }


@router.post("/chat/completions")
def chat_completions_alias(payload: ChatCompletionRequest):
    return chat_completions(payload)
