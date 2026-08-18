"""
Тонкая обёртка над Groq API (OpenAI-совместимый интерфейс).

ВАЖНО (см. docs/LEGAL_SPEC.md, раздел 1): эта модель НЕ используется для
арифметики — только для (1) извлечения параметров из свободного текста и
(2) оформления готового результата человеческим языком. Все числа в ответе
модели должны быть теми же числами, что посчитал domain/calculator.py, —
модель их не пересчитывает и не придумывает.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from groq import Groq

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self, api_key: str, model: str):
        self._client = Groq(api_key=api_key)
        self._model = model

    def complete_json(self, system_prompt: str, user_message: str) -> dict[str, Any] | None:
        """
        Запрашивает у модели строго JSON-ответ (JSON mode). Возвращает словарь
        или None, если модель вернула невалидный JSON / произошла ошибка сети.
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw = response.choices[0].message.content
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Groq вернул невалидный JSON: %s", exc)
            return None
        except Exception:  # noqa: BLE001 — не роняем бота из-за сбоя внешнего API
            logger.exception("Ошибка обращения к Groq API")
            return None

    def complete_text(self, system_prompt: str, user_message: str) -> str | None:
        """Обычный текстовый ответ модели (для оформления финального сообщения)."""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception:  # noqa: BLE001
            logger.exception("Ошибка обращения к Groq API")
            return None
