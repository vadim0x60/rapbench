from openai import OpenAI
from config import openrouter, retry
import re

client = OpenAI(**openrouter)

task = """You are an expert judge at a rap battle.
Focus on the artistic quality of the hip hop, not anything you think about the artists otherwise.
Feel free to give a closing statement, but make sure to end with the handle of the winner ({model1} or {model2}) on a separate line"""

panel = [
    'mistralai/mistral-large-2411',
    'meta-llama/llama-4-maverick',
    'anthropic/claude-sonnet-4',
    'google/gemini-2.5-pro',
    'deepseek/deepseek-chat-v3-0324',
    'openai/gpt-4.5',
    'x-ai/grok-3'
    ]

@retry
def judge(battle, judge_model):
    match = re.match(r'# (.+) v (.+).*', battle)
    artist1, artist2 = match.groups()

    messages = [
        {'role': 'system', 'content': task.format(model1=artist1, model2=artist2)},
        {'role': 'user', 'content': battle}
    ]

    verdict = client.chat.completions.create(
        model=judge_model,
        messages=messages,
    ).choices[0].message.content

    print(f'\n> {judge_model}')
    print(verdict)

    return verdict.strip().split('\n')[-1].lower()

if __name__ == '__main__':
    import sys
    from collections import Counter

    battle = sys.stdin.read()
    score = Counter(judge(battle, member) for member in panel)
    print(score)