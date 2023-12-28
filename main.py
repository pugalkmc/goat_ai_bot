from functions import *
from welcome_conversation import *
from read_files import get_text_from_website, read_pdf

DEFAULT_WELCOME_MESSAGES = ["Hey there {user}, Welcome to the {group_name}!"]


async def start(update, context):
    message = update.message
    chat_id = message.chat_id
    username = message.from_user.username
    if message.chat.type in ['group', 'supergroup']:
        return
    current_time = time_fun.now().strftime("%d-%m-%Y")

    find_people = peoples_col.find_one({"chat_id": chat_id})
    if username is None:
        await bot.send_message(chat_id=chat_id, text=f"Hello @{username}\n"
                                                     f"Please set your telegram username in settings!\n"
                                                     f"Check out this document for guidance: Not set")
    elif find_people is None:
        peoples_col.insert_one({"chat_id": chat_id, "username": username, "first_started": current_time})
        await bot.send_message(chat_id=chat_id, text=f"Hello! welcome @{username}")
    else:
        await menu_button(update, context, text="Welcome to the AI-powered bot! Choose an option:")


async def generate_text(update, context):
    message = update.message
    chat_id = message.chat_id
    value = await generate_ai_content(message.text)
    await bot.send_message(chat_id=chat_id, text=value)

async def chat_assistance(update, context):
    await bot.send_message(chat_id=update.message.chat_id, text="Chat Assistance is Coming Soon!")

async def new_member(update, context):
    chat = update.effective_chat
    user = update.effective_user
    await bot.send_message(chat_id=chat.id, text=random.choice(DEFAULT_WELCOME_MESSAGES).format(user=user.mention_markdown(), group_name=chat.title))

async def is_admin_in_common_group(chat, user):
    return True

def main():
    dp = Application.builder().token(BOT_TOKEN).build()
    dp.add_handler(CommandHandler("start", start))
    # dp.add_handler(MessageHandler(filters.StatusUpdate._NewChatMembers, new_member))

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(re.compile(r'^ai welcome$', re.IGNORECASE)), select_welcome_type)],
        states={
            SELECT_WELCOME_TYPE: [
                MessageHandler(filters.Regex(re.compile(r'^ai greeting$', re.IGNORECASE)), ai_welcome_input),
                MessageHandler(filters.Regex(re.compile(r'^custom welcome$', re.IGNORECASE)), custom_welcome_type),
                MessageHandler(filters.Regex(re.compile(r'^default welcome$', re.IGNORECASE)), default_welcome_message)
            ],
            CUSTOM_WELCOME_INPUT: [MessageHandler(filters.TEXT, custom_welcome_input)],
            AI_CONTENT_INPUT:[
                MessageHandler(filters.TEXT, get_content),
                MessageHandler(filters.ATTACHMENT, file_handler),
                ]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    

    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(filters.Regex(re.compile(r'^chat assistance$', re.IGNORECASE)), chat_assistance))
    dp.add_handler(MessageHandler(filters.TEXT, generate_text))
    # dp.add_handler(MessageHandler(filters.Regex(re.compile(r'^settings$', re.IGNORECASE)), settings))


    dp.run_polling()

main()




