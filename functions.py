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
messages_col = db['message_col']


async def menu_button(update, context, text="Choose Options:"):
    message = update.message
    if message.chat.type == "group" or message.chat.type == "supergroup":
        return

    keyboard = [
        [InlineKeyboardButton("My Project", callback_data="my_project")],
        [InlineKeyboardButton("Functionalities", callback_data="functionalities")],
    ]

    await update.message.chat_id(
          text=text,
          reply_markup=InlineKeyboardMarkup(keyboard),
          reply_to_message_id=update.message.message_id,
    )  
