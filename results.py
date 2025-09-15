import glob
from pathlib import Path
import os

N_ROUNDS = int(os.getenv('N_ROUNDS'))

tiers = ['SSS', 'SS', 'S', 'A', 'B', 'C', 'D', 'F', 'FF', 'FFF']
contestants = []

print('## Battles')

for round in reversed(range(N_ROUNDS)):
    print(f'Round {round}')
    round_dir = Path(f'tournament/round{round}')
    with open(round_dir / 'contestants.txt') as f:
        contestants.append(f.read().splitlines())

    battle_n = 0
    while True:
        try:
            battle_path = round_dir / f'{battle_n}.txt'
            verdict_path = round_dir / f'{battle_n}.yml'
            with open(battle_path) as f:
                battle_title = f.read().splitlines()[0][2:]
                print(f'- {battle_title} [lyrics]({battle_path}), [verdicts]({verdict_path})')
        except FileNotFoundError:
            break
        battle_n += 1

print('## Results')

better_contestants = set()

for tier, contestants in zip(tiers, contestants):
    contestants = set(contestants)
    contestants -= better_contestants
    better_contestants.update(contestants)
    contestants = [f'[{slug}](https://openrouter.ai/{slug})' for slug in contestants]
    contestants = ', '.join(contestants)
    print(f'**{tier}**: {contestants}\n')