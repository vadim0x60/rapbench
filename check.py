"""Validate generated tournament artifacts without making network requests."""

import argparse
from pathlib import Path

import yaml

from transcript import parse_battle


def pairing(contestants, battle_number):
    """Return the Dutch-system pairing for a numbered battle."""
    round_size = len(contestants)
    left = round_size % 2 + battle_number
    right = round_size - round_size // 2 + battle_number
    return contestants[left], contestants[right]


def read_roster(path):
    contestants = path.read_text().splitlines()
    if not contestants or any(not contestant.strip() for contestant in contestants):
        raise ValueError(f"{path}: roster is empty or contains blank model names")
    if len(contestants) != len(set(contestants)):
        raise ValueError(f"{path}: roster contains duplicate model names")
    return contestants


def read_verdict(path, participants):
    try:
        verdict = yaml.safe_load(path.read_text())
    except yaml.YAMLError as error:
        raise ValueError(f"{path}: invalid YAML: {error}") from error

    if not isinstance(verdict, dict) or not isinstance(verdict.get("score"), dict) or not verdict["score"]:
        raise ValueError(f"{path}: verdict must contain a non-empty score mapping")

    score = verdict["score"]
    if not set(score).issubset(participants):
        raise ValueError(f"{path}: score contains a model that did not participate")
    if any(type(votes) is not int or votes < 0 for votes in score.values()):
        raise ValueError(f"{path}: score values must be non-negative integers")
    if sum(score.values()) != 5:
        raise ValueError(f"{path}: expected 5 judge votes, got {sum(score.values())}")
    return score


def validate_round(root, round_number):
    round_dir = root / f"round{round_number}"
    roster_path = round_dir / "contestants.txt"
    contestants = read_roster(roster_path)
    battle_count = len(contestants) // 2

    expected_numbers = set(range(battle_count))
    for suffix in ("txt", "yml"):
        actual_numbers = {
            int(path.stem)
            for path in round_dir.glob(f"*.{suffix}")
            if path.stem.isdigit()
        }
        if actual_numbers != expected_numbers:
            raise ValueError(
                f"{round_dir}: expected {suffix} battle files {sorted(expected_numbers)}, "
                f"got {sorted(actual_numbers)}"
            )

    winners = []
    for battle_number in range(battle_count):
        battle_path = round_dir / f"{battle_number}.txt"
        expected_pairing = pairing(contestants, battle_number)
        try:
            left, right, rounds = parse_battle(battle_path.read_text())
        except ValueError as error:
            raise ValueError(f"{battle_path}: {error}") from error
        if (left, right) != expected_pairing:
            raise ValueError(
                f"{battle_path}: expected pairing {expected_pairing}, got {(left, right)}"
            )

        rapper_rounds = [(author, text) for author, text in rounds if author != "system"]
        if len(rapper_rounds) != 6:
            raise ValueError(
                f"{battle_path}: expected 6 rapper rounds, got {len(rapper_rounds)}"
            )

        verdict_path = round_dir / f"{battle_number}.yml"
        score = read_verdict(verdict_path, set(expected_pairing))
        winners.append(max(score, key=score.get))

    return contestants[:1] + winners if len(contestants) % 2 else winners


def available_rounds(root):
    return sorted(
        int(path.name.removeprefix("round"))
        for path in root.glob("round*")
        if path.is_dir() and path.name.removeprefix("round").isdigit()
    )


def validate_tournament(root=Path("tournament"), first_round=None, last_round=None):
    root = Path(root)
    rounds = available_rounds(root)
    if not rounds:
        raise ValueError(f"{root}: no tournament rounds found")

    first_round = rounds[0] if first_round is None else first_round
    last_round = rounds[-1] if last_round is None else last_round
    selected = list(range(first_round, last_round + 1))
    missing = [round_number for round_number in selected if round_number not in rounds]
    if missing:
        raise ValueError(f"{root}: missing rounds {missing}")

    expected_roster = None
    if first_round > 0:
        expected_roster = validate_round(root, first_round - 1)

    for round_number in selected:
        roster_path = root / f"round{round_number}" / "contestants.txt"
        if expected_roster is not None:
            actual_roster = read_roster(roster_path)
            if actual_roster != expected_roster:
                raise ValueError(f"{roster_path}: roster does not match promoted winners in exact order")
        expected_roster = validate_round(root, round_number)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-round", type=int, dest="first_round")
    parser.add_argument("--through-round", type=int, dest="last_round")
    parser.add_argument("--root", type=Path, default=Path("tournament"))
    args = parser.parse_args()
    validate_tournament(args.root, args.first_round, args.last_round)


if __name__ == "__main__":
    main()
