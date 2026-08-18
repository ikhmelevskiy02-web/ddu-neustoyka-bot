#!/usr/bin/env python3
"""
Вспомогательный CLI для обновления src/data/key_rates.json.

Намеренно НЕ ходит в интернет и не парсит cbr.ru автоматически: таблица
ключевой ставки используется для юридически значимых расчётов, поэтому
безопаснее, чтобы человек явно вносил и подтверждал каждое значение,
сверившись с https://www.cbr.ru/hd_base/keyrate/ (или https://cbr.ru/dkp/cal_mp/
для графика заседаний), чем полагаться на неофициальный скрейпинг.

Примеры:
    python scripts/update_key_rate.py show
    python scripts/update_key_rate.py show --last 5
    python scripts/update_key_rate.py add --date 2026-09-14 --rate 13.75
    python scripts/update_key_rate.py add --date 2026-09-14 --rate 13.75 --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "src" / "data" / "key_rates.json"

# Разумные границы для sanity-check — если ставка вне этого диапазона, это
# почти наверняка опечатка (лишний ноль, перепутанные проценты и т.п.).
MIN_PLAUSIBLE_RATE = 1.0
MAX_PLAUSIBLE_RATE = 30.0


def load(path: Path = DATA_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(payload: dict, path: Path = DATA_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")


def cmd_show(args: argparse.Namespace) -> int:
    payload = load(args.path)
    rates: dict[str, float] = payload["rates"]
    parsed = sorted((datetime.strptime(k, "%Y-%m-%d").date(), v) for k, v in rates.items())
    for d, r in parsed[-args.last:]:
        print(f"{d.isoformat()}  {r:g}%")
    print(f"\nПоследняя проверка таблицы: {payload.get('_last_verified', '—')}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    try:
        new_date = date.fromisoformat(args.date)
    except ValueError:
        print(f"Ошибка: дата '{args.date}' должна быть в формате YYYY-MM-DD", file=sys.stderr)
        return 1

    if not (MIN_PLAUSIBLE_RATE <= args.rate <= MAX_PLAUSIBLE_RATE):
        print(
            f"Ошибка: ставка {args.rate}% выглядит неправдоподобно "
            f"(ожидается диапазон {MIN_PLAUSIBLE_RATE}–{MAX_PLAUSIBLE_RATE}%). "
            "Если это действительно так — измените диапазон в скрипте.",
            file=sys.stderr,
        )
        return 1

    payload = load(args.path)
    rates: dict[str, float] = payload["rates"]

    existing = rates.get(args.date)
    if existing is not None and existing != args.rate:
        print(
            f"Внимание: на {args.date} уже есть значение {existing}%, "
            f"будет заменено на {args.rate}%."
        )
    elif existing == args.rate:
        print(f"На {args.date} уже стоит {args.rate}% — изменений нет.")
        return 0

    latest_date = max(datetime.strptime(k, "%Y-%m-%d").date() for k in rates)
    if new_date < latest_date:
        print(
            f"Внимание: добавляемая дата {args.date} раньше последней записи "
            f"в таблице ({latest_date.isoformat()}). Обычно новые записи идут "
            "после самой последней. Продолжаю, но перепроверьте вводные данные."
        )

    rates[args.date] = args.rate
    payload["_last_verified"] = date.today().isoformat()

    if args.dry_run:
        print("--dry-run: файл не изменён. Итоговая запись была бы:")
        print(json.dumps({args.date: args.rate}, ensure_ascii=False))
        return 0

    save(payload, args.path)
    print(f"Добавлено: {args.date} -> {args.rate}%. Файл обновлён: {args.path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--path", type=Path, default=DATA_PATH, help="Путь к key_rates.json")
    sub = parser.add_subparsers(dest="command", required=True)

    show_parser = sub.add_parser("show", help="Показать последние записи таблицы")
    show_parser.add_argument("--last", type=int, default=10)
    show_parser.set_defaults(func=cmd_show)

    add_parser = sub.add_parser("add", help="Добавить/обновить запись в таблице")
    add_parser.add_argument("--date", required=True, help="Дата вступления ставки в силу, YYYY-MM-DD")
    add_parser.add_argument("--rate", required=True, type=float, help="Ставка в процентах, например 13.75")
    add_parser.add_argument("--dry-run", action="store_true", help="Показать результат, но не сохранять")
    add_parser.set_defaults(func=cmd_add)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
