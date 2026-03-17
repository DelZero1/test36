from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    telegram_bot_token: str
    ollama_base_url: str
    ollama_model: str
    max_context_messages: int
    response_cooldown_seconds: int
    ollama_timeout_seconds: int
    sqlite_path: str
    max_response_chars: int
    log_level: str


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Environment variable {name} is required")
    return value


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        telegram_bot_token=_get_required_env("TELEGRAM_BOT_TOKEN"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        max_context_messages=int(os.getenv("MAX_CONTEXT_MESSAGES", "100")),
        response_cooldown_seconds=int(os.getenv("RESPONSE_COOLDOWN_SECONDS", "10")),
        ollama_timeout_seconds=int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45")),
        sqlite_path=os.getenv("SQLITE_PATH", "bot_memory.db"),
        max_response_chars=int(os.getenv("MAX_RESPONSE_CHARS", "2000")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
