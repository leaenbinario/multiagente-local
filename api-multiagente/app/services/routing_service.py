import unicodedata
from typing import Any, Dict, List

from app.agents.asistente import consultar_asistente
from app.agents.forense import consultar_forense
from app.agents.honorarios import consultar_honorarios
from app.agents.operativa import consultar_operativa
from app.services.memoria_service import buscar_memoria
from app.agents.causas import consultar_causas


def normalizar_texto(texto: str) -> str:
    """
    Pone el texto en minúsculas, sin tildes y sin espacios sobrantes.
    Esto ayuda a que las palabras clave se detecten de forma más robusta.
    """
    texto = (texto or "").lower().strip()
    texto = "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return texto


def enrutar_consulta(pregunta: str) -> str:
    """
    Decide a qué agente enviar la consulta:
    - memoria
    - forense
    - honorarios
    - operativa
    - asistente (por defecto)
    """
    texto = normalizar_texto(pregunta)

    claves_memoria: List[str] = [
        "memoria",
        "recorda",
        "recordas",
        "recordar",
        "recordarme",
        "recuerdo",
        "recuerdos",
        "recuerdas",
        "que recordas de mi",
        "que sabes de mi",
        "que sabes sobre mi",
        "que tenes guardado de mi",
        "que guardaste de mi",
        "mis preferencias",
        "mi perfil",
        "guardar preferencia",
        "guarda ",
        "guardaste",
    ]

    claves_forense: List[str] = [
        "forense",
        "evidencia",
        "evidencia digital",
        "cadena de custodia",
        "hash",
        "hashes",
        "imagen forense",
        "metadato",
        "metadatos",
        "pericia",
        "pericial",
        "informe pericial",
        "integridad",
        "autenticidad",
    ]

    claves_honorarios: List[str] = [
        "honorarios",
        "honorario",
        "tributario",
        "impuesto",
        "impuestos",
        "iva",
        "factura",
        "facturacion",
        "liquidacion",
        "anticipo",
        "regulacion",
    ]

    claves_operativa: List[str] = [
        "mail",
        "email",
        "correo",
        "redacta",
        "redactame",
        "redactar",
        "escrito",
        "nota",
        "nota al juzgado",
        "prorroga",
        "seguimiento",
        "expediente",
        "borrador",
        "mensaje",
        "whatsapp",
    ]
    
    claves_causas = [
        "causa ",
        "causas",
        "expediente",
        "expedientes",
        "historial de la causa",
        "historial del expediente",
    ]

    if any(k in texto for k in claves_memoria):
        return "memoria"

    if any(k in texto for k in claves_forense):
        return "forense"

    if any(k in texto for k in claves_honorarios):
        return "honorarios"

    if any(k in texto for k in claves_causas):
        return "causas"

    if any(k in texto for k in claves_operativa):
        return "operativa"   

    return "asistente"


def _normalizar_resultado(resultado: Any, destino: str) -> Dict[str, Any]:
    """
    Normaliza la salida de todos los agentes a un mismo formato:
    {
        "destino": "...",
        "respuesta": "texto",
        "fuentes": [...]
    }
    Admite:
    - dict con claves "respuesta" y "fuentes"
    - tuplas (respuesta, fuentes)
    - tuplas (algo, respuesta, fuentes)
    - cualquier otro tipo -> se convierte a texto con fuentes vacías
    """
    if isinstance(resultado, dict):
        return {
            "destino": destino,
            "respuesta": str(resultado.get("respuesta", "") or "").strip(),
            "fuentes": list(resultado.get("fuentes", []) or []),
        }

    if isinstance(resultado, tuple):
        if len(resultado) == 2:
            respuesta, fuentes = resultado
            return {
                "destino": destino,
                "respuesta": str(respuesta or "").strip(),
                "fuentes": list(fuentes or []),
            }

        if len(resultado) == 3:
            _, respuesta, fuentes = resultado
            return {
                "destino": destino,
                "respuesta": str(respuesta or "").strip(),
                "fuentes": list(fuentes or []),
            }

    return {
        "destino": destino,
        "respuesta": str(resultado or "").strip(),
        "fuentes": [],
    }


def procesar_consulta_enrutada(pregunta: str) -> Dict[str, Any]:
    """
    Punto de entrada principal para el orquestador interno:
    - Determina el destino con enrutar_consulta.
    - Llama al agente correspondiente.
    - Normaliza la salida.
    """
    destino = enrutar_consulta(pregunta)

    if destino == "memoria":
        # buscar_memoria devuelve (respuesta: str, fuentes: List[str])
        resultado = buscar_memoria(pregunta)
        return _normalizar_resultado(resultado, destino)

    if destino == "forense":
        resultado = consultar_forense(pregunta)
        return _normalizar_resultado(resultado, destino)

    if destino == "honorarios":
        resultado = consultar_honorarios(pregunta)
        return _normalizar_resultado(resultado, destino)

    if destino == "operativa":
        resultado = consultar_operativa(pregunta)
        return _normalizar_resultado(resultado, destino)

    if destino == "causas":
        resultado = consultar_causas(pregunta)
        return _normalizar_resultado(resultado, destino)

    # destino == "asistente" (por defecto)
    resultado = consultar_asistente(pregunta)
    return _normalizar_resultado(resultado, destino)