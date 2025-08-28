python = os.getenv("PYTHON", "python")

def emcee_left(round_size, battle_num):
    """Pick the stronger participant from the rating according to the Dutch system"""
    round_size = int(round_size)
    battle_num = int(battle_num)

    return round_size % 2 + battle_num

def emcee_right(round_size, battle_num):
    """Pick the weaker participant from the rating according to the Dutch system"""
    round_size = int(round_size)
    battle_num = int(battle_num)

    return round_size - round_size // 2 + battle_num

def contestants(round):
    if round == 0:
        out = checkpoints.first_roster.get().output[0]
    else:
        out = checkpoints.further_roster.get(round=round).output[0]
    
    with out.open() as f:
        return f.readlines()

def verdicts(round):
    return [f'tournament/round{round}/{n}.yml' for n in range(len(contestants(round)) // 2)]

def roster(wildcards):
    round = wildcards.round
    battle_num = wildcards.n
    emcees = contestants(round)

    return {'emcee_left': emcees[emcee_left(len(emcees), battle_num)].strip(), 
            'emcee_right': emcees[emcee_right(len(emcees), battle_num)].strip()}

rule battle:
    input:
        "tournament/round{round}/contestants.txt"
    output:
        protected("tournament/round{round}/{n}.txt")
    params:
        roster
    log:
        "tournament/round{round}/battle{n}.log"
    shell:
        "{python} battle.py {params[0][emcee_left]} {params[0][emcee_right]} > {output} 2> {log}"

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

checkpoint further_roster:
    input:
        lambda wildcards: verdicts(int(wildcards.round) - 1)
    output:
        protected("tournament/round{round}/contestants.txt")
    log:
        "tournament/round{round}/contestants.log"
    shell:
        "{python} promote.py {input} > {output} 2> {log}"

ruleorder: first_roster > further_roster