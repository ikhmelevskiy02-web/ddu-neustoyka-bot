"""
Работа с таблицей ключевой ставки ЦБ РФ.

Данные хранятся в src/data/key_rates.json и должны обновляться при каждом
заседании Совета директоров ЦБ РФ. См. комментарий "_comment" внутри файла
и раздел 8 docs/LEGAL_SPEC.md.

ВАЖНО: даты в таблице — это даты ВСТУПЛЕНИЯ СТАВКИ В СИЛУ, а не даты решения
Совета директоров (обычно понедельник после пятничного заседания).
"""
from __future__ import annotations

import json
from bisect import bisect_right
from datetime import date, datetime
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "key_rates.json"


class KeyRateTable:
    """Таблица ключевой ставки ЦБ РФ с поиском значения на произвольную дату."""

    def __init__(self, data_path: Path = _DATA_PATH):
        self._data_path = data_path
        self._dates: list[date] = []
        self._rates: list[float] = []
        self._last_verified: str | None = None
        self._load()

    def _load(self) -> None:
        with open(self._data_path, encoding="utf-8") as f:
            payload = json.load(f)

        self._last_verified = payload.get("_last_verified")
        raw_rates: dict[str, float] = payload["rates"]

        parsed = sorted(
            (datetime.strptime(k, "%Y-%m-%d").date(), float(v))
            for k, v in raw_rates.items()
        )
        self._dates = [d for d, _ in parsed]
        self._rates = [r for _, r in parsed]

    def get_rate_on(self, on_date: date) -> float:
        """
        Возвращает ключевую ставку (в процентах, например 16.0), действовавшую
        на указанную дату — то есть последнее значение, вступившее в силу
        не позднее этой даты.
        """
        if not self._dates:
            raise RuntimeError("Таблица ключевой ставки пуста")

        if on_date < self._dates[0]:
            raise ValueError(
                f"Нет данных о ключевой ставке ранее {self._dates[0].isoformat()}"
            )

        idx = bisect_right(self._dates, on_date) - 1
        return self._rates[idx]

    @property
    def last_verified(self) -> str | None:
        return self._last_verified

    @property
    def latest_known_rate(self) -> tuple[date, float]:
        return self._dates[-1], self._rates[-1]


# Синглтон для удобного импорта в остальном коде.
key_rate_table = KeyRateTable()


def get_key_rate_percent(on_date: date) -> float:
    """Удобная функция-обёртка: ключевая ставка в процентах на дату on_date."""
    return key_rate_table.get_rate_on(on_date)
