


import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import Message, ContentType
from datetime import datetime
from state import UserState, ProductStates, PasswordStates

API_TOKEN = '7487664145:AAGBvFt0lMcTx3pWE_b7Ml6CJt6U_tgTrWc'
storage = MemoryStorage()

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect('clients.db')
cursor = conn.cursor()




@dp.message_handler(commands=['start'])
async def send_welcome(message: Message, state: FSMContext):
    await state.finish() 
    await message.answer("Привет, добро пожаловать!\nДля добавления клиента введите /mijoz_qoshing\nДля просмотра долгов и даты покупок введите /qarzlar_korish")
    await UserState.start_state.set()

@dp.message_handler(commands=['qarzlar_korish'], state=UserState.start_state)
async def ask_for_phone_number(message: Message):
    await message.answer("Введите ваш номер телефона для проверки долгов:")
    await UserState.waiting_for_phone_number.set()

@dp.message_handler(state=UserState.waiting_for_phone_number)
async def ask_for_password(message: Message, state: FSMContext):
    phone_number = message.text
    await state.update_data(phone_number=phone_number)
    await message.answer("Теперь введите пароль:")
    await PasswordStates.waiting_for_password_verification.set()

@dp.message_handler(state=PasswordStates.waiting_for_password_verification)
async def verify_password(message: Message, state: FSMContext):
    entered_password = message.text
    user_data = await state.get_data()
    phone_number = user_data['phone_number']

    cursor.execute('''
    SELECT password FROM users WHERE phone_number=?
    ''', (phone_number,))
    
    user_password_data = cursor.fetchone()

    if user_password_data and user_password_data[0] == entered_password:
        cursor.execute('''
        SELECT client_name, GROUP_CONCAT(product_name || ' - ' || product_price, ', '), SUM(product_price), amount_paid, date FROM clients WHERE client_number=? GROUP BY date
        ''', (phone_number,))
        
        client_data_list = cursor.fetchall()

        if client_data_list:
            response_message = f"Данные для клиента с номером {phone_number}:\n\n"
            total_debt = 0
            total_amount_paid = 0
            for index, client_data in enumerate(client_data_list, start=1):
                client_name, products, total_product_price, amount_paid, date = client_data
                debt = float(total_product_price) - float(amount_paid)
                total_debt += debt
                total_amount_paid += float(amount_paid)

                response_message += (
                    f"Запись {index}:\n"
                    f"Имя клиента: {client_name}\n"
                    f"Дата покупки: {date}\n"
                    f"Продукты: {products}\n"
                    f"Общая сумма продуктов: {float(total_product_price):g}\n"
                    f"Сумма оплаты: {float(amount_paid):g}\n"
                    f"Оставшийся долг: {float(debt):g}\n\n"
                )

            response_message += f"Общий долг клиента: {float(total_debt):g}"
            await message.answer(response_message)
        else:
            await message.answer("У вас нет записей о покупках.")
        await state.finish()
    else:
        await message.answer("Неверный пароль. Попробуйте еще раз.")
        await PasswordStates.waiting_for_password_verification.set()

@dp.message_handler(commands=['mijoz_qoshing'], state=UserState.start_state)
async def ask_for_password(message: Message):
    await message.answer("Введите пароль администратора:")
    await UserState.addclient.set()

@dp.message_handler(lambda message: message.text != '12345', state=UserState.addclient)
async def handle_invalid_password(message: types.Message):
    await message.answer("Неправильный пароль. Пожалуйста, попробуйте снова.\nВведите пароль:")

@dp.message_handler(lambda message: message.text == '12345', state=UserState.addclient)
async def correct_password(message: types.Message, state: FSMContext):
    await message.answer("Успешно, теперь введите номер телефона клиента (например, +998993245464):")
    await UserState.part2.set()

@dp.message_handler(state=UserState.part2)
async def check_existing_client(message: Message, state: FSMContext):
    client_number = message.text
    await state.update_data(client_number=client_number)

    cursor.execute('''
    SELECT client_name FROM clients WHERE client_number=?
    ''', (client_number,))
    
    client_data = cursor.fetchone()

    if client_data:
        await state.update_data(client_name=client_data[0])
        await message.answer("Клиент найден. Введите список продуктов в формате 'Название-Количество*Цена', один продукт или несколько продуктов на строку. Например:\nСалфетка-10*3000\nГубка-5*2000\nКогда закончите, нажмите ENTER.")
        await ProductStates.waiting_for_product_list.set()
    else:
        await message.answer("Клиент не найден. Введите имя клиента:")
        await UserState.part3.set()

@dp.message_handler(state=UserState.part3)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(client_name=message.text)
    await message.answer("Введите список продуктов в формате 'Название-Количество*Цена', один продукт или несколько продуктов на строку. Например:\nСалфетка-10*3000\nГубка-5*2000\nКогда закончите, нажмите ENTER.")
    await ProductStates.waiting_for_product_list.set()

@dp.message_handler(state=ProductStates.waiting_for_product_list)
async def add_product_list(message: Message, state: FSMContext):
    user_data = await state.get_data()

    # Парсинг списка продуктов
    product_lines = message.text.split('\n')
    total_amount = 0
    product_list = []

    for line in product_lines:
        try:
            product_name, quantity_price = line.split('-')
            quantity, price = map(float, quantity_price.split('*'))
            total_price = quantity * price
            if total_price.is_integer():
                total_price = int(total_price)
            product_list.append({'name': product_name, 'price': total_price})
            total_amount += total_price
        except ValueError:
            await message.answer("Неверный формат ввода. Пожалуйста, используйте формат 'Название-Количество*Цена' для каждого продукта, например:\nСалфетка-10*3000")
            return

    await state.update_data(product_list=product_list, total_amount=total_amount)
    await message.answer(f"Общая сумма всех продуктов: {total_amount:g}. Сколько клиент заплатил?")
    await ProductStates.waiting_for_amount_paid.set()

@dp.message_handler(state=ProductStates.waiting_for_amount_paid)
async def add_amount_paid(message: Message, state: FSMContext):
    try:
        amount_paid = float(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите действительную сумму.")
        return

    await state.update_data(amount_paid=amount_paid)

    user_data = await state.get_data()
    client_number = user_data['client_number']


    cursor.execute('''
    SELECT password FROM users WHERE phone_number=?
    ''', (client_number,))
    
    user_password_data = cursor.fetchone()

    if user_password_data:
        await save_client_data(message, state)
    else:
        await message.answer("Придумайте пароль для клиента, чтобы он мог просмотреть свои долги.")
        await ProductStates.waiting_for_password.set()

@dp.message_handler(state=ProductStates.waiting_for_password)
async def set_password(message: Message, state: FSMContext):
    password = message.text
    await state.update_data(password=password)
    await save_client_data(message, state)

async def save_client_data(message: Message, state: FSMContext):
    user_data = await state.get_data()
    client_number = user_data['client_number']
    client_name = user_data['client_name']
    product_list = user_data['product_list']
    total_amount = user_data['total_amount']
    amount_paid = user_data['amount_paid']
    password = user_data.get('password', None)

 
    for item in product_list:
        cursor.execute('''
        INSERT INTO clients (client_number, client_name, product_name, product_price, amount_paid, date)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (client_number, client_name, item['name'], item['price'], amount_paid, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    

    if password:
        cursor.execute('''
        INSERT OR REPLACE INTO users (phone_number, name, password)
        VALUES (?, ?, ?)
        ''', (client_number, client_name, password))

    conn.commit()

    await message.answer("Данные клиента сохранены.")

    # Вывод всех записей клиента
    cursor.execute('''
    SELECT client_name, GROUP_CONCAT(product_name || ' - ' || product_price, ', '), SUM(product_price), amount_paid, date FROM clients WHERE client_number=? GROUP BY date
    ''', (client_number,))
    
    client_data_list = cursor.fetchall()

    if client_data_list:
        response_message = f"Записи для клиента с номером {client_number}:\n\n"
        total_debt = 0
        total_amount_paid = 0
        for index, client_data in enumerate(client_data_list, start=1):
            client_name, products, total_product_price, amount_paid, date = client_data
            debt = float(total_product_price) - float(amount_paid)
            total_debt += debt
            total_amount_paid += float(amount_paid)

            response_message += (
                f"Запись {index}:\n"
                f"Имя клиента: {client_name}\n"
                f"Дата покупки: {date}\n"
                f"Продукты: {products}\n"
                f"Общая сумма продуктов: {float(total_product_price):g}\n"
                f"Сумма оплаты: {float(amount_paid):g}\n"
                f"Оставшийся долг: {float(debt):g}\n\n"
            )

        response_message += f"Общий долг клиента: {float(total_debt):g}"
        await message.answer(response_message)

    await UserState.start_state.set()

if __name__ == '__main__':
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        phone_number TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        password TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY,
        client_number TEXT NOT NULL,
        client_name TEXT NOT NULL,
        product_name TEXT NOT NULL,
        product_price REAL NOT NULL,
        amount_paid REAL NOT NULL,
        date TEXT NOT NULL,
        FOREIGN KEY (client_number) REFERENCES users (phone_number)
    )
    ''')

    conn.commit()

    executor.start_polling(dp, skip_updates=True)
    conn.close()
