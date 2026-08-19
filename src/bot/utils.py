"""Разбор дат и денежных сумм, введённых пользователем вручную (не через Groq)."""
from __future__ import annotations

import re
from datetime import date

_MONTHS_RU = {
    "январ": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5, "июн": 6,
    "июл": 7, "август": 8, "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12,
}


def parse_date_ru(text: str) -> date | None:
    """Понимает форматы: 30.12.2025, 30-12-2025, 2025-12-30, '30 декабря 2025'."""
    text = text.strip().lower()

    match = re.match(r"^(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})$", text)
    if match:
        day, month, year = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    match = re.match(r"^(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})$", text)
    if match:
        year, month, day = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    match = re.match(r"^(\d{1,2})\s+([а-я]+)\s+(\d{4})", text)
    if match:
        day, month_word, year = match.groups()
        for prefix, month_num in _MONTHS_RU.items():
            if month_word.startswith(prefix):
                try:
                    return date(int(year), month_num, int(day))
                except ValueError:
                    return None

    return None


def parse_money_ru(text: str) -> float | None:
    """Понимает: '21 314 231,38', '8500000', '8.5 млн', '8,5 млн руб'."""
    text = text.strip().lower().replace("₽", "").replace("руб.", "").replace("руб", "")

    million_match = re.match(r"^([\d.,]+)\s*(млн|миллион)", text)
    if million_match:
        number = million_match.group(1).replace(",", ".")
        try:
            return float(number) * 1_000_000
        except ValueError:
            return None

    cleaned = text.replace(" ", "").replace("\u00a0", "")
    cleaned = cleaned.replace(",", ".")
    # Если несколько точек (использованы как разделители тысяч) — оставляем только последнюю.
    if cleaned.count(".") > 1:
        head, _, tail = cleaned.rpartition(".")
        cleaned = head.replace(".", "") + "." + tail

    try:
        value = float(cleaned)
        return value if value > 0 else None
    except ValueError:
        return None
