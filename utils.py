import os
import logging
from config import cache
from config import ALLOWED_EXTENSIONS, UPLOAD_FOLDER, cache

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clear_previous_data(user_id):
    user_directory = os.path.join(UPLOAD_FOLDER, user_id)
    # Clear cached data for the user
    cache_key_splits = f'splits_{user_id}'
    cache_key_retriever = f'retriever_{user_id}'
    cache.delete(cache_key_splits)
    cache.delete(cache_key_retriever)

    # Delete encrypted files from the user's directory
    if os.path.exists(user_directory):
        for filename in os.listdir(user_directory):
            if filename.endswith('.enc'):
                try:
                    os.remove(os.path.join(user_directory, filename))
                except Exception as e:
                    logging.error(f"Error removing file {filename}: {e}")
    logging.info(f'Cleared previous data for user {user_id}')

def azure_form_recognizer_ocr(pdf_stream, client):
    """
    Use Azure Form Recognizer to extract text from a PDF stream.
    """
    try:
        pdf_stream.seek(0)
        poller = client.begin_recognize_content(pdf_stream, content_type='application/pdf')
        result = poller.result()  # OCR text
    except Exception as e:
        logging.error(f"Error in OCR processing: {e}")
        return ""

    full_text = ""
    for page in result:
        page_text = ""
        if page.lines:
            for line in page.lines:
                page_text += line.text + "\n"
        full_text += page_text

    return full_text

