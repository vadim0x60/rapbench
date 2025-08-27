from typing import Literal
from keeptalking import vibe
from logwrap import logwrap
import re
import pydantic
from collections import Counter
import asyncio

task = """You are an expert judge at a rap battle.
Focus on the artistic quality of the hip hop, not anything you think about the artists otherwise"""

panel = [
    'nousresearch/hermes-3-llama-3.1-70b',
    'mistralai/mistral-large-2411',
    'meta-llama/llama-4-maverick',
    'google/gemini-2.5-pro',
    'deepseek/deepseek-chat-v3-0324',
    'openai/gpt-5',
    'x-ai/grok-4'
    ]

class Verdict(pydantic.BaseModel):
    winner: Literal['emcee_left', 'emcee_right']
    closing_statement: str

@logwrap
async def judge(battle, judge_model):
    match = re.match(r'# (.+) v (.+).*', battle)
    emcee_left, emcee_right = match.groups()

    @vibe(model=judge_model)
    async def feedback(battle) -> Verdict:
        """Be an expert judge at a rap battle.
        Focus on the artistic quality of the hip hop, not anything you think about the artists otherwise"""
        return battle

    verdict = await feedback(battle.replace(emcee_left, 'emcee_left').replace(emcee_right, 'emcee_right'))

    if verdict.winner == 'emcee_left':
        winner = emcee_left
    elif verdict.winner == 'emcee_right':
        winner = emcee_right
    else:
        raise ValueError(f'Unknown winner: {verdict.winner}')

    return winner, verdict.closing_statement

async def judge_all(battle):
    score = Counter()
    statements = {}
    feedback = [(member, judge(battle, member)) for member in panel]
    for member, verdict in feedback:
        winner, closing_statement = await verdict
        score.update([winner])
        statements[member] = closing_statement

    return {
        'score': dict(score),
        'closing_statements': statements
    }

if __name__ == '__main__':
    import sys
    import yaml

    battle = sys.stdin.read()
    print(yaml.dump(asyncio.run(judge_all(battle))))