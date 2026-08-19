from datetime import date

import pytest

from domain.moratorium import days_excluding_period
from domain.shtraf import calculate_shtraf


def test_days_excluding_period_no_overlap():
    days, excluded = days_excluding_period(
        date(2026, 1, 1), date(2026, 1, 10), date(2020, 1, 1), date(2020, 1, 5)
    )
    assert days == 10
    assert excluded == 0


def test_days_excluding_period_full_overlap():
    days, excluded = days_excluding_period(
        date(2024, 6, 1), date(2024, 6, 10), date(2024, 1, 1), date(2025, 1, 1)
    )
    assert days == 0
    assert excluded == 10


def test_shtraf_basic():
    result = calculate_shtraf(base_amount=2_637_280.90)
    assert result.amount == pytest.approx(131_864.05, abs=0.01)


def test_shtraf_warns_on_moratorium_deadline():
    result = calculate_shtraf(
        base_amount=100_000, voluntary_satisfaction_deadline=date(2025, 6, 1)
    )
    assert any("приостановлено" in w for w in result.warnings)


def test_shtraf_warns_on_pre_reform_date():
    result = calculate_shtraf(
        base_amount=100_000, voluntary_satisfaction_deadline=date(2024, 5, 1)
    )
    assert any("01.09.2024" in w for w in result.warnings)

