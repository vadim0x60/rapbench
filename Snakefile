python = os.getenv("PYTHON", "python")

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
