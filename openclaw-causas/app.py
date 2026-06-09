from pathlib import Path
from typing import Optional, Dict, Any
import json
import re
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import uvicorn

BASE_CAUSAS_DIR = Path("/data/causas")

app = FastAPI(title="OpenClaw Causas", version="0.3.2")


class ContactoCausa(BaseModel):
    fecha: str
    canal: str
    asunto: Optional[str] = None
    nota: str
    resultado: Optional[str] = None


class FichaCausaBase(BaseModel):
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
    proximos_pasos: list[str] = Field(default_factory=list)
    notas: list[str] = Field(default_factory=list)
    contactos: list[ContactoCausa] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class FichaCausa(FichaCausaBase):
    id_causa: str


class FichaCausaCreate(FichaCausaBase):
    id_causa: str


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
    proximos_pasos: Optional[list[str]] = None
    notas: Optional[list[str]] = None
    tags: Optional[list[str]] = None


class ContactoCreateRequest(BaseModel):
    fecha: Optional[str] = None
    canal: str
    asunto: Optional[str] = None
    nota: str
    resultado: Optional[str] = None


class EmailSuggestionRequest(BaseModel):
    id_causa: str
    motivo: Optional[str] = "seguimiento"
    tono: Optional[str] = "profesional_cercano"


class WhatsAppSuggestionRequest(BaseModel):
    id_causa: str
    motivo: Optional[str] = "seguimiento"
    tono: Optional[str] = "profesional_cercano"


class ToolResponse(BaseModel):
    agent: str = "openclaw-causas"
    status: str = "ok"
    mode: str = "tool"
    answer: str
    sources: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validar_id_causa(id_causa: str) -> str:
    limpio = id_causa.strip()
    if not limpio:
        raise HTTPException(status_code=400, detail="id_causa vacío")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", limpio):
        raise HTTPException(
            status_code=400,
            detail="id_causa solo puede contener letras, números, guiones y guiones bajos",
        )
    return limpio


def limpiar_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return email
    return email.strip().lower()


def limpiar_whatsapp(whatsapp: Optional[str]) -> Optional[str]:
    if not whatsapp:
        return whatsapp
    whatsapp = whatsapp.strip()
    whatsapp = whatsapp.replace("(", "").replace(")", "")
    whatsapp = whatsapp.replace("–", "-").replace("—", "-")
    whatsapp = re.sub(r"\s+", " ", whatsapp)
    return whatsapp


def normalizar_canal(canal: str) -> str:
    c = (canal or "").strip().lower()
    if c in {"correo"}:
        return "email"
    if c in {"teléfono", "telefono"}:
        return "telefono"
    return c or "email"


def normalizar_motivo(motivo: Optional[str]) -> str:
    m = (motivo or "").strip().lower()
    if not m:
        return "seguimiento"
    if m in {"seguimiento", "recordatorio", "consulta"}:
        return m
    return "seguimiento"


def normalizar_tono(tono: Optional[str]) -> str:
    t = (tono or "").strip().lower()
    if not t:
        return "profesional_cercano"
    if t in {"profesional_cercano", "formal"}:
        return t
    return "profesional_cercano"


def normalizar_ficha_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    normalizado = dict(data)

    if "abogado_email" in normalizado:
        normalizado["abogado_email"] = limpiar_email(normalizado.get("abogado_email"))

    if "abogado_whatsapp" in normalizado:
        normalizado["abogado_whatsapp"] = limpiar_whatsapp(normalizado.get("abogado_whatsapp"))

    if "abogado_nombre" in normalizado and isinstance(normalizado["abogado_nombre"], str):
        normalizado["abogado_nombre"] = normalizado["abogado_nombre"].strip()

    if "caratula" in normalizado and isinstance(normalizado["caratula"], str):
        normalizado["caratula"] = normalizado["caratula"].strip()

    if "cliente" in normalizado and isinstance(normalizado["cliente"], str):
        normalizado["cliente"] = normalizado["cliente"].strip()

    if "estado_actual" in normalizado and isinstance(normalizado["estado_actual"], str):
        normalizado["estado_actual"] = normalizado["estado_actual"].strip()

    return normalizado


def ruta_causa_dir(id_causa: str) -> Path:
    return BASE_CAUSAS_DIR / validar_id_causa(id_causa)


def ruta_ficha(id_causa: str) -> Path:
    return ruta_causa_dir(id_causa) / "ficha.json"


def ruta_historial(id_causa: str) -> Path:
    return ruta_causa_dir(id_causa) / "historial.json"


def asegurar_directorio_causa(id_causa: str) -> Path:
    path = ruta_causa_dir(id_causa)
    path.mkdir(parents=True, exist_ok=True)
    return path


def cargar_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def guardar_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cargar_ficha(id_causa: str) -> FichaCausa:
    id_causa = validar_id_causa(id_causa)
    path = ruta_ficha(id_causa)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No existe ficha para la causa {id_causa}")
    data = cargar_json(path, {})
    data = normalizar_ficha_dict(data)
    return FichaCausa(**data)


def guardar_ficha(ficha: FichaCausa):
    data = normalizar_ficha_dict(ficha.model_dump())
    guardar_json(ruta_ficha(ficha.id_causa), data)


def registrar_evento(id_causa: str, action: str, detail: Optional[Dict[str, Any]] = None):
    id_causa = validar_id_causa(id_causa)
    asegurar_directorio_causa(id_causa)
    historial = cargar_json(ruta_historial(id_causa), [])
    historial.append(
        {
            "timestamp": now_iso(),
            "action": action,
            "detail": detail or {},
        }
    )
    guardar_json(ruta_historial(id_causa), historial)


def responder_tool(
    answer: str,
    action: str,
    id_causa: Optional[str] = None,
    sources: Optional[list[str]] = None,
    extra_meta: Optional[Dict[str, Any]] = None,
) -> ToolResponse:
    meta = {"action": action, "timestamp": now_iso()}
    if id_causa:
        meta["id_causa"] = id_causa
    if extra_meta:
        meta.update(extra_meta)

    return ToolResponse(
        answer=answer,
        sources=sources or [],
        meta=meta,
    )


def construir_resumen_texto(ficha: FichaCausa) -> str:
    partes = [
        f"Carátula: {ficha.caratula}.",
        f"Fuero: {ficha.fuero or 'No informado'}.",
        f"Juzgado: {ficha.juzgado or 'No informado'}.",
        f"Abogado: {ficha.abogado_nombre or 'No informado'}.",
        f"Email abogado: {ficha.abogado_email or 'No informado'}.",
        f"WhatsApp abogado: {ficha.abogado_whatsapp or 'No informado'}.",
        f"Último contacto: {ficha.fecha_ultimo_contacto or 'No informado'}.",
        f"Estado actual: {ficha.estado_actual or 'Pendiente de análisis'}.",
    ]

    if ficha.proximos_pasos:
        partes.append("Próximos pasos sugeridos: " + "; ".join(ficha.proximos_pasos) + ".")

    if ficha.notas:
        partes.append("Notas relevantes: " + "; ".join(ficha.notas[:3]) + ".")

    return " ".join(partes)


def construir_borrador_email(ficha: FichaCausa, motivo: str, tono: str) -> str:
    abogado = ficha.abogado_nombre or "Doctor/a"
    caratula = ficha.caratula
    estado = ficha.estado_actual or "sin actualización registrada reciente"
    ultimo_contacto = ficha.fecha_ultimo_contacto or "sin fecha registrada"

    if motivo == "seguimiento":
        return f"""Asunto: Consulta sobre estado de la causa {caratula}

Estimado/a {abogado}:

Espero que se encuentre bien. Le escribo para consultar si hubo novedades en la causa "{caratula}", ya que mi último registro indica {estado} y el último contacto registrado fue {ultimo_contacto}.

Quedo a disposición por si consideran útil alguna ampliación, aclaración o nueva intervención de mi parte.

Aprovecho también para quedar disponible para futuras causas o colaboraciones periciales en las que pueda asistirlos.

Saludos cordiales,"""

    return f"""Asunto: Contacto sobre la causa {caratula}

Estimado/a {abogado}:

Espero que se encuentre bien. Le escribo en relación con la causa "{caratula}" para retomar contacto y consultar si consideran útil alguna gestión, ampliación o intervención adicional de mi parte.

Según mi registro actual, el estado informado es: {estado}. El último contacto asentado fue {ultimo_contacto}.

Quedo a disposición para colaborar en esta u otras causas en las que pueda resultar de utilidad.

Saludos cordiales,"""


def construir_borrador_whatsapp(ficha: FichaCausa, motivo: str, tono: str) -> str:
    abogado = ficha.abogado_nombre or "Doctor/a"
    caratula = ficha.caratula
    estado = ficha.estado_actual or "sin actualización registrada reciente"
    ultimo_contacto = ficha.fecha_ultimo_contacto or "sin fecha registrada"

    if motivo == "seguimiento":
        return (
            f'Hola {abogado}, ¿cómo estás? Te escribo por la causa "{caratula}". '
            f"Quería consultarte si hubo alguna novedad. En mi registro figura estado: {estado}, "
            f"y último contacto: {ultimo_contacto}. Quedo a disposición para cualquier ampliación o intervención que necesiten."
        )

    return (
        f'Hola {abogado}, te escribo en relación con la causa "{caratula}" para retomar contacto. '
        f"Según mi registro actual, el estado informado es: {estado}. "
        f"Si les resulta útil, quedo a disposición para colaborar en esta u otras causas."
    )


@app.get("/")
def health():
    return {
        "status": "ok",
        "service": "openclaw-causas",
        "version": "0.3.2",
    }


@app.get("/causas")
def listar_causas():
    if not BASE_CAUSAS_DIR.exists():
        return {"status": "ok", "data": []}

    causas = []
    for carpeta in sorted(BASE_CAUSAS_DIR.iterdir()):
        if not carpeta.is_dir():
            continue

        ficha_path = carpeta / "ficha.json"
        if not ficha_path.exists():
            continue

        try:
            data = normalizar_ficha_dict(cargar_json(ficha_path, {}))
            causas.append(
                {
                    "id_causa": carpeta.name,
                    "caratula": data.get("caratula"),
                    "estado": data.get("estado_actual"),
                    "abogado": data.get("abogado_nombre"),
                    "abogado_email": data.get("abogado_email"),
                    "abogado_whatsapp": data.get("abogado_whatsapp"),
                    "cliente": data.get("cliente"),
                    "ultimo_contacto": data.get("fecha_ultimo_contacto"),
                    "contactos_count": len(data.get("contactos", [])),
                    "tags": data.get("tags", []),
                }
            )
        except Exception:
            continue

    return {"status": "ok", "data": causas}


@app.get("/causas/buscar")
def buscar_causas(
    q: Optional[str] = Query(default=None),
    abogado: Optional[str] = Query(default=None),
    cliente: Optional[str] = Query(default=None),
    estado: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
):
    if not BASE_CAUSAS_DIR.exists():
        return {"status": "ok", "data": []}

    resultados = []
    for carpeta in sorted(BASE_CAUSAS_DIR.iterdir()):
        ficha_path = carpeta / "ficha.json"
        if not carpeta.is_dir() or not ficha_path.exists():
            continue

        try:
            data = normalizar_ficha_dict(cargar_json(ficha_path, {}))
        except Exception:
            continue

        texto_busqueda = " ".join(
            [
                str(carpeta.name),
                str(data.get("caratula", "")),
                str(data.get("abogado_nombre", "")),
                str(data.get("abogado_email", "")),
                str(data.get("abogado_whatsapp", "")),
                str(data.get("cliente", "")),
                str(data.get("estado_actual", "")),
                " ".join(data.get("tags", [])),
            ]
        ).lower()

        if q and q.lower() not in texto_busqueda:
            continue
        if abogado and abogado.lower() not in str(data.get("abogado_nombre", "")).lower():
            continue
        if cliente and cliente.lower() not in str(data.get("cliente", "")).lower():
            continue
        if estado and estado.lower() not in str(data.get("estado_actual", "")).lower():
            continue
        if tag and tag.lower() not in [t.lower() for t in data.get("tags", [])]:
            continue

        resultados.append(
            {
                "id_causa": carpeta.name,
                "caratula": data.get("caratula"),
                "estado": data.get("estado_actual"),
                "abogado": data.get("abogado_nombre"),
                "abogado_email": data.get("abogado_email"),
                "abogado_whatsapp": data.get("abogado_whatsapp"),
                "cliente": data.get("cliente"),
                "ultimo_contacto": data.get("fecha_ultimo_contacto"),
                "contactos_count": len(data.get("contactos", [])),
                "tags": data.get("tags", []),
            }
        )

    return {"status": "ok", "data": resultados}


@app.get("/causas/{id_causa}")
def obtener_causa(id_causa: str):
    ficha = cargar_ficha(id_causa)
    return ficha.model_dump()


@app.post("/causas", response_model=ToolResponse)
def crear_causa(req: FichaCausaCreate):
    id_causa = validar_id_causa(req.id_causa)
    path = ruta_ficha(id_causa)

    if path.exists():
        raise HTTPException(status_code=409, detail=f"La causa {id_causa} ya existe")

    payload = normalizar_ficha_dict(req.model_dump())
    ficha = FichaCausa(**payload)
    guardar_ficha(ficha)
    registrar_evento(
        id_causa,
        "crear_causa",
        {
            "caratula": ficha.caratula,
            "abogado_email": ficha.abogado_email,
            "abogado_whatsapp": ficha.abogado_whatsapp,
        },
    )

    return responder_tool(
        answer=f"Se creó la causa {id_causa} con carátula '{ficha.caratula}'.",
        action="crear_causa",
        id_causa=id_causa,
        sources=[str(path)],
    )


@app.put("/causas/{id_causa}", response_model=ToolResponse)
def actualizar_causa(id_causa: str, req: FichaCausaUpdate):
    id_causa = validar_id_causa(id_causa)
    ficha = cargar_ficha(id_causa)
    cambios = req.model_dump(exclude_unset=True)

    if not cambios:
        raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")

    cambios = normalizar_ficha_dict(cambios)

    for campo, valor in cambios.items():
        setattr(ficha, campo, valor)

    guardar_ficha(ficha)
    registrar_evento(id_causa, "actualizar_causa", {"campos": list(cambios.keys())})

    return responder_tool(
        answer=f"Se actualizó la causa {id_causa}. Campos modificados: {', '.join(cambios.keys())}.",
        action="actualizar_causa",
        id_causa=id_causa,
        sources=[str(ruta_ficha(id_causa))],
        extra_meta={"campos_actualizados": list(cambios.keys())},
    )


@app.post("/causas/{id_causa}/contactos", response_model=ToolResponse)
def registrar_contacto(id_causa: str, req: ContactoCreateRequest):
    id_causa = validar_id_causa(id_causa)
    ficha = cargar_ficha(id_causa)

    nota = req.nota.strip()
    if not nota:
        raise HTTPException(status_code=400, detail="La nota del contacto no puede estar vacía")

    contacto = ContactoCausa(
        fecha=req.fecha or now_iso(),
        canal=normalizar_canal(req.canal),
        asunto=req.asunto.strip() if isinstance(req.asunto, str) else req.asunto,
        nota=nota,
        resultado=req.resultado.strip() if isinstance(req.resultado, str) else req.resultado,
    )

    ficha.contactos.append(contacto)
    ficha.fecha_ultimo_contacto = contacto.fecha

    if contacto.resultado:
        ficha.notas.append(f"Contacto por {contacto.canal}: {contacto.resultado}")

    guardar_ficha(ficha)
    registrar_evento(
        id_causa,
        "registrar_contacto",
        {
            "canal": contacto.canal,
            "fecha": contacto.fecha,
            "asunto": contacto.asunto,
        },
    )

    return responder_tool(
        answer=f"Se registró un contacto en la causa {id_causa} por canal '{contacto.canal}' con fecha {contacto.fecha}.",
        action="registrar_contacto",
        id_causa=id_causa,
        sources=[str(ruta_ficha(id_causa))],
        extra_meta={"canal": contacto.canal, "fecha": contacto.fecha},
    )


@app.get("/causas/{id_causa}/historial")
def obtener_historial(id_causa: str):
    id_causa = validar_id_causa(id_causa)
    _ = cargar_ficha(id_causa)
    historial = cargar_json(ruta_historial(id_causa), [])
    return {"status": "ok", "id_causa": id_causa, "data": historial}


@app.get("/causas/{id_causa}/resumen", response_model=ToolResponse)
def resumen_causa(id_causa: str):
    id_causa = validar_id_causa(id_causa)
    ficha = cargar_ficha(id_causa)
    return responder_tool(
        answer=construir_resumen_texto(ficha),
        action="resumen_causa",
        id_causa=id_causa,
        sources=[str(ruta_ficha(id_causa))],
    )


@app.post("/causas/sugerir-email", response_model=ToolResponse)
def sugerir_email(req: EmailSuggestionRequest):
    id_causa = validar_id_causa(req.id_causa)
    ficha = cargar_ficha(id_causa)
    motivo = normalizar_motivo(req.motivo)
    tono = normalizar_tono(req.tono)

    return responder_tool(
        answer=construir_borrador_email(ficha, motivo, tono),
        action="sugerir_email",
        id_causa=id_causa,
        sources=[str(ruta_ficha(id_causa))],
        extra_meta={"motivo": motivo, "tono": tono},
    )


@app.post("/causas/sugerir-whatsapp", response_model=ToolResponse)
def sugerir_whatsapp(req: WhatsAppSuggestionRequest):
    id_causa = validar_id_causa(req.id_causa)
    ficha = cargar_ficha(id_causa)
    motivo = normalizar_motivo(req.motivo)
    tono = normalizar_tono(req.tono)

    return responder_tool(
        answer=construir_borrador_whatsapp(ficha, motivo, tono),
        action="sugerir_whatsapp",
        id_causa=id_causa,
        sources=[str(ruta_ficha(id_causa))],
        extra_meta={"motivo": motivo, "tono": tono},
    )


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=9100, reload=False)