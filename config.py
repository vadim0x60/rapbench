import os
import tenacity as t
from openai import RateLimitError

retry = t.retry(
    stop=t.stop_after_attempt(5),
    wait=t.wait_random_exponential(),
    retry=t.retry_if_exception_type(RateLimitError))

openrouter = {
    'base_url': 'https://openrouter.ai/api/v1',
    'api_key': os.getenv("OPENROUTER_API_KEY")
}