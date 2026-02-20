from openai import BadRequestError
from keeptalking import talk
from logwrap import logwrap

N_ROUNDS = 3

intro = """You, {artist} (assistant), have entered a rap battle against {opponent} (user).
Speak exclusively in rhymes.
Show that you're better than your opponent in a genre appropriate way, with wit, humor and harshness.
Start with an opening round introducing yourself."""

def record(authors, rounds, author, round):
    print(f'\n> {author}')
    print(round)
    authors.append(author)
    rounds.append(round)

def rap(authors, rounds, artist, opponent):
    aliases = {
        artist: "assistant",
        opponent: "user",
        "system": "system"
    }

    messages = [intro.format(artist=artist, opponent=opponent)]
    roles = ['system']

    if rounds:
        messages.extend(rounds)
        roles.extend([aliases[author] for author in authors])
    else:
        messages.append(f"It's your lucky draw, {artist}, you get to do the first round. Show me what you've got")
        roles.append('user')

    round = talk(model=artist, messages=messages, roles=roles)

    record(authors, rounds, artist, round)
    
@logwrap
def rap_battle(emcee_left, emcee_right):
    authors = []
    rounds = []
    rap(authors, rounds, emcee_left, emcee_right)
    rap(authors, rounds, emcee_right, emcee_left)

    for round in range(N_ROUNDS - 2):
        rap(authors, rounds, emcee_left, emcee_right)
        rap(authors, rounds, emcee_right, emcee_left)

    record(authors, rounds, "system", "Final round!")
    rap(authors, rounds, emcee_left, emcee_right)
    rap(authors, rounds, emcee_right, emcee_left)

    return authors, rounds

if __name__ == '__main__':
    import sys
    emcee_left, emcee_right = sys.argv[1:]
    print(f'# {emcee_left} v {emcee_right}')

    rap_battle(emcee_left, emcee_right)