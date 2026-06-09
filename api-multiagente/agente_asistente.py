from typing import List, Tuple
import os

import ollama

from core_rag import get_operativa_config, responder_con_rag

OPERATIVA_SYSTEM_PROMPT = (
    "Eres la asistente operativa personal del usuario. Respondes siempre en español, "
    "con tono claro, ejecutivo, práctico y profesional. "
    "Tu función es ayudar con organización, redacción, síntesis de información, "
    "correos, mensajes, agenda, próximos pasos, resúmenes y apoyo administrativo general. "
    "Cuando exista CONTEXTO recuperado, debes priorizarlo y basarte en él. "
    "Si no hay contexto documental útil, puedes responder de forma general y práctica "
    "como asistente operativa, sin inventar datos concretos del usuario, fechas, nombres, "
    "compromisos ni instrucciones específicas no proporcionadas. "
    "Si la consulta pertenece principalmente al dominio forense o al dominio contable/honorarios, "
    "indícalo brevemente. "
    "No uses Markdown. No uses títulos. No uses negritas. No uses viñetas salvo que el usuario las pida. "
    "No agregues introducciones, conclusiones ni aclaraciones innecesarias. "
    "Si el usuario pide redactar un correo, mensaje, nota o texto breve, entrega directamente "
    "el texto final listo para copiar y pegar. "
    "Si faltan datos, usa placeholders simples entre corchetes, por ejemplo [nombre], [fecha], [hora]."
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
ollama_client = ollama.Client(host=OLLAMA_BASE_URL)


def _parece_sin_contexto(respuesta: str, fuentes: List[str]) -> bool:
    if fuentes:
        return False

    texto = (respuesta or "").strip().lower()

    marcadores = [
        "no se encontró información relevante",
        "no se encontro informacion relevante",
        "no hay información relevante",
        "no hay informacion relevante",
        "la información es insuficiente",
        "la informacion es insuficiente",
        "revisa si el tema está cargado",
        "revisa si el tema esta cargado",
        "no se encontró contexto",
        "no se encontro contexto",
        "no encontré contexto",
        "no encontre contexto",
        "documentos_operativa",
        "base documentos_operativa",
    ]
    return any(m in texto for m in marcadores)


def _es_pedido_redaccion(consulta: str) -> bool:
    q = consulta.lower()
    claves = [
        "redacta", "redactame", "redactar", "escribi", "escribime", "escribir",
        "mail", "correo", "email", "mensaje", "nota", "whatsapp", "texto",
        "borrador", "modelo", "plantilla",
    ]
    return any(k in q for k in claves)


def _respuesta_operativa_general(consulta: str) -> Tuple[str, List[str]]:
    cfg = get_operativa_config(OPERATIVA_SYSTEM_PROMPT)

    if _es_pedido_redaccion(consulta):
        instruccion_formato = (
            "Entrega solo el texto final, limpio y listo para usar. "
            "No uses Markdown. No pongas títulos. No agregues explicaciones. "
            "No agregues 'Asunto:' salvo que sea necesario."
        )
    else:
        instruccion_formato = (
            "Responde en texto plano, breve, claro y accionable. "
            "No uses Markdown ni títulos."
        )

    prompt_usuario = (
        f"CONSULTA DEL USUARIO:\n{consulta}\n\n"
        f"{instruccion_formato}\n"
        "No afirmes contar con antecedentes, documentos o datos internos "
        "que no fueron proporcionados en la consulta."
    )

    respuesta = ollama_client.chat(
        model=cfg.model,
        options={
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "num_ctx": cfg.num_ctx,
            "num_predict": 220,
        },
        messages=[
            {"role": "system", "content": OPERATIVA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_usuario},
        ],
    )

    contenido = respuesta["message"]["content"].strip()
    return contenido, []


def agente_asistente(consulta: str, n_resultados: int = 4) -> Tuple[str, List[str]]:
    cfg = get_operativa_config(OPERATIVA_SYSTEM_PROMPT)

    respuesta, fuentes = responder_con_rag(
        consulta=consulta,
        cfg=cfg,
        n_resultados=n_resultados,
    )

    if _parece_sin_contexto(respuesta, fuentes):
        return _respuesta_operativa_general(consulta)

    return respuesta, fuentes