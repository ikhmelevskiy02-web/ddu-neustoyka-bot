import pytest

from domain.gosposhlina import calculate_gosposhlina


def test_real_case_from_lawsuit():
    """Цена иска 2 857 280,90 ₽ (неустойка + убытки) -> пошлина 18 572,81 ₽."""
    result = calculate_gosposhlina(2_857_280.90, is_consumer=True)
    assert result.amount_to_pay == pytest.approx(18_572.81, abs=0.01)
    assert result.is_fully_exempt is False


def test_full_exemption_under_one_million():
    result = calculate_gosposhlina(999_999, is_consumer=True)
    assert result.is_fully_exempt is True
    assert result.amount_to_pay == 0.0


def test_exactly_one_million_is_exempt():
    result = calculate_gosposhlina(1_000_000, is_consumer=True)
    assert result.is_fully_exempt is True


def test_non_consumer_no_exemption():
    result = calculate_gosposhlina(500_000, is_consumer=False)
    assert result.is_fully_exempt is False
    # 15 000 + 2% * (500000-500000) = 15 000
    assert result.amount_to_pay == pytest.approx(15_000, abs=0.01)


def test_top_bracket_capped_at_900000():
    result = calculate_gosposhlina(200_000_000, is_consumer=False)
    assert result.amount_to_pay <= 900_000
