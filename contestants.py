from collections import OrderedDict
import requests
from keeptalking import vibe
import asyncio
import config
import logging
import openai

@vibe()
async def is_general_purpose(descr) -> bool:
    """Filter out coding models, non-text models, language-specific and other non-general language models"""
    return f"Is this a general purpose language model?\n\n{descr}"

async def is_alive(slug):
    @vibe(model=slug)
    async def greet():
        """Greeting test to check if the LLM is alive"""
        return "Hi!"

    try:
        logging.info(await greet())
        return True
    except (openai.NotFoundError, openai.InternalServerError, openai.BadRequestError):
        return False

async def contestants():
    models = requests.get("https://openrouter.ai/api/frontend/models/find?order=top-weekly").json()['data']['models']
    models = OrderedDict([(model['slug'], model) for model in models]).values()
    models = [(model, is_general_purpose(model['description'])) for model in models]
    models = (model for model, general_purpose in models if await general_purpose)
    models = [(model, is_alive(model['slug'])) async for model in models]
    models = (model for model, alive in models if await alive)

    async for model in models:
        print(model['slug'])

if __name__ == '__main__':  
    asyncio.run(contestants())