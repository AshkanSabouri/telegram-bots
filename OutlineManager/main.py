import subprocess
import telebot
import requests
from telebot import types
import logging

# Replace with your bot's API token
API_TOKEN = ''
bot = telebot.TeleBot(API_TOKEN)

# The base URL for the Outline Server's API (replace with your actual API URL)
OUTLINE_API_URL = ''

# Set up logging
# logging.basicConfig(level=logging.DEBUG)

def restart_server(message):
    try:
        # Run the shell script
        result = subprocess.run(['/var/opt/tunnel/tunnel.sh'], check=True, text=True, capture_output=True)
        # Send the output back to the user
        bot.send_message(message.chat.id, f"سرور با موفقیت ری استارت شد:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Command error: {e}")
        bot.send_message(message.chat.id, f"خطا در ری استارت سرور:\n{e.stderr}")
    except Exception as e:
        logging.error(f"Error: {e}")
        bot.send_message(message.chat.id, "خطا در ری استارت سرور.")
    finally:
        show_main_menu(message.chat.id)

# Function to replace host and port in the access URL
def modify_access_url(original_url):
    parts = original_url.split('@')
    if len(parts) == 2:
        modified_url = f"{parts[0]}@127.0.0.1/?outline=1"
        return modified_url
    return original_url

# Function to create inline keyboard buttons for each key
def create_key_buttons(keys):
    markup = types.InlineKeyboardMarkup()
    for key in keys:
        button_text = key.get('name', 'Unnamed Key') or 'بدون نام'
        button = types.InlineKeyboardButton(
            text=button_text,
            callback_data=f"key_{key['id']}"
        )
        markup.add(button)
    markup.add(types.InlineKeyboardButton(text="بازگشت به منو", callback_data="back_to_menu"))
    return markup

# Start command handler
@bot.message_handler(commands=['start'])
def start(message):
    show_main_menu(message.chat.id)

def show_main_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(text="لیست اکانت ها", callback_data="list_keys"),
        types.InlineKeyboardButton(text="ساخت اکانت جدید", callback_data="add_key")
    )
    markup.add(
        types.InlineKeyboardButton(text="اعمال محدودیت کلی", callback_data="set_limit"),
        types.InlineKeyboardButton(text="حذف محدودیت کلی", callback_data="remove_limit")
    )
    markup.add(
        types.InlineKeyboardButton(text="ری استارت سرور", callback_data="restart_server")
    )
    bot.send_message(chat_id, "سلام\nبه ربات مدیریت Outline شرکت آیریک خوش آمدید.\nلطفا از منوی زیر عملیات مورد نظر را انتخاب کنید.", reply_markup=markup)

# Inline button callback handler
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    logging.debug(f"Received callback: {call.data}")
    if call.data == 'list_keys':
        list_keys(call.message)
    elif call.data.startswith('key_'):
        key_id = call.data.split('_')[1]
        handle_key_action(call.message, key_id)
    elif call.data == 'add_key':
        add_key(call.message)
    elif call.data == 'set_limit':
        set_limit(call.message)
    elif call.data == 'remove_limit':
        remove_limit(call.message)
    elif call.data.startswith('rename_'):
        rename_key(call)
    elif call.data.startswith('delete_'):
        delete_key(call)
    elif call.data.startswith('show_'):
        show_key(call)
    elif call.data == 'restart_server':
        restart_server(call.message)
    elif call.data == 'back_to_menu':
        show_main_menu(call.message.chat.id)
    elif call.data == 'cancel_action':
        bot.send_message(call.message.chat.id, "از عملیات صرف نظر شد.")
        show_main_menu(call.message.chat.id)
    else:
        bot.send_message(call.message.chat.id, "عملیات نامعتبر.")

# List all access keys
def list_keys(message):
    try:
        response = requests.get(f'{OUTLINE_API_URL}/access-keys/', verify=False)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        keys = response.json()
        logging.debug(f"Response JSON: {keys}")  # Debug log to check the response

        # Extract the list of keys from the response
        keys_list = keys.get('accessKeys', [])

        if not keys_list:
            bot.send_message(message.chat.id, "اکانتی با این مشخصات یافت نشد!")
            return

        # Create the keyboard markup with key buttons
        markup = create_key_buttons(keys_list)
        bot.send_message(message.chat.id, "لطفا یکی از اکانت ها را انتخاب کنید :", reply_markup=markup)
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        bot.send_message(message.chat.id, "خطا در لیست کردن اکانت ها!")
    except Exception as e:
        logging.error(f"Error: {e}")
        bot.send_message(message.chat.id, "خطا در لیست کردن اکانت ها!")

# Handle actions on a specific key
def handle_key_action(message, key_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(text="نمایش اکانت", callback_data=f"show_{key_id}"),
        types.InlineKeyboardButton(text="تغییر نام اکانت", callback_data=f"rename_{key_id}"),
        types.InlineKeyboardButton(text="حذف اکانت", callback_data=f"delete_{key_id}")
    )
    markup.add(types.InlineKeyboardButton(text="بازگشت به منو", callback_data="back_to_menu"))
    bot.send_message(message.chat.id, f"اکانت با شناسه:\n{key_id}\nعملیات را انتخاب فرمایید:", reply_markup=markup)

# Show the connection key (access URL) for the selected key
def show_key(call):
    key_id = call.data.split('_')[1]
    try:
        response = requests.get(f'{OUTLINE_API_URL}/access-keys/', verify=False)
        response.raise_for_status()
        keys = response.json().get('accessKeys', [])
        for key in keys:
            if key['id'] == key_id:
                modified_access_url = modify_access_url(key['accessUrl'])
                bot.send_message(call.message.chat.id, f"{modified_access_url}")
                return
        bot.send_message(call.message.chat.id, f"اکانت با شناسه: {key_id} یافت نشد!")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        bot.send_message(call.message.chat.id, "خطا در دریافت جزئیات اکانت!")
    except Exception as e:
        logging.error(f"Error: {e}")
        bot.send_message(call.message.chat.id, "خطا در دریافت جزئیات اکانت!")
    finally:
        show_cancel_option(call.message.chat.id)

# Rename an access key
def rename_key(call):
    key_id = call.data.split('_')[1]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="صرف نظر", callback_data="cancel_action"))
    bot.send_message(call.message.chat.id, f"لطفا نام جدید اکانت با شناسه : {key_id} را وارد کنید : ", reply_markup=markup)
    bot.register_next_step_handler(call.message, process_rename_key, key_id)

def process_rename_key(message, key_id):
    new_name = message.text
    try:
        response = requests.put(f'{OUTLINE_API_URL}/access-keys/{key_id}/name', data={'name': new_name}, verify=False)
        if response.status_code == 204:
            bot.send_message(message.chat.id, f"Key ID: {key_id} renamed to {new_name}.")
            show_key_action(message.chat.id, key_id)
        else:
            bot.send_message(message.chat.id, f" خطا در تغییر نام اکانت با شناسه {key_id}!.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        bot.send_message(message.chat.id, f"خطا در تغییر نام اکانت با شناسه {key_id}!.")
    except Exception as e:
        logging.error(f"Error: {e}")
        bot.send_message(message.chat.id, f"خطا در تغییر نام اکانت با شناسه {key_id}!.")
    finally:
        show_cancel_option(message.chat.id)

# Delete an access key by ID
def delete_key(call):
    key_id = call.data.split('_')[1]
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(text="اطمینان از حذف اکانت", callback_data=f"confirm_delete_{key_id}"),
        types.InlineKeyboardButton(text="صرف نظر", callback_data="cancel_action")
    )
    bot.send_message(call.message.chat.id, f"آیا از حذف اکانت با شناسه {key_id}اطمینان دارید ?", reply_markup=markup)

# Confirm delete action
def confirm_delete(call):
    key_id = call.data.split('_')[2]
    try:
        response = requests.delete(f'{OUTLINE_API_URL}/access-keys/{key_id}', verify=False)
        if response.status_code == 204:
            bot.send_message(call.message.chat.id, f"اکانت با شناسه {key_id}حذف شد .")
        else:
            bot.send_message(call.message.chat.id, f"خطا در حذف اکانت با شناسه {key_id}.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        bot.send_message(call.message.chat.id, f"خطا در حذف اکانت با شناسه {key_id}.")
    except Exception as e:
        logging.error(f"Error: {e}")
        bot.send_message(call.message.chat.id, f"خطا در حذف اکانت با شناسه {key_id}.")
    finally:
        show_main_menu(call.message.chat.id)

# Create a new access key
def add_key(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="صرف نظر", callback_data="cancel_action"))
    bot.send_message(message.chat.id, "ساخت اکانت جدید...", reply_markup=markup)
    try:
        response = requests.post(f'{OUTLINE_API_URL}/access-keys', verify=False)
        if response.status_code == 201:
            key_data = response.json()
            modified_access_url = modify_access_url(key_data['accessUrl'])
            bot.send_message(message.chat.id, f"اکانت جدید ساخته شد :\n{modified_access_url}")
        else:
            bot.send_message(message.chat.id, "خطا در ایجاد اکانت.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        bot.send_message(message.chat.id,  "خطا در ایجاد اکانت.")
    except Exception as e:
        logging.error(f"Error: {e}")
        bot.send_message(message.chat.id, "خطا در ایجاد اکانت.")
    finally:
        show_main_menu(message.chat.id)

# Polling for updates
bot.polling()
