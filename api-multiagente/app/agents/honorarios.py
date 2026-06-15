try:
    from agente_contador import agente_contador as agente_contador_legacy
except Exception:
    agente_contador_legacy = None


def consultar_honorarios(pregunta: str) -> dict:
    if agente_contador_legacy is not None:
        try:
            resultado = agente_contador_legacy(pregunta)

            if isinstance(resultado, tuple) and len(resultado) >= 2:
                respuesta, fuentes = resultado[0], resultado[1]
            else:
                respuesta, fuentes = str(resultado), []

            return {
                "agente": "honorarios",
                "respuesta": respuesta,
                "fuentes": fuentes
            }
        except Exception as e:
            return {
                "agente": "honorarios",
                "respuesta": f"[honorarios] Error usando legacy: {e}",
                "fuentes": []
            }

    return {
        "agente": "honorarios",
        "respuesta": f"[honorarios] Respuesta stub para: {pregunta}",
        "fuentes": []
    }


def consultar_contador(pregunta: str) -> dict:
    return consultar_honorarios(pregunta)