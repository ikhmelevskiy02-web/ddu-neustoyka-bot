"""
Извлечение структурированных параметров расчёта из свободного текста пользователя.

Например: «Купили квартиру за 8.5 млн, по договору должны были отдать 1 октября
2025, а отдали только в марте 2026, я как физлицо для себя брал» ->
{
  "contract_price": 8500000,
  "planned_transfer_date": "2025-10-01",
  "actual_transfer_date": "2026-03-01",
  "object_not_transferred_yet": false,
  "participant_type": "individual"
}

Модель ТОЛЬКО извлекает поля — саму неустойку она не считает.
"""
from __future__ import annotations

from datetime import date
from typing import Any, TypedDict

from llm.groq_client import GroqClient

_SYSTEM_PROMPT = """\
Ты извлекаешь структурированные данные из сообщения пользователя о просрочке \
передачи квартиры по договору долевого участия (ДДУ). Верни СТРОГО JSON-объект \
без пояснений, без markdown, со следующими полями (используй null, если данные \
не упомянуты или неоднозначны):

{
  "contract_price": число или null — цена договора в рублях,
  "planned_transfer_date": "YYYY-MM-DD" или null — плановая дата передачи по договору,
  "actual_transfer_date": "YYYY-MM-DD" или null — фактическая дата передачи по акту,
  "object_not_transferred_yet": true/false/null — объект ещё не передан на текущий момент,
  "participant_type": "individual" | "legal_entity" | null — гражданин для личных нужд
      или юрлицо/ИП для предпринимательской деятельности (по умолчанию считай individual,
      если явно не указано иное про бизнес/предпринимательство),
  "claim_price_extra_damages": число или null — дополнительные убытки (например, аренда жилья),
      если упомянуты явно
}

Даты приводи к формату YYYY-MM-DD. Если год не указан, но упомянут месяц раньше \
текущей даты в разговоре — переспрашивать не нужно, верни null для этого поля, \
пусть бот уточнит отдельно. Никогда не придумывай числа, которых нет в тексте.
"""


class ExtractedParams(TypedDict, total=False):
    contract_price: float | None
    planned_transfer_date: str | None
    actual_transfer_date: str | None
    object_not_transferred_yet: bool | None
    participant_type: str | None
    claim_price_extra_damages: float | None


def extract_params(client: GroqClient, user_text: str) -> ExtractedParams | None:
    result = client.complete_json(_SYSTEM_PROMPT, user_text)
    if result is None:
        return None
    return result  # type: ignore[return-value]


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
