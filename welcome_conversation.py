from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler
from functions import *
from urllib.request import urlopen

SET_WELCOME, SELECT_WELCOME_TYPE, CUSTOM_WELCOME_INPUT, END_CONVERSATION = range(4)

async def select_welcome_type(update, context):
    keyboard = [
        [InlineKeyboardButton("AI Greeting", callback_data="ai_welcome")],
        [InlineKeyboardButton("Custom Welcome", callback_data="custom_welcome"), InlineKeyboardButton("Default Welcome", callback_data="default_welcome")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_welcome")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(
            text="Choose the welcome message type:", reply_markup=reply_markup
        )
    elif update.callback_query:
        await context.bot.send_message(
            chat_id=update.callback_query.message.chat_id,
            text="Choose the welcome message type:",
            reply_markup=reply_markup,
        )
    # return SELECT_WELCOME_TYPE


async def default_welcome_message(update, context):
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    context.user_data["welcome_type"] = "default"
    await group_col.update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "welcome_type": "default",
            }
        },
    )
    if update.message:
        await update.message.reply_text(text="Default welcome type saved!")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text="Default welcome type saved!")
    return ConversationHandler.END

async def custom_welcome_type(update, context):
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    text = update.message.text if update.message else update.callback_query.message.text
    if update.message:
        await update.message.reply_text(
            text="Provide a list of custom welcome messages separated by '|':"
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text="Provide a list of custom welcome messages separated by '|':"
        )
    context.user_data["welcome_type"] = "custom"
    return CUSTOM_WELCOME_INPUT

async def custom_welcome_input(update, context):
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    text = update.message.text if update.message else update.callback_query.message.text
    context.user_data["list"] = [i.strip() for i in text.split("|")]
    group_col.update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "welcome_type": context.user_data["welcome_type"],
                "welcome_list": context.user_data["list"],
            }
        },
    )
    if update.message:
        await update.message.reply_text(text="Custom welcome messages saved!")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text="Custom welcome messages saved!")
    return ConversationHandler.END

async def cancel_welcome(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
            text="Cancelled!"
        )
    return ConversationHandler.END

