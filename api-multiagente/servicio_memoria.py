from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
import json

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MEMORIA_PATH = DATA_DIR / "memoria_usuario.json"


def cargar_memoria() -> List[dict]:
    if not MEMORIA_PATH.exists():
        return []

    try:
        with open(MEMORIA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def guardar_memoria(data: List[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MEMORIA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def memoria_guardar_item(clave: str, valor: str, categoria: str = "general") -> None:
    data = cargar_memoria()
    data.append({"clave": clave, "valor": valor, "categoria": categoria})
    guardar_memoria(data)


def memoria_buscar_items(consulta: str) -> List[dict]:
    data = cargar_memoria()
    q = consulta.lower().strip()
    resultados = []

    for item in data:
        clave = str(item.get("clave", "")).lower()
        valor = str(item.get("valor", "")).lower()
        categoria = str(item.get("categoria", "")).lower()

        if q in clave or q in valor or q in categoria:
            resultados.append(item)

    return resultados


def formatear_recuerdos(recuerdos: List[dict]) -> str:
    return "Memoria encontrada:\n" + "\n".join(
        f"- {r['clave']}: {r['valor']}" for r in recuerdos
    )


def consultar_memoria(pregunta: str) -> Tuple[str, List[str]]:
    recuerdos = memoria_buscar_items(pregunta)
    if recuerdos:
        return formatear_recuerdos(recuerdos), []
    return "", []