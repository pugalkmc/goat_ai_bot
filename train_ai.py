import os
import PyPDF2
from bs4 import BeautifulSoup
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from functions import *
from goat_ai import *

AI_CONTENT_INPUT = range(1)

async def ai_welcome_input(update, context):
    keyboard = [
        [InlineKeyboardButton("Cancel", callback_data="cancel_input")],
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(
            text="Provide content about the project (text, PDF, or website link):",
            reply_markup=reply_markup
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text="Provide content about the project (text, PDF, or website link):",
            reply_markup=reply_markup
        )
    return AI_CONTENT_INPUT

async def get_content(update, context):
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    text = update.message.text if update.message else update.callback_query.message.text
    if 'http' in text:
        response = requests.get(text)
        content = response.content
        if response.status_code == 200:
            soup = BeautifulSoup(content, "html.parser")
            for tag in soup.findAll(attrs={"style": True}):
                del tag["style"]
            title = soup.find("title").text
            paragraphs = soup.find_all("p")
            links = soup.find_all("a")
            form_data = f"""title: {title}\n\n
                            Contents: {paragraphs}\n\n
                            Links: {links}"""
                            
            completion = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": ai_parser_behaviour},
                {"role": "user", "content": form_data}
                ]
                )
            form_data = completion.choices[0].message.content
            print(form_data)
            await bot.send_message(chat_id=chat_id, text=f"Content on {text} are saved!\n\n"
                                   f"{form_data}")
            text = form_data
        else:
            await bot.send_message(chat_id=update.message.chat_id, text="Please enter a valid website link")
            return AI_CONTENT_INPUT
    else:
        completion = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "system", "content": ai_check_content_prompt},
            {"role": "user", "content": text}
            ]
        )
        form_data = completion.choices[0].message.content

        if form_data == 'True':
            await bot.send_message(chat_id=chat_id, text="Your provided info are verified by G.O.A.T AI and saved!")
            return ConversationHandler.END
        else:
            await bot.send_message(chat_id=chat_id, text=form_data)
            return AI_CONTENT_INPUT
    group_col.update_one({"group_id": -4082239845}, {"$set": {
        'welcome_type':'AI',
        'welcome_text':text
        }})
    return ConversationHandler.END


async def file_handler(update, context):
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
 
     # Check if the file has a ".pdf" extension
    if update.message.document and update.message.document.mime_type == 'application/pdf':
        file = bot.get_file(update.message.document.file_id)
        await file.download_to_drive(custom_path='downloaded.pdf')

        with open('downloaded.pdf', 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_number in range(pdf_reader.numPages):
                page = pdf_reader.getPage(page_number)
                text += page.extractText()

        group_col.update_one({"group_id": -4082239845}, {"$set": {
            'welcome_type':'AI',
            'welcome_text':text
        }})
        # Clean up temporary file
        os.remove('downloaded.pdf')
        await bot.send_message(chat_id=chat_id, text="File contents saved!")
    
        return ConversationHandler.END
    else:
        await bot.send_message(chat_id=chat_id, text="Please send a PDF file.")
        return AI_CONTENT_INPUT