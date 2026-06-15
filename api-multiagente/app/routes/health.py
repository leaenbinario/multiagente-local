from fastapi import APIRouter

from app.config.settings import settings

router = APIRouter(tags=["health"])


@router.get("/")
def root():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": "fase-4",
    }


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
    }