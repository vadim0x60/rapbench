# The great LLM rap-off

Listen on [Youtube Music](https://music.youtube.com/channel/UCPZwAqbsxUiFBp4tf9mOQOQ), [Spotify](https://open.spotify.com/artist/722m0bhfIEIkxc3R0LfVEX) and other streaming platforms.

Are you frustrated by AI companies training on benchmarks? Do you enjoy battle rap? Well, both of you are at the right place. Rap battles combine debate, poetry and improvisation - the three toughest tests of verbal intelligence. State of the art in LLM evaluation. State of the art in generative poetry. The benchmark to end all benchmarks. Built with [keeptalking](https://github.com/vadim0x60/keeptalking).

## Results

The previously published tournament has been withdrawn. Validation found that the promoted contestant roster was reordered before round 2, so the resulting pairings and rankings were not valid. It will not be regenerated; the next tournament should start from a current model roster.

## Reproducibility

This repository is a [Snakemake](https://snakemake.readthedocs.io/) workflow. Install the direct dependencies and set an OpenRouter API key:

```bash
python -m pip install -r requirements.txt
export OPENROUTER_API_KEY=...
```

Clone the results repository at the workflow's output path, then preview a run without making API calls:

```bash
git clone git@github.com:vadim0x60/rapbench-results.git tournament
snakemake --dry-run --cores 1
```

For a new tournament, first remove or archive the existing round directories from the `tournament/` checkout; prior published tournaments remain available in its Git history. Then prepare only the new contestant roster and preview the expected spend:

```bash
snakemake estimate --cores 1
```

Roster preparation makes the filtering and liveness model calls, but does not start any battles or judging; its cost is not included in the estimate. The estimator itself makes no model calls: it fetches current public OpenRouter prices and shows typical and 95th-percentile visible-output estimates from historical artifacts, plus a scenario using the configured completion limits. It assumes each contestant has an equal chance to advance and does not include retries. Hidden reasoning tokens are not visible in historical artifacts, so reasoning models can push spend toward the call-limits scenario. Resolve any missing-price or unavailable-model warnings before starting the tournament. To estimate a roster stored elsewhere, run `python estimate.py path/to/contestants.txt`.

The judge panel in `judge.py` uses an odd number of the smartest models available through OpenRouter, with no more than one model from each provider. Every judge must support structured outputs and have a live, priced endpoint. Recheck those properties before each new tournament because model availability and the frontier change quickly.

After reviewing the estimate, run:

```bash
snakemake --cores all
```

Tournament generation makes paid model calls and can cost tens of dollars. Outputs and runtime logs are written to the nested, independently version-controlled `tournament/` checkout; the outer workflow repository ignores that directory, and the results repository ignores runtime logs. Validate a completed tournament locally with `python check.py`; validate a selected range with, for example, `python check.py --from-round 0 --through-round 1`. Generate the Battles and Results Markdown with `python results.py` (or add `--local-links` for local artifact links).

Published artifacts live in the nested [rapbench-results](https://github.com/vadim0x60/rapbench-results) checkout, not this workflow repository. After validation, commit each round's `contestants.txt`, numbered `.txt` transcripts, and numbered `.yml` verdicts from `tournament/`. Runtime logs remain local and ignored.

## Suno albums

A completed battle can be rendered as a six-track album: each participant round is generated separately so the voice changes between emcees, while an album manifest and M3U playlist keep the battle together. The default prompts give the left and right emcees contrasting vocal character. For stronger consistency, set distinct existing Suno Persona IDs with `SUNO_LEFT_PERSONA_ID` and `SUNO_RIGHT_PERSONA_ID` (and, for voice personas, set the corresponding `SUNO_*_PERSONA_MODEL=voice_persona`).

Suno does not currently offer a generally available official API. This workflow defaults to the third-party [sunoapi.org API](https://docs.sunoapi.org/), whose API is Suno-compatible but whose account, pricing, licensing, and commercial-use terms are separate from a Suno subscription. Verify those terms before publishing. Configure its API key and an HTTPS callback endpoint that accepts its notification POSTs (the workflow still polls for results), then request one battle's album manifest:

```bash
export SUNO_API_KEY=...
export SUNO_CALLBACK_URL=https://your-callback.example/suno
snakemake --cores 1 tournament/round0/0.suno/album.json
```

This makes six paid generation requests. Suno returns two candidates for each; variation `0` is selected by default. Set `SUNO_VARIATION=1` to select the second candidate everywhere, or use a per-track list such as `SUNO_VARIATIONS=0,1,0,0,1,0`. Set the choice before building the protected selection files. Paid submissions and WAV-conversion task IDs are separate protected Snakemake outputs, so a later polling, download, or subtitle failure can resume without generating the song again. Other settings include `SUNO_MODEL` (default `V5_5`), `SUNO_STYLE`, `SUNO_LEFT_VOICE`, `SUNO_RIGHT_VOICE`, `SUNO_API_BASE_URL`, `SUNO_POLL_INTERVAL`, and `SUNO_POLL_TIMEOUT`.

The resulting `tournament/round0/0.suno/` directory contains six numbered WAV files, source lyrics, phrase-level WebVTT and SRT subtitles, enhanced-LRC word timing, per-track provenance, `album.m3u8`, and `album.json`. Subtitle timing comes from Suno's alignment of the generated performance rather than an estimate from track duration. Review it before release: a model can skip or repeat words, and DSP synced-lyrics ingestion is separate from audio distribution.

The album manifest records AI provenance, explicit-content flags, track order, and local WAV paths with a future ONCE release in mind. It is staging metadata, not an ONCE API submission. ONCE accepts Suno tracks and multi-track releases, but cover art, release metadata, rights review, and the actual submission remain manual.
