from openai import OpenAI
from config import openrouter, retry
import re

client = OpenAI(**openrouter)

task = """You are an expert judge at a rap battle
Decide who won, {model1} or {model2}.
In your closing statement, mention the handle of the winner, do not mention the loser's handle.
Focus on the artistic quality of the hip hop, not anything you think about the artists otherwise"""

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

    print(verdict)

    if artist1 in verdict:
        return artist1
    elif artist2 in verdict:
        return artist2
    else:
        raise ValueError(f"Judge {judge_model} could not decide between {artist1} and {artist2}")

if __name__ == '__main__':
    import sys
    judge(sys.stdin.read(), sys.argv[1])