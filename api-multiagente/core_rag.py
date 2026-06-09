from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import List, Tuple
import logging
import os

import chromadb
import ollama
from dotenv import load_dotenv
from chromadb.utils.embedding_functions.ollama_embedding_function import (
    OllamaEmbeddingFunction,
)

load_dotenv()

logger = logging.getLogger("core_rag")

# =========================
# VARIABLES DE ENTORNO
# =========================

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

FORENSE_MODEL = os.getenv("FORENSE_MODEL", "llama3.2:3b")
HONORARIOS_MODEL = os.getenv("HONORARIOS_MODEL", "llama3.2:3b")
OPERATIVA_MODEL = os.getenv("OPERATIVA_MODEL", "llama3.2:3b")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")

FORENSE_CONTEXT_SIZE = int(os.getenv("FORENSE_CONTEXT_SIZE", "2048"))
HONORARIOS_CONTEXT_SIZE = int(os.getenv("HONORARIOS_CONTEXT_SIZE", "2048"))
OPERATIVA_CONTEXT_SIZE = int(os.getenv("OPERATIVA_CONTEXT_SIZE", "4096"))

FORENSE_TEMPERATURE = float(os.getenv("FORENSE_TEMPERATURE", "0.1"))
FORENSE_TOP_P = float(os.getenv("FORENSE_TOP_P", "0.5"))

HONORARIOS_TEMPERATURE = float(os.getenv("HONORARIOS_TEMPERATURE", "0.1"))
HONORARIOS_TOP_P = float(os.getenv("HONORARIOS_TOP_P", "0.5"))

OPERATIVA_TEMPERATURE = float(os.getenv("OPERATIVA_TEMPERATURE", "0.3"))
OPERATIVA_TOP_P = float(os.getenv("OPERATIVA_TOP_P", "0.75"))

FORENSE_NUM_PREDICT = int(os.getenv("FORENSE_NUM_PREDICT", "500"))
HONORARIOS_NUM_PREDICT = int(os.getenv("HONORARIOS_NUM_PREDICT", "500"))
OPERATIVA_NUM_PREDICT = int(os.getenv("OPERATIVA_NUM_PREDICT", "400"))

FORENSE_N_RESULTADOS = int(os.getenv("FORENSE_N_RESULTADOS", "2"))
HONORARIOS_N_RESULTADOS = int(os.getenv("HONORARIOS_N_RESULTADOS", "4"))
OPERATIVA_N_RESULTADOS = int(os.getenv("OPERATIVA_N_RESULTADOS", "4"))

MAX_CHARS_POR_CHUNK = int(os.getenv("MAX_CHARS_POR_CHUNK", "1200"))


# =========================
# CONFIGURACIÓN RAG
# =========================

@dataclass(frozen=True)
class RagConfig:
    model: str
    collection_name: str
    system_prompt: str
    temperature: float = 0.2
    top_p: float = 0.7
    num_ctx: int = 4096
    num_predict: int = 500
    n_results_default: int = 4


def get_forense_config(system_prompt: str) -> RagConfig:
    return RagConfig(
        model=FORENSE_MODEL,
        collection_name="documentos_forense",
        system_prompt=system_prompt,
        temperature=FORENSE_TEMPERATURE,
        top_p=FORENSE_TOP_P,
        num_ctx=FORENSE_CONTEXT_SIZE,
        num_predict=FORENSE_NUM_PREDICT,
        n_results_default=FORENSE_N_RESULTADOS,
    )


def get_honorarios_config(system_prompt: str) -> RagConfig:
    return RagConfig(
        model=HONORARIOS_MODEL,
        collection_name="documentos_honorarios",
        system_prompt=system_prompt,
        temperature=HONORARIOS_TEMPERATURE,
        top_p=HONORARIOS_TOP_P,
        num_ctx=HONORARIOS_CONTEXT_SIZE,
        num_predict=HONORARIOS_NUM_PREDICT,
        n_results_default=HONORARIOS_N_RESULTADOS,
    )


def get_operativa_config(system_prompt: str) -> RagConfig:
    return RagConfig(
        model=OPERATIVA_MODEL,
        collection_name="documentos_operativa",
        system_prompt=system_prompt,
        temperature=OPERATIVA_TEMPERATURE,
        top_p=OPERATIVA_TOP_P,
        num_ctx=OPERATIVA_CONTEXT_SIZE,
        num_predict=OPERATIVA_NUM_PREDICT,
        n_results_default=OPERATIVA_N_RESULTADOS,
    )


# =========================
# CLIENTES CACHEADOS
# =========================

@lru_cache(maxsize=8)
def _embedding_fn():
    return OllamaEmbeddingFunction(
        url=OLLAMA_BASE_URL,
        model_name=EMBEDDING_MODEL,
    )


@lru_cache(maxsize=4)
def _ollama_client():
    return ollama.Client(host=OLLAMA_BASE_URL)


@lru_cache(maxsize=32)
def _collection(collection_name: str):
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=_embedding_fn(),
    )


# =========================
# HELPERS
# =========================

def normalizar_fuente(meta: dict) -> str:
    if not isinstance(meta, dict):
        return "desconocido - chunk ?"

    fuente = meta.get("source", "desconocido")
    idx = meta.get("chunk_index", meta.get("chunk", "?"))
    return f"{fuente} - chunk {idx}"


def recortar_texto(texto: str, max_chars: int) -> str:
    texto = (texto or "").strip()

    if not texto:
        return ""

    if len(texto) <= max_chars:
        return texto

    texto_recortado = texto[:max_chars].rsplit(" ", 1)[0].strip()
    if not texto_recortado:
        texto_recortado = texto[:max_chars].strip()

    return texto_recortado + "..."


def construir_prompt_usuario(contexto_texto: str, consulta: str) -> str:
    return (
        f"CONTEXTO:\n{contexto_texto}\n\n"
        f"PREGUNTA DEL USUARIO:\n{consulta}\n\n"
        "INSTRUCCIONES:\n"
        "- Responde exclusivamente con base en el CONTEXTO.\n"
        "- Si el CONTEXTO no alcanza, indícalo expresamente.\n"
        "- No inventes hechos, normas, fechas, montos ni conclusiones.\n"
        "- Redacta en español, de forma clara y completa.\n"
        "- Usa un máximo de 3 párrafos breves.\n"
    )


# =========================
# FUNCIÓN PRINCIPAL RAG
# =========================

def responder_con_rag(
    consulta: str,
    cfg: RagConfig,
    n_resultados: int | None = None,
) -> Tuple[str, List[str]]:
    try:
        collection = _collection(cfg.collection_name)
        k = cfg.n_results_default if n_resultados is None else n_resultados

        resultados = collection.query(
            query_texts=[consulta],
            n_results=k,
        )

        documentos = resultados.get("documents", [[]])[0] or []
        metadatas = resultados.get("metadatas", [[]])[0] or []

        if not documentos:
            return (
                f"No se encontró información relevante en la base {cfg.collection_name} para responder esta consulta.",
                [],
            )

        partes_contexto: List[str] = []
        fuentes_listado: List[str] = []

        for doc, meta in zip(documentos, metadatas):
            ref = normalizar_fuente(meta)
            doc_limpio = recortar_texto(doc, MAX_CHARS_POR_CHUNK)

            if not doc_limpio:
                continue

            partes_contexto.append(f"[{ref}]\n{doc_limpio}")
            fuentes_listado.append(ref)

        if not partes_contexto:
            return (
                f"No se pudo construir contexto útil desde la base {cfg.collection_name}.",
                [],
            )

        contexto_texto = "\n\n".join(partes_contexto)
        prompt_usuario = construir_prompt_usuario(contexto_texto, consulta)

        respuesta = _ollama_client().chat(
            model=cfg.model,
            options={
                "temperature": cfg.temperature,
                "top_p": cfg.top_p,
                "num_ctx": cfg.num_ctx,
                "num_predict": cfg.num_predict,
            },
            messages=[
                {"role": "system", "content": cfg.system_prompt},
                {"role": "user", "content": prompt_usuario},
            ],
        )

        contenido = respuesta["message"]["content"].strip()

        if not contenido:
            return (
                "No fue posible generar una respuesta válida con el contexto recuperado.",
                fuentes_listado,
            )

        return contenido, fuentes_listado

    except Exception as e:
        logger.exception("Error en responder_con_rag: %s", e)
        return (
            f"Error consultando la base RAG de {cfg.collection_name}: {e}",
            [],
        )