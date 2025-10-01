from typing import Literal
from keeptalking import vibe
import re
import pydantic
from collections import Counter
import asyncio

task = """You are an expert judge at a rap battle.
Focus on the artistic quality of the hip hop, not anything you think about the artists otherwise"""

# The Rules (tm):
# - Latest standard non-reasoning model from each lab
# (reasoning models go over any token limit you set)
# - Odd number of judges to avoid ties
panel = [
    'mistralai/mistral-large',
    'google/gemini-2.5-pro',
    'deepseek/deepseek-chat',
    'openai/gpt-5-chat',
    'x-ai/grok-4'
    ]

async def judge_all(battle):
    match = re.match(r'# (.+) v (.+).*', battle)
    emcee_left, emcee_right = match.groups()

    class Verdict(pydantic.BaseModel):
        winner: Literal[emcee_left, emcee_right]
        closing_statement: str

    verdicts = {}
    for judge_model in panel:
        @vibe(model=judge_model)
        async def judge(battle) -> Verdict:
            """Be an expert judge at a rap battle.
            Focus on the artistic quality of the hip hop, not anything you think about the artists otherwise"""
            return battle

        verdicts[judge_model] = judge(battle)
        
    score = Counter()
    statements = {}
    
    for judge_model, verdict in verdicts.items():
        verdict = await verdict
        score.update([verdict.winner])
        statements[judge_model] = verdict.closing_statement

    return {
        'score': dict(score),
        'closing_statements': statements
    }

if __name__ == '__main__':
    import sys
    import yaml

    battle = sys.stdin.read()
    print(yaml.dump(asyncio.run(judge_all(battle))))