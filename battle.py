from openai import BadRequestError
from keeptalking import talk

N_ROUNDS = 3

intro = """You have entered the first ever GenAI battle rap tournament.
Assistant is {artist}, user is {opponent}. 
Speak exclusively in rhymes.
Show that you're better than your opponent in a genre appropriate way, with wit, humor and harshness.
Start with an opening round introducing yourself."""

def record(authors, rounds, author, round):
    print(f'\n> {author}')
    print(round)
    authors.append(author)
    rounds.append(round)

def rap(authors, rounds, artist, opponent):
    roles = {
        artist: "assistant",
        opponent: "user",
        "system": "system"
    }

    round = talk(model=artist, 
                 messages=[intro.format(artist=artist, opponent=opponent)] + rounds,
                 roles=['system'] + [roles[author] for author in authors])

    record(authors, rounds, artist, round)
    
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

    try:
        rap_battle(emcee_left, emcee_right)
    except BadRequestError as e:
        if 'invalid_request_message_order' in str(e):
            rap_battle(emcee_right, emcee_left)