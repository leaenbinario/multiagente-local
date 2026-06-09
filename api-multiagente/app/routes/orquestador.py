from fastapi import APIRouter
from pydantic import BaseModel

from app.services.routing_service import enrutar_consulta

router = APIRouter()


class OrquestadorRequest(BaseModel):
    pregunta: str


@router.post("/orquestadorconsulta")
def orquestador_consulta(payload: OrquestadorRequest):
    destino = enrutar_consulta(payload.pregunta)

    return {
        "pregunta": payload.pregunta,
        "destino": destino,
        "respuesta": f"Stub de orquestación. La consulta sería enviada a: {destino}"
    }
