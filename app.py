import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import load_settings
from bot.database import Database
from bot.handlers import register_handlers
from bot.ollama_client import OllamaClient


async def main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    db = Database(settings.sqlite_path)
    await db.init()

    ollama_client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )

    register_handlers(dp, bot, db, ollama_client, settings)

    try:
        await dp.start_polling(bot)
    finally:
        await ollama_client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
