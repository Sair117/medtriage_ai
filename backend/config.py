import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

CHAT_MODEL = "gemini-2.5-flash-lite"
REASONING_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "gemini-embedding-2-preview"

CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge_base")

MAX_CONVERSATION_TURNS = 20
TEMPERATURE_CHAT = 0.7
TEMPERATURE_REASONING = 0.2
