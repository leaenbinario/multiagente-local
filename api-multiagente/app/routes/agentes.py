from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.asistente import consultar_asistente
from app.agents.honorarios import consultar_honorarios
from app.agents.forense import consultar_forense
from app.agents.operativa import consultar_operativa

router = APIRouter(tags=["agentes"])


class ConsultaRequest(BaseModel):
    pregunta: str


def _normalizar_resultado(resultado, agente: str) -> dict:
    # Caso nuevo: los wrappers modernos devuelven dict con agente / respuesta / fuentes
    if isinstance(resultado, dict):
        return {
            "agente": agente,
            "respuesta": str(resultado.get("respuesta", "") or "").strip(),
            "fuentes": list(resultado.get("fuentes", []) or []),
        }

    # Compatibilidad con el formato legacy en tu código viejo
    if isinstance(resultado, tuple):
        if len(resultado) == 2:
            respuesta, fuentes = resultado
            return {
                "agente": agente,
                "respuesta": str(respuesta or "").strip(),
                "fuentes": list(fuentes or []),
            }

        if len(resultado) == 3:
            _, respuesta, fuentes = resultado
            return {
                "agente": agente,
                "respuesta": str(respuesta or "").strip(),
                "fuentes": list(fuentes or []),
            }

    return {
        "agente": agente,
        "respuesta": str(resultado or "").strip(),
        "fuentes": [],
    }


@router.post("/forense/consulta")
def forense_consulta(payload: ConsultaRequest):
    resultado = consultar_forense(payload.pregunta)
    return _normalizar_resultado(resultado, "forense")


@router.post("/honorarios/consulta")
def honorarios_consulta(payload: ConsultaRequest):
    resultado = consultar_honorarios(payload.pregunta)
    return _normalizar_resultado(resultado, "honorarios")


@router.post("/operativa/consulta")
def operativa_consulta(payload: ConsultaRequest):
    resultado = consultar_operativa(payload.pregunta)
    return _normalizar_resultado(resultado, "operativa")


@router.post("/asistente/consulta")
def asistente_consulta(payload: ConsultaRequest):
    resultado = consultar_asistente(payload.pregunta)
    return _normalizar_resultado(resultado, "asistente")