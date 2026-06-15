from fastapi import APIRouter
from pydantic import BaseModel

from app.services.memoria_service import guardar_memoria, buscar_memoria

router = APIRouter(tags=["memoria"])


class MemoriaGuardarRequest(BaseModel):
    clave: str
    contenido: str


class MemoriaBuscarRequest(BaseModel):
    consulta: str


@router.post("/memoria/guardar")
def memoria_guardar(payload: MemoriaGuardarRequest):
    item = guardar_memoria(payload.clave, payload.contenido)
    return {
        "status": "ok",
        "guardado": item,
    }


@router.post("/memoria/buscar")
def memoria_buscar(payload: MemoriaBuscarRequest):
    respuesta, fuentes = buscar_memoria(payload.consulta)
    return {
        "status": "ok",
        "respuesta": respuesta,
        "fuentes": fuentes,
    }