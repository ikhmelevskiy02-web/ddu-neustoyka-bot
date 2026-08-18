"""
Шаблонное (без LLM) форматирование результата расчёта — используется как надёжный
базовый вариант и как источник "истинных" цифр, которые при необходимости
пересказывает Groq в llm/explain.py (сами цифры при этом не меняются).
"""
from __future__ import annotations

from domain.models import GosposhlinaResult, NeustoykaResult, ShtrafResult


def _fmt(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " ₽"


def format_neustoyka_result(result: NeustoykaResult) -> str:
    lines = [
        "📊 <b>Расчёт неустойки за просрочку передачи объекта</b> (ч. 2 ст. 6 214-ФЗ)",
        "",
        f"Дней просрочки (за вычетом моратория): <b>{result.delay_days}</b>",
        f"Ключевая ставка ЦБ РФ на плановую дату передачи "
        f"({result.key_rate_date.strftime('%d.%m.%Y')}): <b>{result.key_rate_percent:g}%</b>",
        f"Формула: {result.formula_text}",
        "",
        f"💰 Итого неустойка: <b>{_fmt(result.amount)}</b>",
    ]
    if result.warnings:
        lines.append("")
        lines.append("⚠️ <i>Важно:</i>")
        for w in result.warnings:
            lines.append(f"• {w}")
    return "\n".join(lines)


def format_gosposhlina_result(result: GosposhlinaResult) -> str:
    lines = [
        "",
        "📄 <b>Государственная пошлина</b>",
        result.calculation_text,
    ]
    return "\n".join(lines)


def format_shtraf_result(result: ShtrafResult) -> str:
    lines = [
        "",
        f"⚖️ <b>Штраф {result.percent:g}%</b> (ч. 3 ст. 10 214-ФЗ): <b>{_fmt(result.amount)}</b>",
    ]
    if result.warnings:
        for w in result.warnings:
            lines.append(f"⚠️ {w}")
    return "\n".join(lines)


DISCLAIMER = (
    "\n\nℹ️ Это справочный расчёт, а не юридическая консультация и не гарантия "
    "решения суда. Суд вправе снизить неустойку (ст. 333 ГК РФ). Данные о "
    "ключевой ставке и моратории актуальны на дату в источнике — сверяйте "
    "перед подачей документов."
)
