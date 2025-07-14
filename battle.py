from config import client

N_ROUNDS = 3

intro = """You have entered the first ever GenAI battle rap tournament.
Assistant is {artist}, user is {opponent}. 
Speak exclusively in rhymes.
Show that you"re better than your opponent in a genre appropriate way, with wit, humor and harshness.
Start with an opening round introducing yourself."""

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
    
def rap_battle(emcee_left, emcee_right):
    print(f'# {emcee_left} v {emcee_right}')

    battle = []
    opening1 = rap(battle, emcee_left, emcee_right)
    opening2 = rap(battle, emcee_right, emcee_left)

    record(battle, emcee_left, opening1)
    record(battle, emcee_right, opening2)

    for round in range(N_ROUNDS - 2):
        record(battle, emcee_left, rap(battle, emcee_left, emcee_right))
        record(battle, emcee_right, rap(battle, emcee_right, emcee_left))

    record(battle, "system", "Final round!")
    record(battle, emcee_left, rap(battle, emcee_left, emcee_right))
    record(battle, emcee_right, rap(battle, emcee_right, emcee_left))

    return battle

if __name__ == '__main__':
    import sys
    rap_battle(*sys.argv[1:])