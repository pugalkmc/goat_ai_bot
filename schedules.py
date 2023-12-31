import asyncio
import telegram
from functions import bot


async def schedule_task(delay, coro):
    await asyncio.sleep(delay)
    await coro

async def delete_message(context):
    try:
        await bot.delete_message(chat_id=context.chat_id, message_id=context.message_id)
    except telegram.error.BadRequest as e:
        print(f"Error deleting message: {e}")