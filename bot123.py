import sqlite3
from datetime import datetime, date
import os
from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor

# Получаем токен из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Получаем путь к базе данных из переменной окружения или используем локальный путь
DB_PATH = os.getenv('DATABASE_PATH', 'database_info.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

class UserInput(StatesGroup):
    waiting_for_dob = State()

def calculate_ruling_number(birth_date):
    birth_date = birth_date.replace('.', '/')
    numbers = ''.join(filter(str.isdigit, birth_date))
    num_sum = sum(int(num) for num in numbers)
    while num_sum not in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
        if num_sum in [10, 11, 22]:
            return num_sum
        num_sum = sum(int(num) for num in str(num_sum))
    return num_sum 

def count_digit_occurrences(birth_date):
    numbers = ''.join(filter(str.isdigit, birth_date))
    count_dict = {str(i): 0 for i in range(10)}
    for num in numbers:
        count_dict[num] += 1
    return count_dict

def determine_zodiac_sign(dob):
    zodiac_sign = ""
    if (dob.month == 3 and dob.day >= 21) or (dob.month == 4 and dob.day <= 20):
        zodiac_sign = "♈Овен"
    elif (dob.month == 4 and dob.day >= 21) or (dob.month == 5 and dob.day <= 21):
        zodiac_sign = "♉Телец"
    elif (dob.month == 5 and dob.day >= 22) or (dob.month == 6 and dob.day <= 21):
        zodiac_sign = "♊Близнецы"
    elif (dob.month == 6 and dob.day >= 22) or (dob.month == 7 and dob.day <= 22):
        zodiac_sign = "♋Рак"
    elif (dob.month == 7 and dob.day >= 23) or (dob.month == 8 and dob.day <= 23):
        zodiac_sign = "♌Лев"
    elif (dob.month == 8 and dob.day >= 24) or (dob.month == 9 and dob.day <= 23):
        zodiac_sign = "♍Дева"
    elif (dob.month == 9 and dob.day >= 24) or (dob.month == 10 and dob.day <= 23):
        zodiac_sign = "♎Весы"
    elif (dob.month == 10 and dob.day >= 24) or (dob.month == 11 and dob.day <= 22):
        zodiac_sign = "♏Скорпион"
    elif (dob.month == 11 and dob.day >= 23) or (dob.month == 12 and dob.day <= 22):
        zodiac_sign = "♐Стрелец"
    elif (dob.month == 12 and dob.day >= 23) or (dob.month == 1 and dob.day <= 20):
        zodiac_sign = "♑Козерог"
    elif (dob.month == 1 and dob.day >= 21) or (dob.month == 2 and dob.day <= 19):
        zodiac_sign = "♒Водолей"
    elif (dob.month == 2 and dob.day >= 20) or (dob.month == 3 and dob.day <= 20):
        zodiac_sign = "♓Рыбы"
    return zodiac_sign

def determine_destiny_card(dob, cursor):
    month_day = dob.strftime('%d.%m')
    cursor.execute('SELECT card, description FROM aceqace WHERE card_day_month=?', (month_day,))
    data = cursor.fetchone()

    if data is None:
        return 'Не найден'
    else:
        card, description = data
        return card, description

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    chat_member = await bot.get_chat_member('@orqll', message.from_user.id)
    chat_admins = await bot.get_chat_administrators('@orqll')
    admin_ids = [admin.user.id for admin in chat_admins]
    if chat_member.status == 'member' or message.from_user.id in admin_ids or chat_member.status in ['creator', 'restricted']:
        # пользователь является участником группы с нужным статусом, продолжаем работу
        await bot.send_message(message.chat.id, 'Введите дату рождения в формате дд.мм.гггг')
        await UserInput.waiting_for_dob.set()
    else:
        # пользователь не подписан на канал, отправляем кнопки для подписки
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text='👉 Подписаться на канал', url='https://t.me/orqll'))
        keyboard.add(InlineKeyboardButton(text='✅ Подписался', callback_data='subscribed'))
        await bot.send_message(message.chat.id, 'Для использования бота необходимо подписаться на канал.', reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'subscribed')
async def subscribed_callback(callback_query: types.CallbackQuery):
    chat_member = await bot.get_chat_member('@orqll', callback_query.from_user.id)
    chat_admins = await bot.get_chat_administrators('@orqll')
    admin_ids = [admin.user.id for admin in chat_admins]
    if chat_member.status == 'member' or callback_query.from_user.id in admin_ids or chat_member.status in ['creator', 'restricted']:
        user_name = callback_query.from_user.first_name
        await bot.send_message(callback_query.message.chat.id, f'🎉 Приветствую {user_name}! 🎉\n\nПожалуйста, введите дату рождения в следующем формате 🎂\n\nдд.мм.гггг ', reply_markup=types.ReplyKeyboardRemove())
        await UserInput.waiting_for_dob.set()
        await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    else:
        await bot.answer_callback_query(callback_query.id, 'Пожалуйста, подпишитесь на канал.')

@dp.message_handler(state=UserInput.waiting_for_dob, content_types=types.ContentTypes.TEXT)
async def process_dob(message: types.Message, state: FSMContext):
    try:
        dob = datetime.strptime(message.text, '%d.%m.%Y').date()
    except ValueError:
        try:
            dob = datetime.strptime(message.text, '%d/%m/%Y').date()
        except ValueError:
            await bot.send_message(message.chat.id, 'Пожалуйста, введите дату рождения в формате дд.мм.гггг')
            return

    await state.update_data(dob=dob.strftime('%d.%m.%Y'))
    await send_dob_info_message(bot, message.chat.id, dob)

async def send_dob_info_message(bot, chat_id, dob):
    if dob is None:
        dob = date.today()
    dob_string = dob.strftime('%d.%m.%Y')
    ruling_number = str(calculate_ruling_number(dob_string))
    zodiac_sign = determine_zodiac_sign(dob)

    cursor.execute('SELECT * FROM ruling_numbers WHERE number=?', (ruling_number,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        dob_string = "<strong>" + dob_string + "</strong>"
        zodiac_sign_info = f"Гороскоп по дате рождения поможет лучше понять свой характер и раскроет информацию о сильных и слабых сторонах, перспективах личной и семейной жизни, профессиональных качествах и уязвимых местах организма.\n<b>• Знак зодиака:</b> {zodiac_sign}\n\nНажмите на интересующий раздел⬇️ \n"
        smiley = ""
        if ruling_number == "2":
            smiley = "2️⃣"
        elif ruling_number == "3":
            smiley = "3️⃣"
        elif ruling_number == "4":
            smiley = "4️⃣"
        elif ruling_number == "5":
            smiley = "5️⃣"
        elif ruling_number == "6":
            smiley = "6️⃣"
        elif ruling_number == "7":
            smiley = "7️⃣"
        elif ruling_number == "8":
            smiley = "8️⃣"
        elif ruling_number == "9":
            smiley = "9️⃣"
        elif ruling_number == "10":
            smiley = "🔟"
        elif ruling_number == "11":
            smiley = "1️⃣1️⃣"
        elif ruling_number == "22":
            smiley = "2️⃣2️⃣"

        ruling_number_info = f"Нумерология поможет получить знание о своем внутреннем Я и осознанно выбрать путь в жизни на основе понимания правящего числа.\n<b>• Правящее число:</b> {smiley}\n"
        card, description = determine_destiny_card(dob, cursor)
        destiny_card = f"Система карт раскроет информацию об энергиях и качествах, которыми каждый из нас наделяется при рождении, и которые используются нами на протяжении жизни для самореализации и развития.\n<b>• Карта рождения:</b> {card} ({description})\n"
        response = '\n'.join(["Дата рождения: " + dob_string, "", ruling_number_info, destiny_card, zodiac_sign_info])

    inline_keyboard = InlineKeyboardMarkup(row_width=1)
    button1 = InlineKeyboardButton(text=f'Правящее число {smiley}', callback_data=f'purpose_{ruling_number}')
    button2 = InlineKeyboardButton(text=f' Знак {zodiac_sign}', callback_data=f'zodiac_')
    button3 = InlineKeyboardButton(text=f'Карта рождения {card}', callback_data=f'card_description_{card}')
    inline_keyboard.add(button1, button3, button2)

    await bot.send_message(chat_id, response, parse_mode=ParseMode.HTML, reply_markup=inline_keyboard)

#♈♍♐♑
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('zodiac_'), state=UserInput.waiting_for_dob)
async def show_zodiac_description(callback_query: types.CallbackQuery, state: FSMContext):
    dob = datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date()
    day_month = dob.strftime('%d.%m')

    cursor.execute('SELECT * FROM zodiac_day WHERE day_number=?', (day_month,))
    result = cursor.fetchone()

    if result is not None:
        general_characteristics = result[1]

        description = f"<b>Рожденные {day_month}</b>\n\n"
        description += f"{general_characteristics}\n\n"

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="✅ Основная характеристика", callback_data="zodiac_", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="💑 Отношения", callback_data="love_horoscope_button")
        button2 = InlineKeyboardButton(text="👨 Мужчина", callback_data="man_day")
        button3 = InlineKeyboardButton(text="👩 Женщина", callback_data="girl_day")
        button4 = InlineKeyboardButton(text="💼 Карьера", callback_data="work_career_button")
        button5 = InlineKeyboardButton(text="💊 Здоровье", callback_data="health_disease_button")
        button7 = InlineKeyboardButton(text="💡 Рекомендации", callback_data="tips_button")
        button8 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button2, button3, button1, button4, button5, button7, button8)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await bot.send_message(chat_id=callback_query.message.chat.id, text=description, reply_markup=inline_keyboard, parse_mode=ParseMode.HTML)

    else:
        await bot.send_message(callback_query.message.chat.id, 'К сожалению, информация о знаке зодиака на этот день не найдена.')

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'love_horoscope_button', state=UserInput.waiting_for_dob)
async def show_love_horoscope(callback_query: types.CallbackQuery, state: FSMContext):
    dob = datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date()
    day_month = dob.strftime('%d.%m')

    cursor.execute('SELECT love_horoscope FROM zodiac_day WHERE day_number=?', (day_month,))
    result = cursor.fetchone()

    if result is not None:
        love_horoscope = result[0]

        description = f"<b>Любовь и совместимость рожденных {day_month}</b>\n\n"
        description += f"{love_horoscope}\n\n"

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="🌱 Основная характеристика", callback_data="zodiac_", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="✅ Отношения", callback_data="love_horoscope_button")
        button2 = InlineKeyboardButton(text="👨 Мужчина", callback_data="man_day")
        button3 = InlineKeyboardButton(text="👩 Женщина", callback_data="girl_day")
        button4 = InlineKeyboardButton(text="💼 Карьера", callback_data="work_career_button")
        button5 = InlineKeyboardButton(text="💊 Здоровье", callback_data="health_disease_button")
        button7 = InlineKeyboardButton(text="💡 Рекомендации", callback_data="tips_button")
        button8 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button2, button3, button1, button4, button5, button7, button8)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await bot.send_message(chat_id=callback_query.message.chat.id, text=description, reply_markup=inline_keyboard, parse_mode=ParseMode.HTML)

    else:
        await bot.send_message(callback_query.message.chat.id, 'К сожалению, информация о знаке зодиака на этот день не найдена.')

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'man_day', state=UserInput.waiting_for_dob)
async def show_man_day(callback_query: types.CallbackQuery, state: FSMContext):
    dob = datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date()
    day_month = dob.strftime('%d.%m')

    cursor.execute('SELECT man_day FROM zodiac_day WHERE day_number=?', (day_month,))
    result = cursor.fetchone()

    if result is not None:
        particulars_horoscope = result[0]

        description = f"<b>Характеристика мужчин рожденных {day_month}</b>\n\n"
        description += f"{particulars_horoscope}\n\n"

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="🌱 Основная характеристика", callback_data="zodiac_", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="💑 Отношения", callback_data="love_horoscope_button")
        button2 = InlineKeyboardButton(text="✅ Мужчина", callback_data="man_day")
        button3 = InlineKeyboardButton(text="👩 Женщина", callback_data="girl_day")
        button4 = InlineKeyboardButton(text="💼 Карьера", callback_data="work_career_button")
        button5 = InlineKeyboardButton(text="💊 Здоровье", callback_data="health_disease_button")
        button7 = InlineKeyboardButton(text="💡 Рекомендации", callback_data="tips_button")
        button8 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button2, button3, button1, button4, button5, button7, button8)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await bot.send_message(chat_id=callback_query.message.chat.id, text=description, reply_markup=inline_keyboard, parse_mode=ParseMode.HTML)

    else:
        await bot.send_message(callback_query.message.chat.id, 'К сожалению, информация о знаке зодиака на этот день не найдена.')

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'girl_day', state=UserInput.waiting_for_dob)
async def show_girl_day(callback_query: types.CallbackQuery, state: FSMContext):
    dob = datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date()
    day_month = dob.strftime('%d.%m')

    cursor.execute('SELECT girl_day FROM zodiac_day WHERE day_number=?', (day_month,))
    result = cursor.fetchone()

    if result is not None:
        particulars_horoscope = result[0]

        description = f"<b>Характеристика женщин рожденных {day_month}</b>\n\n"
        description += f"{particulars_horoscope}\n\n"

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="🌱 Основная характеристика", callback_data="zodiac_", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="💑 Отношения", callback_data="love_horoscope_button")
        button2 = InlineKeyboardButton(text="👨 Мужчина", callback_data="man_day")
        button3 = InlineKeyboardButton(text="✅ Женщина", callback_data="girl_day")
        button4 = InlineKeyboardButton(text="💼 Карьера", callback_data="work_career_button")
        button5 = InlineKeyboardButton(text="💊 Здоровье", callback_data="health_disease_button")
        button7 = InlineKeyboardButton(text="💡 Рекомендации", callback_data="tips_button")
        button8 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button2, button3, button1, button4, button5, button7, button8)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await bot.send_message(chat_id=callback_query.message.chat.id, text=description, reply_markup=inline_keyboard, parse_mode=ParseMode.HTML)

    else:
        await bot.send_message(callback_query.message.chat.id, 'К сожалению, информация о знаке зодиака на этот день не найдена.')

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'work_career_button', state=UserInput.waiting_for_dob)
async def show_work_career(callback_query: types.CallbackQuery, state: FSMContext):
    dob = datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date()
    day_month = dob.strftime('%d.%m')

    cursor.execute('SELECT work_career FROM zodiac_day WHERE day_number=?', (day_month,))
    result = cursor.fetchone()

    if result is not None:
        particulars_horoscope = result[0]

        description = f"<b>Работа и Карьера рожденных {day_month}</b>\n\n"
        description += f"{particulars_horoscope}\n\n"

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="🌱 Основная характеристика", callback_data="zodiac_", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="💑 Отношения", callback_data="love_horoscope_button")
        button2 = InlineKeyboardButton(text="👨 Мужчина", callback_data="man_day")
        button3 = InlineKeyboardButton(text="👩 Женщина", callback_data="girl_day")
        button4 = InlineKeyboardButton(text="✅ Карьера", callback_data="work_career_button")
        button5 = InlineKeyboardButton(text="💊 Здоровье", callback_data="health_disease_button")
        button7 = InlineKeyboardButton(text="💡 Рекомендации", callback_data="tips_button")
        button8 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button2, button3, button1, button4, button5, button7, button8)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await bot.send_message(chat_id=callback_query.message.chat.id, text=description, reply_markup=inline_keyboard, parse_mode=ParseMode.HTML)

    else:
        await bot.send_message(callback_query.message.chat.id, 'К сожалению, информация о знаке зодиака на этот день не найдена.')

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'health_disease_button', state=UserInput.waiting_for_dob)
async def show_health_disease(callback_query: types.CallbackQuery, state: FSMContext):
    dob = datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date()
    day_month = dob.strftime('%d.%m')

    cursor.execute('SELECT health_disease FROM zodiac_day WHERE day_number=?', (day_month,))
    result = cursor.fetchone()

    if result is not None:
        particulars_horoscope = result[0]

        description = f"<b>Здоровье рожденных {day_month}</b>\n\n"
        description += f"{particulars_horoscope}\n\n"

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="🌱 Основная характеристика", callback_data="zodiac_", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="💑 Отношения", callback_data="love_horoscope_button")
        button2 = InlineKeyboardButton(text="👨 Мужчина", callback_data="man_day")
        button3 = InlineKeyboardButton(text="👩 Женщина", callback_data="girl_day")
        button4 = InlineKeyboardButton(text="💼 Карьера", callback_data="work_career_button")
        button5 = InlineKeyboardButton(text="✅ Здоровье", callback_data="health_disease_button")
        button7 = InlineKeyboardButton(text="💡 Рекомендации", callback_data="tips_button")
        button8 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button2, button3, button1, button4, button5, button7, button8)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await bot.send_message(chat_id=callback_query.message.chat.id, text=description, reply_markup=inline_keyboard, parse_mode=ParseMode.HTML)

    else:
        await bot.send_message(callback_query.message.chat.id, 'К сожалению, информация о знаке зодиака на этот день не найдена.')

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'tips_button', state=UserInput.waiting_for_dob)
async def show_tips(callback_query: types.CallbackQuery, state: FSMContext):
    dob = datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date()
    day_month = dob.strftime('%d.%m')

    cursor.execute('SELECT tips FROM zodiac_day WHERE day_number=?', (day_month,))
    result = cursor.fetchone()

    if result is not None:
        particulars_horoscope = result[0]

        description = f"<b>Советы рожденным {day_month}</b>\n\n"
        description += f"{particulars_horoscope}\n\n"

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="🌱 Основная характеристика", callback_data="zodiac_", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="💑 Отношения", callback_data="love_horoscope_button")
        button2 = InlineKeyboardButton(text="👨 Мужчина", callback_data="man_day")
        button3 = InlineKeyboardButton(text="👩 Женщина", callback_data="girl_day")
        button4 = InlineKeyboardButton(text="💼 Карьера", callback_data="work_career_button")
        button5 = InlineKeyboardButton(text="💊 Здоровье", callback_data="health_disease_button")
        button7 = InlineKeyboardButton(text="✅ Рекомендации", callback_data="tips_button")
        button8 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button2, button3, button1, button4, button5, button7, button8)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await bot.send_message(chat_id=callback_query.message.chat.id, text=description, reply_markup=inline_keyboard, parse_mode=ParseMode.HTML)

    else:
        await bot.send_message(callback_query.message.chat.id, 'К сожалению, информация о знаке зодиака на этот день не найдена.')

#КАРТЫ СУДЬБЫ 👇
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('card_description'), state=UserInput.waiting_for_dob)
async def show_card_description(callback_query: types.CallbackQuery, state: FSMContext):
    dob = datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date()
    cursor.execute('SELECT * FROM aceqace WHERE card_day_month=?', (dob.strftime('%d.%m'),))
    result = cursor.fetchone()
    if result is not None:
        short_description = result[4]
        personality_description = result[5]
        card_description = f"<b>Карта рождения:</b> {result[1]} ({result[3]})\n\n"
        description = card_description + short_description + "\n\n" + personality_description

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="👫 Отношения", callback_data="love_relationship")
        button2 = InlineKeyboardButton(text="🌠 Особенности", callback_data="planetary_control_maps")
        button3 = InlineKeyboardButton(text="🌀 Способности", callback_data="karmic_maps")
        button4 = InlineKeyboardButton(text="💡 Рекомендации", callback_data="planetary_sequence")
        button5 = InlineKeyboardButton(text="👤 Личные карты", callback_data="personal_charts")
        button6 = InlineKeyboardButton(text="⚙ О методе", callback_data="about_method")
        button7 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="✅ Карта рождения", callback_data="card_description")
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

        await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, text=description, reply_markup=inline_keyboard, parse_mode=ParseMode.HTML)
    else:
        await bot.send_message(callback_query.message.chat.id, 'К сожалению, информация о карте не найдена.')

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'love_relationship', state=UserInput.waiting_for_dob)
async def show_love_relationship(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT love_relationship FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="✅ Отношения", callback_data="love_relationship")
        button2 = InlineKeyboardButton(text="🌠 Особенности", callback_data="planetary_control_maps")
        button3 = InlineKeyboardButton(text="🌀 Способности", callback_data="karmic_maps")
        button4 = InlineKeyboardButton(text="💡 Рекомендации", callback_data="planetary_sequence")
        button5 = InlineKeyboardButton(text="👤 Личные карты", callback_data="personal_charts")
        button7 = InlineKeyboardButton(text="⚙ О методе", callback_data="about_method")
        button8 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button1, button2, button3, button4, button5, button7, button8)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="🃏 Карта рождения", callback_data="card_description")
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'planetary_control_maps', state=UserInput.waiting_for_dob)
async def show_planetary_control_maps(callback_query: types.CallbackQuery, state: FSMContext):
    dob = datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date()
    cursor.execute('SELECT planetary_control_maps FROM aceqace WHERE card_day_month=?', (dob.strftime('%d.%m'),))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="👫 Отношения", callback_data="love_relationship")
        button2 = InlineKeyboardButton(text="✅ Особенности", callback_data="planetary_control_maps")
        button3 = InlineKeyboardButton(text="🌀 Способности", callback_data="karmic_maps")
        button4 = InlineKeyboardButton(text="💡 Рекомендации", callback_data="planetary_sequence")
        button5 = InlineKeyboardButton(text="👤 Личные карты", callback_data="personal_charts")
        button7 = InlineKeyboardButton(text="⚙ О методе", callback_data="about_method")
        button8 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button1, button2, button3, button4, button5, button7, button8)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О картах планетарного управления", callback_data="about_planetary", row_width=1)
        inline_keyboard_3.add(button_about_planets)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="🃏 Карта рождения", callback_data="card_description")
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_3.inline_keyboard + inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'about_planetary', state=UserInput.waiting_for_dob)
async def show_about_planetary(callback_query: types.CallbackQuery, state: FSMContext):
    dob = datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date()
    cursor.execute('SELECT about_planetary FROM aceqace WHERE card_day_month=?', (dob.strftime('%d.%m'),))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="👫 Отношения", callback_data="love_relationship")
        button2 = InlineKeyboardButton(text="✅ Особенности", callback_data="planetary_control_maps")
        button3 = InlineKeyboardButton(text="🌀 Способности", callback_data="karmic_maps")
        button4 = InlineKeyboardButton(text="💡 Рекомендации", callback_data="planetary_sequence")
        button5 = InlineKeyboardButton(text="👤 Личные карты", callback_data="personal_charts")
        button6 = InlineKeyboardButton(text="🃏 Карта рождения", callback_data="card_description")
        button7 = InlineKeyboardButton(text="⚙ О методе", callback_data="about_method")
        button8 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="✅ О картах планетарного управления", callback_data="about_planetary", row_width=1)
        inline_keyboard_3.add(button_about_planets)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="🃏 Карта рождения", callback_data="card_description")
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_3.inline_keyboard + inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'karmic_maps', state=UserInput.waiting_for_dob)
async def show_karmic_maps(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT karmic_maps FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = "Кармические карты\n\n" + data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="👫 Отношения", callback_data="love_relationship")
        button2 = InlineKeyboardButton(text="🌠 Особенности", callback_data="planetary_control_maps")
        button3 = InlineKeyboardButton(text="✅ Способности", callback_data="karmic_maps")
        button4 = InlineKeyboardButton(text="💡 Рекомендации", callback_data="planetary_sequence")
        button5 = InlineKeyboardButton(text="👤 Личные карты", callback_data="personal_charts")
        button7 = InlineKeyboardButton(text="⚙ О методе", callback_data="about_method")
        button8 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button1, button2, button3, button4, button5, button7, button8)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О кармических картах", callback_data="about_karmic", row_width=1)
        inline_keyboard_3.add(button_about_planets)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="🃏 Карта рождения", callback_data="card_description")
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_3.inline_keyboard + inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'about_karmic', state=UserInput.waiting_for_dob)
async def show_about_karmic(callback_query: types.CallbackQuery, state: FSMContext):
    dob = datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date()
    cursor.execute('SELECT about_karmic FROM aceqace WHERE card_day_month=?', (dob.strftime('%d.%m'),))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        button1 = InlineKeyboardButton(text="👫 Отношения", callback_data="love_relationship")
        button2 = InlineKeyboardButton(text="🌠 Особенности", callback_data="planetary_control_maps")
        button3 = InlineKeyboardButton(text="✅ Способности", callback_data="karmic_maps")
        button4 = InlineKeyboardButton(text="💡 Рекомендации", callback_data="planetary_sequence")
        button5 = InlineKeyboardButton(text="👤 Личные карты", callback_data="personal_charts")
        button6 = InlineKeyboardButton(text="🃏 Карта рождения", callback_data="card_description")
        button7 = InlineKeyboardButton(text="⚙ О методе", callback_data="about_method")
        button8 = InlineKeyboardButton(text="Вернуться", callback_data="back")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="✅ О кармических картах", callback_data="about_karmic", row_width=1)
        inline_keyboard_3.add(button_about_planets)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="🃏 Карта рождения", callback_data="card_description")
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_3.inline_keyboard + inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'planetary_sequence', state=UserInput.waiting_for_dob)
async def show_planetary_sequence(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT planetary_sequence FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Меркурий", callback_data="map_mercury")
        button2 = InlineKeyboardButton(text="Венера", callback_data="map_veners")
        button3 = InlineKeyboardButton(text="Марс", callback_data="map_marce")
        button4 = InlineKeyboardButton(text="Юпитер", callback_data="map_jupiter")
        button5 = InlineKeyboardButton(text="Сатурн", callback_data="map_saturn")
        button6 = InlineKeyboardButton(text="Уран", callback_data="map_uranium")
        button7 = InlineKeyboardButton(text="Нептун", callback_data="map_neptune")
        button8 = InlineKeyboardButton(text="Плутон", callback_data="map_life_objective")
        button9 = InlineKeyboardButton(text="Результат", callback_data="map_result")
        button10 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8, button9, button10)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О планетах", callback_data="about_planets", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'personal_charts', state=UserInput.waiting_for_dob)
async def show_personal_charts(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT personal_charts FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Валеты", callback_data="personal_jacks")
        button2 = InlineKeyboardButton(text="Дамы", callback_data="personal_lady")
        button3 = InlineKeyboardButton(text="Короли", callback_data="personal_kings")
        button4 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="✅ О личных картах", callback_data="personal_charts", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'personal_jacks', state=UserInput.waiting_for_dob)
async def show_personal_jacks(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT personal_jacks FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="✅ Валеты", callback_data="personal_jacks")
        button2 = InlineKeyboardButton(text="Дамы", callback_data="personal_lady")
        button3 = InlineKeyboardButton(text="Короли", callback_data="personal_kings")
        button4 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О личных картах", callback_data="personal_charts", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'personal_lady', state=UserInput.waiting_for_dob)
async def show_personal_lady(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT personal_lady FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Валеты", callback_data="personal_jacks")
        button2 = InlineKeyboardButton(text="✅ Дамы", callback_data="personal_lady")
        button3 = InlineKeyboardButton(text="Короли", callback_data="personal_kings")
        button4 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О личных картах", callback_data="personal_charts", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'personal_kings', state=UserInput.waiting_for_dob)
async def show_personal_kings(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT personal_kings FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Валеты", callback_data="personal_jacks")
        button2 = InlineKeyboardButton(text="Дамы", callback_data="personal_lady")
        button3 = InlineKeyboardButton(text="✅ Короли", callback_data="personal_kings")
        button4 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О личных картах", callback_data="personal_charts", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'about_method', state=UserInput.waiting_for_dob)
async def show_about_method(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT about_method FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="✅ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'spades', state=UserInput.waiting_for_dob)
async def show_spades(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT spades FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="✅ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'hearts', state=UserInput.waiting_for_dob)
async def show_hearts(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT hearts FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="✅ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'treffs', state=UserInput.waiting_for_dob)
async def show_treffs(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT treffs FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="✅ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'tambourines', state=UserInput.waiting_for_dob)
async def show_tambourines(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT tambourines FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="✅ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'jacks_1', state=UserInput.waiting_for_dob)
async def show_jacks_1(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT jacks_1 FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="✅ Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'ladies_1', state=UserInput.waiting_for_dob)
async def show_ladies_1(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT ladies_1 FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="✅ Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'kings_1', state=UserInput.waiting_for_dob)
async def show_kings_1(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT kings_1 FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="✅ Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'aces', state=UserInput.waiting_for_dob)
async def show_aces(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT aces FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="✅ Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'twos', state=UserInput.waiting_for_dob)
async def show_twos(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT twos FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="✅ Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'triplets', state=UserInput.waiting_for_dob)
async def show_triplets(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT triplets FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="✅ Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'fours', state=UserInput.waiting_for_dob)
async def show_fours(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT fours FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="✅ Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'fives', state=UserInput.waiting_for_dob)
async def show_fives(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT fives FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="✅ Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'sixes', state=UserInput.waiting_for_dob)
async def show_sixes(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT sixes FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="✅ Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'sevens', state=UserInput.waiting_for_dob)
async def show_sevens(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT sevens FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="✅ Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'eights', state=UserInput.waiting_for_dob)
async def show_eights(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT eights FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="✅ Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'nines', state=UserInput.waiting_for_dob)
async def show_nines(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT nines FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="✅ Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'dozens', state=UserInput.waiting_for_dob)
async def show_dozens(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT dozens FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=4)
        button1 = InlineKeyboardButton(text="♠ Пики", callback_data="spades")
        button2 = InlineKeyboardButton(text="♥ Червы", callback_data="hearts")
        button3 = InlineKeyboardButton(text="♣ Трефы", callback_data="treffs")
        button4 = InlineKeyboardButton(text="♦ Бубны", callback_data="tambourines")
        inline_keyboard.add(button1, button2, button3, button4)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О методе", callback_data="about_method", row_width=1)
        inline_keyboard_2.add(button_about_planets)

        inline_keyboard_3 = InlineKeyboardMarkup(row_width=3)
        button6 = InlineKeyboardButton(text="Валеты", callback_data="jacks_1")
        button7 = InlineKeyboardButton(text="Дамы", callback_data="ladies_1")
        button8 = InlineKeyboardButton(text="Короли", callback_data="kings_1")
        inline_keyboard_3.add(button6, button7, button8)

        inline_keyboard_4 = InlineKeyboardMarkup(row_width=5)
        button9 = InlineKeyboardButton(text="Тузы", callback_data="aces")
        button10 = InlineKeyboardButton(text="Двойки", callback_data="twos")
        button11 = InlineKeyboardButton(text="Тройки", callback_data="triplets")
        button12 = InlineKeyboardButton(text="Четверки", callback_data="fours")
        button13 = InlineKeyboardButton(text="Пятерки", callback_data="fives")
        button14 = InlineKeyboardButton(text="Шестерки", callback_data="sixes")
        button15 = InlineKeyboardButton(text="Семерки", callback_data="sevens")
        button16 = InlineKeyboardButton(text="Восьмерки", callback_data="eights")
        button17 = InlineKeyboardButton(text="Девятки", callback_data="nines")
        button18 = InlineKeyboardButton(text="✅ Десятки", callback_data="dozens")
        inline_keyboard_4.add(button9, button10, button11, button12, button13, button14, button15, button16, button17, button18)

        inline_keyboard_5 = InlineKeyboardMarkup(row_width=1)
        button_5 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard_5.add(button_5)

        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard + inline_keyboard_3.inline_keyboard + inline_keyboard_4.inline_keyboard + inline_keyboard_5.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

#Планетарная последовательность
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'about_planets', state=UserInput.waiting_for_dob)
async def show_about_planets(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT about_planets FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Информация о планетах не найдена'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Меркурий", callback_data="map_mercury")
        button2 = InlineKeyboardButton(text="Венера", callback_data="map_veners")
        button3 = InlineKeyboardButton(text="Марс", callback_data="map_marce")
        button4 = InlineKeyboardButton(text="Юпитер", callback_data="map_jupiter")
        button5 = InlineKeyboardButton(text="Сатурн", callback_data="map_saturn")
        button6 = InlineKeyboardButton(text="Уран", callback_data="map_uranium")
        button7 = InlineKeyboardButton(text="Нептун", callback_data="map_neptune")
        button8 = InlineKeyboardButton(text="Плутон", callback_data="map_life_objective")
        button9 = InlineKeyboardButton(text="Результат", callback_data="map_result")
        button10 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8, button9, button10)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="✅ О планетах", callback_data="about_planets", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'map_mercury', state=UserInput.waiting_for_dob)
async def show_map_mercury(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT map_mercury FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="✅ Меркурий", callback_data="map_mercury")
        button2 = InlineKeyboardButton(text="Венера", callback_data="map_veners")
        button3 = InlineKeyboardButton(text="Марс", callback_data="map_marce")
        button4 = InlineKeyboardButton(text="Юпитер", callback_data="map_jupiter")
        button5 = InlineKeyboardButton(text="Сатурн", callback_data="map_saturn")
        button6 = InlineKeyboardButton(text="Уран", callback_data="map_uranium")
        button7 = InlineKeyboardButton(text="Нептун", callback_data="map_neptune")
        button8 = InlineKeyboardButton(text="Плутон", callback_data="map_life_objective")
        button9 = InlineKeyboardButton(text="Результат", callback_data="map_result")
        button10 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8, button9, button10)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О планетах", callback_data="about_planets", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'map_veners', state=UserInput.waiting_for_dob)
async def show_map_veners(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT map_veners FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Меркурий", callback_data="map_mercury")
        button2 = InlineKeyboardButton(text="✅ Венера", callback_data="map_veners")
        button3 = InlineKeyboardButton(text="Марс", callback_data="map_marce")
        button4 = InlineKeyboardButton(text="Юпитер", callback_data="map_jupiter")
        button5 = InlineKeyboardButton(text="Сатурн", callback_data="map_saturn")
        button6 = InlineKeyboardButton(text="Уран", callback_data="map_uranium")
        button7 = InlineKeyboardButton(text="Нептун", callback_data="map_neptune")
        button8 = InlineKeyboardButton(text="Плутон", callback_data="map_life_objective")
        button9 = InlineKeyboardButton(text="Результат", callback_data="map_result")
        button10 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8, button9, button10)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О планетах", callback_data="about_planets", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'map_marce', state=UserInput.waiting_for_dob)
async def show_map_marce(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT map_marce FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Меркурий", callback_data="map_mercury")
        button2 = InlineKeyboardButton(text="Венера", callback_data="map_veners")
        button3 = InlineKeyboardButton(text="✅ Марс", callback_data="map_marce")
        button4 = InlineKeyboardButton(text="Юпитер", callback_data="map_jupiter")
        button5 = InlineKeyboardButton(text="Сатурн", callback_data="map_saturn")
        button6 = InlineKeyboardButton(text="Уран", callback_data="map_uranium")
        button7 = InlineKeyboardButton(text="Нептун", callback_data="map_neptune")
        button8 = InlineKeyboardButton(text="Плутон", callback_data="map_life_objective")
        button9 = InlineKeyboardButton(text="Результат", callback_data="map_result")
        button10 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8, button9, button10)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О планетах", callback_data="about_planets", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'map_jupiter', state=UserInput.waiting_for_dob)
async def show_map_jupiter(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT map_jupiter FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Меркурий", callback_data="map_mercury")
        button2 = InlineKeyboardButton(text="Венера", callback_data="map_veners")
        button3 = InlineKeyboardButton(text="Марс", callback_data="map_marce")
        button4 = InlineKeyboardButton(text="✅ Юпитер", callback_data="map_jupiter")
        button5 = InlineKeyboardButton(text="Сатурн", callback_data="map_saturn")
        button6 = InlineKeyboardButton(text="Уран", callback_data="map_uranium")
        button7 = InlineKeyboardButton(text="Нептун", callback_data="map_neptune")
        button8 = InlineKeyboardButton(text="Плутон", callback_data="map_life_objective")
        button9 = InlineKeyboardButton(text="Результат", callback_data="map_result")
        button10 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8, button9, button10)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О планетах", callback_data="about_planets", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'map_saturn', state=UserInput.waiting_for_dob)
async def show_map_saturn(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT map_saturn FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Меркурий", callback_data="map_mercury")
        button2 = InlineKeyboardButton(text="Венера", callback_data="map_veners")
        button3 = InlineKeyboardButton(text="Марс", callback_data="map_marce")
        button4 = InlineKeyboardButton(text="Юпитер", callback_data="map_jupiter")
        button5 = InlineKeyboardButton(text="✅ Сатурн", callback_data="map_saturn")
        button6 = InlineKeyboardButton(text="Уран", callback_data="map_uranium")
        button7 = InlineKeyboardButton(text="Нептун", callback_data="map_neptune")
        button8 = InlineKeyboardButton(text="Плутон", callback_data="map_life_objective")
        button9 = InlineKeyboardButton(text="Результат", callback_data="map_result")
        button10 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8, button9, button10)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О планетах", callback_data="about_planets", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'map_uranium', state=UserInput.waiting_for_dob)
async def show_map_uranium(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT map_uranium FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Меркурий", callback_data="map_mercury")
        button2 = InlineKeyboardButton(text="Венера", callback_data="map_veners")
        button3 = InlineKeyboardButton(text="Марс", callback_data="map_marce")
        button4 = InlineKeyboardButton(text="Юпитер", callback_data="map_jupiter")
        button5 = InlineKeyboardButton(text="Сатурн", callback_data="map_saturn")
        button6 = InlineKeyboardButton(text="✅ Уран", callback_data="map_uranium")
        button7 = InlineKeyboardButton(text="Нептун", callback_data="map_neptune")
        button8 = InlineKeyboardButton(text="Плутон", callback_data="map_life_objective")
        button9 = InlineKeyboardButton(text="Результат", callback_data="map_result")
        button10 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8, button9, button10)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О планетах", callback_data="about_planets", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'map_neptune', state=UserInput.waiting_for_dob)
async def show_map_neptune(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT map_neptune FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Меркурий", callback_data="map_mercury")
        button2 = InlineKeyboardButton(text="Венера", callback_data="map_veners")
        button3 = InlineKeyboardButton(text="Марс", callback_data="map_marce")
        button4 = InlineKeyboardButton(text="Юпитер", callback_data="map_jupiter")
        button5 = InlineKeyboardButton(text="Сатурн", callback_data="map_saturn")
        button6 = InlineKeyboardButton(text="Уран", callback_data="map_uranium")
        button7 = InlineKeyboardButton(text="✅ Нептун", callback_data="map_neptune")
        button8 = InlineKeyboardButton(text="Плутон", callback_data="map_life_objective")
        button9 = InlineKeyboardButton(text="Результат", callback_data="map_result")
        button10 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8, button9, button10)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О планетах", callback_data="about_planets", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'map_life_objective', state=UserInput.waiting_for_dob)
async def show_map_life_objective(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT map_life_objective FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Меркурий", callback_data="map_mercury")
        button2 = InlineKeyboardButton(text="Венера", callback_data="map_veners")
        button3 = InlineKeyboardButton(text="Марс", callback_data="map_marce")
        button4 = InlineKeyboardButton(text="Юпитер", callback_data="map_jupiter")
        button5 = InlineKeyboardButton(text="Сатурн", callback_data="map_saturn")
        button6 = InlineKeyboardButton(text="Уран", callback_data="map_uranium")
        button7 = InlineKeyboardButton(text="Нептун", callback_data="map_neptune")
        button8 = InlineKeyboardButton(text="✅ Плутон", callback_data="map_life_objective")
        button9 = InlineKeyboardButton(text="Результат", callback_data="map_result")
        button10 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8, button9, button10)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О планетах", callback_data="about_planets", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'map_result', state=UserInput.waiting_for_dob)
async def show_map_result(callback_query: types.CallbackQuery, state: FSMContext):
    card = determine_destiny_card(datetime.strptime((await state.get_data())['dob'], '%d.%m.%Y').date(), cursor)[0]
    cursor.execute('SELECT map_result FROM aceqace WHERE card=?', (card,))
    data = cursor.fetchone()

    if data is None:
        response = 'Не найден'
    else:
        response = data[0]

        inline_keyboard = InlineKeyboardMarkup(row_width=3)
        button1 = InlineKeyboardButton(text="Меркурий", callback_data="map_mercury")
        button2 = InlineKeyboardButton(text="Венера", callback_data="map_veners")
        button3 = InlineKeyboardButton(text="Марс", callback_data="map_marce")
        button4 = InlineKeyboardButton(text="Юпитер", callback_data="map_jupiter")
        button5 = InlineKeyboardButton(text="Сатурн", callback_data="map_saturn")
        button6 = InlineKeyboardButton(text="Уран", callback_data="map_uranium")
        button7 = InlineKeyboardButton(text="Нептун", callback_data="map_neptune")
        button8 = InlineKeyboardButton(text="Плутон", callback_data="map_life_objective")
        button9 = InlineKeyboardButton(text="✅ Результат", callback_data="map_result")
        button10 = InlineKeyboardButton(text="Назад", callback_data="card_description")
        inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8, button9, button10)

        inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
        button_about_planets = InlineKeyboardButton(text="❓ О планетах", callback_data="about_planets", row_width=1)
        inline_keyboard_2.add(button_about_planets)
        inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(callback_query.from_user.id, response, reply_markup=inline_keyboard)

# ЖИЗНЕННЫЙ ПУТЬ 💫
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('purpose'), state=UserInput.waiting_for_dob)
async def cmd_purpose(callback_query: types.CallbackQuery, state: FSMContext):
    ruling_number = callback_query.data.split('_')[1]
    user_data = await state.get_data()
    dob_string = user_data['dob']

    cursor.execute("SELECT meaning FROM ruling_numbers WHERE number = ?", (ruling_number,))
    result = cursor.fetchone()
    meaning = result[0] if result else "Информация не найдена"

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    button1 = InlineKeyboardButton(text='🎯 Цель жизни', callback_data=f'life_purpose_{ruling_number}')
    button2 = InlineKeyboardButton(text='🌟 Самореализация', callback_data=f'self_actualization_{ruling_number}')
    button3 = InlineKeyboardButton(text='🎨 Особенности', callback_data=f'characteristics_{ruling_number}')
    button4 = InlineKeyboardButton(text='🚫 Недостатки', callback_data=f'negative_trends_{ruling_number}')
    button5 = InlineKeyboardButton(text='🔝 Рекомендации', callback_data=f'recommended_destinations_{ruling_number}')
    button6 = InlineKeyboardButton(text='🧭 Направления', callback_data=f'suitable_occupations_{ruling_number}')
    button7 = InlineKeyboardButton(text='Вернуться', callback_data='back')
    inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7)

    inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
    button_about_planets = InlineKeyboardButton(text="✅ Правящее число", callback_data=f'purpose_{ruling_number}')
    inline_keyboard_2.add(button_about_planets)

    inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)

    response = f'🔢 Ваше правящее число: {ruling_number} 🔢\n\n{meaning}'
    await bot.send_message(callback_query.message.chat.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('life_purpose'), state=UserInput.waiting_for_dob)
async def cmd_life_purpose(callback_query: types.CallbackQuery, state: FSMContext):
    ruling_number = callback_query.data.split('_')[2]

    cursor.execute("SELECT life_purpose FROM ruling_numbers WHERE number = ?", (ruling_number,))
    result = cursor.fetchone()
    life_purpose = result[0] if result else "Информация не найдена"

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    button1 = InlineKeyboardButton(text='✅ Цель жизни', callback_data=f'life_purpose_{ruling_number}')
    button2 = InlineKeyboardButton(text='🌟 Самореализация', callback_data=f'self_actualization_{ruling_number}')
    button3 = InlineKeyboardButton(text='🎨 Особенности', callback_data=f'characteristics_{ruling_number}')
    button4 = InlineKeyboardButton(text='🚫 Недостатки', callback_data=f'negative_trends_{ruling_number}')
    button5 = InlineKeyboardButton(text='🔝 Рекомендации', callback_data=f'recommended_destinations_{ruling_number}')
    button6 = InlineKeyboardButton(text='🧭 Направления', callback_data=f'suitable_occupations_{ruling_number}')
    button7 = InlineKeyboardButton(text='Вернуться', callback_data='back')
    inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7)

    inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
    button_about_planets = InlineKeyboardButton(text="🔢 Правящее число", callback_data=f'purpose_{ruling_number}')
    inline_keyboard_2.add(button_about_planets)
    inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)

    response = f'🎯 Цель жизни для числа {ruling_number}:\n\n{life_purpose}'
    await bot.send_message(callback_query.message.chat.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('self_actualization'), state=UserInput.waiting_for_dob)
async def cmd_self_actualization(callback_query: types.CallbackQuery, state: FSMContext):
    ruling_number = callback_query.data.split('_')[2]

    cursor.execute("SELECT self_actualization FROM ruling_numbers WHERE number = ?", (ruling_number,))
    result = cursor.fetchone()
    self_actualization = result[0] if result else "Информация не найдена"

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    button1 = InlineKeyboardButton(text='🎯 Цель жизни', callback_data=f'life_purpose_{ruling_number}')
    button2 = InlineKeyboardButton(text='✅ Самореализация', callback_data=f'self_actualization_{ruling_number}')
    button3 = InlineKeyboardButton(text='🎨 Особенности', callback_data=f'characteristics_{ruling_number}')
    button4 = InlineKeyboardButton(text='🚫 Недостатки', callback_data=f'negative_trends_{ruling_number}')
    button5 = InlineKeyboardButton(text='🔝 Рекомендации', callback_data=f'recommended_destinations_{ruling_number}')
    button6 = InlineKeyboardButton(text='🧭 Направления', callback_data=f'suitable_occupations_{ruling_number}')
    button7 = InlineKeyboardButton(text='Вернуться', callback_data='back')
    inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7)

    inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
    button_about_planets = InlineKeyboardButton(text="🔢 Правящее число", callback_data=f'purpose_{ruling_number}')
    inline_keyboard_2.add(button_about_planets)
    inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)

    response = f'🌟 Самореализация для числа {ruling_number}:\n\n{self_actualization}'
    await bot.send_message(callback_query.message.chat.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('characteristics'), state=UserInput.waiting_for_dob)
async def cmd_characteristics(callback_query: types.CallbackQuery, state: FSMContext):
    ruling_number = callback_query.data.split('_')[1]
    
    cursor.execute("SELECT characteristics FROM ruling_numbers WHERE number = ?", (ruling_number,))
    result = cursor.fetchone()
    characteristics = result[0] if result else "Информация не найдена"
    
    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    button1 = InlineKeyboardButton(text='🎯 Цель жизни', callback_data=f'life_purpose_{ruling_number}')
    button2 = InlineKeyboardButton(text='🌟 Самореализация', callback_data=f'self_actualization_{ruling_number}')
    button3 = InlineKeyboardButton(text='✅ Особенности', callback_data=f'characteristics_{ruling_number}')
    button4 = InlineKeyboardButton(text='🚫 Недостатки', callback_data=f'negative_trends_{ruling_number}')
    button5 = InlineKeyboardButton(text='🔝 Рекомендации', callback_data=f'recommended_destinations_{ruling_number}')
    button6 = InlineKeyboardButton(text='🧭 Направления', callback_data=f'suitable_occupations_{ruling_number}')
    button7 = InlineKeyboardButton(text='Вернуться', callback_data='back')
    inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7)

    inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
    button_about_planets = InlineKeyboardButton(text="🔢 Правящее число", callback_data=f'purpose_{ruling_number}')
    inline_keyboard_2.add(button_about_planets)
    inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    
    response = f'🎨 Характерные черты для числа {ruling_number}:\n\n{characteristics}'
    await bot.send_message(callback_query.message.chat.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('negative_trends'), state=UserInput.waiting_for_dob)
async def cmd_negative_trends(callback_query: types.CallbackQuery, state: FSMContext):
    ruling_number = callback_query.data.split('_')[2]

    cursor.execute("SELECT negative_trends FROM ruling_numbers WHERE number = ?", (ruling_number,))
    result = cursor.fetchone()
    negative_trends = result[0] if result else "Информация не найдена"

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    button1 = InlineKeyboardButton(text='🎯 Цель жизни', callback_data=f'life_purpose_{ruling_number}')
    button2 = InlineKeyboardButton(text='🌟 Самореализация', callback_data=f'self_actualization_{ruling_number}')
    button3 = InlineKeyboardButton(text='🎨 Особенности', callback_data=f'characteristics_{ruling_number}')
    button4 = InlineKeyboardButton(text='✅ Недостатки', callback_data=f'negative_trends_{ruling_number}')
    button5 = InlineKeyboardButton(text='🔝 Рекомендации', callback_data=f'recommended_destinations_{ruling_number}')
    button6 = InlineKeyboardButton(text='🧭 Направления', callback_data=f'suitable_occupations_{ruling_number}')
    button7 = InlineKeyboardButton(text='Вернуться', callback_data='back')
    inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7)

    inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
    button_about_planets = InlineKeyboardButton(text="🔢 Правящее число", callback_data=f'purpose_{ruling_number}')
    inline_keyboard_2.add(button_about_planets)
    inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)

    response = f'🚫 Негативные тенденции для числа {ruling_number}:\n\n{negative_trends}'
    await bot.send_message(callback_query.message.chat.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('recommended_destinations'), state=UserInput.waiting_for_dob)
async def cmd_recommended_destinations(callback_query: types.CallbackQuery, state: FSMContext):
    ruling_number = callback_query.data.split('_')[2]

    cursor.execute("SELECT recommended_destinations FROM ruling_numbers WHERE number = ?", (ruling_number,))
    result = cursor.fetchone()
    recommended_destinations = result[0] if result else "Информация не найдена"

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    button1 = InlineKeyboardButton(text='🎯 Цель жизни', callback_data=f'life_purpose_{ruling_number}')
    button2 = InlineKeyboardButton(text='🌟 Самореализация', callback_data=f'self_actualization_{ruling_number}')
    button3 = InlineKeyboardButton(text='🎨 Особенности', callback_data=f'characteristics_{ruling_number}')
    button4 = InlineKeyboardButton(text='🚫 Недостатки', callback_data=f'negative_trends_{ruling_number}')
    button5 = InlineKeyboardButton(text='✅ Рекомендации', callback_data=f'recommended_destinations_{ruling_number}')
    button6 = InlineKeyboardButton(text='🧭 Направления', callback_data=f'suitable_occupations_{ruling_number}')
    button7 = InlineKeyboardButton(text='Вернуться', callback_data='back')
    inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7)

    inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
    button_about_planets = InlineKeyboardButton(text="🔢 Правящее число", callback_data=f'purpose_{ruling_number}')
    inline_keyboard_2.add(button_about_planets)
    inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)

    response = f'🔝 Рекомендации для числа {ruling_number}:\n\n{recommended_destinations}'
    await bot.send_message(callback_query.message.chat.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('suitable_occupations'), state=UserInput.waiting_for_dob)
async def cmd_suitable_occupations(callback_query: types.CallbackQuery, state: FSMContext):
    ruling_number = callback_query.data.split('_')[2]

    cursor.execute("SELECT suitable_occupations FROM ruling_numbers WHERE number = ?", (ruling_number,))
    result = cursor.fetchone()
    suitable_occupations = result[0] if result else "Информация не найдена"

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    button1 = InlineKeyboardButton(text='🎯 Цель жизни', callback_data=f'life_purpose_{ruling_number}')
    button2 = InlineKeyboardButton(text='🌟 Самореализация', callback_data=f'self_actualization_{ruling_number}')
    button3 = InlineKeyboardButton(text='🎨 Особенности', callback_data=f'characteristics_{ruling_number}')
    button4 = InlineKeyboardButton(text='🚫 Недостатки', callback_data=f'negative_trends_{ruling_number}')
    button5 = InlineKeyboardButton(text='🔝 Рекомендации', callback_data=f'recommended_destinations_{ruling_number}')
    button6 = InlineKeyboardButton(text='✅ Направления', callback_data=f'suitable_occupations_{ruling_number}')
    button7 = InlineKeyboardButton(text='Вернуться', callback_data='back')
    inline_keyboard.add(button1, button2, button3, button4, button5, button6, button7)

    inline_keyboard_2 = InlineKeyboardMarkup(row_width=1)
    button_about_planets = InlineKeyboardButton(text="🔢 Правящее число", callback_data=f'purpose_{ruling_number}')
    inline_keyboard_2.add(button_about_planets)
    inline_keyboard.inline_keyboard = inline_keyboard_2.inline_keyboard + inline_keyboard.inline_keyboard

    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)

    response = f'🧭 Подходящие профессии для числа {ruling_number}:\n\n{suitable_occupations}'
    await bot.send_message(callback_query.message.chat.id, response, reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'back', state=UserInput.waiting_for_dob)
async def cmd_back(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    dob_string = user_data.get('dob', None)

    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await send_dob_info_message(bot, callback_query.message.chat.id, datetime.strptime(dob_string, '%d.%m.%Y').date() if dob_string else None)

#Числа ДР🔢
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('dr_numbers'), state=UserInput.waiting_for_dob)
async def cmd_dr_numbers(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    dob_string = user_data['dob']

    # Получите количества чисел в дате рождения с помощью функции count_digit_occurrences
    count_dict = count_digit_occurrences(dob_string)

    # Определите, сколько чисел содержит дата рождения
    num_of_digits = len(set(count_dict.values()))

    # Выберите соответствующий столбец в таблице SQLite
    if num_of_digits == 1:
        column_name = 'one_unit'
    elif num_of_digits == 2:
        column_name = 'two_units'
    elif num_of_digits == 3:
        column_name = 'three_units'
    elif num_of_digits == 4:
        column_name = 'four_units'
    else:
        column_name = 'five_units'

    # Запросите информацию из таблицы SQLite
    cursor.execute(f'SELECT {column_name} FROM DR_numbers')
    data = cursor.fetchone()

    if data is None:
        response = 'Информация не найдена'
    else:
        response = data[0]  # В данном примере используется первый элемент кортежа, так как SELECT вернет одно значение

    # Отправьте сообщение с информацией о числах в дате рождения
    await bot.send_message(callback_query.message.chat.id, response)



if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
