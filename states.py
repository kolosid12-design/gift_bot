from aiogram.fsm.state import State, StatesGroup

class CreateDealStates(StatesGroup):
    role = State()
    currency = State()
    amount = State()
    description = State()

class JoinDealStates(StatesGroup):
    enter_number = State()

class RekvStates(StatesGroup):
    choose_type = State()
    enter_details = State()
    manage = State()  # FIX: было в RekvManageStates, но bot.py использует RekvStates.manage

class RekvManageStates(StatesGroup):
    manage = State()
