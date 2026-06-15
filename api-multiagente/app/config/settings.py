import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.BASE_DIR = Path(__file__).resolve().parents[2]
        self.DATA_DIR = self.BASE_DIR / "data"

        self.APP_NAME = os.getenv("APP_NAME", "api-multiagente")
        self.APP_HOST = os.getenv("API_HOST", "0.0.0.0")
        self.APP_PORT = int(os.getenv("API_PORT", "9000"))
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"

        self.OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
        self.CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
        self.OPENCLAW_CAUSAS_URL = os.getenv(
            "OPENCLAW_CAUSAS_URL",
            "http://openclaw-causas:9100",
        )

        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "dummy-key")
        self.DEFAULT_CHAT_MODEL = os.getenv("DEFAULT_CHAT_MODEL", "multiagente-local")

        self.ROUTING_MIN_SCORE = float(os.getenv("ROUTING_MIN_SCORE", "0.35"))
        self.ROUTING_MIN_DIFF = float(os.getenv("ROUTING_MIN_DIFF", "0.03"))
        self.DEFAULT_N_RESULTADOS = int(os.getenv("DEFAULT_N_RESULTADOS", "4"))

        self.MEMORIA_FILE = self.DATA_DIR / "memoria.json"


settings = Settings()