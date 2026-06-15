from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import logging
import math
import os

import requests
from dotenv import load_dotenv

import agente_asistente as aa
import agente_contador as ac
import agente_forense as af

from servicio_causas import (
    detectar_intencion_causas,
    ejecutar_intencion_causas,
    normalizar_texto_entrada,
    resolver_consulta_causas_generica,
)
from servicio_memoria import consultar_memoria

load_dotenv()

logger = logging.getLogger("api_multiagente")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")
OPENCLAW_CAUSAS_URL = os.getenv("OPENCLAW_CAUSAS_URL", "http://openclaw-causas:9100")

ROUTING_MIN_SCORE = float(os.getenv("ROUTING_MIN_SCORE", "0.35"))
ROUTING_MIN_DIFF = float(os.getenv("ROUTING_MIN_DIFF", "0.03"))
DEFAULT_N_RESULTADOS = int(os.getenv("DEFAULT_N_RESULTADOS", "4"))

DOMINIOS_SEMANTICOS: Dict[str, List[str]] = {
    "forense": [
        "qué es la cadena de custodia",
        "cómo preservar evidencia digital",
        "cómo verificar integridad con hash",
        "análisis forense de un disco",
        "metadatos de un archivo como prueba",
    ],
    "honorarios": [
        "cómo regular honorarios periciales",
        "anticipo de gastos del perito",
        "iva en honorarios periciales",
        "liquidación de honorarios",
        "base regulatoria del perito",
    ],
    "operativa": [
        "redactar un escrito breve",
        "pedir fecha de pericia",
        "pronto despacho simple",
        "nota breve al juzgado",
        "seguimiento de expediente",
    ],
    "memoria": [
        "qué recuerdas de mí",
        "qué sabes de mi perfil",
        "recordá mis preferencias",
        "buscá datos guardados",
        "qué guardaste en memoria",
    ],
    "causas": [
        "estado de una causa",
        "resumen de una causa",
        "seguimiento de una causa",
        "redactar un email de seguimiento de una causa",
        "redactar un whatsapp de seguimiento de una causa",
        "listar mis causas activas",
        "crear una causa",
        "actualizar una causa",
        "registrar contacto en una causa",
        "buscar causas por abogado o estado",
        "historial de una causa",
        "mostrar una causa",
        "ver una causa",
        "detalle de una causa",
    ],
}

EMBEDDINGS_DOMINIOS: Dict[str, List[List[float]]] = {}


def normalizar_respuesta(respuesta: Any, fuentes: Any) -> Tuple[str, List[str]]:
    texto = str(respuesta).strip() if respuesta is not None else ""

    if not isinstance(fuentes, list):
        fuentes_norm = [str(fuentes)] if fuentes else []
    else:
        fuentes_norm = [str(f) for f in fuentes if str(f).strip()]

    return texto, fuentes_norm


def consultar_forense(
    pregunta: str,
    n_resultados: int = DEFAULT_N_RESULTADOS,
) -> Tuple[str, List[str]]:
    respuesta, fuentes = af.agente_forense(pregunta, n_resultados)
    return normalizar_respuesta(respuesta, fuentes)


def consultar_operativa(
    pregunta: str,
    n_resultados: int = DEFAULT_N_RESULTADOS,
) -> Tuple[str, List[str]]:
    respuesta, fuentes = aa.agente_asistente(pregunta, n_resultados)
    return normalizar_respuesta(respuesta, fuentes)


def consultar_honorarios(
    pregunta: str,
    n_resultados: int = DEFAULT_N_RESULTADOS,
) -> Tuple[str, List[str]]:
    respuesta, fuentes = ac.agente_contador(pregunta, n_resultados)
    return normalizar_respuesta(respuesta, fuentes)


def request_embedding(texto: str) -> List[float]:
    url = f"{OLLAMA_BASE_URL}/api/embeddings"
    resp = requests.post(
        url,
        json={"model": EMBEDDING_MODEL, "prompt": texto},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    emb = data.get("embedding")
    if not emb:
        raise ValueError("No se recibió embedding desde Ollama.")
    return emb


def similitud_coseno(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    norma_a = math.sqrt(sum(x * x for x in a))
    norma_b = math.sqrt(sum(y * y for y in b))
    if norma_a == 0 or norma_b == 0:
        return -1.0
    return dot / (norma_a * norma_b)


def precalcular_embeddings_dominios() -> None:
    global EMBEDDINGS_DOMINIOS
    tmp: Dict[str, List[List[float]]] = {}
    for dominio, ejemplos in DOMINIOS_SEMANTICOS.items():
        tmp[dominio] = [request_embedding(ejemplo) for ejemplo in ejemplos]
    EMBEDDINGS_DOMINIOS = tmp


def clasificar_dominio(pregunta: str) -> Tuple[str, float, float]:
    if not EMBEDDINGS_DOMINIOS:
        precalcular_embeddings_dominios()

    emb_pregunta = request_embedding(pregunta)
    scores: Dict[str, float] = {}

    for dominio, embeddings in EMBEDDINGS_DOMINIOS.items():
        mejores = [similitud_coseno(emb_pregunta, emb) for emb in embeddings]
        scores[dominio] = max(mejores) if mejores else -1.0

    ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    mejor_dominio, mejor_score = ranking[0]
    segundo_score = ranking[1][1] if len(ranking) > 1 else -1.0
    return mejor_dominio, mejor_score, segundo_score


def enrutar_consulta(
    pregunta: str,
    n_resultados: int = DEFAULT_N_RESULTADOS,
    forzar_agente: Optional[str] = None,
) -> Tuple[str, str, List[str]]:
    pregunta = normalizar_texto_entrada(pregunta)
    pregunta_l = pregunta.lower()

    if forzar_agente == "forense":
        respuesta, fuentes = consultar_forense(pregunta, n_resultados)
        return "forense", respuesta, fuentes

    if forzar_agente == "operativa":
        respuesta, fuentes = consultar_operativa(pregunta, n_resultados)
        return "operativa", respuesta, fuentes

    if forzar_agente == "honorarios":
        respuesta, fuentes = consultar_honorarios(pregunta, n_resultados)
        return "honorarios", respuesta, fuentes

    intencion_causas = detectar_intencion_causas(pregunta)
    if intencion_causas:
        return ejecutar_intencion_causas(intencion_causas, pregunta)

    if any(k in pregunta_l for k in ["memoria", "recuerdas", "recordá", "recorda", "guardaste"]):
        respuesta, fuentes = consultar_memoria(pregunta)
        if respuesta.strip():
            return "memoria", respuesta, fuentes

    if any(
        k in pregunta_l
        for k in [
            "causa", "causas", "expediente", "carátula", "caratula",
            "historial de la causa", "resumen de la causa",
            "email de seguimiento", "mail de seguimiento",
            "whatsapp de seguimiento", "detalle de la causa",
            "ver la causa", "mostrar la causa", "ficha de la causa",
        ]
    ):
        return resolver_consulta_causas_generica(pregunta)

    try:
        dominio, score, segundo = clasificar_dominio(pregunta)
    except Exception as exc:
        logger.warning("Fallo clasificación semántica, fallback a operativa: %s", exc)
        respuesta, fuentes = consultar_operativa(pregunta, n_resultados=n_resultados)
        return "operativa", respuesta, fuentes

    if score < ROUTING_MIN_SCORE or (score - segundo) < ROUTING_MIN_DIFF:
        respuesta, fuentes = consultar_operativa(pregunta, n_resultados=n_resultados)
        return "operativa", respuesta, fuentes

    if dominio == "forense":
        respuesta, fuentes = consultar_forense(pregunta, n_resultados=n_resultados)
        return "forense", respuesta, fuentes

    if dominio == "honorarios":
        respuesta, fuentes = consultar_honorarios(pregunta, n_resultados=n_resultados)
        return "honorarios", respuesta, fuentes

    if dominio == "memoria":
        respuesta, fuentes = consultar_memoria(pregunta)
        if respuesta.strip():
            return "memoria", respuesta, fuentes
        respuesta, fuentes = consultar_operativa(pregunta, n_resultados=n_resultados)
        return "operativa", respuesta, fuentes

    if dominio == "causas":
        return resolver_consulta_causas_generica(pregunta)

    respuesta, fuentes = consultar_operativa(pregunta, n_resultados=n_resultados)
    return "operativa", respuesta, fuentes