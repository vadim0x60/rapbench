import re
from glob import glob

for battle_path in glob('tournament/round*/*.txt'):
    if battle_path.endswith('contestants.txt'):
        continue
    with open(battle_path) as battle_f:
        content = battle_f.read()
        prompts = re.findall(r'^\> \S+/\S+', content, re.MULTILINE)
        assert len(prompts) == 6, f"{battle_path}: expected 7 prompts, got {len(prompts)}"
