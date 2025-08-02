import config
import requests
import ell
from pydantic import BaseModel
import logging
import yaml

class GeneralPurpose(BaseModel):
    general_purpose: bool
    rationale: str

@ell.complex(model='google/gemini-2.5-flash', response_format=GeneralPurpose)
def is_general_purpose(model) -> GeneralPurpose:
    """Filter out coding models and other non-general language models"""
    descr = model['description']
    return f"Is this a general purpose language model?\n\n{descr}"

def greet():
    """Greeting test to check if the LLM is alive"""
    return "Hi!"

def alive(model):
    try:
        logging.info(ell.simple(model=model)(greet)())
        return True
    except (openai.NotFoundError, openai.InternalServerError):
        return False

def round_sizes(contestants):
    round_sizes = []
    round_size = len(contestants)
    while round_size > 1:
        round_sizes.append(round_size)
        round_size = round_size - round_size // 2

    return round_sizes

catalog = requests.get("https://openrouter.ai/api/frontend/models/find?order=top-weekly").json()['data']['models']
contestants = []
for model in catalog:
    gp = is_general_purpose(model).parsed
    logging.info(gp.rationale)
    if gp.general_purpose and alive(model['slug']):
        contestants.append(model)

print(yaml.dump({
    'contestants': contestants,
    'rounds': round_sizes(contestants)
}))