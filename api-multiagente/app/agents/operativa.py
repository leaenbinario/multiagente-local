from app.agents.asistente import consultar_asistente


def consultar_operativa(pregunta: str) -> dict:
    resultado = consultar_asistente(pregunta)
    return {
        "agente": "operativa",
        "respuesta": resultado.get("respuesta", ""),
        "fuentes": resultado.get("fuentes", [])
    }