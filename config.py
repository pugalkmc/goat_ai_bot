from os import getenv
from dotenv import load_dotenv

load_dotenv()

""" General config """
# Set ENV to any value to use webhook instead of polling for bot. Must be set in prod environment.
ENV = getenv("ENV")
TZ_OFFSET = 8.0  # (UTC+08:00)
JOB_LIMIT_PER_PERSON = 10
BOT_NAME = "@cron_telebot"


""" Telegram config """
BOT_TOKEN = getenv("BOT_TOKEN")
BOTHOST = getenv("BOTHOST")
URL = getenv('URL')
ADMIN_CHAT_ID = getenv('ADMIN_CHAT_ID')
PORT = getenv('PORT')

""" DB config """
MONGODB_CONNECTION_STRING = getenv("MONGODB_CONNECTION_STRING")

"""OPEN AI"""
OPENAI_API_KEY = getenv("OPENAI_API_KEY")
MODEL_NAME = getenv("MODEL_NAME")