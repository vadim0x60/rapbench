import os
from openai import OpenAI
import ell
import logging

logging.basicConfig(level=logging.INFO)

client = OpenAI(
    base_url='https://openrouter.ai/api/v1',
    api_key=os.getenv("OPENROUTER_API_KEY"),
    max_retries=50
)
ell.config.default_client = client