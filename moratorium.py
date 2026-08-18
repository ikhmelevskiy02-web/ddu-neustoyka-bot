"""
Мораторий на начисление неустойки/штрафа по Постановлению Правительства РФ
от 18.03.2024 № 326 (в ред. от 30.12.2025).

См. раздел 3 docs/LEGAL_SPEC.md для полного правового обоснования.

ВНИМАНИЕ: это не указ президента, а постановление Правительства РФ.
"""
from __future__ import annotations

from datetime import date

# Период, исключаемый из начисления неустойки за просрочку передачи объекта
# по ч. 2 ст. 6 214-ФЗ (раздел 3.1 спецификации).
# Мораторий действовал с даты вступления постановления в силу до 31.12.2025
# включительно и НЕ был продлён на 2026 год.
NEUSTOYKA_MORATORIUM_START = date(2024, 3, 22)
NEUSTOYKA_MORATORIUM_END = date(2025, 12, 31)

# Период, в течение которого не начисляется штраф 5% по ч. 3 ст. 10 214-ФЗ
# (введён Постановлением № 1916 от 26.12.2024, раздел 3.2 спецификации).
SHTRAF_MORATORIUM_START = date(2025, 1, 1)
SHTRAF_MORATORIUM_END = date(2025, 12, 31)


def is_within(d: date, start: date, end: date) -> bool:
    """True, если дата d попадает в закрытый интервал [start, end]."""
    return start <= d <= end


def days_excluding_period(
    period_start: date,
    period_end: date,
    exclude_start: date,
    exclude_end: date,
) -> tuple[int, int]:
    """
    Считает количество дней в закрытом интервале [period_start, period_end],
    исключая дни, попадающие в закрытый интервал [exclude_start, exclude_end].

    Возвращает (итоговые_дни, исключённые_дни).
    Если period_end < period_start — просрочки нет, возвращает (0, 0).
    """
    if period_end < period_start:
        return 0, 0

    total_days = (period_end - period_start).days + 1

    overlap_start = max(period_start, exclude_start)
    overlap_end = min(period_end, exclude_end)
    excluded_days = (overlap_end - overlap_start).days + 1 if overlap_start <= overlap_end else 0

    return total_days - excluded_days, excluded_days


def days_excluding_neustoyka_moratorium(period_start: date, period_end: date) -> tuple[int, int]:
    """Удобная обёртка specifically для моратория на неустойку по ч. 2 ст. 6."""
    return days_excluding_period(
        period_start, period_end, NEUSTOYKA_MORATORIUM_START, NEUSTOYKA_MORATORIUM_END
    )
