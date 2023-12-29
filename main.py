import asyncio
import random
import datetime
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    Application
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
import logging
import pymongo
from contextlib import asynccontextmanager
from http import HTTPStatus
from goat_ai import generate_ai_content
from welcome_conversation import *
from functions import messages_col
from config import *
from functions import *
from goat_ai import *
from train_ai import *

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

DEFAULT_WELCOME_MESSAGES = ["Hey there {user}, Welcome to the {group_name}!"]

# Create FastAPI app
app = FastAPI()

# Initialize the Telegram Updater
dp = Application.builder().token(BOT_TOKEN).build()

# Set the webhook URL (replace with your public URL)
WEBHOOK_URL = "https://e00a-2409-4072-88b-47ea-8066-a3fa-187-20c5.ngrok-free.app/webhook"

# Set your server's port
PORT = 8443

@asynccontextmanager
async def lifespan(_: FastAPI):
    await bot.setWebhook(WEBHOOK_URL)
    async with dp:
        yield

# Your existing routes and handlers
@app.post("/")
async def process_update(request: Request):
    try:
        req = await request.json()
        update = Update.de_json(req, bot)
        await dp.process_update(update)
        return Response(status_code=HTTPStatus.OK)
    except Exception as e:
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content=jsonable_encoder({"error": str(e)}),
        )

# Your existing handlers
async def settings(update, context):
    message = update.message
    chat_id = message.chat_id

    if message.chat.type in ["group", "supergroup"]:
        return
    
    groups_as_admin = list(group_col.find({
        "admin_list": {
            "$elemMatch": {
                "$eq": chat_id
            }
        }
    }))

    keyboard = []
    for i in range(len(groups_as_admin)):
        keyboard.append([InlineKeyboardButton(groups_as_admin[i]['group_title'], callback_data=groups_as_admin[i]['chat_id'])])

    keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")],)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(
        chat_id=chat_id,
        text=f"Select the group you wanted to change the settings and my behaviour to act\n\n",
        reply_markup=reply_markup,
    )

async def start(update, context):
    message = update.message
    chat_id = message.chat_id
    username = message.from_user.username
    if message.chat.type in ["group", "supergroup"]:
        return

    keyboard = [
        [InlineKeyboardButton("Greeting", callback_data="greeting"), InlineKeyboardButton("Chat Assistance", callback_data="chat_assistance")],
        [InlineKeyboardButton("Train Me", callback_data="train_me"), InlineKeyboardButton("Documentation", callback_data="documentation")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(
        chat_id=chat_id,
        text=f"Choose below option:",
        reply_markup=reply_markup,
    )

async def generate_text(update, context):
    message = update.message
    chat_id = message.chat_id
    value = generate_ai_content(message.text)
    await bot.send_message(chat_id=chat_id, text=value)

async def chat_assistance(update, context):
    await bot.send_message(chat_id=update.message.chat_id, text="Chat Assistance is Coming Soon!")

async def new_member(update, context):
    chat = update.effective_chat
    user = update.effective_user
    await bot.send_message(chat_id=chat.id, text=random.choice(DEFAULT_WELCOME_MESSAGES).format(user=user.mention_markdown(), group_name=chat.title))


async def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


@app.post("/")
async def process_update(request: Request):
    req = await request.json()
    update = Update.de_json(req, bot)
    await dp.process_update(update)
    return Response(status_code=HTTPStatus.OK)


async def update_admin_list(update, context):
    chat_id = update.message.chat_id
    bot = context.bot

    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        if bot_member.status in ['administrator', 'creator']:
            pass
        else:
            update.message.reply_text("I don't have admin permission to check admins info")
    except Exception as e:
        print(f"Error checking admin status: {e}")

    members_count = await bot.get_chat_member_count(chat_id)
    admins = await bot.get_chat_administrators(chat_id)
    admin_list = [admin.user.id for admin in admins]
    group_col.update_one(
            {"chat_id": chat_id},
                {
                    "$set": {
                        "latest_admin_list_updated": datetime.datetime.now(),
                        "admin_list": admin_list,
                        'members_count': members_count,
                    }
            }
            )
    await bot.send_message(chat_id=chat_id, text="Admin list updated!")


async def handle_mention_or_reply(update, context):
    message = update.message

        # Extract message details
    message_id = message.message_id
    user_id = message.from_user.id
    chat_id = message.chat_id
    text = message.text
    timestamp = message.date

    # Check if the bot is mentioned in the message or the message is a reply to the bot's message
    if message.text and (f"@{context.bot.username}" in message.text or message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id):
        last_10_messages = list(messages_col.find({"user_id": user_id}).sort("_id", pymongo.DESCENDING).limit(10))
        # Store message details in MongoDB
        messages=[
            {"role": "system", "content": prompt_text},
        ]
        for i in range(len(last_10_messages)-1,0,-1):
            messages.append({"role":"user", 'content': last_10_messages[i]['text']})
            messages.append({"role":"assistant", 'content': last_10_messages[i]['assistant']})

        messages.append({"role": "user", "content": message.text+"\n\nI'm not expecting anything outside from your system behaviour"})
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        response = completion.choices[0].message.content


        messages_col.insert_one({
            'message_id': message_id,
            'user_id': user_id,
            'chat_id': chat_id,
            'text': message.text,
            'assistant': response,
            'timestamp': timestamp,
        })

        await message.reply_text(response)


async def schedule_task(delay, coro):
    await asyncio.sleep(delay)
    await coro

async def delete_message(context):
    try:
        await bot.delete_message(chat_id=context.chat_id, message_id=context.message_id)
    except telegram.error.BadRequest as e:
        print(f"Error deleting message: {e}")

async def new_member(update, context):
    new_members = update.message.new_chat_members
    for member in new_members:
        if member.is_bot and member.id == context.bot.id:
            chat_id = update.effective_chat.id
            group_id = update.effective_chat.id  # Same as chat_id for groups
            group_title = update.effective_chat.title
    
            # Get the current time in Indian Kolkata time zone
            indian_kolkata_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))


            # Store the data in your database or perform any other actions
            # Example: You can use a MongoDB client to store data in MongoDB
            group_col.insert_one({
                'group_title': group_title,
                'chat_id': chat_id,
                'group_id': group_id,
                "welcome_type": 'default',
                "content": "nothing",
                "cost":0,
                'indian_kolkata_time': indian_kolkata_time,
                'latest_admin_list_updated': datetime.datetime.now(),
            })

            await bot.send_message(chat_id=chat_id, text="Hello guys! Just now I'm headed to this community")
        else:
            await bot.send_message(chat_id=update.effective_chat.id, text=f"Welcome {member.full_name}!")

            # **Corrected context usage:**
            asyncio.create_task(schedule_task(10, delete_message(context)))  # Pass `context` directly



def add_handlers(dp):
    dp.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    dp.add_handler(CommandHandler("reload", update_admin_list))
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(select_welcome_type, pattern="^greeting$"),
            CallbackQueryHandler(custom_welcome_type, pattern="^custom_welcome$"),
            CallbackQueryHandler(default_welcome_message, pattern="^default_welcome$"),
            CallbackQueryHandler(cancel_welcome, pattern="^cancel_welcome$"),
        ],
        states={
            CUSTOM_WELCOME_INPUT: [
                CallbackQueryHandler(
                    custom_welcome_input, pattern="^custom_text$"
                ),
                MessageHandler(filters.TEXT, custom_welcome_input)
                # Add other callbacks for different types of custom welcome
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel_welcome, pattern="^cancel_welcome$")],
    )


    train_me = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ai_welcome_input, pattern="^train_me$"),
            CallbackQueryHandler(cancel_welcome, pattern="^cancel_welcome$"),
        ],
        states={
            AI_CONTENT_INPUT: [
                MessageHandler(filters.TEXT, get_content),
                MessageHandler(filters.ATTACHMENT, file_handler),
                CallbackQueryHandler(cancel_welcome, pattern="^cancel_welcome$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel_welcome, pattern="^cancel_welcome$")],
    )


    dp.add_handler(conv_handler)
    dp.add_handler(train_me)
    dp.add_handler(
        MessageHandler(filters.Regex(re.compile(r"^chat assistance$", re.IGNORECASE)), chat_assistance)
    )
    dp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mention_or_reply))
    dp.add_handler(CommandHandler('settings',settings))
    


add_handlers(dp)

# Run FastAPI app
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=PORT)
