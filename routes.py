from flask import Blueprint, request, jsonify, current_app as app
from werkzeug.utils import secure_filename
import os
import logging
import shutil
from langchain.chains import RetrievalQA
from security import encrypt_file_aes, key
from utils import clear_previous_data, allowed_file
from document_processor import load_docs, split_texts, create_retriever, get_relevant_questions
from config import azure_api_key, azure_endpoint, embeddings, chat_openai, UPLOAD_FOLDER, cache


# Define a blueprint for the routes
routes_blueprint = Blueprint('routes', __name__)

@routes_blueprint.route('/upload', methods=['POST'])
def upload_file():
    userId = request.headers.get('userId')
    if not userId:
        return jsonify({'error': 'User ID not provided in the header'}), 400

    logging.info('Running upload_file for user: {userId}')
    clear_previous_data(userId)  # Clear all previous data
  
    # Create user-specific directory
    user_directory = os.path.join(app.config['UPLOAD_FOLDER'], userId)
    if not os.path.exists(user_directory):
        os.makedirs(user_directory)

    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Save file to user-specific directory
    filename = secure_filename(file.filename)
    temp_file_path = os.path.join(user_directory, filename)
    file.save(temp_file_path)

    # Debug: Check temp file path
    print(f"Temp file path: {temp_file_path}")
    
    # Encrypt the temporary file and save encrypted version
    encrypted_file_path = temp_file_path + '.enc'
    encrypt_file_aes(temp_file_path, key)
    logging.info('File saved and encrypted')

    # Debug: Check encrypted file path
    print(f"Encrypted file path: {encrypted_file_path}")

    # Remove the original file after encryption
    os.remove(temp_file_path)

    if not azure_endpoint or not azure_api_key:
        return jsonify({'error': 'Azure Form Recognizer configurations not found'}), 500
    
    loaded_text = load_docs(encrypted_file_path,key, azure_endpoint, azure_api_key)  # Key is passed for decryption
    if not loaded_text:
        return jsonify({'error': 'Failed to load document text'}), 400
    logging.info('Document text loaded')

    #created the splits and kept in cache
    splits = split_texts(loaded_text, chunk_size=1000, overlap=0)
    if not splits:
        return jsonify({'error': 'Failed to split document text'}), 400
    logging.info('Document text split')
    cache_key_splits = f'splits_{userId}'
    cache.set(cache_key_splits, splits, timeout=3000)  

    # #created retiever and stored in cache 
    retriever = create_retriever(embeddings, splits)
    if not retriever:
        return jsonify({'error': 'Failed to create retriever'}), 400
    logging.info('Created retriever')
    cache_key_retriever = f'retriever_{userId}'
    cache.set(cache_key_retriever, retriever, timeout=3000)

    return jsonify({'message': 'File uploaded and processed', 'splits': splits}), 200

@routes_blueprint.route('/ask', methods=['POST'])
def ask():

    logging.info('Running ask')
    data = request.get_json()
    user_question = data.get('question')

    # Check for a valid user_question
    if not user_question or user_question.strip() == '':
        return jsonify({'error': 'Invalid or empty question provided'}), 400

    # Use user-specific cache keys
    userId = request.headers.get('userId')  # Assuming you are using the same userId header as before
    cache_key_splits = f'splits_{userId}'
    cache_key_retriever = f'retriever_{userId}'

    splits = cache.get(cache_key_splits)  
    if not splits:
        return jsonify({'error': 'No document uploaded yet'}), 400

    retriever = cache.get(cache_key_retriever)

    qa = RetrievalQA.from_chain_type(llm=chat_openai, retriever=retriever, chain_type="stuff", verbose=False)
    logging.info('Prepared LLM and QA')

    # Answer the question
    answer = qa.run(user_question)
    logging.info(f'Raw answer: {answer}')

    # Check if the answer is empty
    if not answer.strip():
        return {"answer": "Sorry, I couldn't find an answer to your question."}

    # Split the answer into lines and filter out blank lines
    answer_lines = [line.strip() for line in answer.split('\n') if line.strip()]

    # Check if the first non-blank line contains "Question:", and return the next line if it does
    if answer_lines and "Question:""Q:" in answer_lines[0]:
        first_answer = answer_lines[1].replace('<|im_end|>', '').strip()  # Take the line after "Question:"
    else:
        first_answer = answer_lines[0].replace('<|im_end|>', '').strip()  # Take the first line
    
    logging.info(f'Extracted first answer: {first_answer}')
    return {"answer": first_answer}

@routes_blueprint.route('/get-questions', methods=['GET'])
def get_questions():
    logging.info('Running generate_questions')

    # Use user-specific cache keys
    userId = request.headers.get('userId')
    if not userId:
        return jsonify({'error': 'User ID not provided in the header'}), 400

    cache_key_splits = f'splits_{userId}'
    splits = cache.get(cache_key_splits)
    if not splits:
        return jsonify({'error': 'No document uploaded yet'}), 400
    
    print(splits)

    # Combine all splits to form the entire document text
    document_text = ' '.join(splits)

    try:
        # Use the new function to generate questions
        questions = get_relevant_questions(document_text, num_questions=3)
        logging.info(f'Generated questions: {questions}')
        return jsonify({
            "status": "success",
            "questions": questions
        }), 200

    except Exception as e:
        logging.error(f'Error in generate_questions: {str(e)}')
        return jsonify({"status": "error", "message": str(e)}), 500


@routes_blueprint.route('/flush', methods=['POST'])
def flush_user_data():

    userId = request.headers.get('userId')
    if not userId:
        return jsonify({'error': 'User ID not provided in the header'}), 400

    # Delete the user's data directory
    user_directory = os.path.join(UPLOAD_FOLDER, userId)
    if os.path.exists(user_directory):
        shutil.rmtree(user_directory)
        logging.info(f"Deleted directory for user {userId}")

    # Delete splits and retriever from cache using user-specific cache keys
    cache.delete(f'splits_{userId}')
    cache.delete(f'retriever_{userId}')
    logging.info(f"Cleared cache for user {userId}")

    return jsonify({'message': 'User data flushed successfully'}), 200
