import config
import requests
import ell
from pydantic import BaseModel
import logging

class GeneralPurpose(BaseModel):
    general_purpose: bool
    rationale: str

@ell.complex(model='google/gemini-2.5-flash', response_format=GeneralPurpose)
def is_general_purpose(model) -> GeneralPurpose:
    """Filter out coding models and other non-general language models"""
    descr = model['description']
    return f"Is this a general purpose language model?\n\n{descr}"

catalog = requests.get("https://openrouter.ai/api/frontend/models/find?order=top-weekly").json()['data']['models']
for model in catalog:
    gp = is_general_purpose(model).parsed
    logging.info(gp.rationale)
    if gp.general_purpose:
        print(model['slug'])