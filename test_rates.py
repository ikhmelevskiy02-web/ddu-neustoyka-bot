from datetime import date

import pytest

from domain.rates import KeyRateTable


def test_rate_on_exact_effective_date():
    table = KeyRateTable()
    assert table.get_rate_on(date(2025, 12, 22)) == 16.0


def test_rate_between_changes_uses_previous():
    table = KeyRateTable()
    # 13.02.2026 ещё не наступило -> действует ставка, вступившая 22.12.2025
    assert table.get_rate_on(date(2026, 1, 15)) == 16.0


def test_rate_matches_lawsuit_date():
    table = KeyRateTable()
    assert table.get_rate_on(date(2025, 12, 30)) == 16.0


def test_rate_before_earliest_entry_raises():
    table = KeyRateTable()
    with pytest.raises(ValueError):
        table.get_rate_on(date(2000, 1, 1))


def test_latest_known_rate_is_reasonable():
    table = KeyRateTable()
    d, r = table.latest_known_rate
    assert d.year >= 2026
    assert 1.0 <= r <= 30.0
