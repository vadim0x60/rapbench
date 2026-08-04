python = os.getenv("PYTHON", "python")
SUNO_TRACKS = [f"{track:02d}" for track in range(1, 7)]


def suno_track_metadata(wildcards):
    return expand(
        "tournament/round{round}/{n}.suno/{track}.json",
        round=wildcards.round,
        n=wildcards.n,
        track=SUNO_TRACKS,
    )

def initial_contestants():
    out = checkpoints.first_roster.get().output[0]
    with out.open() as f:
        return f.read().splitlines()

def round_size(round):
    remaining = len(initial_contestants())
    for _ in range(int(round)):
        remaining = (remaining + 1) // 2
    return remaining

def verdicts(round):
    return [f'tournament/round{round}/{n}.yml' for n in range(round_size(round) // 2)]

def promotion_inputs(wildcards):
    previous_round = int(wildcards.round) - 1
    roster = f"tournament/round{previous_round}/contestants.txt"
    return [roster, *verdicts(previous_round)]

def tournament_files(wildcards):
    remaining = len(initial_contestants())
    round = 0
    files = ["tournament/round0/contestants.txt"]
    while remaining > 1:
        for battle_num in range(remaining // 2):
            files.extend((
                f"tournament/round{round}/{battle_num}.txt",
                f"tournament/round{round}/{battle_num}.yml",
            ))
        remaining = (remaining + 1) // 2
        round += 1
        files.append(f"tournament/round{round}/contestants.txt")
    return files

rule all:
    input:
        tournament_files

rule estimate:
    input:
        "tournament/round0/contestants.txt"
    shell:
        "{python} estimate.py {input}"

rule battle:
    input:
        "tournament/round{round}/contestants.txt"
    output:
        protected("tournament/round{round}/{n}.txt")
    log:
        "tournament/round{round}/battle{n}.log"
    shell:
        "{python} battle.py --roster {input} --battle {wildcards.n} > {output} 2> {log}"

rule judge:
    input:
        "tournament/round{round}/{n}.txt"
    output:
        protected("tournament/round{round}/{n}.yml")
    log:
        "tournament/round{round}/judge{n}.log"
    shell:
        "{python} judge.py < {input} > {output} 2> {log}"

rule suno_submit:
    input:
        battle="tournament/round{round}/{n}.txt"
    output:
        generation=protected("tournament/round{round}/{n}.suno/{track}.generation.json")
    log:
        "tournament/round{round}/{n}.suno/{track}.generation.log"
    wildcard_constraints:
        track="0[1-6]"
    shell:
        "{python} suno.py submit --battle {input.battle} --track {wildcards.track} "
        "--output {output.generation} > {log} 2>&1"

rule suno_select:
    input:
        generation="tournament/round{round}/{n}.suno/{track}.generation.json"
    output:
        selection=protected("tournament/round{round}/{n}.suno/{track}.selection.json")
    log:
        "tournament/round{round}/{n}.suno/{track}.selection.log"
    wildcard_constraints:
        track="0[1-6]"
    shell:
        "{python} suno.py select --generation {input.generation} "
        "--output {output.selection} > {log} 2>&1"

rule suno_submit_wav:
    input:
        selection="tournament/round{round}/{n}.suno/{track}.selection.json"
    output:
        task=protected("tournament/round{round}/{n}.suno/{track}.wav-task.json")
    log:
        "tournament/round{round}/{n}.suno/{track}.wav-task.log"
    wildcard_constraints:
        track="0[1-6]"
    shell:
        "{python} suno.py submit-wav --selection {input.selection} "
        "--output {output.task} > {log} 2>&1"

rule suno_track:
    input:
        selection="tournament/round{round}/{n}.suno/{track}.selection.json",
        task="tournament/round{round}/{n}.suno/{track}.wav-task.json"
    output:
        wav=protected("tournament/round{round}/{n}.suno/{track}.wav"),
        lyrics=protected("tournament/round{round}/{n}.suno/{track}.lyrics.txt"),
        vtt=protected("tournament/round{round}/{n}.suno/{track}.vtt"),
        srt=protected("tournament/round{round}/{n}.suno/{track}.srt"),
        lrc=protected("tournament/round{round}/{n}.suno/{track}.lrc"),
        metadata=protected("tournament/round{round}/{n}.suno/{track}.json")
    log:
        "tournament/round{round}/{n}.suno/{track}.track.log"
    wildcard_constraints:
        track="0[1-6]"
    shell:
        "{python} suno.py finish --selection {input.selection} --wav-task {input.task} "
        "--wav {output.wav} --lyrics {output.lyrics} --vtt {output.vtt} "
        "--srt {output.srt} --lrc {output.lrc} --metadata {output.metadata} "
        "> {log} 2>&1"

rule suno_album:
    input:
        battle="tournament/round{round}/{n}.txt",
        tracks=suno_track_metadata
    output:
        manifest=protected("tournament/round{round}/{n}.suno/album.json"),
        playlist=protected("tournament/round{round}/{n}.suno/album.m3u8")
    shell:
        "{python} suno.py album --battle {input.battle} --tracks {input.tracks} "
        "--output {output.manifest} --playlist {output.playlist}"

checkpoint first_roster:
    output: protected("tournament/round0/contestants.txt")
    log: "tournament/round0/contestants.log"
    shell: "{python} contestants.py > {output} 2> {log}"

rule further_roster:
    input:
        promotion_inputs
    output:
        protected("tournament/round{round}/contestants.txt")
    params:
        previous_round=lambda wildcards: int(wildcards.round) - 1
    log:
        "tournament/round{round}/contestants.log"
    shell:
        "{python} check.py --through-round {params.previous_round} && "
        "{python} promote.py {input} > {output} 2> {log}"

ruleorder: first_roster > further_roster
