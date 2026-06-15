from fastapi import APIRouter
from pydantic import BaseModel

from app.services.routing_service import procesar_consulta_enrutada

router = APIRouter(tags=["orquestador"])


class OrquestadorRequest(BaseModel):
    pregunta: str


@router.post("/orquestador/consulta")
def orquestador_consulta(payload: OrquestadorRequest):
    resultado = procesar_consulta_enrutada(payload.pregunta)

    return {
        "pregunta": payload.pregunta,
        "destino": resultado.get("destino"),
        "respuesta": resultado.get("respuesta"),
        "fuentes": resultado.get("fuentes", []),
    }