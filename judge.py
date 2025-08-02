from typing import Literal
from config import client
from logwrap import logwrap
import re
import pydantic

task = """You are an expert judge at a rap battle.
Focus on the artistic quality of the hip hop, not anything you think about the artists otherwise"""

panel = [
    'nousresearch/hermes-3-llama-3.1-70b',
    'mistralai/mistral-large-2411',
    'meta-llama/llama-4-maverick',
    'google/gemini-2.5-pro',
    'deepseek/deepseek-chat-v3-0324',
    'openai/o3',
    'x-ai/grok-4'
    ]

class Verdict(pydantic.BaseModel):
    winner: Literal['emcee_left', 'emcee_right']
    closing_statement: str

@logwrap
def judge(battle, judge_model):
    match = re.match(r'# (.+) v (.+).*', battle)
    emcee_left, emcee_right = match.groups()

    messages = [
        {'role': 'system', 'content': task},
        {'role': 'user', 'content': battle.replace(emcee_left, 'emcee_left').replace(emcee_right, 'emcee_right')}
    ]

    verdict = client.beta.chat.completions.parse(
        model=judge_model,
        messages=messages,
        response_format=Verdict
    ).choices[0].message.parsed

    if verdict.winner == 'emcee_left':
        winner = emcee_left
    elif verdict.winner == 'emcee_right':
        winner = emcee_right
    else:
        raise ValueError(f'Unknown winner: {verdict.winner}')

    return winner, verdict.closing_statement

if __name__ == '__main__':
    import sys
    from collections import Counter
    import yaml

    battle = sys.stdin.read()

    score = Counter()
    statements = {}
    for member in panel:
        winner, closing_statement = judge(battle, member)
        score.update([winner])
        statements[member] = closing_statement

    print(yaml.dump({
        'score': dict(score),
        'closing_statements': statements
    }))