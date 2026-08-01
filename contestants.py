from collections import OrderedDict
import requests
from keeptalking import vibe
from logwrap import logwrap
import asyncio
from config import provider_tantrums
import logging

exclude = ['switchpoint/router']
MODEL_CATALOG_URL = "https://openrouter.ai/api/v1/models?sort=top-weekly"

@logwrap()
async def can_rap(slug):
    @vibe(model=slug)
    async def audition():
        """You are about to enter a rap battle tournament as a contestant."""
        return "Write exactly two original English lines introducing yourself as a rapper. Return only those two lines."

    try:
        response = await audition()
        logging.info(response)
        return bool(response and response.strip())
    except (TypeError, *provider_tantrums):
        return False

async def contestants():
    response = requests.get(MODEL_CATALOG_URL, timeout=30)
    response.raise_for_status()
    models = response.json()['data']
    models = OrderedDict([(model['id'], model) for model in models]).values()
    models = (model for model in models
              if model['id'] not in exclude
              and not model['id'].startswith(('~', 'openrouter/')))
    models = [(model, can_rap(model['id'])) for model in models]
    models = (model for model, capable in models if await capable)

    async for model in models:
        print(model['id'])

if __name__ == '__main__':  
    asyncio.run(contestants())
