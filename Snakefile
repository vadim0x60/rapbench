import yaml

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

def first_round_roster(wildcards):
    with checkpoints.tournament.get().output[0].open('r') as tournament:
        tournament = yaml.safe_load(tournament)
        contestants = tournament['contestants']
        round_size = tournament['rounds'][0]
    return {
        'emcee_right': contestants[emcee_right(round_size, wildcards.n)],
        'emcee_left': contestants[emcee_left(round_size, wildcards.n)]
        }

def parent_battles(wildcards):
    round = int(wildcards.round)
    prev_round = round - 1

    with checkpoints.tournament.get().output[0].open('r') as tournament:
        tournament = yaml.safe_load(tournament)
        round_size = tournament['rounds'][prev_round]

    return [
        f"tournament/round{prev_round}/{emcee_left(round_size, wildcards.n)}.yml",
        f"tournament/round{prev_round}/{emcee_right(round_size, wildcards.n)}.yml"
    ]

def winner(battle_verdict):
    print(battle_verdict)
    with open(battle_verdict) as fh:
        score = yaml.full_load(fh)['score']
        return max(score, key=score.get)

rule first_battle:
    input:
        "tournament/tournament.yml"
    params:
        first_round_roster
    output:
        protected("tournament/round0/{n}.txt")
    log:
        "tournament/round0/{n}.log"
    priority: 1
    shell:
        "python battle.py {params[0][emcee_left]} {params[0][emcee_right]} > {output} 2> {log}"

rule further_battle:
    input:
        "tournament/tournament.yml",
        parent_battles
    params:
        emcee_left=lambda wildcards, input: winner(input),
        emcee_right=lambda wildcards, input: winner(input)
    output:
        protected("tournament/round{round}/{n}.txt")
    log:
        "tournament/round{round}/{n}.log"
    shell:
        "python battle.py {params.emcee_left} {params.emcee_right} > {output} 2> {log}"

rule judge:
    input:
        "tournament/round{round}/{n}.txt"
    output:
        protected("tournament/round{round}/{n}.yml")
    log:
        "tournament/round{round}/judge{n}.log"
    shell:
        "python judge.py < {input} > {output} 2> {log}"

checkpoint tournament:
    output: protected("tournament/tournament.yml")
    log: "tournament/tournament.log"
    shell: "python contestants.py > {output} 2> {log}"

ruleorder: first_battle > further_battle