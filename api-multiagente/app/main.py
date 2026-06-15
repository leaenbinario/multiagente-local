import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.routes.agentes import router as agentes_router
from app.routes.causas import router as causas_router
from app.routes.health import router as health_router
from app.routes.memoria import router as memoria_router
from app.routes.openai_compat import router as openai_router
from app.routes.orquestador import router as orquestador_router
from app.routes.consulta import router as consulta_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("api_multiagente")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Hooks de arranque y cierre de la API multiagente.
    Acá podrías inicializar conexiones, pools, etc.
    """
    logger.info("Iniciando API Multiagente...")
    yield
    logger.info("Cerrando API Multiagente...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Backend local multiagente para forense, operativa, honorarios, "
            "memoria y causas, con compatibilidad OpenAI."
        ),
        version="0.4.0",
        lifespan=lifespan,
    )

    # CORS abierto para poder probar desde Open WebUI, navegador, etc.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers básicos
    app.include_router(health_router)       # /health, /estado, etc.
    app.include_router(openai_router)       # /v1/models, /v1/chat/completions
    app.include_router(orquestador_router)  # orquestador estilo OpenAI para Open WebUI
    app.include_router(agentes_router)      # accesos directos a agentes forense/operativa/etc.
    app.include_router(memoria_router)      # /memoria/guardar, /memoria/buscar
    app.include_router(causas_router)       # endpoints de gestión de causas
    app.include_router(consulta_router)     # /consulta: enrutado unificado por intención

    # Endpoint raíz muy simple para pruebas rápidas
    @app.get("/")
    async def root():
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": "0.4.0",
        }

    return app


app = create_app()