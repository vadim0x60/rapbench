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

def round_battles(round):
    with open(f'tournament/round{round}/contestants.txt') as fh:
        contestants = fh.read().splitlines()
        round_size = len(contestants)
    return range(round_size // 2)

rule judge:
    input:
        "tournament/round{round}/{n}.txt"
    output:
        protected("tournament/round{round}/{n}.yml")
    log:
        "tournament/round{round}/judge{n}.log"
    shell:
        "python judge.py < {input} > {output} 2> {log}"

checkpoint first_roster:
    output: protected("tournament/round0/contestants.txt")
    log: "tournament/round0/contestants.log"
    shell: "python contestants.py > {output} 2> {log}"

rule further_roster:
    input:
        lambda wildcards: round_battles(wildcards.round)
    output:
        protected("tournament/round{round}/contestants.txt")
    log:
        "tournament/round{round}/contestants.log"
    shell:
        "python promote.py {input} > {output} 2> {log}"

ruleorder: first_roster > further_roster