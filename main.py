import asyncio
from dataclasses import dataclass
import html
import random
import datetime
import time
from fastapi import Response
from flask import Flask, jsonify, make_response, request
from asgiref.wsgi import WsgiToAsgi
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    Application
)
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    CallbackContext,
    ContextTypes,
    ExtBot,
    TypeHandler,
)
import logging
import pymongo
from http import HTTPStatus
from telegram.constants import ParseMode
import uvicorn
from goat_ai import generate_ai_content
from welcome_conversation import *
from functions import messages_col
from config import *
from functions import *
from goat_ai import *
from train_ai import *

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@dataclass
class WebhookUpdate:
    """Simple dataclass to wrap a custom update type"""

    user_id: int
    payload: str


class CustomContext(CallbackContext[ExtBot, dict, dict, dict]):
    """
    Custom CallbackContext class that makes `user_data` available for updates of type
    `WebhookUpdate`.
    """

    @classmethod
    def from_update(
        cls,
        update: object,
        application: "Application",) -> "CustomContext":
        if isinstance(update, WebhookUpdate):
            return cls(application=application, user_id=update.user_id)
        return super().from_update(update, application)


async def webhook_update(update: WebhookUpdate, context: CustomContext) -> None:
    """Handle custom updates."""
    chat_member = await context.bot.get_chat_member(chat_id=update.user_id, user_id=update.user_id)
    payloads = context.user_data.setdefault("payloads", [])
    payloads.append(update.payload)
    combined_payloads = "</code>\n• <code>".join(payloads)
    text = (
        f"The user {chat_member.user.mention_html()} has sent a new payload. "
        f"So far they have sent the following payloads: \n\n• <code>{combined_payloads}</code>"
    )
    await update.message.reply_text(text=text, parse_mode=ParseMode.HTML)


async def start_web(update: Update, context: CustomContext) -> None:
    """Display a message with instructions on how to use this bot."""
    payload_url = html.escape(f"{URL}/submitpayload?user_id=<your user id>&payload=<payload>")
    text = (
        f"To check if the bot is still running, call <code>{URL}/healthcheck</code>.\n\n"
        f"To post a custom update, call <code>{payload_url}</code>."
    )
    await update.message.reply_html(text=text)



async def settings(update, context):
    if update.message:
        if 'chat_id' not in context.user_data:
            group_col.find_one({'chat_id':int(update.message.text)})
            context.user_data.clear()
            context.user_data['chat_id'] = group_col['chat_id']
    else:
        context.user_data['chat_id'] = update.callback_query.data
    keyboard = [
        [InlineKeyboardButton("Greeting", callback_data="greeting"), InlineKeyboardButton("Chat Assistance", callback_data="chat_assistance")],
        [InlineKeyboardButton("Train Me", callback_data="train_me"), InlineKeyboardButton("Documentation", callback_data="documentation")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        text=f"Choose below option:",
        reply_markup=reply_markup,
    )

# Your existing handlers
async def start(update, context):
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

    if not groups_as_admin:
        await update.message.reply_text(
            text="There are no groups founded you as admin\n" \
                f"Also ensure that @goat_ai_bot is also an admin in there\n\n" \
                f"Still not found? : Try using /reload command on the group and use /start in this chat"
        )
        return

    keyboard = []
    for i in range(len(groups_as_admin)):
        keyboard.append([InlineKeyboardButton(groups_as_admin[i]['group_title'], callback_data=groups_as_admin[i]['chat_id'])])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        text=f"Select the group you wanted to change the settings and my behaviour to act\n\n",
        reply_markup=reply_markup,
    )


async def generate_text(update, context):
    await update.message.reply_text(text=generate_ai_content(update.message.text))

async def chat_assistance_settings(update, context):
    group_col.update_one(
        {"chat_id": update.message.chat_id},
            {
                "$set": {
                    "ai_welcome": not context.user_data['ai_welcome']
                }
            }
        )
    await update.message.reply_text(text="Chat Assistance is Coming Soon!")



async def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


async def update_admin_list(update, context):
    chat_id = update.message.chat_id
    check = await bot.get_chat_member(chat_id, bot.id)
    try:
        if check.status in ['administrator', 'creator']:
            pass
        else:
            await update.message.reply_text("I don't have admin permission to check admins info")
    except Exception as e:
        await update.message.reply_text("I don't have admin permission to check admins info")
        return

    members_count = await bot.get_chat_member_count(chat_id)
    admins = await bot.get_chat_administrators(chat_id)
    group_col.update_one(
            {"chat_id": chat_id},
                {
                    "$set": {
                        "latest_admin_list_updated": datetime.datetime.now(),
                        "admin_list": [admin.user.id for admin in admins],
                        'members_count': members_count,
                    }
            }
        )
    await update.message.reply_text(text="Admin list updated!")


async def handle_mention_or_reply(update, context):
    message = update.message

    # Check if the bot is mentioned in the message or the message is a reply to the bot's message
    if message.text and (f"@{context.bot.username}" in message.text or message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id):
        last_10_messages = list(messages_col.find({"user_id": message.from_user.id, "user_id":message.from_user.id}).sort("_id", pymongo.DESCENDING).limit(20))
        # Store message details in MongoDB
        messages=[
            {"role": "system", "content": prompt_text},
        ]
        for i in range(len(last_10_messages)-1,0,-1):
            messages.append({"role":"user", 'content': last_10_messages[i]['text']})
            messages.append({"role":"assistant", 'content': last_10_messages[i]['assistant']})

        messages.append({"role": "user", "content": message.text+"\n\nI'm not expecting anything outside from your system behaviour"})
        
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages
        )

        response = completion.choices[0].message.content


        messages_col.insert_one({
            'message_id': message.message_id,
            'user_id': message.from_user.id,
            'chat_id': message.chat_id,
            'text': message.text,
            'assistant': response,
            'timestamp':  message.date,
        })

        await message.reply_text(response)


async def generate_random_welcome(template, **kwargs):

    try:
        welcome_message = template.format(**kwargs)
    except KeyError as e:
        # Handle missing keys (placeholders) gracefully
        welcome_message = f"Error: Missing key '{e.args[0]}' in template."

    return welcome_message


async def new_member(update, context):
    user = update.message.from_user
    username = user.username
    first_name = user.first_name
    last_name = user.last_name
    start_time = time.time()  # Mark start time

    for member in update.message.new_chat_members:
        if member.is_bot and member.id == context.bot.id:
            # Store the data in your database or perform any other actions
            # Example: You can use a MongoDB client to store data in MongoDB
            group_col.insert_one({
                'group_title': update.effective_chat.title,
                'chat_id': update.effective_chat.id,
                'group_id': update.effective_chat.id,
                'ai_welcome':False,
                'default_welcome':True,
                'custom_welcome':False,
                "content": "nothing",
                "cost":0,
                'indian_kolkata_time': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))),
                'latest_admin_list_updated': datetime.datetime.now(),
            })

            await update.message.reply_text(text="Hello crypto crew! I'm just joined the voyage")
        else:
            pipeline = [
                {"$match": {'chat_id': update.message.chat_id}},
                {"$project": {
                    "true_options": {
                        "$map": {
                            "input": {
                                "$filter": {
                                    "input": {"$objectToArray": "$$ROOT"},
                                    "cond": {
                                        "$and": [
                                            {"$eq": ["$$this.v", True]},
                                            {"$in": ["$$this.k", ["custom_welcome", "default_welcome", "ai_welcome"]]}
                                        ]
                                    }
                                }
                            },
                            "in": "$$this.k"
                        }
                    },
                    "_id": 0
                }},
                {"$project": {
                    "random_option": {"$arrayElemAt": ["$true_options", {"$floor": {"$multiply": [{"$rand": {}}, {"$size": "$true_options"}]}}]},
                    "_id": 0
                }},
                {"$replaceRoot": {"newRoot": "$random_option"}}
            ]

            cursor = group_col.aggregate(pipeline)
            result = list(cursor)
            if result:
                await update.message.reply_text(
                                        text=await generate_random_welcome(result[0],username=username , 
                                                                          first_name=first_name, 
                                                                          last_name=last_name))
            print(f"Response time: {time.time() - start_time:.4f} seconds")
            

            # **Corrected context usage:**
            # asyncio.create_task(schedule_task(10, delete_message(context)))



async def main() -> None:

    await bot.initialize()

    """Set up PTB application and a web application for handling the incoming requests."""
    context_types = ContextTypes(context=CustomContext)
    # Here we set updater to None because we want our custom webhook server to handle the updates
    # and hence we don't need an Updater instance
    dp = (
        Application.builder().token(BOT_TOKEN).updater(None).context_types(context_types).build()
    )

    await dp.initialize()
    
    # register handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(TypeHandler(type=WebhookUpdate, callback=webhook_update))

    dp.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    dp.add_handler(CommandHandler("reload", update_admin_list))
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(select_welcome_type, pattern="^greeting$"),
            CallbackQueryHandler(custom_welcome_start, pattern="^custom_welcome$"),
            CallbackQueryHandler(default_welcome_message, pattern="^default_welcome$"),
            CallbackQueryHandler(cancel_welcome, pattern="^cancel_welcome$"),
        ],
        states={
            CUSTOM_WELCOME_INPUT: [
                CallbackQueryHandler(
                    custom_welcome, pattern="^custom_text$"
                ),
                MessageHandler(filters.TEXT, custom_welcome)
                # Add other callbacks for different types of custom welcome
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel_welcome, pattern="^cancel_welcome$")],
    )

    conv_welcome_message = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(custom_welcome, pattern="^add_more_custom_welcome$"),
        ],
        states={
            CUSTOM_WELCOME_INPUT: [
                CallbackQueryHandler(custom_welcome, pattern="^add_more_custom_welcome$"),
                CallbackQueryHandler(reset_welcome, pattern="^reset_all_custom_welcome$"),
                CallbackQueryHandler(cancel_welcome, pattern="^cancel_custom_welcome$"),
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
    dp.add_handler(conv_welcome_message)
    dp.add_handler(train_me)
    dp.add_handler(CallbackQueryHandler(chat_assistance_settings, pattern="^chat_assistance_settings$"))
    dp.add_handler(CallbackQueryHandler(settings, pattern=r"-?\d+"))
    dp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mention_or_reply))
    dp.add_handler(CommandHandler('settings',settings))


    # Pass webhook settings to telegram
    await dp.bot.set_webhook(url=f"{URL}/telegram", allowed_updates=Update.ALL_TYPES)

    # Set up webserver
    flask_app = Flask(__name__)

    @flask_app.post("/telegram")  # type: ignore[misc]
    async def telegram() -> Response:
        """Handle incoming Telegram updates by putting them into the `update_queue`"""
        await dp.update_queue.put(Update.de_json(data=request.json, bot=dp.bot))
        return jsonify({"status": "OK"})
    
    @flask_app.route("/submitpayload", methods=["GET", "POST"])  # type: ignore[misc]

    async def custom_updates() -> Response:
        """
        Handle incoming webhook updates by also putting them into the `update_queue` if
        the required parameters were passed correctly.
        """
        try:
            user_id = int(request.args["user_id"])
            payload = request.args["payload"]
        except KeyError:
            return jsonify({"error": "Please pass both `user_id` and `payload` as query parameters."}), HTTPStatus.BAD_REQUEST
        except ValueError:
            return jsonify({"error": "The `user_id` must be an integer."}), HTTPStatus.BAD_REQUEST
        await dp.update_queue.put(WebhookUpdate(user_id=user_id, payload=payload))
        return jsonify({"status": "OK"})
    
    @flask_app.get("/healthcheck")  # type: ignore[misc]
    async def health() -> Response:
        """For the health endpoint, reply with a simple plain text message."""
        return make_response("The bot is still running fine :)", HTTPStatus.OK)

    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=WsgiToAsgi(flask_app),
            port=PORT,
            use_colors=False,
            host="0.0.0.0",
        )
    )

    # Run application and webserver together
    async with dp:
        await dp.start()
        await webserver.serve()
        await dp.stop()

# Run FastAPI app
if __name__ == "__main__":
    asyncio.run(main())