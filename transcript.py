"""Parse rap battle transcript files."""

import re


def parse_battle(text):
    """Parse a battle transcript into structured data.

    Args:
        text: Full text content of a battle .txt file.

    Returns:
        (model_left, model_right, rounds) where rounds is a list of
        (author, text) tuples. System rounds (e.g. "Final round!") are
        included with author "system".
    """
    if not text or not text.strip():
        raise ValueError("battle transcript is empty")

    lines = text.splitlines()
    match = re.fullmatch(r"#\s+(\S+/\S+)\s+v\s+(\S+/\S+)\s*", lines[0])
    if not match:
        raise ValueError("battle transcript must start with '# <model> v <model>'")

    model_left = match.group(1).strip()
    model_right = match.group(2).strip()
    participants = {model_left, model_right}

    rounds = []
    current_author = None
    current_lines = []

    for line in lines[1:]:
        header = re.fullmatch(r">\s*(\S+)\s*", line)
        author = header.group(1) if header else None
        if author == "system" or author in participants:
            if current_author is not None:
                round_text = "\n".join(current_lines).strip()
                if not round_text:
                    raise ValueError(f"round by {current_author!r} is empty")
                rounds.append((current_author, round_text))
            elif any(previous_line.strip() for previous_line in current_lines):
                raise ValueError("transcript contains text before the first author header")
            current_author = author
            current_lines = []
        else:
            current_lines.append(line)

    if current_author is None:
        raise ValueError("battle transcript contains no author rounds")

    round_text = "\n".join(current_lines).strip()
    if not round_text:
        raise ValueError(f"round by {current_author!r} is empty")
    rounds.append((current_author, round_text))

    return model_left, model_right, rounds
