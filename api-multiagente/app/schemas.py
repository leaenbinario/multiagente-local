from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ConsultaRequest(BaseModel):
    pregunta: str = Field(..., min_length=1)
    n_resultados: int = Field(default=4, ge=1, le=10)


class ConsultaResponse(BaseModel):
    respuesta: str
    fuentes: List[str] = Field(default_factory=list)


class OrquestadorResponse(BaseModel):
    agente: str
    respuesta: str
    fuentes: List[str] = Field(default_factory=list)


class MemoriaGuardarRequest(BaseModel):
    clave: str
    valor: str
    categoria: str = "general"


class MemoriaBuscarRequest(BaseModel):
    consulta: str


class MemoriaItem(BaseModel):
    clave: str
    valor: str
    categoria: str


class MemoriaBuscarResponse(BaseModel):
    resultados: List[MemoriaItem] = Field(default_factory=list)


class OpenAIMessage(BaseModel):
    role: str
    content: Any


class OpenAIChatCompletionRequest(BaseModel):
    model: str = "multiagente-local"
    messages: List[OpenAIMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


class CausaRequest(BaseModel):
    id_causa: str


class EmailCausaRequest(BaseModel):
    id_causa: str
    motivo: Optional[str] = "seguimiento"
    tono: Optional[str] = "profesional_cercano"


class WhatsAppCausaRequest(BaseModel):
    id_causa: str
    motivo: Optional[str] = "seguimiento"
    tono: Optional[str] = "profesional_cercano"


class FichaCausaCreate(BaseModel):
    id_causa: str
    caratula: str
    fuero: Optional[str] = None
    juzgado: Optional[str] = None
    abogado_nombre: Optional[str] = None
    abogado_email: Optional[str] = None
    abogado_whatsapp: Optional[str] = None
    cliente: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_ultimo_contacto: Optional[str] = None
    estado_actual: Optional[str] = None
    proximos_pasos: List[str] = Field(default_factory=list)
    notas: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class FichaCausaUpdate(BaseModel):
    caratula: Optional[str] = None
    fuero: Optional[str] = None
    juzgado: Optional[str] = None
    abogado_nombre: Optional[str] = None
    abogado_email: Optional[str] = None
    abogado_whatsapp: Optional[str] = None
    cliente: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_ultimo_contacto: Optional[str] = None
    estado_actual: Optional[str] = None
    proximos_pasos: Optional[List[str]] = None
    notas: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class ContactoCreateRequest(BaseModel):
    fecha: Optional[str] = None
    canal: str
    asunto: Optional[str] = None
    nota: str
    resultado: Optional[str] = None