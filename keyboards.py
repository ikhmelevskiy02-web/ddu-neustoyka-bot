from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

START_CALC_CALLBACK = "start_calc"
TRANSFERRED_YES = "transferred_yes"
TRANSFERRED_NO = "transferred_no"
PARTICIPANT_INDIVIDUAL = "participant_individual"
PARTICIPANT_LEGAL = "participant_legal"
SKIP_EXTRA_DAMAGES = "skip_extra_damages"


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧮 Рассчитать неустойку", callback_data=START_CALC_CALLBACK)]
        ]
    )


def transferred_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, уже передан", callback_data=TRANSFERRED_YES),
                InlineKeyboardButton(text="Нет, ещё не передан", callback_data=TRANSFERRED_NO),
            ]
        ]
    )


def participant_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Я физлицо (для себя)", callback_data=PARTICIPANT_INDIVIDUAL
                ),
                InlineKeyboardButton(
                    text="Юрлицо / ИП / бизнес", callback_data=PARTICIPANT_LEGAL
                ),
            ]
        ]
    )


def skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data=SKIP_EXTRA_DAMAGES)]
        ]
    )
