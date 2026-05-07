import os

from dotenv import load_dotenv
from openai import AsyncOpenAI


load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://tokenrai.com/v1/chat/completions")
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-v4-flash")
if not DEEPSEEK_BASE_URL.endswith("chat/completions"):
    DEEPSEEK_BASE_URL = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
