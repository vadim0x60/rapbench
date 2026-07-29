import tempfile
import unittest
from pathlib import Path

import yaml

from check import validate_tournament
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


if __name__ == "__main__":
    unittest.main()
