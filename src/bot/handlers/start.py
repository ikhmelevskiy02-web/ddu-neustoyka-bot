from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.keyboards import main_menu_keyboard
from domain.rates import key_rate_table

router = Router(name="start")

WELCOME_TEXT = (
    "👋 Привет! Я помогу прикинуть неустойку по договору участия в долевом "
    "строительстве (214-ФЗ), если застройщик задержал передачу квартиры.\n\n"
    "Достаточно указать цену договора, плановую и фактическую дату передачи — "
    "остальное (мораторий 2024–2025 гг., ключевую ставку ЦБ) я учту сам.\n\n"
    "Можно просто описать ситуацию своими словами одним сообщением — я попробую "
    "понять детали сам.\n\n"
    "⚠️ Это справочный расчёт, не юридическая консультация."
)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(
        "Команды:\n"
        "/calc — начать расчёт неустойки\n"
        "/cancel — отменить текущий расчёт\n"
        "/rate — текущая ключевая ставка ЦБ РФ в базе бота\n"
        "/help — это сообщение"
    )


@router.message(Command("rate"))
async def handle_rate(message: Message) -> None:
    latest_date, latest_rate = key_rate_table.latest_known_rate
    await message.answer(
        f"Последняя ставка в базе бота: <b>{latest_rate:g}%</b> "
        f"(действует с {latest_date.strftime('%d.%m.%Y')}).\n"
        f"Таблица проверена по состоянию на {key_rate_table.last_verified or 'см. src/data/key_rates.json'}.\n"
        "Актуальное значение всегда можно свериться на "
        "<a href='https://www.cbr.ru/hd_base/keyrate/'>cbr.ru</a>."
    )
