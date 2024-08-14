from aiogram.dispatcher.filters.state import StatesGroup, State

class UserState(StatesGroup):
    start_state = State()
    addclient = State()
    part1 = State()  
    part2 = State()
    part3 = State()
    part4 = State()
    part5 = State()
    part6 = State()
    viewe = State()
    waiting_for_contact = State()
    waiting_for_contact_for_debts = State()
    waiting_for_phone_number = State()

class ProductStates(StatesGroup):
    waiting_for_product_list = State()
    waiting_for_amount_paid = State()
    waiting_for_password = State()



class PasswordStates(StatesGroup):
    waiting_for_password_verification = State()
