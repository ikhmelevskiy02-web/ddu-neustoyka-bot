"""
Расчёт неустойки за нарушение срока передачи объекта долевого строительства
(ч. 2 ст. 6 Федерального закона от 30.12.2004 № 214-ФЗ).

Формула и правовое обоснование — раздел 2 docs/LEGAL_SPEC.md:

    Неустойка = Цена договора × (1 / N) × Ключевая ставка × Дни просрочки

где N = 150 для граждан (личные нужды) и N = 300 для юрлиц/ИП (предпринимательская
деятельность), а ключевая ставка фиксируется на дату, предусмотренную договором
для передачи объекта (Определение СК по гражд. делам ВС РФ от 27.02.2024
№ 127-КГ23-18-К4), и не меняется при последующих изменениях ставки ЦБ.

Этот модуль НЕ обращается к LLM и не должен от неё зависеть — вся арифметика
детерминирована и покрыта тестами (tests/test_calculator.py).
"""
from __future__ import annotations

from datetime import date, timedelta

from domain.models import NeustoykaInput, NeustoykaResult, ParticipantType
from domain.moratorium import (
    NEUSTOYKA_MORATORIUM_END,
    NEUSTOYKA_MORATORIUM_START,
    days_excluding_neustoyka_moratorium,
)
from domain.rates import get_key_rate_percent


def calculate_neustoyka(data: NeustoykaInput) -> NeustoykaResult:
    warnings: list[str] = []

    # ст. 191 ГК РФ: течение срока начинается со дня, следующего за плановой датой.
    delay_start = data.planned_transfer_date + timedelta(days=1)
    # День фактической передачи в просрочку не включается.
    delay_end = data.actual_transfer_date - timedelta(days=1)

    if delay_end < delay_start:
        return NeustoykaResult(
            delay_days=0,
            key_rate_percent=0.0,
            key_rate_date=data.planned_transfer_date,
            divisor=150 if data.participant_type == ParticipantType.INDIVIDUAL else 300,
            amount=0.0,
            excluded_moratorium_days=0,
            formula_text="Просрочка отсутствует: объект передан не позднее срока по договору.",
            warnings=["Плановая и фактическая даты не образуют просрочки — проверьте вводные данные."],
        )

    delay_days, excluded_days = days_excluding_neustoyka_moratorium(delay_start, delay_end)

    if excluded_days > 0:
        warnings.append(
            f"Из расчёта исключено {excluded_days} дн., приходящихся на период моратория "
            f"({NEUSTOYKA_MORATORIUM_START.strftime('%d.%m.%Y')}–"
            f"{NEUSTOYKA_MORATORIUM_END.strftime('%d.%m.%Y')}) по Постановлению Правительства РФ "
            f"№ 326 от 18.03.2024 (в ред. от 30.12.2025)."
        )

    if delay_days == 0:
        return NeustoykaResult(
            delay_days=0,
            key_rate_percent=0.0,
            key_rate_date=data.planned_transfer_date,
            divisor=150 if data.participant_type == ParticipantType.INDIVIDUAL else 300,
            amount=0.0,
            excluded_moratorium_days=excluded_days,
            formula_text="Весь период просрочки попадает под мораторий — неустойка не начисляется.",
            warnings=warnings,
        )

    # Ставка фиксируется на дату, предусмотренную договором для передачи (не на дату
    # фактической передачи и не на дату расчёта!).
    try:
        rate_percent = get_key_rate_percent(data.planned_transfer_date)
    except ValueError as exc:
        raise ValueError(
            "Не удалось определить ключевую ставку ЦБ РФ на плановую дату передачи "
            f"({data.planned_transfer_date.isoformat()}): {exc}. "
            "Обновите таблицу в src/data/key_rates.json."
        ) from exc

    divisor = 150 if data.participant_type == ParticipantType.INDIVIDUAL else 300
    rate_fraction = rate_percent / 100

    amount = data.contract_price * (1 / divisor) * rate_fraction * delay_days
    amount = round(amount, 2)

    formula_text = (
        f"{_fmt_money(data.contract_price)} × 1/{divisor} × {rate_percent:g}% × {delay_days} дн. "
        f"= {_fmt_money(amount)}"
    )

    if data.participant_type == ParticipantType.INDIVIDUAL:
        warnings.append(
            "Учтён двойной размер неустойки (1/150), т.к. участник — гражданин, "
            "заключивший договор для личных нужд (абз. 2 ч. 2 ст. 6 214-ФЗ)."
        )
    else:
        warnings.append(
            "Использован базовый размер неустойки (1/300) для юрлица/ИП. "
            "Если объект приобретался физлицом для личных нужд, укажите тип участника "
            "«гражданин», чтобы получить удвоенный размер."
        )

    warnings.append(
        "Суд вправе снизить неустойку по заявлению застройщика на основании ст. 333 ГК РФ — "
        "расчёт показывает сумму до возможного снижения судом."
    )

    return NeustoykaResult(
        delay_days=delay_days,
        key_rate_percent=rate_percent,
        key_rate_date=data.planned_transfer_date,
        divisor=divisor,
        amount=amount,
        excluded_moratorium_days=excluded_days,
        formula_text=formula_text,
        warnings=warnings,
    )


def _fmt_money(value: float) -> str:
    """Форматирует сумму в рублях в привычном для РФ виде: 2 637 280,90 ₽."""
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " ₽"
