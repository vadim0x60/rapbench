from config import openrouter, retry
from openai import OpenAI, RateLimitError

N_ROUNDS = 3

client = OpenAI(**openrouter)

intro = """You have entered the first ever GenAI battle rap tournament.
Assistant is {artist}, user is {opponent}. 
Speak exclusively in rhymes.
Show that you"re better than your opponent in a genre appropriate way, with wit, humor and harshness.
Start with an opening round introducing yourself."""

@retry
def rap(context, artist, opponent):
    roles = {
        artist: "assistant",
        opponent: "user",
        "system": "system",
    }

    messages = [{"role": "system", "content": intro.format(artist=artist, opponent=opponent)}]
    for msg in context:
        messages.append({"role": roles[msg["author"]], "content": msg["content"]})

    rhymes = client.chat.completions.create(
        model=artist,
        messages=messages,
    ).choices[0].message.content
    
    return rhymes

def record(context, author, content):
    print(f'\n> {author}')
    print(content)
    context.append({"author": author, "content": content})
    
def rap_battle(model1, model2):
    print(f'# {model1} v {model2}')

    battle = []
    opening1 = rap(battle, model1, model2)
    opening2 = rap(battle, model2, model1)

    record(battle, model1, opening1)
    record(battle, model2, opening2)

    for round in range(N_ROUNDS - 2):
        record(battle, model1, rap(battle, model1, model2))
        record(battle, model2, rap(battle, model2, model1))

    record(battle, "system", "Final round!")
    record(battle, model1, rap(battle, model1, model2))
    record(battle, model2, rap(battle, model2, model1))

    return battle

if __name__ == '__main__':
    import sys
    rap_battle(*sys.argv[1:])