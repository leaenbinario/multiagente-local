from typing import Any, Dict, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.causas_service import (
    actualizar_causa,
    agregar_contacto,
    buscar_causas,
    crear_causa,
    generar_resumen_causa,
    listar_causas,
    obtener_causa,
    obtener_historial_causa,
    obtener_resumen_causa,
    sugerir_email_seguimiento,
    sugerir_whatsapp_seguimiento,
)

router = APIRouter(tags=["causas"])


class CausaPayload(BaseModel):
    data: Dict[str, Any]


class ContactoPayload(BaseModel):
    data: Dict[str, Any]


class ResumenPayload(BaseModel):
    data: Dict[str, Any]


class SugerenciaPayload(BaseModel):
    data: Dict[str, Any]


@router.get("/causas")
def causas_listar():
    return listar_causas()


@router.get("/causas/buscar")
def causas_buscar(q: str = Query(..., min_length=1)):
    return buscar_causas(q)


@router.get("/causas/{id_causa}")
def causas_obtener(id_causa: str):
    return obtener_causa(id_causa)


@router.post("/causas")
def causas_crear(payload: CausaPayload):
    return crear_causa(payload.data)


@router.put("/causas/{id_causa}")
def causas_actualizar(id_causa: str, payload: CausaPayload):
    return actualizar_causa(id_causa, payload.data)


@router.post("/causas/{id_causa}/contactos")
def causas_agregar_contacto(id_causa: str, payload: ContactoPayload):
    return agregar_contacto(id_causa, payload.data)


@router.get("/causas/{id_causa}/historial")
def causas_historial(id_causa: str):
    return obtener_historial_causa(id_causa)


@router.get("/causas/{id_causa}/resumen")
def causas_resumen(id_causa: str):
    return obtener_resumen_causa(id_causa)


@router.post("/causas/resumen")
def causas_generar_resumen(payload: ResumenPayload):
    return generar_resumen_causa(payload.data)


@router.post("/causas/sugerir-email")
def causas_sugerir_email(payload: SugerenciaPayload):
    return sugerir_email_seguimiento(payload.data)


@router.post("/causas/sugerir-whatsapp")
def causas_sugerir_whatsapp(payload: SugerenciaPayload):
    return sugerir_whatsapp_seguimiento(payload.data)