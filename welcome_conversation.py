import os
import PyPDF2
from functions import *
from urllib.request import urlopen
from bs4 import BeautifulSoup
from goat_ai import client , ai_parser_behaviour , ai_check_content_prompt

SET_WELCOME , SELECT_WELCOME_TYPE, CUSTOM_WELCOME_INPUT , AI_CONTENT_INPUT , END_CONVERSATION= range(5)

async def select_welcome_type(update, context):
    keyboard = [
        ["AI Greeting", "Custom Welcome", "Default Welcome"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    await bot.send_message(chat_id=update.message.chat_id, text="Choose the welcome message type:", reply_markup=reply_markup)
    return SELECT_WELCOME_TYPE

async def ai_welcome_input(update, context):
    await bot.send_message(chat_id=update.message.chat_id, text="Provide content about the project (text, PDF, or website link):")
    return AI_CONTENT_INPUT

async def get_content(update, context):
    chat_id = update.message.chat_id
    text = update.message.text
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
        print(form_data)

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
    chat_id = update.message.chat_id

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

        print(text)
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
    

async def default_welcome_message(update, context):
    chat_id = update.message.chat_id
    context.user_data['welcome_type'] = 'default'
    group_col.update_one({"group_id": -4082239845}, {"$set": {
            'welcome_type':'default'
            }})
    await bot.send_message(chat_id=chat_id, text="Default welcome type saved!")
    return ConversationHandler.END

async def custom_welcome_type(update, context):
    chat_id = update.message.chat_id
    text = update.message.text
    await bot.send_message(chat_id=chat_id, text="Provide a list of custom welcome messages separated by '|':")
    context.user_data['welcome_type'] = 'custom'
    return CUSTOM_WELCOME_INPUT
    
async def custom_welcome_input(update, context):
    chat_id = update.message.chat_id
    text = update.message.text
    context.user_data['list'] = [i.strip() for i in text.split("|")]
    group_col.update_one({"group_id": -4082239845}, {"$set": {
            'welcome_type':context.user_data['welcome_type'],
            'welcome_list':context.user_data['list']
            }})
    await bot.send_message(chat_id=chat_id, text="Custom welcome messages saved!")
    return ConversationHandler.END

# async def ai_welcome_text_input(update,context):
#         chat_id = update.message.chat_id
#         text = update.message.text
