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

To preview a run without making API calls:

```bash
snakemake --dry-run --cores 1
```

For a new tournament, first remove or archive any existing `tournament/` directory outside this repository. Then prepare only the new contestant roster and preview the expected spend:

```bash
snakemake estimate --cores 1
```

Roster preparation makes the filtering and liveness model calls, but does not start any battles or judging; its cost is not included in the estimate. The estimator itself makes no model calls: it fetches current public OpenRouter prices and shows typical and 95th-percentile visible-output estimates from historical artifacts, plus a scenario using the configured completion limits. It assumes each contestant has an equal chance to advance and does not include retries. Hidden reasoning tokens are not visible in historical artifacts, so reasoning models can push spend toward the call-limits scenario. Resolve any missing-price or unavailable-model warnings before starting the tournament. To estimate a roster stored elsewhere, run `python estimate.py path/to/contestants.txt`.

The judge panel in `judge.py` uses an odd number of the smartest models available through OpenRouter, with no more than one model from each provider. Every judge must support structured outputs and have a live, priced endpoint. Recheck those properties before each new tournament because model availability and the frontier change quickly.

After reviewing the estimate, run:

```bash
snakemake --cores all
```

Tournament generation makes paid model calls and can cost tens of dollars. Outputs and runtime logs are written under the ignored `tournament/` directory. Validate a completed tournament locally with `python check.py`; validate a selected range with, for example, `python check.py --from-round 0 --through-round 1`. Generate the Battles and Results Markdown with `python results.py` (or add `--local-links` for local artifact links).

Published artifacts live in [rapbench-results](https://github.com/vadim0x60/rapbench-results), not this workflow repository. After validation, copy only each round's `contestants.txt`, numbered `.txt` transcripts, and numbered `.yml` verdicts there. Do not copy runtime logs.
