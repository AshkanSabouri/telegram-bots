import os
from dotenv import load_dotenv
import psycopg2
import logging
from datetime import datetime, timedelta
from telebot import TeleBot, types
from geopy.distance import geodesic
from persiantools.jdatetime import JalaliDate, JalaliDateTime

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')

TOKEN = os.getenv('TELEGRAM_API_TOKEN')

logging.basicConfig(level=logging.INFO)

bot = TeleBot(TOKEN)

conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST
)
cursor = conn.cursor()

# Function to get allowed locations from the database
def get_allowed_locations_from_db():
    cursor.execute('SELECT location_nickname, latitude, longitude FROM allowed_locations')
    allowed_locations = {}
    for row in cursor.fetchall():
        location_nickname, latitude, longitude = row
        allowed_locations[location_nickname] = (latitude, longitude)
    return allowed_locations

# Function to get the closest allowed location to the user's location
def get_closest_allowed_location(user_location):
    threshold_distance = 100
    closest_location = None
    min_distance = float('inf')

    allowed_locations = get_allowed_locations_from_db()

    for location_nickname, location_coords in allowed_locations.items():
        distance = geodesic(user_location, location_coords).meters
        if distance <= threshold_distance and distance < min_distance:
            closest_location = location_nickname
            min_distance = distance

    return closest_location

user_last_action = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    enter_button = types.KeyboardButton('ورود')
    exit_button = types.KeyboardButton('خروج')
    markup.add(enter_button, exit_button)
    bot.send_message(message.chat.id, "با سلام 🖐\nبه ربات حضور و غیاب شرکت آیریک خوش آمدید.\nلطفا یکی از گزینه های زیر را انتخاب نمایید. ⌨️\n", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ['ورود', 'خروج'])
def handle_button_press(message):
    user_last_action[message.chat.id] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    location_button = types.KeyboardButton('اشتراک گذاری', request_location=True)
    markup.add(location_button)
    bot.send_message(message.chat.id, f"لطفا جهت ثبت موقعیت {message.text.lower()} لوکیشن خود را با ما به اشتراک بگذارید.", reply_markup=markup)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    chat_id = message.chat.id
    nickname = message.from_user.username or message.from_user.first_name
    user_location = (message.location.latitude, message.location.longitude)

    action = user_last_action.get(chat_id)

    location_nickname = get_closest_allowed_location(user_location)
    if location_nickname is None:
        bot.send_message(chat_id, "⛔️ موقعیت شما در لیست لوکیشن های مجاز برای حضور و غیاب نیست . لطفا فاصله خود را به شرکت مورد نظر نزدیک تر کنید . ⛔️")
        return

    if action == 'ورود':
        cursor.execute('SELECT * FROM attendance WHERE chat_id = %s AND exit_time IS NULL', (chat_id,))
        record = cursor.fetchone()

        if record is None:
            enter_time_shamsi = JalaliDateTime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('INSERT INTO attendance (chat_id, nickname, enter_time, enter_location_nickname) VALUES (%s, %s, %s, %s)',
                           (chat_id, nickname, enter_time_shamsi, location_nickname))
            bot.send_message(chat_id, f"ورود شما به {location_nickname} ثبت شد ✅")
        else:
            bot.send_message(chat_id, f"❗️ورود شما به {location_nickname} قبلا ثبت شده.")
    elif action == 'خروج':
        cursor.execute('SELECT id, enter_time FROM attendance WHERE chat_id = %s AND exit_time IS NULL', (chat_id,))
        record = cursor.fetchone()

        if record is not None:
            exit_time_shamsi = JalaliDateTime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('UPDATE attendance SET exit_time = %s, exit_location_nickname = %s WHERE id = %s',
                            (exit_time_shamsi, location_nickname, record[0]))
            bot.send_message(chat_id, f"خروج شما از {location_nickname} ثبت شد ✅")
        else:
            bot.send_message(chat_id, f"❗️ورود شما به {location_nickname} هنوز ثبت نشده")

    user_last_action.pop(chat_id, None)  # Remove the user's last action
    send_welcome(message)  # Send the welcome/start menu again

    conn.commit()

bot.polling(none_stop=True)

cursor.close()
conn.close()
