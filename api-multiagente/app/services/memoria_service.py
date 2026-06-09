import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
MEMORIA_FILE = DATA_DIR / "memoria.json"


def _asegurar_archivo():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not MEMORIA_FILE.exists():
        MEMORIA_FILE.write_text("[]", encoding="utf-8")


def guardar_memoria(clave: str, contenido: str):
    _asegurar_archivo()
    data = json.loads(MEMORIA_FILE.read_text(encoding="utf-8"))
    item = {"clave": clave, "contenido": contenido}
    data.append(item)
    MEMORIA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return item


def buscar_memoria(texto: str):
    _asegurar_archivo()
    data = json.loads(MEMORIA_FILE.read_text(encoding="utf-8"))
    texto = (texto or "").lower()

    resultados = [
        item for item in data
        if texto in item.get("clave", "").lower()
        or texto in item.get("contenido", "").lower()
    ]
    return resultados
