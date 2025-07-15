import os
from dotenv import load_dotenv

# --- Project Metadata ---
__version__ = "2.2.0"
__author__ = "aidreama"
__license__ = "MIT"


# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# --- General Configuration ---
SECRET_KEY = os.getenv('SECRET_KEY', 'a-default-secret-key-for-development')
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DEBUG = FLASK_ENV == 'development'
PORT = int(os.getenv('PORT', 8888))

# --- Database Configuration ---
# Example: DATABASE_URL=mysql+pymysql://user:password@host/dbname
DATABASE_URL = os.getenv('DATABASE_URL')

# --- API Keys ---
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
SERP_API_KEY = os.getenv('SERP_API_KEY') # 新增

# --- LLM Model Configuration ---
OPENAI_API_URL = os.getenv('OPENAI_API_URL', 'https://api.openai.com/v1')
OPENAI_API_MODEL = os.getenv('OPENAI_API_MODEL', 'gpt-4o')
FUNCTION_CALL_MODEL = os.getenv('FUNCTION_CALL_MODEL', 'gpt-4o')
MAX_QA_ROUNDS = os.getenv('MAX_QA_ROUNDS', 10)

# --- Model Paths ---
# Example: SCENARIO_MODEL_PATH=./models/scenario_predictor.pkl
SCENARIO_MODEL_PATH = os.getenv('SCENARIO_MODEL_PATH')

# --- Cache Configuration ---
# Example: CACHE_TYPE=redis
# Example: CACHE_REDIS_URL=redis://localhost:6379/0
CACHE_TYPE = os.getenv('CACHE_TYPE', 'SimpleCache')  # Default to in-memory cache
CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))
CACHE_REDIS_URL = os.getenv('CACHE_REDIS_URL')

print("Configuration loaded:")
print(f"  - DATABASE_URL: {'*' * 8 if DATABASE_URL else 'Not Set'}")
print(f"  - OPENAI_API_KEY: {'*' * 8 if OPENAI_API_KEY else 'Not Set'}") 