from glob import glob

for battle_path in glob('tournament/round*/*.txt'):
    if battle_path.endswith('contestants.txt'):
        continue
    with open(battle_path) as battle_f:
        assert battle_f.read().count('\n>') == 7, battle_path