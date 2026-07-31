from typing import Literal
from keeptalking import vibe
from transcript import parse_battle
import pydantic
from collections import Counter
import asyncio
import tenacity as t
import openai

task = """You are an expert judge at a rap battle.
Focus on the artistic quality of the hip hop, not anything you think about the artists otherwise"""

# An odd number of the smartest available models, with at most one per provider.
# All judges must be live on OpenRouter and support structured outputs.
panel = [
    'openai/gpt-5.6-sol-pro',
    'anthropic/claude-opus-5',
    'google/gemini-3.6-flash',
    'x-ai/grok-4.5',
    'moonshotai/kimi-k3',
    ]
MAX_VERDICT_TOKENS = 5000

async def judge_all(battle):
    emcee_left, emcee_right, _ = parse_battle(battle)

    class Verdict(pydantic.BaseModel):
        winner: Literal[emcee_left, emcee_right]
        closing_statement: str

    verdicts = {}
    for judge_model in panel:
        @t.retry(retry=t.retry_if_exception_type(openai.LengthFinishReasonError), 
                 stop=t.stop_after_attempt(3),
                 wait=t.wait_random_exponential(max=float('inf')))
        @vibe(model=judge_model, tokens=MAX_VERDICT_TOKENS)
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
