import os
import logging
from dotenv import load_dotenv
from azure.ai.formrecognizer import FormRecognizerClient
from azure.core.credentials import AzureKeyCredential
from langchain.llms import AzureOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings

load_dotenv()

logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler("app.log"), logging.StreamHandler()])
azure_endpoint = os.environ.get('AZURE_ENDPOINT')
azure_api_key = os.environ.get('AZURE_KEY')
client = FormRecognizerClient(azure_endpoint, AzureKeyCredential(azure_api_key))
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize embeddings
embeddings = OpenAIEmbeddings(
                openai_api_key=OPENAI_API_KEY,
                deployment="embeddings_model", 
                model="text-embedding-ada-002",
                openai_api_type='azure',
                chunk_size=1
            )

# Initialize AzureAi
chat_openai = AzureOpenAI(
            openai_api_key=OPENAI_API_KEY,
            deployment_name="reviews_analysis_bot",
            model_name="gpt_35_turbo", 
            openai_api_version= "2023-05-15" 
        )

UPLOAD_FOLDER = 'upload'
ALLOWED_EXTENSIONS = {'txt', 'pdf'}

from flask_caching import Cache

# Other config variables ...

CACHE_TYPE = 'simple'
cache = Cache(config={'CACHE_TYPE': CACHE_TYPE})