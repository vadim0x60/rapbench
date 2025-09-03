import yaml
import config
import logging

def winner(verdict_path):
    with open(verdict_path) as fh:
        score = yaml.full_load(fh)['score']
        return max(score, key=score.get)

if __name__ == '__main__':
    import sys
    
    with open(sys.argv[1], 'r') as f:
        contestants = f.readlines()

    if len(contestants) % 2:
        # If the number of contestants is odd, the most popular model on openrouter gets promoted without a battle
        print(contestants[0])

    for verdict_path in sys.argv[2:]:
        print(winner(verdict_path))