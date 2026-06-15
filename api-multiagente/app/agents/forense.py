try:
    from agente_forense import agente_forense as agente_forense_legacy
except Exception:
    agente_forense_legacy = None


def consultar_forense(pregunta: str) -> dict:
    if agente_forense_legacy is not None:
        try:
            resultado = agente_forense_legacy(pregunta)

            if isinstance(resultado, tuple) and len(resultado) >= 2:
                respuesta, fuentes = resultado[0], resultado[1]
            else:
                respuesta, fuentes = str(resultado), []

            return {
                "agente": "forense",
                "respuesta": respuesta,
                "fuentes": fuentes
            }
        except Exception as e:
            return {
                "agente": "forense",
                "respuesta": f"[forense] Error usando legacy: {e}",
                "fuentes": []
            }

    return {
        "agente": "forense",
        "respuesta": f"[forense] Respuesta stub para: {pregunta}",
        "fuentes": []
    }
