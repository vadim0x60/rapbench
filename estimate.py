"""Estimate OpenRouter spend for a tournament roster without making model calls."""

import argparse
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import ceil
from pathlib import Path

import requests

from battle import MAX_VERSE_TOKENS, N_ROUNDS, intro
from check import read_roster
from judge import MAX_VERDICT_TOKENS, panel, task


MODEL_CATALOG_URL = "https://openrouter.ai/api/v1/models"
CHARS_PER_TOKEN = 4
MESSAGE_OVERHEAD_TOKENS = 4
REPLY_PRIMER_TOKENS = 3
STRUCTURED_OUTPUT_OVERHEAD_TOKENS = 100
FINAL_MARKER = "Final round!"


@dataclass(frozen=True)
class TokenAssumptions:
    name: str
    verse: int
    verdict: int


# The first two profiles are calibrated from visible text in the published
# rapbench-results artifacts. The third exposes the configured call limits.
PROFILES = (
    TokenAssumptions("Typical", verse=225, verdict=160),
    TokenAssumptions("P95 visible", verse=500, verdict=525),
    TokenAssumptions(
        "Call limits",
        verse=MAX_VERSE_TOKENS,
        verdict=MAX_VERDICT_TOKENS,
    ),
)


@dataclass(frozen=True)
class Price:
    prompt: Decimal
    completion: Decimal
    request: Decimal = Decimal(0)

    def cost(self, prompt_tokens, completion_tokens):
        return (
            self.request
            + self.prompt * prompt_tokens
            + self.completion * completion_tokens
        )


@dataclass(frozen=True)
class Estimate:
    rounds: int
    battles: int
    rapper_calls: int
    judge_calls: int
    rapper_cost: Decimal
    judge_cost: Decimal
    missing_models: tuple[str, ...]

    @property
    def total(self):
        return self.rapper_cost + self.judge_cost


def approximate_tokens(text):
    """Approximate provider tokenization using the usual four-char heuristic."""
    return ceil(len(text) / CHARS_PER_TOKEN)


def message_tokens(text):
    return approximate_tokens(text) + MESSAGE_OVERHEAD_TOKENS


def parse_prices(models):
    """Extract non-negative text pricing from an OpenRouter model catalog."""
    prices = {}
    for model in models:
        pricing = model.get("pricing", {})
        try:
            price = Price(
                prompt=Decimal(pricing["prompt"]),
                completion=Decimal(pricing["completion"]),
                request=Decimal(pricing.get("request", 0)),
            )
        except (InvalidOperation, KeyError, TypeError):
            continue
        if min(price.prompt, price.completion, price.request) < 0:
            continue
        prices[model["id"]] = price
    return prices


def fetch_prices():
    response = requests.get(MODEL_CATALOG_URL, timeout=30)
    response.raise_for_status()
    return parse_prices(response.json()["data"])


def battle_prompt_tokens(turn, artist, opponent, verse_tokens):
    """Estimate input tokens for one sequential rapper turn."""
    total = REPLY_PRIMER_TOKENS + message_tokens(
        intro.format(artist=artist, opponent=opponent)
    )
    if turn == 0:
        total += message_tokens(
            f"It's your lucky draw, {artist}, you get to do the first round. "
            "Show me what you've got"
        )
    else:
        total += turn * (verse_tokens + MESSAGE_OVERHEAD_TOKENS)

    if turn >= 2 * (N_ROUNDS - 1):
        total += message_tokens(FINAL_MARKER)
    return total


def transcript_tokens(left, right, verse_tokens):
    fixed_text = f"# {left} v {right}\n"
    for turn in range(2 * N_ROUNDS):
        if turn == 2 * (N_ROUNDS - 1):
            fixed_text += f"\n> system\n{FINAL_MARKER}\n"
        artist = left if turn % 2 == 0 else right
        fixed_text += f"\n> {artist}\n"
    return approximate_tokens(fixed_text) + 2 * N_ROUNDS * verse_tokens


def judge_prompt_tokens(left, right, verse_tokens):
    return (
        REPLY_PRIMER_TOKENS
        + message_tokens(task)
        + transcript_tokens(left, right, verse_tokens)
        + MESSAGE_OVERHEAD_TOKENS
        + STRUCTURED_OUTPUT_OVERHEAD_TOKENS
    )


def model_call_cost(prices, model, prompt_tokens, completion_tokens):
    price = prices.get(model)
    if price is None:
        return Decimal(0)
    return price.cost(prompt_tokens, completion_tokens)


def pair_cost(left, right, prices, assumptions, judge_models):
    rapper_cost = Decimal(0)
    for turn in range(2 * N_ROUNDS):
        artist, opponent = (left, right) if turn % 2 == 0 else (right, left)
        rapper_cost += model_call_cost(
            prices,
            artist,
            battle_prompt_tokens(turn, artist, opponent, assumptions.verse),
            assumptions.verse,
        )

    judge_input = judge_prompt_tokens(left, right, assumptions.verse)
    judge_cost = sum(
        (
            model_call_cost(
                prices,
                judge_model,
                judge_input,
                assumptions.verdict,
            )
            for judge_model in judge_models
        ),
        Decimal(0),
    )
    return rapper_cost, judge_cost


def merged_winner_distribution(left, right):
    winner = defaultdict(Decimal)
    for model, probability in left.items():
        winner[model] += probability / 2
    for model, probability in right.items():
        winner[model] += probability / 2
    return dict(winner)


def estimate_tournament(contestants, prices, assumptions, judge_models=panel):
    """Estimate cost, treating either contestant as equally likely to advance."""
    positions = [{model: Decimal(1)} for model in contestants]
    rapper_cost = Decimal(0)
    judge_cost = Decimal(0)
    battles = 0
    rounds = 0

    while len(positions) > 1:
        round_size = len(positions)
        battle_count = round_size // 2
        next_positions = positions[:1] if round_size % 2 else []

        for battle_number in range(battle_count):
            left = positions[round_size % 2 + battle_number]
            right = positions[round_size - battle_count + battle_number]
            for left_model, left_probability in left.items():
                for right_model, right_probability in right.items():
                    probability = left_probability * right_probability
                    pair_rapper_cost, pair_judge_cost = pair_cost(
                        left_model,
                        right_model,
                        prices,
                        assumptions,
                        judge_models,
                    )
                    rapper_cost += probability * pair_rapper_cost
                    judge_cost += probability * pair_judge_cost
            next_positions.append(merged_winner_distribution(left, right))

        battles += battle_count
        rounds += 1
        positions = next_positions

    required_models = set(contestants) | set(judge_models)
    missing_models = tuple(sorted(required_models - prices.keys()))
    return Estimate(
        rounds=rounds,
        battles=battles,
        rapper_calls=battles * 2 * N_ROUNDS,
        judge_calls=battles * len(judge_models),
        rapper_cost=rapper_cost,
        judge_cost=judge_cost,
        missing_models=missing_models,
    )


def money(value):
    return f"${value:,.2f}"


def print_report(roster_path, contestants, estimates):
    representative = estimates[0]
    print(f"Tournament cost preview for {len(contestants)} contestants")
    print(f"Roster: {roster_path}")
    print(
        f"Plan: {representative.rounds} rounds, {representative.battles} battles, "
        f"{representative.rapper_calls} rapper calls, {representative.judge_calls} judge calls"
    )
    print("Pricing: current OpenRouter model catalog (USD)")
    print()

    heading = f"{'':24}" + "".join(f"{profile.name:>16}" for profile in PROFILES)
    print(heading)
    print(
        f"{'Verse tokens/call':24}"
        + "".join(f"{profile.verse:>16,}" for profile in PROFILES)
    )
    print(
        f"{'Verdict tokens/call':24}"
        + "".join(f"{profile.verdict:>16,}" for profile in PROFILES)
    )
    print(
        f"{'Rapper generation':24}"
        + "".join(f"{money(estimate.rapper_cost):>16}" for estimate in estimates)
    )
    print(
        f"{'Judging':24}"
        + "".join(f"{money(estimate.judge_cost):>16}" for estimate in estimates)
    )
    total_label = "Known-price subtotal" if representative.missing_models else "Estimated total"
    print(
        f"{total_label:24}"
        + "".join(f"{money(estimate.total):>16}" for estimate in estimates)
    )

    if representative.missing_models:
        print("\nWARNING: no current OpenRouter text price was found for:")
        for model in representative.missing_models:
            roles = []
            if model in contestants:
                roles.append("contestant")
            if model in panel:
                roles.append("judge")
            print(f"  - {model} ({', '.join(roles)})")
        print("The subtotals exclude those calls; an unavailable model can also stop the run.")

    print(
        "\nAssumptions: four characters per input token, equal chance to advance, "
        "and no retries. Billable hidden reasoning is not visible in historical "
        "artifacts and can move actual spend toward the call-limits scenario. "
        "Roster filtering and liveness calls are not included."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roster",
        nargs="?",
        type=Path,
        default=Path("tournament/round0/contestants.txt"),
    )
    args = parser.parse_args()

    if not args.roster.exists():
        parser.error(
            f"roster not found: {args.roster}; prepare it with "
            "'snakemake --cores 1 tournament/round0/contestants.txt'"
        )

    contestants = read_roster(args.roster)
    prices = fetch_prices()
    estimates = [
        estimate_tournament(contestants, prices, profile)
        for profile in PROFILES
    ]
    print_report(args.roster, contestants, estimates)


if __name__ == "__main__":
    main()
