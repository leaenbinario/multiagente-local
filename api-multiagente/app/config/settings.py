import os


class Settings:
    APP_NAME = "api-multiagente"
    APP_HOST = os.getenv("API_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("API_PORT", "9000"))

    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
    CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
    OPENCLAW_CAUSAS_URL = os.getenv("OPENCLAW_CAUSAS_URL", "http://openclaw-causas:9100")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "dummy-key")
    DEFAULT_CHAT_MODEL = os.getenv("DEFAULT_CHAT_MODEL", "multiagente-local")

    ROUTING_MIN_SCORE = float(os.getenv("ROUTING_MIN_SCORE", "0.35"))
    ROUTING_MIN_DIFF = float(os.getenv("ROUTING_MIN_DIFF", "0.03"))
    DEFAULT_N_RESULTADOS = int(os.getenv("DEFAULT_N_RESULTADOS", "4"))


settings = Settings()
