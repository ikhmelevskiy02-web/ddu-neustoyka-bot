"""
Общие обработчики: /cancel и глобальный перехват необработанных исключений.

Важно для прод-режима: без этого одно необработанное исключение в хендлере
может либо уронить polling, либо оставить пользователя в "подвисшем" FSM-
состоянии без какой-либо обратной связи.
"""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent, Message

logger = logging.getLogger(__name__)

router = Router(name="common")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Сейчас нечего отменять. Наберите /calc, чтобы начать расчёт.")
        return
    await state.clear()
    await message.answer("Расчёт отменён. Наберите /calc, чтобы начать заново.")


@router.error()
async def handle_error(event: ErrorEvent) -> bool:
    """
    Ловит любое необработанное исключение в хендлерах, логирует его и не даёт
    боту упасть целиком. Пользователю уходит нейтральное сообщение об ошибке.

    ВАЖНО: намеренно НЕ пытается угадать/подставить какие-либо числа при сбое —
    при ошибке пользователь просто начинает заново через /calc, а не получает
    частично посчитанный результат.
    """
    logger.exception(
        "Необработанная ошибка при обработке апдейта %s",
        event.update.update_id,
        exc_info=event.exception,
    )

    update = event.update
    chat = None
    if update.message:
        chat = update.message.chat
    elif update.callback_query and update.callback_query.message:
        chat = update.callback_query.message.chat

    if chat is not None:
        try:
            await event.update.bot.send_message(
                chat.id,
                "⚠️ Что-то пошло не так при обработке запроса. Попробуйте начать заново "
                "командой /calc. Если ошибка повторяется — это повод сообщить разработчику.",
            )
        except Exception:  # noqa: BLE001 — не хотим падать ещё раз при отправке об ошибке
            logger.exception("Не удалось отправить сообщение об ошибке пользователю")

    return True
