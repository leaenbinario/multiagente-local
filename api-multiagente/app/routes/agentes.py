from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.asistente import consultar_asistente
from app.agents.contador import consultar_contador
from app.agents.forense import consultar_forense

router = APIRouter()


class ConsultaRequest(BaseModel):
    pregunta: str


@router.post("/forenseconsulta")
def forenseconsulta(payload: ConsultaRequest):
    return consultar_forense(payload.pregunta)


@router.post("/contadorconsulta")
def contadorconsulta(payload: ConsultaRequest):
    return consultar_contador(payload.pregunta)


@router.post("/asistenteconsulta")
def asistenteconsulta(payload: ConsultaRequest):
    return consultar_asistente(payload.pregunta)
