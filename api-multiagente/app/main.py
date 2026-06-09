from fastapi import FastAPI

from app.config.settings import settings
from app.routes.openai_compat import router as openai_compat_router

app = FastAPI(title=settings.APP_NAME)

@app.get("/")
def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME
    }

app.include_router(openai_compat_router)
