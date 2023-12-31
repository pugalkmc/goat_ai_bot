import datetime
from pymongo import MongoClient
from goat_ai import generate_ai_content
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import config

bot = Bot(config.BOT_TOKEN)
time_fun = datetime.datetime

mongo_client = MongoClient(config.MONGODB_CONNECTION_STRING)
db = mongo_client["goatdb"]
peoples_col = db["peoples"]
group_col = db["group_col"]
messages_col = db['messages_col']


async def menu_button(update, context, text="Choose Options:"):
    message = update.message
    if message.chat.type == "group" or message.chat.type == "supergroup":
        return

    chat_id = update.message.chat_id
    keyboard = [
        [InlineKeyboardButton("My Project", callback_data="my_project")],
        [InlineKeyboardButton("Functionalities", callback_data="functionalities")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        reply_to_message_id=update.message.message_id,
    )

async def check_user_admin(chat_id, user_id):
    # You can implement your logic here to check if the user is an admin in the group
    return True
