from typing import Any, Dict, Optional

import requests

from app.config.settings import settings


def _build_url(path: str) -> str:
    base_url = settings.OPENCLAW_CAUSAS_URL.rstrip("/")
    clean_path = path.lstrip("/")
    return f"{base_url}/{clean_path}"


def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response = requests.get(
        _build_url(path),
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _post(path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response = requests.post(
        _build_url(path),
        json=payload or {},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _put(path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response = requests.put(
        _build_url(path),
        json=payload or {},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def listar_causas() -> Dict[str, Any]:
    return _get("/causas")


def buscar_causas(q: str) -> Dict[str, Any]:
    return _get("/causas/buscar", params={"q": q})


def obtener_causa(id_causa: str) -> Dict[str, Any]:
    return _get(f"/causas/{id_causa}")


def crear_causa(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _post("/causas", payload)


def actualizar_causa(id_causa: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _put(f"/causas/{id_causa}", payload)


def agregar_contacto(id_causa: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _post(f"/causas/{id_causa}/contactos", payload)


def obtener_historial_causa(id_causa: str) -> Dict[str, Any]:
    return _get(f"/causas/{id_causa}/historial")


def obtener_resumen_causa(id_causa: str) -> Dict[str, Any]:
    return _get(f"/causas/{id_causa}/resumen")


def generar_resumen_causa(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _post("/causas/resumen", payload)


def sugerir_email_seguimiento(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _post("/causas/sugerir-email", payload)


def sugerir_whatsapp_seguimiento(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _post("/causas/sugerir-whatsapp", payload)
