"""
Диалог сбора параметров и расчёта неустойки.

Архитектурный принцип (см. docs/LEGAL_SPEC.md, раздел 1): Groq используется
только для (а) извлечения параметров из свободного текста и (б) финального
пересказа результата человеческим языком. Вся арифметика — в domain/*, без LLM.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.formatting import (
    DISCLAIMER,
    format_gosposhlina_result,
    format_neustoyka_result,
    format_shtraf_result,
)
from bot.keyboards import (
    PARTICIPANT_INDIVIDUAL,
    PARTICIPANT_LEGAL,
    SKIP_EXTRA_DAMAGES,
    START_CALC_CALLBACK,
    TRANSFERRED_NO,
    TRANSFERRED_YES,
    participant_type_keyboard,
    skip_keyboard,
    transferred_keyboard,
)
from bot.states import CalcStates
from bot.utils import parse_date_ru, parse_money_ru
from domain.calculator import calculate_neustoyka
from domain.gosposhlina import calculate_gosposhlina
from domain.models import NeustoykaInput, ParticipantType
from domain.shtraf import calculate_shtraf
from llm.explain import generate_explanation
from llm.extraction import extract_params, parse_iso_date

logger = logging.getLogger(__name__)

router = Router(name="calculator")


def setup_calculator_router(groq_client, use_llm_extraction: bool, use_llm_explanation: bool) -> Router:
    """
    Фабрика роутера — принимает уже созданный GroqClient (или None, если ключ
    не задан / интеграция отключена) и флаги использования LLM.
    """

    async def start_calc(entry_point: Message, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(CalcStates.describing)
        await entry_point.answer(
            "Опишите ситуацию одним сообщением (например: «цена договора 8 500 000, "
            "должны были передать 1 октября 2025, передали в марте 2026, я физлицо»)\n\n"
            "Либо просто отправьте цену договора в рублях, и я задам вопросы по шагам."
        )

    @router.message(Command("calc"))
    async def cmd_calc(message: Message, state: FSMContext) -> None:
        await start_calc(message, state)

    @router.callback_query(F.data == START_CALC_CALLBACK)
    async def cb_start_calc(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await start_calc(callback.message, state)

    @router.message(CalcStates.describing)
    async def handle_description(message: Message, state: FSMContext) -> None:
        text = message.text or ""
        extracted_anything = False

        if use_llm_extraction and groq_client is not None:
            extracted = extract_params(groq_client, text)
            if extracted:
                updates = {}
                if extracted.get("contract_price"):
                    updates["contract_price"] = float(extracted["contract_price"])
                    extracted_anything = True
                planned = parse_iso_date(extracted.get("planned_transfer_date"))
                if planned:
                    updates["planned_transfer_date"] = planned.isoformat()
                    extracted_anything = True
                actual = parse_iso_date(extracted.get("actual_transfer_date"))
                if actual:
                    updates["actual_transfer_date"] = actual.isoformat()
                    extracted_anything = True
                if extracted.get("object_not_transferred_yet") is True:
                    updates["actual_transfer_date"] = (date.today() + timedelta(days=1)).isoformat()
                    extracted_anything = True
                if extracted.get("participant_type") in ("individual", "legal_entity"):
                    updates["participant_type"] = extracted["participant_type"]
                    extracted_anything = True
                if extracted.get("claim_price_extra_damages"):
                    updates["extra_damages"] = float(extracted["claim_price_extra_damages"])
                if updates:
                    await state.update_data(**updates)

        if not extracted_anything:
            # Групк недоступен / ничего не извлёк — пробуем понять как цену вручную.
            price = parse_money_ru(text)
            if price:
                await state.update_data(contract_price=price)
            else:
                await message.answer(
                    "Не удалось распознать данные автоматически. Укажите цену договора "
                    "числом в рублях, например: 8500000"
                )
                return

        await _ask_next_or_calculate(message, state)

    @router.message(CalcStates.waiting_price)
    async def handle_price(message: Message, state: FSMContext) -> None:
        price = parse_money_ru(message.text or "")
        if not price:
            await message.answer("Не понял сумму. Введите число, например: 8500000 или 8.5 млн")
            return
        await state.update_data(contract_price=price)
        await _ask_next_or_calculate(message, state)

    @router.message(CalcStates.waiting_planned_date)
    async def handle_planned_date(message: Message, state: FSMContext) -> None:
        parsed = parse_date_ru(message.text or "")
        if not parsed:
            await message.answer("Не понял дату. Формат: 30.12.2025")
            return
        await state.update_data(planned_transfer_date=parsed.isoformat())
        await _ask_next_or_calculate(message, state)

    @router.callback_query(F.data.in_({TRANSFERRED_YES, TRANSFERRED_NO}))
    async def handle_transferred_choice(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        if callback.data == TRANSFERRED_NO:
            calc_date = date.today() + timedelta(days=1)
            await state.update_data(actual_transfer_date=calc_date.isoformat())
            await callback.message.answer(
                "Хорошо, посчитаю на сегодняшний день (сумма будет расти с каждым днём просрочки)."
            )
        else:
            await state.set_state(CalcStates.waiting_actual_date)
            await callback.message.answer("Укажите фактическую дату передачи по акту (например: 27.04.2026)")
            return
        await _ask_next_or_calculate(callback.message, state)

    @router.message(CalcStates.waiting_actual_date)
    async def handle_actual_date(message: Message, state: FSMContext) -> None:
        parsed = parse_date_ru(message.text or "")
        if not parsed:
            await message.answer("Не понял дату. Формат: 27.04.2026")
            return
        await state.update_data(actual_transfer_date=parsed.isoformat())
        await _ask_next_or_calculate(message, state)

    @router.callback_query(F.data.in_({PARTICIPANT_INDIVIDUAL, PARTICIPANT_LEGAL}))
    async def handle_participant_type(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        participant = (
            ParticipantType.INDIVIDUAL.value
            if callback.data == PARTICIPANT_INDIVIDUAL
            else ParticipantType.LEGAL_ENTITY.value
        )
        await state.update_data(participant_type=participant)
        await _ask_next_or_calculate(callback.message, state)

    @router.callback_query(F.data == SKIP_EXTRA_DAMAGES)
    async def handle_skip_extra(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await state.update_data(extra_damages=0.0)
        await _finalize(callback.message, state)

    @router.message(CalcStates.waiting_extra_damages)
    async def handle_extra_damages(message: Message, state: FSMContext) -> None:
        amount = parse_money_ru(message.text or "")
        await state.update_data(extra_damages=amount or 0.0)
        await _finalize(message, state)

    async def _ask_next_or_calculate(message: Message, state: FSMContext) -> None:
        data = await state.get_data()

        if "contract_price" not in data:
            await state.set_state(CalcStates.waiting_price)
            await message.answer("Укажите цену договора в рублях (например: 8500000)")
            return

        if "planned_transfer_date" not in data:
            await state.set_state(CalcStates.waiting_planned_date)
            await message.answer(
                "Какая дата передачи объекта предусмотрена договором? Формат: 30.12.2025"
            )
            return

        if "actual_transfer_date" not in data:
            await state.set_state(CalcStates.waiting_transferred_flag)
            await message.answer("Объект уже передан вам по акту?", reply_markup=transferred_keyboard())
            return

        if "participant_type" not in data:
            await state.set_state(CalcStates.waiting_participant_type)
            await message.answer(
                "Вы заключали договор как физлицо для личных нужд, или как юрлицо/ИП "
                "для предпринимательской деятельности?",
                reply_markup=participant_type_keyboard(),
            )
            return

        # Всё собрано — считаем неустойку и предлагаем дополнительно посчитать
        # госпошлину и штраф 5% (для этого нужны доп. убытки, необязательно).
        await state.set_state(CalcStates.waiting_extra_damages)
        await message.answer(
            "Если у вас есть подтверждённые дополнительные убытки (например, аренда "
            "жилья на время просрочки), укажите сумму в рублях — я включу её в цену иска "
            "и пересчитаю госпошлину. Либо нажмите «Пропустить».",
            reply_markup=skip_keyboard(),
        )

    async def _finalize(message: Message, state: FSMContext) -> None:
        data = await state.get_data()

        neustoyka_input = NeustoykaInput(
            contract_price=data["contract_price"],
            planned_transfer_date=date.fromisoformat(data["planned_transfer_date"]),
            actual_transfer_date=date.fromisoformat(data["actual_transfer_date"]),
            participant_type=ParticipantType(data["participant_type"]),
        )
        neustoyka_result = calculate_neustoyka(neustoyka_input)

        extra_damages = data.get("extra_damages", 0.0) or 0.0
        claim_price = neustoyka_result.amount + extra_damages
        is_consumer = neustoyka_input.participant_type == ParticipantType.INDIVIDUAL
        gosposhlina_result = calculate_gosposhlina(claim_price, is_consumer=is_consumer)
        shtraf_result = calculate_shtraf(base_amount=claim_price)

        text = format_neustoyka_result(neustoyka_result)
        text += "\n" + format_gosposhlina_result(gosposhlina_result)
        text += "\n" + format_shtraf_result(shtraf_result)
        text += DISCLAIMER

        if use_llm_explanation and groq_client is not None:
            payload = json.dumps(
                {
                    "delay_days": neustoyka_result.delay_days,
                    "key_rate_percent": neustoyka_result.key_rate_percent,
                    "neustoyka_amount": neustoyka_result.amount,
                    "extra_damages": extra_damages,
                    "gosposhlina": gosposhlina_result.amount_to_pay,
                    "shtraf_5_percent": shtraf_result.amount,
                    "warnings": neustoyka_result.warnings + shtraf_result.warnings,
                },
                ensure_ascii=False,
            )
            explanation = generate_explanation(groq_client, payload)
            if explanation:
                await message.answer(explanation)

        await message.answer(text)
        await state.clear()

    return router
