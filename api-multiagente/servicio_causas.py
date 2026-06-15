from __future__ import annotations

from typing import Any, List, Optional, Tuple
from uuid import uuid4
import json
import os
import re

import requests
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

OPENCLAW_CAUSAS_URL = os.getenv("OPENCLAW_CAUSAS_URL", "http://openclaw-causas:9100")


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