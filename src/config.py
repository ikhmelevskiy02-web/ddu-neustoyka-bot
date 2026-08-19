"""Загрузка конфигурации из переменных окружения (.env для локальной разработки)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    bot_token: str
    groq_api_key: str | None
    groq_model: str
    use_llm_extraction: bool
    use_llm_explanation: bool
    log_level: str


def load_settings() -> Settings:
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError(
            "Не задан BOT_TOKEN. Создайте .env на основе .env.example и укажите токен, "
            "выданный @BotFather."
        )

    return Settings(
        bot_token=bot_token,
        groq_api_key=os.environ.get("GROQ_API_KEY"),
        # openai/gpt-oss-120b — актуальная (2026) рекомендованная модель Groq для
        # рассуждений/структурированного вывода; llama-3.3-70b-versatile снята с
        # поддержки в июне 2026. Можно переопределить через .env.
        groq_model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        use_llm_extraction=_get_bool("USE_LLM_EXTRACTION", True),
        use_llm_explanation=_get_bool("USE_LLM_EXPLANATION", True),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
