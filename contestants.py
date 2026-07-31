from collections import OrderedDict
import requests
from keeptalking import vibe
from logwrap import logwrap
import asyncio
from config import provider_tantrums
import logging

exclude = ['openrouter/auto', 'switchpoint/router']
MODEL_CATALOG_URL = "https://openrouter.ai/api/v1/models?sort=top-weekly"

@vibe()
async def is_general_purpose(descr) -> bool:
    """Filter out coding models, non-text models, language-specific and other non-general language models"""
    return f"Is this a general purpose language model?\n\n{descr}"

@logwrap()
async def is_alive(slug):
    @vibe(model=slug)
    async def greet():
        """Greeting test to check if the LLM is alive"""
        return "Hi!"

    try:
        logging.info(await greet())
        return True
    except (TypeError, *provider_tantrums):
        return False

async def contestants():
    response = requests.get(MODEL_CATALOG_URL, timeout=30)
    response.raise_for_status()
    models = response.json()['data']
    models = OrderedDict([(model['id'], model) for model in models]).values()
    models = (model for model in models
              if model['id'] not in exclude and not model['id'].startswith('~'))
    models = [(model, is_general_purpose(model['description'])) for model in models]
    models = (model for model, general_purpose in models if await general_purpose)
    models = [(model, is_alive(model['id'])) async for model in models]
    models = (model for model, alive in models if await alive)

    async for model in models:
        print(model['id'])

if __name__ == '__main__':  
    asyncio.run(contestants())
