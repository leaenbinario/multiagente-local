from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MEMORIA_PATH = DATA_DIR / "memoria_usuario.json"

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "9000"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")

CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

OPENCLAW_CAUSAS_URL = os.getenv("OPENCLAW_CAUSAS_URL", "http://openclaw-causas:9100")

ROUTING_MIN_SCORE = float(os.getenv("ROUTING_MIN_SCORE", "0.35"))
ROUTING_MIN_DIFF = float(os.getenv("ROUTING_MIN_DIFF", "0.03"))
DEFAULT_N_RESULTADOS = int(os.getenv("DEFAULT_N_RESULTADOS", "4"))

OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "multiagente-local")