from fastapi import APIRouter
from pydantic import BaseModel

from app.services.routing_service import procesar_consulta_enrutada

router = APIRouter(tags=["consulta"])


class ConsultaRequest(BaseModel):
    pregunta: str


@router.post("/consulta")
def consulta(payload: ConsultaRequest):
    resultado = procesar_consulta_enrutada(payload.pregunta)
    return {
        "status": "ok",
        **resultado,
    }