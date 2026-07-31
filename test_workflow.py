import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import yaml

from check import validate_tournament
from estimate import Price, TokenAssumptions, estimate_tournament, parse_prices
from judge import panel
from transcript import parse_battle


LEFT = "lab/left"
RIGHT = "lab/right"
SILENCE = "[Stands on stage nervously looking at the crowd. Stays completely silent (inference API returned no tokens)]"


def transcript(left=LEFT, right=RIGHT, verse="line one\nline > inside a verse"):
    sections = [f"# {left} v {right}"]
    for round_number in range(3):
        sections.extend((f"> {left}", SILENCE if round_number == 1 else verse))
        if round_number == 2:
            sections.extend(("> system", "Final round!"))
        sections.extend((f"> {right}", verse))
    return "\n\n".join(sections) + "\n"


class TranscriptTests(unittest.TestCase):
    def test_parses_six_turns_final_marker_silence_and_multiline_verses(self):
        left, right, rounds = parse_battle(transcript())

        self.assertEqual((left, right), (LEFT, RIGHT))
        self.assertEqual(sum(author != "system" for author, _ in rounds), 6)
        self.assertIn(("system", "Final round!"), rounds)
        self.assertIn((LEFT, SILENCE), rounds)
        self.assertIn("line > inside a verse", rounds[0][1])

    def test_model_like_quote_inside_verse_is_not_an_author_header(self):
        _, _, rounds = parse_battle(transcript(verse="setup\n> other/model\npunchline"))

        self.assertIn("> other/model", rounds[0][1])

    def test_rejects_empty_and_malformed_input_with_useful_errors(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            parse_battle("")
        with self.assertRaisesRegex(ValueError, "must start"):
            parse_battle("not a battle")


class TournamentValidationTests(unittest.TestCase):
    def test_judge_panel_is_odd_and_has_unique_providers(self):
        providers = [model.partition("/")[0] for model in panel]

        self.assertEqual(len(panel) % 2, 1)
        self.assertEqual(len(providers), len(set(providers)))

    def test_validates_pairings_votes_and_exact_promotion_order(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            round0 = root / "round0"
            round1 = root / "round1"
            round0.mkdir()
            round1.mkdir()
            contestants = ["lab/bye", LEFT, RIGHT]
            (round0 / "contestants.txt").write_text("\n".join(contestants) + "\n")
            (round0 / "0.txt").write_text(transcript())
            (round0 / "0.yml").write_text(yaml.safe_dump({"score": {LEFT: 3, RIGHT: 2}}))

            (round1 / "contestants.txt").write_text(f"lab/bye\n{LEFT}\n")
            (round1 / "0.txt").write_text(transcript("lab/bye", LEFT))
            (round1 / "0.yml").write_text(yaml.safe_dump({"score": {"lab/bye": 2, LEFT: 3}}))

            validate_tournament(root)

    def test_rejects_incomplete_verdict(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            round0 = root / "round0"
            round0.mkdir()
            (round0 / "contestants.txt").write_text(f"{LEFT}\n{RIGHT}\n")
            (round0 / "0.txt").write_text(transcript())
            (round0 / "0.yml").write_text(yaml.safe_dump({"score": {LEFT: 1}}))

            with self.assertRaisesRegex(ValueError, "expected 5 judge votes"):
                validate_tournament(root)


class CostEstimationTests(unittest.TestCase):
    def test_counts_calls_and_models_byes_and_winners_as_coin_flips(self):
        prices = {
            "lab/bye": Price(Decimal(0), Decimal(1)),
            LEFT: Price(Decimal(0), Decimal(2)),
            RIGHT: Price(Decimal(0), Decimal(4)),
        }
        assumptions = TokenAssumptions("test", verse=1, verdict=0)

        estimate = estimate_tournament(
            ["lab/bye", LEFT, RIGHT], prices, assumptions, judge_models=()
        )

        self.assertEqual(estimate.rounds, 2)
        self.assertEqual(estimate.battles, 2)
        self.assertEqual(estimate.rapper_calls, 12)
        self.assertEqual(estimate.judge_calls, 0)
        # First battle: 3*2 + 3*4 = 18. Final: 3*1 plus an
        # equal-chance LEFT/RIGHT winner costing 3*(2+4)/2 = 9.
        self.assertEqual(estimate.rapper_cost, Decimal(30))

    def test_reports_models_without_current_pricing(self):
        assumptions = TokenAssumptions("test", verse=1, verdict=1)

        estimate = estimate_tournament(
            [LEFT, RIGHT],
            {LEFT: Price(Decimal(0), Decimal(1))},
            assumptions,
            judge_models=("lab/judge",),
        )

        self.assertEqual(estimate.missing_models, ("lab/judge", RIGHT))
        self.assertGreater(estimate.total, 0)

    def test_includes_every_judge_call(self):
        assumptions = TokenAssumptions("test", verse=0, verdict=3)
        prices = {
            LEFT: Price(Decimal(0), Decimal(0)),
            RIGHT: Price(Decimal(0), Decimal(0)),
            "lab/judge": Price(Decimal(0), Decimal(2)),
        }

        estimate = estimate_tournament(
            [LEFT, RIGHT], prices, assumptions, judge_models=("lab/judge",)
        )

        self.assertEqual(estimate.judge_calls, 1)
        self.assertEqual(estimate.judge_cost, Decimal(6))

    def test_ignores_router_and_incomplete_prices(self):
        prices = parse_prices(
            [
                {"id": "lab/valid", "pricing": {"prompt": "0.1", "completion": "0.2"}},
                {"id": "lab/router", "pricing": {"prompt": "-1", "completion": "-1"}},
                {"id": "lab/missing", "pricing": {"prompt": "0.1"}},
            ]
        )

        self.assertEqual(set(prices), {"lab/valid"})


if __name__ == "__main__":
    unittest.main()
