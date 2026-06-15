def consultar_asistente(pregunta: str) -> dict:
    return {
        "agente": "asistente",
        "respuesta": f"[asistente] Respuesta stub para: {pregunta}",
        "fuentes": []
    }