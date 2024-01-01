from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from functions import *
from goat_ai import ai_check_welcome_message_prompt

SET_WELCOME, SELECT_WELCOME_TYPE, END_CONVERSATION = range(3)
CUSTOM_WELCOME_INPUT = range(1)

async def select_welcome_type(update, context):
    if 'group_title' in context.user_data:
        keyboard = [
            [InlineKeyboardButton(f"AI Greeting {'✅' if context.user_data['ai_welcome'] else '❌'}", callback_data="ai_welcome")],
            [InlineKeyboardButton(f"Custom Welcome {'✅' if context.user_data['custom_welcome'] else '❌'}", callback_data="custom_welcome")],
            [InlineKeyboardButton(f"Default Welcome {'✅' if context.user_data['default_welcome'] else '❌'}", callback_data="default_welcome")],
            [InlineKeyboardButton(f"🔙BAck", callback_data=context.user_data['chat_id'])],
        ]
    else:
        res = group_col.find_one({'chat_id':int(context.user_data['chat_id'])})
        keyboard = [
            [InlineKeyboardButton(f"AI Greeting {'✅' if res['ai_welcome'] else '❌'}", callback_data="ai_welcome")],
            [InlineKeyboardButton(f"Custom Welcome {'✅' if res['custom_welcome'] else '❌'}", callback_data="custom_welcome")],
            [InlineKeyboardButton(f"Default Welcome {'✅' if res['default_welcome'] else '❌'}", callback_data="default_welcome")],
            [InlineKeyboardButton(f"🔙BAck", callback_data=context.user_data['chat_id'])],
        ]
        context.user_data['default_welcome'] = res['default_welcome']
        context.user_data['custom_welcome'] = res['custom_welcome']
        context.user_data['ai_welcome'] = res['ai_welcome']
        context.user_data['group_title'] = res['group_title']
    
    text = f"I have the capability to welcome the users by sharing them a small info about your project\n\n" \
           f"Welcome methods for {context.user_data['group_title']} are:\n"
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    # return SELECT_WELCOME_TYPE


async def default_welcome_message(update, context):
    keyboard = [
        [InlineKeyboardButton(f"AI Greeting {'✅' if context.user_data['ai_welcome'] else '❌'}", callback_data="ai_welcome")],
        [InlineKeyboardButton(f"Custom Welcome {'✅' if context.user_data['custom_welcome'] else '❌'}", callback_data="custom_welcome")],
        [InlineKeyboardButton(f"Default Welcome {'✅' if not context.user_data['default_welcome'] else '❌'}", callback_data="default_welcome")],
        [InlineKeyboardButton(f"🔙BAck", callback_data=context.user_data['chat_id'])],
    ]

    text = f"I have the capability to welcome the users by sharing them a small info about your project\n\n" \
           f"Welcome methods for {context.user_data['group_title']} are:\n"
    
    await group_col.update_one(
        {"chat_id": int(context.user_data['chat_id'])},
        {
            "$set": {
                "default_welcome": not context.user_data['default_welcome'],
            }
        },
    )
    
    context.user_data['default_welcome'] = True
    
    await update.callback_query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def custom_welcome_start(update, context):
    res = group_col.find_one({'chat_id':int(context.user_data['chat_id'])})
    await update.callback_query.answer()
    if 'custom_welcome_list' in res:
        message_add_on = ""
        num = 1
        for i in res['custom_welcome_list']:
            message_add_on += f'{num}) {i}\n'
            num += 1
        keyboard = [
            [InlineKeyboardButton(f"Add More", callback_data="add_more_custom_welcome"), InlineKeyboardButton(f"Reset", callback_data="reset_all_custom_welcome")],
            [InlineKeyboardButton(f"🔙BAck", callback_data="greeting")]
        ]
        await update.message.reply_text(
            text=f"Previous custom welcome messages:\n\n" \
                 f"{message_add_on}\n" \
                 f"Choose options:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [
            [InlineKeyboardButton(f"Add Messages", callback_data="add_more_custom_welcome")],
            [InlineKeyboardButton(f"🔙BAck", callback_data="cancel_custom_welcome")]
        ]
        await update.callback_query.edit_message_text(
            text=f"There is no custom messages set:\n\n" \
                 f"Choose options:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END


async def custom_welcome(update, context):
    text = update.message.text if update.message else update.callback_query.message.text
    keyboard = [
        [InlineKeyboardButton(f"Cancel", callback_data="cancel_custom_welcome")]
    ]
    text=f"Now provide the list of welcome messages line by line\n\n" \
         f"Example:\n" \
         "Hello {username}, welcome to the community\n" \
         "Seems good , {first_name} entered the chat\n\n"
         
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return CUSTOM_WELCOME_INPUT


async def custom_welcome_input(update, context):
    text = update.message.text if update.message else update.callback_query.message.text
    welcome_sentence = text.splitlines()

    text = ""
    num = 1
    for i in welcome_sentence:
        text += f"{num}) {i}\n"
        num += 1

    ai_output = generate_ai_content(ai_check_welcome_message_prompt)
    if ai_output=='True':
        text=f"Previous custom welcome messages:\n\n" \
             f"{text}\n" \
             f"Choose options:"
    elif ai_output=='False':
        text="None of your welcome messages are valid"
    else:
        text="Few of your welcomes correct formatted and some are rejected"
    group_col.update_one(
        {"chat_id": int(context.user_data['chat_id'])},  # Add a filter to specify the document to update
        {"$addToSet": {"custom_welcome_list": {"$each": welcome_sentence}}},
        upsert=True  # Create the document if it doesn't exist
    )
    # res = group_col.find_one({'chat_id':int(context.user_data['chat_id'])})


    keyboard = [
        [InlineKeyboardButton(f"Add More", callback_data="add_more_custom_welcome"), InlineKeyboardButton(f"Reset", callback_data="reset_all_custom_welcome")],
        [InlineKeyboardButton(f"🔙BAck", callback_data="cancel_custom_welcome")]
    ]
    await update.message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def reset_welcome(update, context):
    await group_col.update_one(
        {'chat_id':int(context.user_data['chat_id'])},  # Add a filter to specify the document to update
        {"$set": {"custom_welcome_list": []}}
    )
    return await custom_welcome_start(update, context)



async def cancel_welcome(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
            text="Cancelled!"
        )
    return ConversationHandler.END

