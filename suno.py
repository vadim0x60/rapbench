"""Turn the six participant rounds in a battle into a Suno album."""

import argparse
import html
import json
import math
import os
import re
import tempfile
import time
from pathlib import Path

import requests

from transcript import parse_battle


DEFAULT_API_BASE_URL = "https://api.sunoapi.org"
DEFAULT_MODEL = "V5_5"
DEFAULT_STYLE = (
    "battle rap, hip-hop, hard drums, sparse beat, clear articulate lead vocal, "
    "one continuous verse, immediate vocal entrance, end immediately after the verse"
)
DEFAULT_VOICES = {
    "left": "low gravelly forceful voice",
    "right": "bright nimble cutting voice",
}
FAILED_GENERATION_STATES = {
    "CREATE_TASK_FAILED",
    "GENERATE_AUDIO_FAILED",
    "CALLBACK_EXCEPTION",
    "SENSITIVE_WORD_ERROR",
}
FAILED_WAV_STATES = {
    "CREATE_TASK_FAILED",
    "GENERATE_WAV_FAILED",
    "CALLBACK_EXCEPTION",
}
SECTION_TAG = re.compile(r"\[[^\]\n]+\]")


class SunoError(RuntimeError):
    pass


def atomic_write(path, content, mode="w"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    binary = "b" in mode
    with tempfile.NamedTemporaryFile(
        mode=mode,
        dir=path.parent,
        delete=False,
        encoding=None if binary else "utf-8",
    ) as temporary_file:
        temporary_file.write(content)
        temporary_path = Path(temporary_file.name)
    temporary_path.replace(path)


def write_json(path, value):
    atomic_write(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def read_json(path):
    with open(path, encoding="utf-8") as input_file:
        return json.load(input_file)


def battle_tracks(text):
    left, right, rounds = parse_battle(text)
    participant_rounds = [(author, lyrics) for author, lyrics in rounds if author != "system"]
    if len(participant_rounds) != 6:
        raise ValueError(f"a Suno album needs exactly 6 participant rounds, found {len(participant_rounds)}")

    tracks = []
    for number, (author, lyrics) in enumerate(participant_rounds, 1):
        if author not in (left, right):
            raise ValueError(f"round {number} has unknown author {author!r}")
        side = "left" if author == left else "right"
        tracks.append(
            {
                "track_number": number,
                "author": author,
                "side": side,
                "title": f"Round {number} — {author.rsplit('/', 1)[-1]}",
                "lyrics": lyrics,
            }
        )
    return left, right, tracks


def track_from_file(battle_path, track_number):
    text = Path(battle_path).read_text(encoding="utf-8")
    left, right, tracks = battle_tracks(text)
    if not 1 <= track_number <= len(tracks):
        raise ValueError(f"track number must be between 1 and {len(tracks)}")
    return left, right, tracks[track_number - 1]


def generation_payload(track, callback_url, model=DEFAULT_MODEL, style=DEFAULT_STYLE, persona_id=None):
    voice = os.getenv(f"SUNO_{track['side'].upper()}_VOICE", DEFAULT_VOICES[track["side"]])
    full_style = f"{style}, {voice}, no chorus, no repeated lyrics, no long intro or outro"
    prompt = f"[Verse]\n{track['lyrics']}\n[End]"
    prompt_limit = 3000 if model == "V4" else 5000
    title_limit = 80 if model in {"V4", "V4_5ALL"} else 100
    if len(prompt) > prompt_limit:
        raise ValueError(
            f"round {track['track_number']} has {len(prompt)} lyric characters; "
            f"Suno {model} accepts at most {prompt_limit}"
        )
    if len(full_style) > (200 if model == "V4" else 1000):
        raise ValueError(f"Suno style is too long for {model}")

    payload = {
        "customMode": True,
        "instrumental": False,
        "model": model,
        "title": track["title"][:title_limit],
        "style": full_style,
        "prompt": prompt,
        "negativeTags": "instrumental intro, instrumental outro, chorus, repeated lyrics, backing vocals",
        "callBackUrl": callback_url,
    }
    if persona_id:
        payload["personaId"] = persona_id
        payload["personaModel"] = os.getenv(
            f"SUNO_{track['side'].upper()}_PERSONA_MODEL", "style_persona"
        )
    return payload


class SunoClient:
    def __init__(self, api_key, base_url=DEFAULT_API_BASE_URL):
        if not api_key:
            raise SunoError("SUNO_API_KEY is required")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        self.request_timeout = float(os.getenv("SUNO_REQUEST_TIMEOUT", "60"))

    def request(self, method, path, **kwargs):
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                timeout=self.request_timeout,
                **kwargs,
            )
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError) as error:
            raise SunoError(f"Suno API request failed: {error}") from error
        if result.get("code") != 200:
            raise SunoError(f"Suno API error {result.get('code')}: {result.get('msg', 'unknown error')}")
        return result.get("data") or {}

    def submit_generation(self, payload):
        return self.request("POST", "/api/v1/generate", json=payload)["taskId"]

    def generation(self, task_id):
        return self.request("GET", "/api/v1/generate/record-info", params={"taskId": task_id})

    def timestamped_lyrics(self, task_id, audio_id):
        return self.request(
            "POST",
            "/api/v1/generate/get-timestamped-lyrics",
            json={"taskId": task_id, "audioId": audio_id},
        )

    def submit_wav(self, task_id, audio_id, callback_url):
        return self.request(
            "POST",
            "/api/v1/wav/generate",
            json={"taskId": task_id, "audioId": audio_id, "callBackUrl": callback_url},
        )["taskId"]

    def wav(self, task_id):
        return self.request("GET", "/api/v1/wav/record-info", params={"taskId": task_id})


def client_from_environment():
    return SunoClient(
        os.getenv("SUNO_API_KEY"),
        os.getenv("SUNO_API_BASE_URL", DEFAULT_API_BASE_URL),
    )


def callback_url():
    value = os.getenv("SUNO_CALLBACK_URL")
    if not value:
        raise SunoError(
            "SUNO_CALLBACK_URL is required by the Suno-compatible API even though this workflow polls"
        )
    return value


def poll(fetch, status_key, success, failed, description):
    timeout = float(os.getenv("SUNO_POLL_TIMEOUT", "1800"))
    interval = float(os.getenv("SUNO_POLL_INTERVAL", "10"))
    deadline = time.monotonic() + timeout
    while True:
        result = fetch()
        status = result.get(status_key)
        print(f"{description}: {status}", flush=True)
        if status == success:
            return result
        if status in failed:
            message = result.get("errorMessage") or "no error message returned"
            raise SunoError(f"{description} failed ({status}): {message}")
        if time.monotonic() >= deadline:
            raise SunoError(f"timed out waiting for {description} after {timeout:g} seconds")
        time.sleep(interval)


def submit_round(battle_path, track_number, output_path):
    left, right, track = track_from_file(battle_path, track_number)
    model = os.getenv("SUNO_MODEL", DEFAULT_MODEL)
    style = os.getenv("SUNO_STYLE", DEFAULT_STYLE)
    persona_id = os.getenv(f"SUNO_{track['side'].upper()}_PERSONA_ID")
    payload = generation_payload(track, callback_url(), model, style, persona_id)
    client = client_from_environment()
    task_id = client.submit_generation(payload)
    print(f"submitted track {track_number}: generation task {task_id}", flush=True)

    stored_request = {key: value for key, value in payload.items() if key != "callBackUrl"}
    write_json(
        output_path,
        {
            "schema_version": 1,
            "provider": "Suno-compatible API",
            "api_base_url": client.base_url,
            "battle": {"left": left, "right": right, "source": str(battle_path)},
            "track": track,
            "request": stored_request,
            "generation_task_id": task_id,
        },
    )


def variation_for_track(track_number):
    per_track = os.getenv("SUNO_VARIATIONS")
    if not per_track:
        return int(os.getenv("SUNO_VARIATION", "0"))
    variations = [value.strip() for value in per_track.split(",")]
    if len(variations) != 6:
        raise SunoError("SUNO_VARIATIONS must contain six comma-separated candidate indexes")
    try:
        return int(variations[track_number - 1])
    except ValueError as error:
        raise SunoError("SUNO_VARIATIONS values must be integers") from error


def select_round(generation_path, output_path):
    generation = read_json(generation_path)
    client = client_from_environment()
    task_id = generation["generation_task_id"]
    result = poll(
        lambda: client.generation(task_id),
        "status",
        "SUCCESS",
        FAILED_GENERATION_STATES,
        f"generation {task_id}",
    )
    candidates = ((result.get("response") or {}).get("sunoData") or [])
    if not candidates:
        raise SunoError("completed generation returned no tracks")
    variation = variation_for_track(generation["track"]["track_number"])
    if not 0 <= variation < len(candidates):
        raise SunoError(
            f"candidate {variation} is unavailable; generation returned {len(candidates)} tracks"
        )
    selected = candidates[variation]
    if not selected.get("id") or not selected.get("audioUrl"):
        raise SunoError("selected Suno track has no audio ID or download URL")
    generation.update(
        {
            "selected_variation": variation,
            "selected": selected,
            "candidates": candidates,
        }
    )
    write_json(output_path, generation)


def submit_wav(selection_path, output_path):
    selection = read_json(selection_path)
    wav_task_id = client_from_environment().submit_wav(
        selection["generation_task_id"], selection["selected"]["id"], callback_url()
    )
    print(f"submitted WAV conversion task {wav_task_id}", flush=True)
    write_json(
        output_path,
        {
            "schema_version": 1,
            "generation_task_id": selection["generation_task_id"],
            "audio_id": selection["selected"]["id"],
            "wav_task_id": wav_task_id,
        },
    )


def aligned_tokens(aligned_words):
    tokens = []
    for aligned_word in aligned_words:
        text = SECTION_TAG.sub("", str(aligned_word.get("word", "")))
        text = " ".join(text.split())
        try:
            start = float(aligned_word["startS"])
            end = float(aligned_word["endS"])
        except (KeyError, TypeError, ValueError):
            continue
        if not text or not math.isfinite(start) or not math.isfinite(end) or end <= start:
            continue
        tokens.append({"text": text, "start": max(0.0, start), "end": end})
    tokens.sort(key=lambda token: (token["start"], token["end"]))
    if not tokens:
        raise SunoError("Suno returned no usable lyric timestamps")
    return tokens


def subtitle_cues(tokens, max_words=9, max_duration=4.5):
    cues = []
    current = []
    word_count = 0
    for token in tokens:
        gap = token["start"] - current[-1]["end"] if current else 0
        duration = token["end"] - current[0]["start"] if current else 0
        if current and (word_count + len(token["text"].split()) > max_words or duration > max_duration or gap > 1.2):
            cues.append(current)
            current = []
            word_count = 0
        current.append(token)
        word_count += len(token["text"].split())
        if re.search(r"[.!?…][\"')\]]?$", token["text"]):
            cues.append(current)
            current = []
            word_count = 0
    if current:
        cues.append(current)
    return cues


def cue_times(cues, index):
    start = cues[index][0]["start"]
    end = cues[index][-1]["end"] + 0.12
    if index + 1 < len(cues):
        end = min(end, cues[index + 1][0]["start"])
    return start, max(start + 0.01, end)


def vtt_time(seconds):
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"


def srt_time(seconds):
    return vtt_time(seconds).replace(".", ",")


def lrc_time(seconds):
    centiseconds = round(seconds * 100)
    minutes, remainder = divmod(centiseconds, 6000)
    whole_seconds, centiseconds = divmod(remainder, 100)
    return f"{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def render_vtt(cues):
    lines = ["WEBVTT", ""]
    for index, cue in enumerate(cues):
        start, end = cue_times(cues, index)
        text = html.escape(" ".join(token["text"] for token in cue), quote=False)
        lines.extend((f"{index + 1}", f"{vtt_time(start)} --> {vtt_time(end)}", text, ""))
    return "\n".join(lines)


def render_srt(cues):
    lines = []
    for index, cue in enumerate(cues):
        start, end = cue_times(cues, index)
        text = " ".join(token["text"] for token in cue)
        lines.extend((str(index + 1), f"{srt_time(start)} --> {srt_time(end)}", text, ""))
    return "\n".join(lines)


def render_lrc(cues, title, artist, album):
    lines = [f"[ti:{title}]", f"[ar:{artist}]", f"[al:{album}]", "[by:Suno word alignment]"]
    for cue in cues:
        words = " ".join(f"<{lrc_time(token['start'])}>{token['text']}" for token in cue)
        lines.append(f"[{lrc_time(cue[0]['start'])}]{words}")
    return "\n".join(lines) + "\n"


def download_wav(url, output_path):
    try:
        with requests.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as output_file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output_file.write(chunk)
                temporary_path = Path(output_file.name)
    except requests.RequestException as error:
        raise SunoError(f"could not download generated WAV: {error}") from error
    with temporary_path.open("rb") as wav_file:
        header = wav_file.read(12)
    if len(header) != 12 or header[:4] not in (b"RIFF", b"RF64") or header[8:12] != b"WAVE":
        temporary_path.unlink(missing_ok=True)
        raise SunoError("WAV download did not contain a RIFF/RF64 WAVE file")
    temporary_path.replace(output_path)


def finish_round(selection_path, wav_task_path, outputs):
    selection = read_json(selection_path)
    wav_task = read_json(wav_task_path)
    client = client_from_environment()
    wav_result = poll(
        lambda: client.wav(wav_task["wav_task_id"]),
        "successFlag",
        "SUCCESS",
        FAILED_WAV_STATES,
        f"WAV conversion {wav_task['wav_task_id']}",
    )
    wav_url = (wav_result.get("response") or {}).get("audioWavUrl")
    if not wav_url:
        raise SunoError("completed WAV conversion returned no download URL")

    selected = selection["selected"]
    alignment = client.timestamped_lyrics(selection["generation_task_id"], selected["id"])
    tokens = aligned_tokens(alignment.get("alignedWords") or [])
    cues = subtitle_cues(tokens)
    track = selection["track"]
    album_title = f"{selection['battle']['left']} vs {selection['battle']['right']}"

    download_wav(wav_url, outputs["wav"])
    atomic_write(outputs["lyrics"], track["lyrics"].rstrip() + "\n")
    atomic_write(outputs["vtt"], render_vtt(cues))
    atomic_write(outputs["srt"], render_srt(cues))
    atomic_write(outputs["lrc"], render_lrc(cues, track["title"], track["author"], album_title))
    write_json(
        outputs["metadata"],
        {
            "schema_version": 1,
            "track_number": track["track_number"],
            "title": track["title"],
            "author": track["author"],
            "side": track["side"],
            "explicit": True,
            "ai_generated": True,
            "generator": "Suno",
            "generation_task_id": selection["generation_task_id"],
            "audio_id": selected["id"],
            "model": selected.get("modelName") or selection["request"]["model"],
            "duration_seconds": selected.get("duration"),
            "alignment_error_rate": alignment.get("hootCer"),
            "files": {name: Path(path).name for name, path in outputs.items() if name != "metadata"},
        },
    )


def write_album(battle_path, track_paths, output_path, playlist_path):
    left, right, source_tracks = battle_tracks(Path(battle_path).read_text(encoding="utf-8"))
    tracks = sorted((read_json(path) for path in track_paths), key=lambda track: track["track_number"])
    if [track["track_number"] for track in tracks] != list(range(1, 7)):
        raise ValueError("album metadata must contain tracks 1 through 6 exactly once")
    for expected, actual in zip(source_tracks, tracks):
        if (expected["track_number"], expected["author"]) != (
            actual["track_number"],
            actual["author"],
        ):
            raise ValueError("track metadata does not match the battle transcript")

    album_title = f"{left} vs {right}"
    album_artist = os.getenv("SUNO_ALBUM_ARTIST", "Rapbench")
    manifest = {
        "schema_version": 1,
        "release_type": "album",
        "title": album_title,
        "album_artist": album_artist,
        "explicit": True,
        "ai_generated": True,
        "generator": "Suno",
        "source_battle": str(battle_path),
        "participants": [left, right],
        "track_count": 6,
        "tracks": tracks,
        "publishing": {
            "target": "ONCE",
            "status": "not submitted",
            "note": "Review metadata and add square cover art before distribution.",
        },
    }
    write_json(output_path, manifest)

    playlist = ["#EXTM3U"]
    for track in tracks:
        duration = round(track["duration_seconds"] or -1)
        playlist.extend((f"#EXTINF:{duration},{track['title']}", track["files"]["wav"]))
    atomic_write(playlist_path, "\n".join(playlist) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    submit_parser = subparsers.add_parser("submit", help="submit one participant round")
    submit_parser.add_argument("--battle", type=Path, required=True)
    submit_parser.add_argument("--track", type=int, required=True)
    submit_parser.add_argument("--output", type=Path, required=True)

    select_parser = subparsers.add_parser("select", help="wait for and select one variation")
    select_parser.add_argument("--generation", type=Path, required=True)
    select_parser.add_argument("--output", type=Path, required=True)

    wav_parser = subparsers.add_parser("submit-wav", help="submit the selected variation for WAV")
    wav_parser.add_argument("--selection", type=Path, required=True)
    wav_parser.add_argument("--output", type=Path, required=True)

    finish_parser = subparsers.add_parser("finish", help="download WAV and render timed lyrics")
    finish_parser.add_argument("--selection", type=Path, required=True)
    finish_parser.add_argument("--wav-task", type=Path, required=True)
    finish_parser.add_argument("--wav", type=Path, required=True)
    finish_parser.add_argument("--lyrics", type=Path, required=True)
    finish_parser.add_argument("--vtt", type=Path, required=True)
    finish_parser.add_argument("--srt", type=Path, required=True)
    finish_parser.add_argument("--lrc", type=Path, required=True)
    finish_parser.add_argument("--metadata", type=Path, required=True)

    album_parser = subparsers.add_parser("album", help="group six finished rounds as an album")
    album_parser.add_argument("--battle", type=Path, required=True)
    album_parser.add_argument("--tracks", type=Path, nargs=6, required=True)
    album_parser.add_argument("--output", type=Path, required=True)
    album_parser.add_argument("--playlist", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "submit":
        submit_round(args.battle, args.track, args.output)
    elif args.command == "select":
        select_round(args.generation, args.output)
    elif args.command == "submit-wav":
        submit_wav(args.selection, args.output)
    elif args.command == "finish":
        finish_round(
            args.selection,
            args.wav_task,
            {
                "wav": args.wav,
                "lyrics": args.lyrics,
                "vtt": args.vtt,
                "srt": args.srt,
                "lrc": args.lrc,
                "metadata": args.metadata,
            },
        )
    else:
        write_album(args.battle, args.tracks, args.output, args.playlist)


if __name__ == "__main__":
    main()
