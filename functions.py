import re
from telegram import ReplyKeyboardMarkup , Update , Document
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler , Application
from telegram._bot import Bot
import datetime
import time
import requests
from pymongo import MongoClient
from goat_ai import generate_ai_content
import random


BOT_TOKEN = "6989747287:AAFbdbNWRx_8AQpnxuFqi57ztTX6lCqCt88"

bot = Bot(token=BOT_TOKEN)
time_fun = datetime.datetime

mongo_client = MongoClient("mongodb+srv://pugalkmc:pugalsaran143@cluster0.dnr2yma.mongodb.net/")
db = mongo_client["goatdb"]
peoples_col = db["peoples"]
group_col = db["group_col"]

async def menu_button(update, context,text="Choose Options:"):
    message = update.message
    if message.chat.type == 'group' or message.chat.type == 'supergroup':
        return
    chat_id = update.message.chat_id
    reply_keyboard = []
    reply_keyboard = [["My Project", "Functionalities"]]
    await context.bot.send_message(chat_id=chat_id, text=text,
                                   reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True,
                                                                    one_time_keyboard=True),
                                   reply_to_message_id=update.message.message_id)
    
async def check_user_admin(chat_id, user_id):
    return True