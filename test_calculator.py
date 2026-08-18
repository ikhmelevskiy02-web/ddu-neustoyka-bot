"""
Тесты для domain/calculator.py.

Контрольный пример взят из реального искового заявления (Хмелевские vs
ООО «СЗ «Альмандин», Вилегодский районный суд Архангельской области):
- цена договора: 21 314 231,38 ₽
- плановая дата передачи: 30.12.2025
- фактическая дата передачи: 27.04.2026
- участник — гражданин (личные нужды)
- ожидаемый результат: 116 дней просрочки, ставка 16%, неустойка 2 637 280,90 ₽

Это позволяет проверить, что реализация формулы и логики моратория даёт
именно ту сумму, которая была рассчитана в реальном судебном документе.
"""
from datetime import date

import pytest

from domain.calculator import calculate_neustoyka
from domain.models import NeustoykaInput, ParticipantType


def test_real_case_from_lawsuit():
    data = NeustoykaInput(
        contract_price=21_314_231.38,
        planned_transfer_date=date(2025, 12, 30),
        actual_transfer_date=date(2026, 4, 27),
        participant_type=ParticipantType.INDIVIDUAL,
    )
    result = calculate_neustoyka(data)

    assert result.delay_days == 116
    assert result.key_rate_percent == 16.0
    assert result.divisor == 150
    assert result.amount == pytest.approx(2_637_280.90, abs=0.01)


def test_moratorium_fully_covers_delay():
    """Если весь период просрочки попадает в мораторий — сумма 0."""
    data = NeustoykaInput(
        contract_price=10_000_000,
        planned_transfer_date=date(2024, 6, 1),
        actual_transfer_date=date(2024, 6, 10),
        participant_type=ParticipantType.INDIVIDUAL,
    )
    result = calculate_neustoyka(data)
    assert result.amount == 0.0
    assert result.delay_days == 0


def test_deadline_after_moratorium_no_exclusion():
    """Плановая дата в 2026 году — мораторий вообще не применяется."""
    data = NeustoykaInput(
        contract_price=5_000_000,
        planned_transfer_date=date(2026, 3, 1),
        actual_transfer_date=date(2026, 4, 1),  # 02.03–31.03 = 30 дней просрочки
        participant_type=ParticipantType.LEGAL_ENTITY,
    )
    result = calculate_neustoyka(data)
    assert result.excluded_moratorium_days == 0
    assert result.delay_days == 30
    assert result.divisor == 300


def test_deadline_before_moratorium_partial_exclusion():
    """Плановая дата до моратория, объект передан после его окончания —
    считаются дни до 22.03.2024 и дни после 31.12.2025, середина исключается."""
    data = NeustoykaInput(
        contract_price=1_000_000,
        planned_transfer_date=date(2024, 3, 1),  # старт просрочки 02.03.2024
        actual_transfer_date=date(2026, 1, 5),  # конец просрочки 04.01.2026
        participant_type=ParticipantType.INDIVIDUAL,
    )
    result = calculate_neustoyka(data)
    # 02.03.2024–21.03.2024 = 20 дней (до моратория) + 01.01.2026–04.01.2026 = 4 дня (после)
    assert result.delay_days == 24
    assert result.excluded_moratorium_days > 0


def test_no_delay_returns_zero():
    data = NeustoykaInput(
        contract_price=1_000_000,
        planned_transfer_date=date(2026, 5, 1),
        actual_transfer_date=date(2026, 4, 1),  # передано раньше срока
        participant_type=ParticipantType.INDIVIDUAL,
    )
    result = calculate_neustoyka(data)
    assert result.amount == 0.0
    assert result.delay_days == 0


def test_legal_entity_uses_divisor_300():
    data = NeustoykaInput(
        contract_price=5_000_000,
        planned_transfer_date=date(2026, 1, 1),
        actual_transfer_date=date(2026, 1, 11),  # 10 дней просрочки
        participant_type=ParticipantType.LEGAL_ENTITY,
    )
    result = calculate_neustoyka(data)
    assert result.divisor == 300
