from typing import Any, Dict, List

from app.services.causas_service import (
    buscar_causas,
    obtener_historial_causa,
)


def _extraer_termino_busqueda(pregunta: str) -> str:
    """
    Extrae un término de búsqueda razonable desde la pregunta.
    Estrategia simple:
    - Si encuentra la palabra 'causa', usa todo lo que viene después.
    - Si no, usa toda la pregunta.
    """
    texto = (pregunta or "").strip()
    lower = texto.lower()

    marcador = "causa"
    idx = lower.find(marcador)
    if idx != -1:
        # Tomar todo lo que viene después de la palabra 'causa'
        termino = texto[idx + len(marcador):].strip(" :,-")
        if termino:
            return termino

    return texto


def _elegir_causa(resultados: Dict[str, Any]) -> str | None:
    """
    Dado el JSON devuelto por buscar_causas, elige el primer id_causa.

    Formato esperado (según GET /causas):
    {
        "status": "ok",
        "data": [
            {"id_causa": "causa-demo", "caratula": "...", ...},
            ...
        ]
    }
    """
    if not isinstance(resultados, dict):
        return None

    items = resultados.get("data")
    if not isinstance(items, list) or not items:
        return None

    primera = items[0]
    if not isinstance(primera, dict):
        return None

    return str(primera.get("id_causa") or primera.get("id") or "")


def consultar_causas(pregunta: str) -> Dict[str, Any]:
    """
    Agente de causas (versión inicial).
    - Si la pregunta contiene 'historial', busca la causa y devuelve su historial.
    - Si no, responde que por ahora solo entiende historial.
    """
    texto = (pregunta or "").lower()

    # 1) Intención: historial
    if "historial" in texto:
        termino = _extraer_termino_busqueda(pregunta)

        # 2) Buscar causas que coincidan con el término
        resultados_busqueda = buscar_causas(termino)

        id_causa = _elegir_causa(resultados_busqueda)
        if not id_causa:
            return {
                "respuesta": (
                    "Busqué causas relacionadas con tu descripción, "
                    "pero no encontré ninguna coincidencia clara."
                ),
                "fuentes": [],
            }

        # 3) Con el id_causa elegido, obtener el historial
        historial = obtener_historial_causa(id_causa)

        return {
            "respuesta": f"Historial de la causa {id_causa}: revisá los eventos listados.",
            "fuentes": [f"causa:{id_causa}"],
            "detalle": historial,
        }

    # Intención no reconocida aún
    return {
        "respuesta": (
            "Por ahora solo entiendo pedidos de historial de causa. "
            "Probá con algo como: 'Mostrame el historial de la causa Banco Nación contra Pérez'."
        ),
        "fuentes": [],
    }