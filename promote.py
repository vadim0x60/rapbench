def winner(verdict_path):
    with open(verdict_path) as fh:
        score = yaml.full_load(fh)['score']
        return max(score, key=score.get)

if __name__ == '__main__':
    import sys
    for verdict_path in sys.argv[1:]:
        print(winner(verdict_path))