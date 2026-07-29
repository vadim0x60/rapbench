# Rapbench transition and tournament repair plan

## Goal

Finish the split between the workflow repository (`rapbench`) and the generated-data repository (`rapbench-results`), make the workflow reproducible, and correct the February 2026 tournament from the first known inconsistency.

The round-2 and round-3 roster reordering was not intentional. Round 1 and its verdicts are therefore the last authoritative point in the existing tournament. `round2/contestants.txt` must be regenerated in `promote.py` order, and all battles and verdicts from round 2 onward must be regenerated because roster order determines subsequent pairings.

Do not rerun round 0 or round 1.

## Desired repository boundaries

### `rapbench`

Keep:

- Snakemake workflow and Python source
- dependency declarations
- generated-results presentation code
- README and reproducibility instructions
- tests and lightweight fixtures

Do not track:

- `tournament/` outputs
- Snakemake state
- runtime logs
- local environment files

### `rapbench-results`

Keep the published tournament artifacts:

- contestant rosters
- battle transcripts
- verdict YAML files

Do not publish runtime logs unless there is a specific reason to preserve them. Existing logs contain stack traces and provider/user metadata, even though no API keys were found.

## Phase 1: stabilize the workflow before spending API credits

1. Fix `final_winner_file()` in `Snakefile`.
   - Replace the natural-log calculation with a base-2 calculation, or derive the terminal round by repeatedly applying the tournament's promotion rule until one contestant remains.
   - Avoid requiring NumPy solely for this calculation.
   - Verify that 161 initial contestants resolve to `tournament/round8/contestants.txt`, not round 6.

2. Finish the shared transcript parser.
   - Add `transcript.py` to the source tree.
   - Keep `judge.py`, `check.py`, and `results.py` on the shared parser.
   - Add tests covering:
     - a normal six-turn battle;
     - the `> system` final-round marker;
     - the silent-turn placeholder;
     - multiline verses, including lines containing `>` that are not author headers;
     - malformed or empty input with a useful error.

3. Strengthen tournament validation.
   - Retain the existing check for exactly six rapper turns per transcript.
   - Validate that each transcript's two model names match the pairing calculated from that round's roster.
   - Validate that each verdict has a non-empty `score`, contains only the two battle participants, and totals the expected five judge votes.
   - Validate that each next-round roster equals the previous round's promoted roster in exact order, not merely as a set.
   - Make validation usable for a selected range of rounds so the preserved rounds 0 and 1 can be checked independently from regenerated downstream rounds.

4. Make generation failures explicit and recoverable.
   - Keep the current silent-turn policy for expected provider failures unless deliberately changing tournament policy.
   - Remove the duplicate `openai.NotFoundError` from `provider_tantrums`.
   - Review the February logs and include the provider exceptions that should count as a silent turn, without swallowing programming errors or malformed local data.
   - Ensure failed judge jobs cannot leave a syntactically valid-looking but incomplete YAML output.

5. Repair direct dependencies.
   - Add direct runtime dependencies such as `loguru` and `requests` to `requirements.txt`.
   - Remove the NumPy dependency from the workflow if the final-round fix makes it unnecessary.
   - Test installation and imports in a clean environment.

6. Add a no-cost workflow check.
   - Run Python compilation and parser/validation tests.
   - Run a Snakemake dry run against a small fixture tournament or mocked commands.
   - Confirm that `rule all` follows checkpoints through to a one-contestant roster.
   - Confirm that generating a roster does not accidentally pass `contestants.txt` as a verdict file, as happened in the February checkpoint logs.

## Phase 2: finalize the results-repository split

1. Update `results.py` so generated Markdown uses the public `rapbench-results` base URL directly.
   - Prefer a named constant or command-line option over a post-generation search-and-replace.
   - Keep an option for local relative links if useful during development.
   - Infer the available rounds or accept an explicit argument instead of requiring an undocumented `N_ROUNDS` environment variable.

2. Stop tracking generated tournament data in `rapbench`.
   - Preserve the local files until the corrected results have been verified and published.
   - Remove `tournament/` from the main repository's tracked contents while retaining it in `.gitignore` as local workflow output.
   - Do not delete the working copy as part of the untracking operation.

3. Clean the result export.
   - Copy only rosters, transcripts, and verdicts into `rapbench-results`.
   - Remove or exclude `battle*.log`, `judge*.log`, and `contestants.log` from future exports.
   - Add an ignore file or export script so logs are not republished accidentally.
   - Publish corrected results as a normal follow-up commit; do not rewrite the already-pushed result repository history.

## Phase 3: reconstruct the tournament from the authoritative boundary

### Preserve rounds 0 and 1

1. Validate all round-0 and round-1 transcripts and verdicts with the strengthened checks.
2. Treat the existing `round1/*.yml` files as the authoritative inputs to promotion.
3. Back up or retain a reference to the currently published downstream artifacts before replacing them.

### Regenerate round 2

1. Generate a new `round2/contestants.txt` by running `promote.py` over:
   - `round1/contestants.txt`; and
   - every round-1 verdict in numeric battle order.
2. Verify exact ordered equality between the new roster and an independently calculated promotion result.
3. Confirm that the roster still contains 41 unique contestants.
4. Remove or move aside the stale round-2 through round-8 outputs before running Snakemake. Merely replacing the roster is insufficient because protected downstream files may otherwise prevent regeneration or be considered up to date.
5. Regenerate all 20 round-2 battles and verdicts using the corrected roster order.

### Regenerate rounds 3 through 8

1. Let the corrected workflow promote round-2 winners in deterministic verdict order.
2. Generate every downstream battle, verdict, and roster through a one-contestant round-8 roster.
3. Do not manually shuffle or reseed between rounds.
4. Expect approximately 40 regenerated battles in total:
   - round 2: 20
   - round 3: 10
   - round 4: 5
   - round 5: 3
   - round 6: 1
   - round 7: 1
5. Each battle invokes both contestants and five judges, so estimate and approve API cost before starting the live run.

### Validate the corrected tournament

Require all of the following before publication:

- roster sizes are `161, 81, 41, 21, 11, 6, 3, 2, 1`;
- every roster has unique model names;
- every battle uses the exact pairing implied by its roster and battle number;
- every transcript contains six rapper turns;
- every verdict contains five valid votes for the two participants;
- every next-round roster exactly matches `promote.py` output, including order;
- the final roster contains exactly one champion;
- a clean Snakemake dry run reports nothing left to generate;
- rerunning all local validators makes no network requests and succeeds.

## Phase 4: publish corrected results and documentation

1. Export the corrected roster, transcript, and verdict files to `rapbench-results`.
2. Verify the exported files byte-for-byte against the validated local tournament, excluding logs and Snakemake metadata.
3. Commit and push the correction to `rapbench-results` as a new commit that explains:
   - rounds 0 and 1 were preserved;
   - an unintended winner-roster reorder was found before round 2;
   - rounds 2 onward were regenerated with deterministic promotion order.
4. Generate the `rapbench` README's Battles and Results sections from the corrected artifacts.
5. Verify every README battle label against the linked transcript header.
6. Remove the accidental `Merge branch 'master'...` text currently embedded in the rankings.
7. Incorporate the remote README change removing the monthly-release promise.
8. Update reproducibility documentation with:
   - the actual install command;
   - required environment variables;
   - the correct Snakemake invocation;
   - expected API cost and the fact that outputs are written under ignored `tournament/`;
   - how to validate and export results.

## Phase 5: organize and publish `rapbench`

Keep the final history reviewable. A reasonable sequence is:

1. Existing judge-panel and provider-resilience commits.
2. Shared transcript parsing and validation.
3. Reproducible terminal-round and checkpoint fixes.
4. Results-repository split and removal of generated files from main-repository tracking.
5. Corrected generated README and documentation.
6. Dependency cleanup.

Before pushing:

- reconcile the one remote-only README commit;
- ensure no secrets, local environment files, logs, or generated tournament artifacts are included in `rapbench`;
- run source tests, tournament validation, Python compilation, and a Snakemake dry run;
- inspect both repository diffs independently;
- verify that GitHub links resolve to the corrected `rapbench-results` files.

## Explicit non-goals

- Do not rerun rounds 0 or 1 without discovering a separate correctness problem in them.
- Do not preserve the accidental round-2/3 ordering merely to retain the current downstream outcome.
- Do not edit verdicts or rosters by hand to force the existing champion to remain unchanged.
- Do not rewrite the public `rapbench-results` Git history.
- Do not treat generated transcript whitespace as source-code formatting debt.

## Definition of done

- `rapbench` contains only workflow/source/documentation files and can reproduce a tournament through one champion.
- `rapbench-results` contains a validated, corrected tournament with no runtime logs.
- The corrected round-2 roster is the deterministic output of round-1 verdicts.
- Every later roster, pairing, transcript, and verdict descends from that corrected order.
- The README is generated from and accurately links to the corrected public results.
- Local and remote `rapbench` history are reconciled and all intended commits are pushed.
