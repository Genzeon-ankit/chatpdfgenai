import logging
from io import BytesIO
from utils import azure_form_recognizer_ocr
from pdfminer.high_level import extract_text
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from security import decrypt_file_aes
from config import chat_openai
from azure.ai.formrecognizer import FormRecognizerClient
from azure.core.credentials import AzureKeyCredential

def load_docs(encrypted_file_path, key, azure_endpoint, azure_api_key):
    try:
        # Initialize Azure Form Recognizer client
        client = FormRecognizerClient(azure_endpoint, AzureKeyCredential(azure_api_key))
    except Exception as e:
        logging.error(f"Error initializing Azure Form Recognizer client: {e}")
        return ""

    decrypted_bytes = decrypt_file_aes(encrypted_file_path, key)  

    if not decrypted_bytes:
        return ""

    pdf_stream = BytesIO(decrypted_bytes)

    # Extract regular text
    pdf_text = extract_text(pdf_stream)

    # Extract text using Azure Form Recognizer
    image_text = azure_form_recognizer_ocr(pdf_stream, client)

    full_text = pdf_text + image_text

    logging.info(f"Length of text extracted from images (OCR): {len(image_text)}")
    logging.info(f"Length of text extracted directly from PDF: {len(pdf_text)}")

    return full_text

def split_texts(text, chunk_size, overlap):
    if text is None or text.strip() == '':
        logging.warning("Received empty text. Cannot perform split.")
        return []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    splits = text_splitter.split_text(text)
    if not splits:
        logging.error("Failed to split document")
    return splits

def create_retriever(_embeddings, splits):
    try:
        vectorstore = FAISS.from_texts(splits, _embeddings)
    except (IndexError, ValueError) as e:
        logging.error(f"Error creating vectorstore: {e}")
        return None
    retriever = vectorstore.as_retriever(k=5)
    return retriever

def generate_question_prompt(document_text):
    system_template = (
        "You are an advanced AI model designed to generate questions based on provided document content. "
        "Your goal is to help users further understand or summarize the main points of a document by asking relevant questions."
    )

    human_template = (
        "Based on the content I'm about to provide, please generate questions that can help someone understand its main points. "
        "Here's the document content: {document_content}."
    )

    prompt = system_template + " " + human_template.format(document_content=document_text)
    return prompt

def get_relevant_questions(document_text, num_questions=5):
    prompt = generate_question_prompt(document_text)

   # Assuming you're using the Azure LLM or similar:
    chat_result = chat_openai(prompt)  # Directly get the string response

    # Assuming the answer contains the questions separated by line breaks, split into a list
    relevant_questions = [question.strip() for question in chat_result.split('\n') if question.strip()]

    # Take only the first `num_questions` questions
    return relevant_questions[:num_questions]