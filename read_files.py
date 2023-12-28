import PyPDF2
import re
import requests
from bs4 import BeautifulSoup


def get_text_from_website(url):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Check for errors in the request

        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract text from all the paragraphs on the page
        paragraphs = soup.find_all('p')
        text_content = '\n'.join([p.get_text() for p in paragraphs])

        return text_content

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None



def read_pdf(file_path):
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfFileReader(file)
        num_pages = pdf_reader.numPages

        text = ""
        for page_num in range(num_pages):
            page = pdf_reader.getPage(page_num)
            text += page.extractText()

    return text