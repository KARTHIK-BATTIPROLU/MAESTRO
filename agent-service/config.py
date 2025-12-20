"""
MOSTRO Agent Service Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Agent configuration
    MODEL_NAME = "gemini-pro"
    TEMPERATURE = 0.7
    MAX_TOKENS = 4096
