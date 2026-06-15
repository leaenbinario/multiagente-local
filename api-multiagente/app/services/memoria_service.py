import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

from app.config.settings import settings

DATA_DIR = settings.DATA_DIR
MEMORIA_FILE = settings.MEMORIA_FILE


def _asegurar_archivo_memoria() -> None:
    """Crea la carpeta y el archivo de memoria si no existen."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not MEMORIA_FILE.exists():
        MEMORIA_FILE.write_text("[]", encoding="utf-8")


def _leer_memoria() -> List[Dict[str, Any]]:
    """Lee el archivo de memoria y devuelve una lista de items."""
    _asegurar_archivo_memoria()

    try:
        contenido = MEMORIA_FILE.read_text(encoding="utf-8")
        data = json.loads(contenido)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        # Si el archivo está corrupto o no se puede leer, volvemos a lista vacía
        return []


def _escribir_memoria(items: List[Dict[str, Any]]) -> None:
    """Escribe la lista completa de items en el archivo de memoria."""
    _asegurar_archivo_memoria()
    MEMORIA_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def guardar_memoria(clave: str, contenido: str) -> Dict[str, Any]:
    """
    Guarda un nuevo recuerdo en memoria.

    - clave: etiqueta o título del recuerdo
    - contenido: texto asociado a esa clave
    """
    clave_limpia = str(clave or "").strip()
    contenido_limpio = str(contenido or "").strip()

    ahora = datetime.utcnow().isoformat()

    item = {
        "id": f"{clave_limpia}:{int(datetime.utcnow().timestamp())}",
        "clave": clave_limpia,
        "contenido": contenido_limpio,
        "created_at": ahora,
    }

    items = _leer_memoria()
    items.append(item)
    _escribir_memoria(items)

    return item


def buscar_items_memoria(texto: str) -> List[Dict[str, Any]]:
    """
    Devuelve la lista de items cuyo texto coincida (substring case-insensitive)
    con la consulta, ya sea en la clave o en el contenido.
    """
    consulta = str(texto or "").strip().lower()

    if not consulta:
        return []

    items = _leer_memoria()

    return [
        item
        for item in items
        if consulta in str(item.get("clave", "")).lower()
        or consulta in str(item.get("contenido", "")).lower()
    ]


def formatear_resultados_memoria(resultados: List[Dict[str, Any]]) -> str:
    """
    Convierte la lista de resultados en un texto legible para el usuario.
    Pensado para que el agente pueda devolverlo como respuesta directa.
    """
    if not resultados:
        return "No encontré recuerdos guardados para esa consulta."

    lineas = ["Memoria encontrada:"]
    for item in resultados:
        clave = str(item.get("clave", "")).strip()
        contenido = str(item.get("contenido", "")).strip()
        lineas.append(f"- {clave}: {contenido}")

    return "\n".join(lineas)


def construir_fuentes_memoria(resultados: List[Dict[str, Any]]) -> List[str]:
    """
    A partir de los resultados, construye una lista de fuentes tipo 'memoria:clave'
    para que el agente pueda mostrarlas como referencias.
    """
    fuentes = []

    for item in resultados:
        clave = str(item.get("clave", "")).strip()
        if clave:
            fuentes.append(f"memoria:{clave}")

    return fuentes


def buscar_memoria(texto: str) -> Tuple[str, List[str]]:
    """
    API principal de búsqueda de memoria para el resto de la app.

    - Recibe un texto de consulta.
    - Devuelve (respuesta_en_texto, lista_de_fuentes).

    Esto es lo que debería usar el orquestador o el agente de memoria.
    """
    resultados = buscar_items_memoria(texto)
    respuesta = formatear_resultados_memoria(resultados)
    fuentes = construir_fuentes_memoria(resultados)
    return respuesta, fuentes