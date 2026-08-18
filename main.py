import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import common as common_handlers
from bot.handlers import start as start_handlers
from bot.handlers.calculator import setup_calculator_router
from config import load_settings
from llm.groq_client import GroqClient


async def main() -> None:
    settings = load_settings()
    logging.basicConfig(level=settings.log_level)
    logger = logging.getLogger(__name__)

    groq_client = None
    if settings.groq_api_key:
        groq_client = GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)
        logger.info("Groq включён, модель: %s", settings.groq_model)
    else:
        logger.warning(
            "GROQ_API_KEY не задан — бот будет работать только в пошаговом режиме, "
            "без распознавания свободного текста и без LLM-объяснений."
        )

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common_handlers.router)
    dp.include_router(start_handlers.router)
    dp.include_router(
        setup_calculator_router(
            groq_client=groq_client,
            use_llm_extraction=settings.use_llm_extraction,
            use_llm_explanation=settings.use_llm_explanation,
        )
    )

    logger.info("Бот запущен, начинаю polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
