from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.asistente import consultar_asistente
from app.agents.contador import consultar_contador
from app.agents.forense import consultar_forense
from app.services.routing_service import enrutar_consulta

router = APIRouter()


class OrquestadorRequest(BaseModel):
    pregunta: str


@router.post("/orquestadorconsulta")
def orquestador_consulta(payload: OrquestadorRequest):
    destino = enrutar_consulta(payload.pregunta)

    if destino == "forense":
        resultado = consultar_forense(payload.pregunta)
    elif destino == "contador":
        resultado = consultar_contador(payload.pregunta)
    else:
        resultado = consultar_asistente(payload.pregunta)

    return {
        "pregunta": payload.pregunta,
        "destino": destino,
        "resultado": resultado
    }
