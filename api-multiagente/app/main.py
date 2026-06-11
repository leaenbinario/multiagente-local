from __future__ import annotations

import logging

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import API_HOST, API_PORT, OPENCLAW_CAUSAS_URL
from router_consulta import precalcular_embeddings_dominios
from routes.openai_compat import router as openai_router
from routes.consulta import router as consulta_router
from routes.memoria import router as memoria_router
from routes.causas import router as causas_router

logger = logging.getLogger("api_multiagente")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


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

app.include_router(openai_router)
app.include_router(consulta_router)
app.include_router(memoria_router)
app.include_router(causas_router)

logger.info("API Multiagente cargada correctamente.")


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
    uvicorn.run(app, host=API_HOST, port=API_PORT)