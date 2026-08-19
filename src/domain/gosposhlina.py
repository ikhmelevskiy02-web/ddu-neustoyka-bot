"""
Расчёт государственной пошлины для имущественных исков в судах общей юрисдикции
(ст. 333.19 НК РФ) с учётом льготы потребителя (ст. 333.36 НК РФ).

Шкала — в действующей редакции по Федеральному закону от 08.08.2024 № 259-ФЗ,
применяется к делам, поданным после 08.09.2024. См. раздел 7 docs/LEGAL_SPEC.md.

ВАЖНО: многие сайты в интернете публикуют устаревшую шкалу (до реформы 2024 года).
Данный модуль сверен напрямую с текстом ст. 333.19 НК РФ по состоянию на 18.08.2026.
"""
from __future__ import annotations

from domain.models import GosposhlinaResult

# (нижняя_граница_включительно, верхняя_граница_включительно_или_None, база, процент_сверх_нижней_границы)
_BRACKETS: list[tuple[float, float | None, float, float]] = [
    (0, 100_000, 4_000, 0.0),
    (100_000, 300_000, 4_000, 3.0),
    (300_000, 500_000, 10_000, 2.5),
    (500_000, 1_000_000, 15_000, 2.0),
    (1_000_000, 3_000_000, 25_000, 1.0),
    (3_000_000, 8_000_000, 45_000, 0.7),
    (8_000_000, 24_000_000, 80_000, 0.35),
    (24_000_000, 50_000_000, 136_000, 0.3),
    (50_000_000, 100_000_000, 214_000, 0.2),
    (100_000_000, None, 314_000, 0.15),
]

_MAX_TOP_BRACKET_FEE = 900_000
_CONSUMER_EXEMPTION_THRESHOLD = 1_000_000
# Пошлина, которая была бы уплачена при цене иска ровно 1 000 000 ₽ — используется
# как вычитаемая льгота для потребителей при цене иска свыше 1 000 000 ₽
# (п. 3 ст. 333.36 НК РФ). При price=1_000_000 обе соседние строки шкалы дают 25 000 ₽.
_FEE_AT_ONE_MILLION = 25_000.0


def _raw_fee(price: float) -> float:
    """Пошлина по общей шкале ст. 333.19 НК РФ без учёта льгот потребителя."""
    if price < 0:
        raise ValueError("Цена иска не может быть отрицательной")

    for lower, upper, base, percent in _BRACKETS:
        if upper is None or price <= upper:
            if price <= lower:
                # Для нижней границы первой строки (0) — платится минимум 4000.
                return base
            fee = base + (price - lower) * percent / 100
            if upper is None:
                fee = min(fee, _MAX_TOP_BRACKET_FEE)
            return round(fee, 2)

    raise RuntimeError("Не удалось определить строку шкалы госпошлины")


def calculate_gosposhlina(claim_price: float, is_consumer: bool = True) -> GosposhlinaResult:
    """
    claim_price — цена иска (сумма ИМУЩЕСТВЕННЫХ требований: неустойка + убытки;
    компенсация морального вреда и штраф 5% сюда НЕ включаются — они не входят
    в цену иска для целей госпошлины).
    is_consumer — истец является потребителем (пп. 4 п. 2 ст. 333.36 НК РФ).
    """
    if is_consumer and claim_price <= _CONSUMER_EXEMPTION_THRESHOLD:
        return GosposhlinaResult(
            claim_price=claim_price,
            amount_to_pay=0.0,
            is_fully_exempt=True,
            calculation_text=(
                f"Цена иска {claim_price:,.2f} ₽ не превышает 1 000 000 ₽ — истец-потребитель "
                "полностью освобождён от уплаты госпошлины (пп. 4 п. 2 ст. 333.36 НК РФ)."
            ).replace(",", " ").replace(".", ","),
        )

    fee = _raw_fee(claim_price)

    if is_consumer and claim_price > _CONSUMER_EXEMPTION_THRESHOLD:
        amount_to_pay = round(fee - _FEE_AT_ONE_MILLION, 2)
        calc_text = (
            f"Пошлина по шкале ст. 333.19 НК РФ для цены иска {claim_price:,.2f} ₽ составляет "
            f"{fee:,.2f} ₽; за вычетом льготы потребителя (п. 3 ст. 333.36 НК РФ, "
            f"пошлина при цене иска 1 000 000 ₽ = {_FEE_AT_ONE_MILLION:,.2f} ₽) "
            f"к уплате: {amount_to_pay:,.2f} ₽."
        ).replace(",", " ").replace(".", ",")
        return GosposhlinaResult(
            claim_price=claim_price,
            amount_to_pay=amount_to_pay,
            is_fully_exempt=False,
            calculation_text=calc_text,
        )

    # Не потребитель (юрлицо/ИП) — льгота не применяется, платится полная сумма.
    calc_text = (
        f"Пошлина по шкале ст. 333.19 НК РФ для цены иска {claim_price:,.2f} ₽: "
        f"{fee:,.2f} ₽ (льгота по ст. 333.36 НК РФ не применяется, истец не является потребителем)."
    ).replace(",", " ").replace(".", ",")
    return GosposhlinaResult(
        claim_price=claim_price,
        amount_to_pay=fee,
        is_fully_exempt=False,
        calculation_text=calc_text,
    )
