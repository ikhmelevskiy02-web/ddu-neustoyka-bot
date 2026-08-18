"""
Доменные модели калькулятора неустойки по ДДУ (214-ФЗ).

Это чистый слой без зависимостей от Telegram или Groq — только данные и типы.
Подробное описание формул и правовой базы см. docs/LEGAL_SPEC.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class ParticipantType(str, Enum):
    """Тип участника долевого строительства — влияет на делитель в формуле неустойки."""

    INDIVIDUAL = "individual"       # гражданин, для личных/семейных нужд -> 1/150
    LEGAL_ENTITY = "legal_entity"   # юрлицо/ИП/предпринимательская деятельность -> 1/300


@dataclass
class NeustoykaInput:
    """Входные данные для расчёта неустойки за просрочку передачи объекта (ч. 2 ст. 6 214-ФЗ)."""

    contract_price: float
    planned_transfer_date: date
    # Если объект ещё не передан, actual_transfer_date = дата расчёта (сегодня) + 1 день,
    # либо передавать флаг not_transferred_yet=True и calculation_date.
    actual_transfer_date: date
    participant_type: ParticipantType = ParticipantType.INDIVIDUAL


@dataclass
class NeustoykaResult:
    """Результат расчёта неустойки за просрочку передачи объекта."""

    delay_days: int
    key_rate_percent: float          # ставка в процентах (например, 16.0)
    key_rate_date: date              # дата, на которую зафиксирована ставка (плановая дата передачи)
    divisor: int                     # 150 или 300
    amount: float                    # итоговая сумма неустойки, округлённая до копеек
    excluded_moratorium_days: int    # сколько дней "вырезано" мораторием — для прозрачности
    formula_text: str                # человекочитаемая формула для показа пользователю
    warnings: list[str] = field(default_factory=list)


@dataclass
class GosposhlinaResult:
    """Результат расчёта государственной пошлины (ст. 333.19, 333.36 НК РФ)."""

    claim_price: float
    amount_to_pay: float
    is_fully_exempt: bool            # цена иска <= 1 000 000 -> потребитель полностью освобождён
    calculation_text: str


@dataclass
class ShtrafResult:
    """Результат расчёта штрафа за отказ удовлетворить требования добровольно (ч. 3 ст. 10 214-ФЗ)."""

    base_amount: float
    percent: float                   # обычно 5.0
    amount: float
    warnings: list[str] = field(default_factory=list)
