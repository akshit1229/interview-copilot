"""
Application configuration loaded from environment variables.
Uses pydantic-settings for validation and .env file support.
"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Central configuration for the ParakeetAI Clone backend."""

    # ── Groq API ──────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_LLM_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_ASR_MODEL: str = "distil-whisper-large-v3-en"

    # ── Context Documents ─────────────────────────────────────
    CONTEXT_DIR: str = str(Path(__file__).parent.parent / "context_docs")

    # ── Conversation History ──────────────────────────────────
    MAX_HISTORY_TURNS: int = 20

    # ── Server ────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "*"

    # ── Audio / Question Detection ────────────────────────────
    # Minimum word count in an utterance to trigger LLM answer
    MIN_WORDS_FOR_ANSWER: int = 3
    # Whether to auto-answer every utterance or only detected questions
    AUTO_ANSWER_ALL: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton instance
settings = Settings()
