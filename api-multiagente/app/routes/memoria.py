from fastapi import APIRouter
from pydantic import BaseModel

from app.services.memoria_service import guardar_memoria, buscar_memoria

router = APIRouter()


class MemoriaGuardarRequest(BaseModel):
    clave: str
    contenido: str


class MemoriaBuscarRequest(BaseModel):
    texto: str


@router.post("/memoriaguardar")
def memoriaguardar(payload: MemoriaGuardarRequest):
    item = guardar_memoria(payload.clave, payload.contenido)
    return {
        "status": "ok",
        "guardado": item
    }


@router.post("/memoriabuscar")
def memoriabuscar(payload: MemoriaBuscarRequest):
    resultados = buscar_memoria(payload.texto)
    return {
        "status": "ok",
        "resultados": resultados
    }
