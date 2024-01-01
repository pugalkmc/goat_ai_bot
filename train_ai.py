import os
import PyPDF2
from bs4 import BeautifulSoup
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from functions import *
from goat_ai import *

welcome_messages = [
    "Welcome, {username}! Explore the crypto universe with us.",
    "Hey {first_name}! Excited to have you in our crypto community.",
    "Greetings, {username}! Join us on the path to crypto success.",
    "Welcome aboard, {first_name}! Let's navigate the crypto landscape together.",
    "{username}, welcome to our crypto space. Ready to innovate?",
    "Hey {first_name}! Delighted to welcome you to the crypto world.",
    "Greetings, {username}! Dive into the possibilities of crypto.",
    "Welcome, {first_name}! Your journey into crypto greatness begins now.",
    "{username}, thrilled to have you part of our crypto adventure.",
    "Hey {first_name}! Explore the exciting world of cryptocurrency with us.",
    "Welcome, {username}! Dive into crypto excitement! 🚀",
    "Hey {first_name}! Crypto awaits. Let's innovate together!",
    "Greetings, {username}! Join our crypto journey. 🌟",
    "Welcome, {first_name}! Unleash crypto potential! 💎",
    "{username}, crypto vibes await! Let's soar high! 🌌"
]

AI_CONTENT_INPUT = range(1)

async def ai_welcome_input(update, context):
    keyboard = [
        [InlineKeyboardButton("Cancel", callback_data="cancel_input")],
        ]
    if update.message:
        await update.message.reply_text(
            text="Provide content about the project (text, PDF, or website link):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text="Provide content about the project (text, PDF, or website link):",
            reply_markup=InlineKeyboardMarkup(keyboard)
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
            await update.message.reply_text(
                text=f"Content on {text} are saved!\n\n"
                     f"{form_data}")
            text = form_data
        else:
            await update.message.reply_text(text="Please enter a valid website link")
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
            await update.message.reply_text(text="Your provided info are verified by G.O.A.T AI and saved!")
            return ConversationHandler.END
        else:
            await update.message.reply_text(text=form_data)
            return AI_CONTENT_INPUT
    await group_col.update_one({"group_id": -4082239845}, {"$set": {
        'welcome_type':'AI',
        'welcome_text':text
        }})
    return ConversationHandler.END


async def file_handler(update, context):
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
 
     # Check if the file has a ".pdf" extension
    if update.message.document and update.message.document.mime_type == 'application/pdf':
        file = await bot.get_file(update.message.document.file_id)
        await file.download_to_drive(custom_path='downloaded.pdf')

        with open('downloaded.pdf', 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_number in range(pdf_reader.numPages):
                page = pdf_reader.getPage(page_number)
                text += page.extractText()

        await group_col.update_one({"group_id": -4082239845}, {"$set": {
            'content':text
        }})
        # Clean up temporary file
        os.remove('downloaded.pdf')
        await update.message.reply_text(text="File contents saved!")
    
        return ConversationHandler.END
    else:
        await update.message.reply_text(text="Please send a PDF file.")
        return AI_CONTENT_INPUT