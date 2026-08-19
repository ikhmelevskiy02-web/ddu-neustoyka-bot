from aiogram.fsm.state import State, StatesGroup


class CalcStates(StatesGroup):
    describing = State()            # пользователь описывает ситуацию свободным текстом
    waiting_price = State()         # цена договора
    waiting_planned_date = State()  # плановая дата передачи
    waiting_transferred_flag = State()  # передан ли объект уже
    waiting_actual_date = State()   # фактическая дата передачи
    waiting_participant_type = State()  # гражданин / юрлицо
    waiting_extra_damages = State()     # доп. убытки (для госпошлины), опционально
