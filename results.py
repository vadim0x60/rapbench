import argparse
from pathlib import Path

from transcript import parse_battle

RESULTS_BASE_URL = "https://github.com/vadim0x60/rapbench-results/blob/master"

tiers = ['SSS', 'SS', 'S', 'A', 'B', 'C', 'D', 'F', 'FF', 'FFF']


def battle_rounds(root):
    return sorted(
        (
            path
            for path in root.glob("round*")
            if path.is_dir() and any(battle.stem.isdigit() for battle in path.glob("*.txt"))
        ),
        key=lambda path: int(path.name.removeprefix("round")),
        reverse=True,
    )


def artifact_link(round_dir, filename, base_url):
    if base_url:
        return f"{base_url.rstrip('/')}/{round_dir.name}/{filename}"
    return str(round_dir / filename)


def render(root=Path("tournament"), base_url=RESULTS_BASE_URL):
    round_rosters = []
    print('## Battles')

    for round_dir in battle_rounds(root):
        print(f'Round {round_dir.name.removeprefix("round")}')
        round_rosters.append((round_dir / 'contestants.txt').read_text().splitlines())

        battle_paths = sorted(
            (path for path in round_dir.glob("*.txt") if path.stem.isdigit()),
            key=lambda path: int(path.stem),
        )
        for battle_path in battle_paths:
            left, right, _ = parse_battle(battle_path.read_text())
            verdict_path = battle_path.with_suffix(".yml")
            lyrics_link = artifact_link(round_dir, battle_path.name, base_url)
            verdict_link = artifact_link(round_dir, verdict_path.name, base_url)
            print(f'- {left} v {right} [lyrics]({lyrics_link}), [verdicts]({verdict_link})')
        print('\n')

    print('## Results')
    better_contestants = set()
    for tier, roster in zip(tiers, round_rosters):
        tier_contestants = [contestant for contestant in roster if contestant not in better_contestants]
        better_contestants.update(tier_contestants)
        links = [f'[{slug}](https://openrouter.ai/{slug})' for slug in tier_contestants]
        print(f'**{tier}**: {", ".join(links)}\n')


def main():
    parser = argparse.ArgumentParser(description="Render tournament results as Markdown")
    parser.add_argument("--root", type=Path, default=Path("tournament"))
    parser.add_argument("--local-links", action="store_true")
    args = parser.parse_args()
    render(args.root, None if args.local_links else RESULTS_BASE_URL)


if __name__ == "__main__":
    main()
