from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from uuid import uuid4
from contextlib import asynccontextmanager
import json
import logging
import math
import os
import re
import time

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import agente_asistente as aa
import agente_contador as ac
import agente_forense as af

load_dotenv()

logger = logging.getLogger("api_multiagente")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MEMORIA_PATH = DATA_DIR / "memoria_usuario.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")
OPENCLAW_CAUSAS_URL = os.getenv("OPENCLAW_CAUSAS_URL", "http://openclaw-causas:9100")

ROUTING_MIN_SCORE = float(os.getenv("ROUTING_MIN_SCORE", "0.35"))
ROUTING_MIN_DIFF = float(os.getenv("ROUTING_MIN_DIFF", "0.03"))
DEFAULT_N_RESULTADOS = int(os.getenv("DEFAULT_N_RESULTADOS", "4"))


class ConsultaRequest(BaseModel):
    pregunta: str = Field(..., min_length=1)
    n_resultados: int = Field(default=DEFAULT_N_RESULTADOS, ge=1, le=10)


class ConsultaResponse(BaseModel):
    respuesta: str
    fuentes: List[str] = Field(default_factory=list)


class OrquestadorResponse(BaseModel):
    agente: str
    respuesta: str
    fuentes: List[str] = Field(default_factory=list)


class MemoriaGuardarRequest(BaseModel):
    clave: str
    valor: str
    categoria: str = "general"


class MemoriaBuscarRequest(BaseModel):
    consulta: str


class MemoriaItem(BaseModel):
    clave: str
    valor: str
    categoria: str


class MemoriaBuscarResponse(BaseModel):
    resultados: List[MemoriaItem]


class OpenAIMessage(BaseModel):
    role: str
    content: Any


class OpenAIChatCompletionRequest(BaseModel):
    model: str = "multiagente-local"
    messages: List[OpenAIMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


class CausaRequest(BaseModel):
    id_causa: str


class EmailCausaRequest(BaseModel):
    id_causa: str
    motivo: Optional[str] = "seguimiento"
    tono: Optional[str] = "profesional_cercano"


class WhatsAppCausaRequest(BaseModel):
    id_causa: str
    motivo: Optional[str] = "seguimiento"
    tono: Optional[str] = "profesional_cercano"


class FichaCausaCreate(BaseModel):
    id_causa: str
    caratula: str
    fuero: Optional[str] = None
    juzgado: Optional[str] = None
    abogado_nombre: Optional[str] = None
    abogado_email: Optional[str] = None
    abogado_whatsapp: Optional[str] = None
    cliente: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_ultimo_contacto: Optional[str] = None
    estado_actual: Optional[str] = None
    proximos_pasos: List[str] = Field(default_factory=list)
    notas: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class FichaCausaUpdate(BaseModel):
    caratula: Optional[str] = None
    fuero: Optional[str] = None
    juzgado: Optional[str] = None
    abogado_nombre: Optional[str] = None
    abogado_email: Optional[str] = None
    abogado_whatsapp: Optional[str] = None
    cliente: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_ultimo_contacto: Optional[str] = None
    estado_actual: Optional[str] = None
    proximos_pasos: Optional[List[str]] = None
    notas: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class ContactoCreateRequest(BaseModel):
    fecha: Optional[str] = None
    canal: str
    asunto: Optional[str] = None
    nota: str
    resultado: Optional[str] = None


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando API Multiagente...")
    try:
        precalcular_embeddings_dominios()
        logger.info("Embeddings de dominios precalculados.")
    except Exception as exc:
        logger.exception("Error precalculando embeddings de dominios: %s", exc)
    yield
    logger.info("Cerrando API Multiagente...")


app = FastAPI(title="API Multiagente Local", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def cargar_memoria() -> List[dict]:
    if not MEMORIA_PATH.exists():
        return []

    try:
        with open(MEMORIA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        logger.warning("No se pudo leer memoria_usuario.json; se devuelve memoria vacía.")
        return []


def guardar_memoria(data: List[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MEMORIA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def memoria_guardar_item(clave: str, valor: str, categoria: str = "general") -> None:
    data = cargar_memoria()
    data.append({"clave": clave, "valor": valor, "categoria": categoria})
    guardar_memoria(data)


def memoria_buscar_items(consulta: str) -> List[dict]:
    data = cargar_memoria()
    q = consulta.lower().strip()
    resultados = []

    for item in data:
        clave = str(item.get("clave", "")).lower()
        valor = str(item.get("valor", "")).lower()
        categoria = str(item.get("categoria", "")).lower()

        if q in clave or q in valor or q in categoria:
            resultados.append(item)

    return resultados


def _formatear_recuerdos(recuerdos: List[dict]) -> str:
    return "Memoria encontrada:\n" + "\n".join(
        f"- {r['clave']}: {r['valor']}" for r in recuerdos
    )


def _normalizar_respuesta(respuesta: Any, fuentes: Any) -> Tuple[str, List[str]]:
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
    return _normalizar_respuesta(respuesta, fuentes)


def consultar_operativa(
    pregunta: str,
    n_resultados: int = DEFAULT_N_RESULTADOS,
) -> Tuple[str, List[str]]:
    respuesta, fuentes = aa.agente_asistente(pregunta, n_resultados)
    return _normalizar_respuesta(respuesta, fuentes)


def consultar_honorarios(
    pregunta: str,
    n_resultados: int = DEFAULT_N_RESULTADOS,
) -> Tuple[str, List[str]]:
    respuesta, fuentes = ac.agente_contador(pregunta, n_resultados)
    return _normalizar_respuesta(respuesta, fuentes)


def consultar_asistente(
    pregunta: str,
    n_resultados: int = DEFAULT_N_RESULTADOS,
) -> Tuple[str, List[str]]:
    return consultar_operativa(pregunta, n_resultados)


def consultar_contador(
    pregunta: str,
    n_resultados: int = DEFAULT_N_RESULTADOS,
) -> Tuple[str, List[str]]:
    return consultar_honorarios(pregunta, n_resultados)


def consultar_memoria(pregunta: str) -> Tuple[str, List[str]]:
    recuerdos = memoria_buscar_items(pregunta)
    if recuerdos:
        return _formatear_recuerdos(recuerdos), []
    return "", []


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


def request_openclaw(
    method: str,
    path: str,
    payload: Optional[dict] = None,
    params: Optional[dict] = None,
):
    url = f"{OPENCLAW_CAUSAS_URL}{path}"
    try:
        if method == "GET":
            resp = requests.get(url, params=params, timeout=30)
        elif method == "POST":
            resp = requests.post(url, json=payload, timeout=30)
        elif method == "PUT":
            resp = requests.put(url, json=payload, timeout=30)
        else:
            raise ValueError(f"Método no soportado: {method}")

        if resp.status_code in (400, 404, 409, 422):
            try:
                detalle = resp.json()
            except Exception:
                detalle = {"detail": resp.text}
            raise HTTPException(status_code=resp.status_code, detail=detalle)

        resp.raise_for_status()
        return resp.json()

    except HTTPException:
        raise
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando openclaw-causas: {str(exc)}",
        )


def listar_causas_openclaw():
    return request_openclaw("GET", "/causas")


def buscar_causas_openclaw(params: dict):
    return request_openclaw("GET", "/causas/buscar", params=params)


def obtener_causa_openclaw(id_causa: str):
    return request_openclaw("GET", f"/causas/{id_causa}")


def crear_causa_openclaw(payload: dict):
    return request_openclaw("POST", "/causas", payload=payload)


def actualizar_causa_openclaw(id_causa: str, payload: dict):
    return request_openclaw("PUT", f"/causas/{id_causa}", payload=payload)


def registrar_contacto_openclaw(id_causa: str, payload: dict):
    return request_openclaw("POST", f"/causas/{id_causa}/contactos", payload=payload)


def obtener_historial_openclaw(id_causa: str):
    return request_openclaw("GET", f"/causas/{id_causa}/historial")


def consultar_resumen_causa_openclaw(id_causa: str):
    return request_openclaw("GET", f"/causas/{id_causa}/resumen")


def sugerir_email_causa_openclaw(
    id_causa: str,
    motivo: str = "seguimiento",
    tono: str = "profesional_cercano",
):
    return request_openclaw(
        "POST",
        "/causas/sugerir-email",
        payload={
            "id_causa": id_causa,
            "motivo": motivo,
            "tono": tono,
        },
    )


def sugerir_whatsapp_causa_openclaw(
    id_causa: str,
    motivo: str = "seguimiento",
    tono: str = "profesional_cercano",
):
    return request_openclaw(
        "POST",
        "/causas/sugerir-whatsapp",
        payload={
            "id_causa": id_causa,
            "motivo": motivo,
            "tono": tono,
        },
    )


def limpiar_markdown_mailto(texto: str) -> str:
    if not texto:
        return texto

    texto = re.sub(
        r"\[([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\]\(mailto:[^)]+\)",
        r"\1",
        texto,
        flags=re.IGNORECASE,
    )

    texto = re.sub(
        r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
        r"\1",
        texto,
        flags=re.IGNORECASE,
    )

    return texto


def limpiar_whatsapp(texto: str) -> str:
    if not texto:
        return texto

    texto = texto.strip()
    texto = texto.replace("(", "").replace(")", "")
    texto = texto.replace("–", "-").replace("—", "-")
    texto = re.sub(r"\s+", " ", texto)
    return texto


def normalizar_texto_entrada(pregunta: str) -> str:
    if not pregunta:
        return pregunta
    return limpiar_markdown_mailto(pregunta)


def extraer_id_causa(pregunta: str) -> Optional[str]:
    patrones = [
        r"\bid_causa\s*[:=]\s*([A-Za-z0-9_-]+)\b",
        r"\b(?:causa|expediente)\s+([A-Za-z0-9][A-Za-z0-9_-]*)\b",
    ]

    for patron in patrones:
        m = re.search(patron, pregunta, re.IGNORECASE)
        if m:
            return m.group(1)

    m = re.search(r"\b([A-Za-z0-9]+(?:-[A-Za-z0-9]+)+)\b", pregunta)
    if m:
        return m.group(1)

    return None


def detectar_intencion_causas(pregunta: str) -> Optional[str]:
    p = pregunta.lower().strip()

    mapa = {
        "crear_causa": [
            "creá la causa", "crea la causa", "crear causa", "nueva causa",
            "alta de causa", "registrar causa",
        ],
        "actualizar_causa": [
            "actualizá la causa", "actualiza la causa", "actualizar causa",
            "editar causa", "modificar causa",
        ],
        "registrar_contacto": [
            "registrá un contacto", "registra un contacto", "registrar contacto",
            "agregar contacto", "nuevo contacto",
        ],
        "obtener_historial": [
            "mostrame el historial", "muéstrame el historial",
            "ver historial", "historial de la causa",
        ],
        "obtener_causa": [
            "mostrame la causa", "muéstrame la causa",
            "mostrar la causa", "mostrar causa",
            "ver la causa", "ver causa",
            "detalle de la causa", "detalle causa",
            "ficha de la causa", "ficha causa",
        ],
        "resumen_causa": [
            "resumen de la causa", "resumen de causa",
            "resumí la causa", "resumi la causa",
            "ver resumen", "resumen causa",
        ],
        "sugerir_whatsapp": [
            "sugerime un whatsapp", "sugiéreme un whatsapp",
            "generame un whatsapp", "genera un whatsapp",
            "borrador de whatsapp", "mensaje de whatsapp",
            "whatsapp de seguimiento",
        ],
        "sugerir_email": [
            "sugerime un email", "sugiéreme un email",
            "generame un email", "genera un email",
            "borrador de email", "mail de seguimiento",
            "email de seguimiento",
        ],
        "listar_causas": [
            "listá causas", "lista causas", "listar causas",
            "mostrame causas", "muéstrame causas", "mis causas",
        ],
        "buscar_causas": [
            "buscá causas", "busca causas", "buscar causas",
            "filtrá causas", "filtra causas",
        ],
    }

    for intencion, claves in mapa.items():
        if any(k in p for k in claves):
            return intencion

    return None


def extraer_caratula(pregunta: str) -> Optional[str]:
    patrones = [
        r"(?:carátula|caratula)\s*[:=]\s*(.+?)(?=\s+estado\s*[:=]|\s+abogado\s*[:=]|\s+cliente\s*[:=]|\s+email\s*[:=]|\s+whatsapp\s*[:=]|$)",
        r"(?:para|con)\s+carátula\s+(.+?)(?=\s+estado\s*[:=]|\s+abogado\s*[:=]|\s+cliente\s*[:=]|\s+email\s*[:=]|\s+whatsapp\s*[:=]|$)",
        r"(?:para|con)\s+caratula\s+(.+?)(?=\s+estado\s*[:=]|\s+abogado\s*[:=]|\s+cliente\s*[:=]|\s+email\s*[:=]|\s+whatsapp\s*[:=]|$)",
    ]
    for patron in patrones:
        m = re.search(patron, pregunta, re.IGNORECASE)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def extraer_estado_actual(pregunta: str) -> Optional[str]:
    m = re.search(
        r"estado\s*[:=]\s*([A-Za-z0-9ÁÉÍÓÚáéíóúñÑ _-]+?)(?=\s+abogado\s*[:=]|\s+cliente\s*[:=]|\s+email\s*[:=]|\s+whatsapp\s*[:=]|$)",
        pregunta,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return None


def extraer_email(pregunta: str) -> Optional[str]:
    pregunta = limpiar_markdown_mailto(pregunta)
    patrones = [
        r"email\s*[:=]\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
        r"correo\s*[:=]\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
    ]
    for patron in patrones:
        m = re.search(patron, pregunta, re.IGNORECASE)
        if m:
            return m.group(1).strip().lower()
    return None


def extraer_whatsapp(pregunta: str) -> Optional[str]:
    patrones = [
        r"(?:whatsapp|wa)\s*[:=]\s*(\+?[0-9][0-9\s\-\(\)]{7,})",
        r"(?:número de whatsapp|numero de whatsapp)\s*[:=]\s*(\+?[0-9][0-9\s\-\(\)]{7,})",
    ]
    for patron in patrones:
        m = re.search(patron, pregunta, re.IGNORECASE)
        if m:
            return limpiar_whatsapp(m.group(1))
    return None


def extraer_canal(pregunta: str) -> Optional[str]:
    p = pregunta.lower()
    for canal in ["email", "correo", "whatsapp", "llamada", "telefono", "teléfono", "presencial"]:
        if canal in p:
            if canal in ["email", "correo"]:
                return "email"
            if canal in ["telefono", "teléfono"]:
                return "telefono"
            return canal
    return None


def extraer_asunto_contacto(pregunta: str) -> Optional[str]:
    m = re.search(
        r"asunto\s*[:=]\s*(.+?)(?=\s+nota\s*[:=]|\s+resultado\s*[:=]|$)",
        pregunta,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().strip('"').strip("'")
    return None


def extraer_nota_contacto(pregunta: str) -> Optional[str]:
    m = re.search(
        r"nota\s*[:=]\s*(.+?)(?=\s+resultado\s*[:=]|\s+asunto\s*[:=]|$)",
        pregunta,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().strip('"').strip("'")
    return None


def extraer_resultado_contacto(pregunta: str) -> Optional[str]:
    m = re.search(
        r"resultado\s*[:=]\s*(.+?)(?=\s+nota\s*[:=]|\s+asunto\s*[:=]|$)",
        pregunta,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().strip('"').strip("'")
    return None


def extraer_motivo(pregunta: str) -> str:
    p = pregunta.lower()
    if "recordatorio" in p:
        return "recordatorio"
    if "consulta" in p:
        return "consulta"
    return "seguimiento"


def extraer_tono(pregunta: str) -> str:
    p = pregunta.lower()
    if "formal" in p:
        return "formal"
    if "cercano" in p or "amable" in p:
        return "profesional_cercano"
    return "profesional_cercano"


def renderizar_resultado_causas(resultado: Any) -> Tuple[str, List[str]]:
    if resultado is None:
        return "No obtuve respuesta del servicio de causas.", []

    if isinstance(resultado, dict):
        if "answer" in resultado:
            texto = str(resultado.get("answer", "")).strip()
            fuentes = [str(x) for x in resultado.get("sources", []) if str(x).strip()]
            return texto, fuentes

        if "detail" in resultado and not resultado.get("id_causa"):
            detail = resultado.get("detail")
            if isinstance(detail, (dict, list)):
                return json.dumps(detail, ensure_ascii=False, indent=2), []
            return str(detail), []

        if "id_causa" in resultado:
            id_causa = resultado.get("id_causa", "sin id")
            caratula = resultado.get("caratula", "sin carátula")
            estado = resultado.get("estado_actual") or resultado.get("estado") or "sin estado"
            email = resultado.get("abogado_email") or "sin email"
            whatsapp = resultado.get("abogado_whatsapp") or "sin whatsapp"
            abogado = resultado.get("abogado_nombre") or "sin abogado"
            cliente = resultado.get("cliente") or "sin cliente"
            fuero = resultado.get("fuero") or "sin fuero"
            juzgado = resultado.get("juzgado") or "sin juzgado"
            fecha_inicio = resultado.get("fecha_inicio") or "sin fecha de inicio"
            fecha_ultimo_contacto = resultado.get("fecha_ultimo_contacto") or "sin último contacto"
            tags = resultado.get("tags") or []
            notas = resultado.get("notas") or []
            proximos_pasos = resultado.get("proximos_pasos") or []

            lineas = [
                f"Causa: {id_causa}",
                f"Carátula: {caratula}",
                f"Estado: {estado}",
                f"Cliente: {cliente}",
                f"Abogado: {abogado}",
                f"Email: {email}",
                f"WhatsApp: {whatsapp}",
                f"Fuero: {fuero}",
                f"Juzgado: {juzgado}",
                f"Fecha de inicio: {fecha_inicio}",
                f"Último contacto: {fecha_ultimo_contacto}",
            ]

            if tags:
                lineas.append("Tags: " + ", ".join(str(t) for t in tags if str(t).strip()))

            if proximos_pasos:
                lineas.append("Próximos pasos:")
                lineas.extend(f"- {str(p).strip()}" for p in proximos_pasos if str(p).strip())

            if notas:
                lineas.append("Notas:")
                lineas.extend(f"- {str(n).strip()}" for n in notas if str(n).strip())

            return "\n".join(lineas), []

        if "data" in resultado and isinstance(resultado["data"], list):
            data = resultado["data"]
            if not data:
                return "No encontré resultados.", []

            primer_item = data[0]

            if len(data) == 1 and isinstance(primer_item, dict) and "id_causa" in primer_item:
                return renderizar_resultado_causas(primer_item)

            if isinstance(primer_item, dict) and "timestamp" in primer_item and "action" in primer_item:
                lineas = ["Historial de la causa:"]
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    timestamp = item.get("timestamp", "sin fecha")
                    action = item.get("action", "sin acción")
                    detail = item.get("detail", "")
                    if detail:
                        lineas.append(f"- {timestamp} | {action} | {detail}")
                    else:
                        lineas.append(f"- {timestamp} | {action}")
                return "\n".join(lineas), []

            if isinstance(primer_item, dict) and "id_causa" in primer_item:
                lineas = ["Causas encontradas:"]
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    id_causa = item.get("id_causa", "sin id")
                    caratula = item.get("caratula", "sin carátula")
                    estado = item.get("estado_actual") or item.get("estado") or "sin estado"
                    email = item.get("abogado_email") or "sin email"
                    whatsapp = item.get("abogado_whatsapp") or "sin whatsapp"
                    lineas.append(
                        f"- {id_causa} | {caratula} | Estado: {estado} | Email: {email} | WhatsApp: {whatsapp}"
                    )
                return "\n".join(lineas), []

        return json.dumps(resultado, ensure_ascii=False, indent=2), []

    if isinstance(resultado, list):
        if not resultado:
            return "No encontré resultados.", []
        return json.dumps(resultado, ensure_ascii=False, indent=2), []

    return str(resultado), []


def ejecutar_intencion_causas(intencion: str, pregunta: str) -> Tuple[str, str, List[str]]:
    id_causa = extraer_id_causa(pregunta)

    if intencion == "listar_causas":
        resultado = listar_causas_openclaw()
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if intencion == "buscar_causas":
        q = pregunta
        for token in ["buscá causas", "busca causas", "buscar causas", "filtrá causas", "filtra causas"]:
            q = re.sub(token, "", q, flags=re.IGNORECASE).strip()
        resultado = buscar_causas_openclaw({"q": q} if q else {})
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if intencion == "obtener_causa":
        if not id_causa:
            return "causas", "Necesito el ID de la causa para mostrarla.", []
        resultado = obtener_causa_openclaw(id_causa)
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if intencion == "obtener_historial":
        if not id_causa:
            return "causas", "Necesito el ID de la causa para consultar el historial.", []
        resultado = obtener_historial_openclaw(id_causa)
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if intencion == "resumen_causa":
        if not id_causa:
            return "causas", "Necesito el ID de la causa para resumirla.", []
        resultado = consultar_resumen_causa_openclaw(id_causa)
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if intencion == "sugerir_email":
        if not id_causa:
            return "causas", "Necesito el ID de la causa para sugerir el email.", []
        resultado = sugerir_email_causa_openclaw(
            id_causa=id_causa,
            motivo=extraer_motivo(pregunta),
            tono=extraer_tono(pregunta),
        )
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if intencion == "sugerir_whatsapp":
        if not id_causa:
            return "causas", "Necesito el ID de la causa para sugerir el WhatsApp.", []
        resultado = sugerir_whatsapp_causa_openclaw(
            id_causa=id_causa,
            motivo=extraer_motivo(pregunta),
            tono=extraer_tono(pregunta),
        )
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if intencion == "registrar_contacto":
        if not id_causa:
            return "causas", "Necesito el ID de la causa para registrar el contacto.", []

        payload = {
            "canal": extraer_canal(pregunta) or "email",
            "asunto": extraer_asunto_contacto(pregunta),
            "nota": extraer_nota_contacto(pregunta) or pregunta,
            "resultado": extraer_resultado_contacto(pregunta) or "registrado desde lenguaje natural",
        }
        resultado = registrar_contacto_openclaw(id_causa, payload)
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if intencion == "crear_causa":
        id_nuevo = id_causa or f"causa-{uuid4().hex[:8]}"
        payload = {
            "id_causa": id_nuevo,
            "caratula": extraer_caratula(pregunta) or "Carátula no especificada",
        }

        estado = extraer_estado_actual(pregunta)
        email = extraer_email(pregunta)
        whatsapp = extraer_whatsapp(pregunta)

        if estado:
            payload["estado_actual"] = estado
        if email:
            payload["abogado_email"] = email
        if whatsapp:
            payload["abogado_whatsapp"] = whatsapp

        resultado = crear_causa_openclaw(payload)
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if intencion == "actualizar_causa":
        if not id_causa:
            return "causas", "Necesito el ID de la causa para actualizarla.", []

        payload = {}
        caratula = extraer_caratula(pregunta)
        estado = extraer_estado_actual(pregunta)
        email = extraer_email(pregunta)
        whatsapp = extraer_whatsapp(pregunta)

        if caratula:
            payload["caratula"] = caratula
        if estado:
            payload["estado_actual"] = estado
        if email:
            payload["abogado_email"] = email
        if whatsapp:
            payload["abogado_whatsapp"] = whatsapp

        if not payload:
            return (
                "causas",
                "No detecté campos para actualizar. Probá indicando por ejemplo: estado: en análisis, email: x@y.com o whatsapp: +54...",
                [],
            )

        resultado = actualizar_causa_openclaw(id_causa, payload)
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    return "causas", "No pude interpretar la acción sobre la causa.", []


def resolver_consulta_causas_generica(pregunta: str) -> Tuple[str, str, List[str]]:
    pregunta_l = pregunta.lower()
    id_causa = extraer_id_causa(pregunta)

    if "historial" in pregunta_l:
        if not id_causa:
            return "causas", "Necesito el ID de la causa para consultar el historial.", []
        resultado = obtener_historial_openclaw(id_causa)
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if "resumen" in pregunta_l:
        if not id_causa:
            return "causas", "Necesito el ID de la causa para resumirla.", []
        resultado = consultar_resumen_causa_openclaw(id_causa)
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if "whatsapp" in pregunta_l:
        if not id_causa:
            return "causas", "Necesito el ID de la causa para sugerir el WhatsApp.", []
        resultado = sugerir_whatsapp_causa_openclaw(
            id_causa=id_causa,
            motivo=extraer_motivo(pregunta),
            tono=extraer_tono(pregunta),
        )
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if "mail" in pregunta_l or "email" in pregunta_l:
        if not id_causa:
            return "causas", "Necesito el ID de la causa para sugerir el email.", []
        resultado = sugerir_email_causa_openclaw(
            id_causa=id_causa,
            motivo=extraer_motivo(pregunta),
            tono=extraer_tono(pregunta),
        )
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    if id_causa:
        resultado = obtener_causa_openclaw(id_causa)
        texto, fuentes = renderizar_resultado_causas(resultado)
        return "causas", texto, fuentes

    resultado = listar_causas_openclaw()
    texto, fuentes = renderizar_resultado_causas(resultado)
    return "causas", texto, fuentes


def enrutar_consulta(
    pregunta: str,
    n_resultados: int = DEFAULT_N_RESULTADOS,
) -> Tuple[str, str, List[str]]:
    pregunta = normalizar_texto_entrada(pregunta)
    pregunta_l = pregunta.lower()

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


@app.post("/consulta", response_model=ConsultaResponse)
def consulta_agente_legacy(req: ConsultaRequest) -> ConsultaResponse:
    try:
        _, respuesta, fuentes = enrutar_consulta(req.pregunta, req.n_resultados)
        return ConsultaResponse(respuesta=respuesta, fuentes=fuentes)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en consulta legacy: {str(exc)}")


@app.post("/forense/consulta", response_model=ConsultaResponse)
def consulta_forense_endpoint(req: ConsultaRequest) -> ConsultaResponse:
    try:
        respuesta, fuentes = consultar_forense(req.pregunta, req.n_resultados)
        return ConsultaResponse(respuesta=respuesta, fuentes=fuentes)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en agente_forense: {str(exc)}")


@app.post("/operativa/consulta", response_model=ConsultaResponse)
def consulta_operativa_endpoint(req: ConsultaRequest) -> ConsultaResponse:
    try:
        respuesta, fuentes = consultar_operativa(req.pregunta, req.n_resultados)
        return ConsultaResponse(respuesta=respuesta, fuentes=fuentes)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en agente_operativa: {str(exc)}")


@app.post("/honorarios/consulta", response_model=ConsultaResponse)
def consulta_honorarios_endpoint(req: ConsultaRequest) -> ConsultaResponse:
    try:
        respuesta, fuentes = consultar_honorarios(req.pregunta, req.n_resultados)
        return ConsultaResponse(respuesta=respuesta, fuentes=fuentes)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en agente_honorarios: {str(exc)}")


@app.post("/asistente/consulta", response_model=ConsultaResponse)
def consulta_asistente_endpoint(req: ConsultaRequest) -> ConsultaResponse:
    return consulta_operativa_endpoint(req)


@app.post("/contador/consulta", response_model=ConsultaResponse)
def consulta_contador_endpoint(req: ConsultaRequest) -> ConsultaResponse:
    return consulta_honorarios_endpoint(req)


@app.post("/memoria/guardar")
def memoria_guardar_endpoint(req: MemoriaGuardarRequest):
    try:
        memoria_guardar_item(req.clave, req.valor, req.categoria)
        return {"ok": True, "mensaje": "Memoria guardada correctamente."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error guardando memoria: {str(exc)}")


@app.post("/memoria/buscar", response_model=MemoriaBuscarResponse)
def memoria_buscar_endpoint(req: MemoriaBuscarRequest):
    try:
        resultados = memoria_buscar_items(req.consulta)
        return MemoriaBuscarResponse(resultados=[MemoriaItem(**r) for r in resultados])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error buscando memoria: {str(exc)}")


@app.post("/orquestador/consulta", response_model=OrquestadorResponse)
def orquestador_consulta_endpoint(req: ConsultaRequest):
    try:
        agente, respuesta, fuentes = enrutar_consulta(req.pregunta, req.n_resultados)
        return OrquestadorResponse(agente=agente, respuesta=respuesta, fuentes=fuentes)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en orquestador: {str(exc)}")


@app.get("/causas")
def causas_listar():
    return listar_causas_openclaw()


@app.get("/causas/buscar")
def causas_buscar(
    q: Optional[str] = Query(default=None),
    abogado: Optional[str] = Query(default=None),
    cliente: Optional[str] = Query(default=None),
    estado: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
):
    params = {
        k: v for k, v in {
            "q": q,
            "abogado": abogado,
            "cliente": cliente,
            "estado": estado,
            "tag": tag,
        }.items() if v is not None
    }
    return buscar_causas_openclaw(params)


@app.get("/causas/{id_causa}")
def causas_obtener(id_causa: str):
    return obtener_causa_openclaw(id_causa)


@app.post("/causas")
def causas_crear(req: FichaCausaCreate):
    return crear_causa_openclaw(req.model_dump())


@app.put("/causas/{id_causa}")
def causas_actualizar(id_causa: str, req: FichaCausaUpdate):
    payload = req.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")
    return actualizar_causa_openclaw(id_causa, payload)


@app.post("/causas/{id_causa}/contactos")
def causas_registrar_contacto(id_causa: str, req: ContactoCreateRequest):
    return registrar_contacto_openclaw(id_causa, req.model_dump())


@app.get("/causas/{id_causa}/historial")
def causas_historial(id_causa: str):
    return obtener_historial_openclaw(id_causa)


@app.get("/causas/{id_causa}/resumen")
def causas_resumen_get(id_causa: str):
    return consultar_resumen_causa_openclaw(id_causa)


@app.post("/causas/resumen")
def causas_resumen(req: CausaRequest):
    return consultar_resumen_causa_openclaw(req.id_causa)


@app.post("/causas/sugerir-email")
def causas_sugerir_email(req: EmailCausaRequest):
    return sugerir_email_causa_openclaw(
        id_causa=req.id_causa,
        motivo=req.motivo,
        tono=req.tono,
    )


@app.post("/causas/sugerir-whatsapp")
def causas_sugerir_whatsapp(req: WhatsAppCausaRequest):
    return sugerir_whatsapp_causa_openclaw(
        id_causa=req.id_causa,
        motivo=req.motivo,
        tono=req.tono,
    )


@app.post("/v1/chat/completions")
def openai_chat_completions(req: OpenAIChatCompletionRequest):
    try:
        mensajes_usuario = [
            m for m in req.messages
            if m.role == "user" and isinstance(m.content, str)
        ]

        if not mensajes_usuario:
            raise HTTPException(
                status_code=400,
                detail="No se encontró un mensaje de usuario válido.",
            )

        pregunta = mensajes_usuario[-1].content
        agente, respuesta, fuentes = enrutar_consulta(
            pregunta,
            n_resultados=DEFAULT_N_RESULTADOS,
        )

        contenido = (respuesta or "").strip()

        if agente == "memoria" and not contenido and not fuentes:
            respuesta, fuentes = consultar_operativa(
                pregunta,
                n_resultados=DEFAULT_N_RESULTADOS,
            )
            agente = "operativa"
            contenido = (respuesta or "").strip()

        return {
            "id": f"chatcmpl-{uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": contenido,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "metadata": {
                "agente": agente,
                "fuentes": fuentes,
            },
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error en endpoint OpenAI-compatible: {str(exc)}",
        )


@app.get("/v1/models")
def openai_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "multiagente-local",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local",
            }
        ],
    }


@app.options("/models")
async def options_models():
    return JSONResponse(content={}, headers={"Access-Control-Allow-Origin": "*"})


@app.get("/models")
async def openai_models_alias():
    return openai_models()


@app.options("/chat/completions")
async def options_chat_completions():
    return JSONResponse(content={}, headers={"Access-Control-Allow-Origin": "*"})


@app.post("/chat/completions")
async def openai_chat_completions_alias(request: Request):
    body = await request.json()
    req = OpenAIChatCompletionRequest(**body)
    return openai_chat_completions(req)


@app.get("/")
def root():
    return {
        "status": "ok",
        "app": "API Multiagente Local",
        "openclaw_causas_url": OPENCLAW_CAUSAS_URL,
        "endpoints": [
            "/consulta",
            "/forense/consulta",
            "/operativa/consulta",
            "/honorarios/consulta",
            "/asistente/consulta",
            "/contador/consulta",
            "/memoria/guardar",
            "/memoria/buscar",
            "/orquestador/consulta",
            "/causas",
            "/causas/buscar",
            "/causas/{id_causa}",
            "/causas/{id_causa}/contactos",
            "/causas/{id_causa}/historial",
            "/causas/{id_causa}/resumen",
            "/causas/resumen",
            "/causas/sugerir-email",
            "/causas/sugerir-whatsapp",
            "/v1/models",
            "/v1/chat/completions",
            "/models",
            "/chat/completions",
        ],
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "9000")),
    )